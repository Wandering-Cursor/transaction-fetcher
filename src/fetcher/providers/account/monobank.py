import datetime
from decimal import Decimal

import pydantic
import pydantic.alias_generators
import pytz

from fetcher.enums.transaction import TransactionType
from fetcher.providers.account.base import BaseAccountProvider, BaseAccountProviderConfiguration
from fetcher.repository import settings
from fetcher.schemas.account import BalanceSchema
from fetcher.schemas.base import BaseSchema
from fetcher.schemas.transaction import TransactionSchema
from fetcher.services.currency import get_currency_by_numerical_code
from fetcher.utils import amount_with_sign

monobank_timezone = pytz.timezone("UTC")


class MonoBankProviderConfiguration(BaseAccountProviderConfiguration):
    account_id: str
    api_token: str

    use_to_timestamp: bool = False


class BaseMonoBankSchema(BaseSchema):
    model_config = pydantic.ConfigDict(
        alias_generator=pydantic.AliasGenerator(
            validation_alias=pydantic.alias_generators.to_camel,
        )
    )


class MonoBankAccountSchema(BaseMonoBankSchema):
    id: str
    balance: int
    credit_limit: int | None = None
    currency_code: int

    def to_balance_schema(self) -> "BalanceSchema":
        return BalanceSchema(
            end_balance=Decimal(self.balance) / 100,
            at_time=datetime.datetime.now(tz=settings.settings.default_timezone),
        )


class MonoBankClientInfoSchema(BaseMonoBankSchema):
    client_id: str
    name: str
    accounts: list[MonoBankAccountSchema]
    jars: list[MonoBankAccountSchema]

    def find_account_by_id(self, account_id: str) -> MonoBankAccountSchema | None:
        for account in self.accounts:
            if account.id == account_id:
                return account
        for jar in self.jars:
            if jar.id == account_id:
                return jar

        return None


class MonoBankTransaction(BaseMonoBankSchema):
    id: str
    time: int
    description: str
    mcc: int
    original_mcc: int | None = None
    hold: bool
    amount: int
    operation_amount: int | None = None
    currency_code: int
    commission_rate: int | None = None
    cashback_amount: int | None = None
    balance: int
    comment: str | None = None
    receipt_id: str | None = None
    invoice_id: str | None = None
    counter_edrpou: str | None = None
    counter_iban: str | None = None
    counter_name: str | None = None

    model_config = pydantic.ConfigDict(
        alias_generator=pydantic.AliasGenerator(
            validation_alias=pydantic.alias_generators.to_camel,
        )
    )

    def to_transaction_schema(self) -> TransactionSchema:
        description = ""

        if self.description:
            # Using both latin and cyrillic i letters
            if self.description.startswith("Від: ") or self.description.startswith("Вiд: "):  # noqa: RUF001
                description += f"{self.description}\n"
            else:
                description += f"Опис: {self.description}\n"
        if self.comment:
            description += f"Коментар: {self.comment}\n"

        description = description.strip()

        amount = self.amount

        if self.operation_amount is not None and self.operation_amount != self.amount:
            amount = self.operation_amount
            description += f"\nСума в оригінальній валюті: {amount_with_sign(round(Decimal(self.amount) / 100, 2))}"  # noqa: E501, RUF001

        return TransactionSchema(
            unique_id=self.id,
            type=TransactionType.DEPOSIT if amount > 0 else TransactionType.WITHDRAWAL,
            amount=Decimal(amount) / 100,
            currency=get_currency_by_numerical_code(
                self.currency_code,
            ),
            description=description,
            at_time=datetime.datetime.fromtimestamp(
                self.time,
                tz=monobank_timezone,
            ).astimezone(
                settings.settings.default_timezone,
            ),
        )


class MonoBankProvider(BaseAccountProvider):
    @property
    def base_url(self) -> str:
        return "https://api.monobank.ua"

    @property
    def account_id(self) -> str:
        return self.configuration.account_id

    @property
    def auth_headers(self) -> dict[str, str]:
        return {
            "X-Token": self.configuration.api_token,
        }

    def get_configuration_type(self) -> MonoBankProviderConfiguration:
        return MonoBankProviderConfiguration

    @property
    def configuration(self) -> MonoBankProviderConfiguration:
        return self._configuration

    def get_transactions(self) -> list["TransactionSchema"]:
        to_time = datetime.datetime.now(tz=datetime.UTC)
        from_time = to_time - datetime.timedelta(seconds=self._account.interval_seconds)

        path_arguments = [
            self.account_id,
            int(from_time.timestamp()),
        ]

        if self.configuration.use_to_timestamp:
            path_arguments.append(
                int(to_time.timestamp()),
            )

        path = "/personal/statement/"

        path += "/".join(map(str, path_arguments))

        response = self.http_client.get(
            url=path,
            headers=self.auth_headers,
        )
        response.raise_for_status()

        response_data = response.json()

        monobank_transactions = [
            MonoBankTransaction.model_validate(transaction) for transaction in response_data
        ]

        return [transaction.to_transaction_schema() for transaction in monobank_transactions]

    def get_balance(self) -> "BalanceSchema | None":
        path = "/personal/client-info"

        response = self.http_client.get(
            url=path,
            headers=self.auth_headers,
        )
        response.raise_for_status()

        response_data = response.json()

        client_info = MonoBankClientInfoSchema.model_validate(response_data)
        account = client_info.find_account_by_id(account_id=self.account_id)

        if not account:
            return None

        balance = account.to_balance_schema()
        balance.currency = account.currency_code

        return balance
