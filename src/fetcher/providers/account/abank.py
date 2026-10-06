import base64
import datetime
import json
from decimal import Decimal
from uuid import uuid4

import httpx
import pydantic
import pytz
import rsa

from fetcher.enums.transaction import TransactionType
from fetcher.logger import main_logger
from fetcher.providers.account.base import BaseAccountProvider, BaseAccountProviderConfiguration
from fetcher.schemas.account import BalanceSchema
from fetcher.schemas.base import BaseSchema
from fetcher.schemas.transaction import TransactionSchema

abank_timezone = pytz.timezone("Europe/Kyiv")


class ABankProviderConfiguration(BaseAccountProviderConfiguration):
    system: str
    api_key: str
    iban: str
    private_key_base64: str

    @property
    def private_key(self) -> bytes:
        return base64.b64decode(self.private_key_base64)


class BaseABankRequestSchema(BaseSchema):
    request_ref: pydantic.UUID4 = pydantic.Field(
        default_factory=uuid4,
    )
    token: str


class ABankTransactionsRequestSchema(BaseABankRequestSchema):
    iban: str

    date_from: datetime.datetime
    date_to: datetime.datetime

    @pydantic.field_serializer(
        "date_from",
        "date_to",
        when_used="json",
    )
    def serialize_datetime(self, value: datetime.datetime) -> str:
        return value.strftime("%Y-%m-%d %H:%M:%S")


class ABankAccount(BaseSchema):
    iban: str
    name: str


class ABankTransaction(BaseSchema):
    payment_id: int | str
    date_change: datetime.datetime
    description: str = pydantic.Field(alias="title")
    amount: Decimal = pydantic.Field(alias="amount_eq")
    currency: int
    debit: ABankAccount
    credit: ABankAccount

    def to_transaction_schema(self, own_iban: str) -> "TransactionSchema":
        return TransactionSchema(
            unique_id=str(self.payment_id),
            at_time=self.date_change.astimezone(abank_timezone),
            description=self.description,
            amount=self.amount,
            type=(
                TransactionType.DEPOSIT
                if self.credit.iban == own_iban
                else TransactionType.WITHDRAWAL
            ),
            currency_code=self.currency,
        )


class ABankTransactionsResponseSchema(BaseSchema):
    payments: list[ABankTransaction]


class ABankAccount(BaseSchema):
    iban: str
    balance_available: Decimal


class ABankCompany(BaseSchema):
    accounts: list[ABankAccount]


class ABankAccountListResponseSchema(BaseSchema):
    companies: list[ABankCompany]


class ABankProvider(BaseAccountProvider):
    @property
    def base_url(self) -> str:
        return "https://open-api.a-bank.com.ua/legal-entity"

    @property
    def iban(self) -> str:
        return self.configuration.iban

    def get_configuration_type(self) -> ABankProviderConfiguration:
        return ABankProviderConfiguration

    @property
    def configuration(self) -> ABankProviderConfiguration:
        return self._configuration

    def _make_signature(self, body: dict) -> tuple[str, bytes]:
        """Returns a prepared signature and body for the request."""
        post_body = json.dumps(body, separators=(",", ":")).encode("utf-8")

        private_key = rsa.PrivateKey.load_pkcs1(
            self.configuration.private_key,
        )

        return rsa.sign(post_body, private_key, "SHA-1").hex(), post_body

    def _headers(self) -> dict:
        return {
            "system": self.configuration.system,
            "Content-Type": "application/json",
        }

    def make_request(
        self,
        method: str,
        endpoint: str,
        body: BaseSchema | None = None,
    ) -> "httpx.Response":
        headers = self._headers()

        headers["signature"], body_bytes = self._make_signature(
            body=body.model_dump(
                mode="json",
            )
        )

        return self.http_client.request(
            method=method,
            url=endpoint,
            content=body_bytes,
            headers=headers,
        )

    def get_transactions(self) -> list["TransactionSchema"]:
        to_time = datetime.datetime.now(tz=abank_timezone)
        from_time = to_time - datetime.timedelta(
            seconds=self._account.interval_seconds,
        )

        request_data = ABankTransactionsRequestSchema(
            token=self.configuration.api_key,
            iban=self.iban,
            date_from=from_time,
            date_to=to_time,
        )

        response = self.make_request(
            method="POST",
            endpoint="/payments-list",
            body=request_data,
        )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            main_logger.error(
                {
                    "msg": "Failed to get transactions",
                    "status_code": response.status_code,
                    "response": response.content,
                }
            )
            raise e

        response_data = ABankTransactionsResponseSchema.model_validate(response.json())

        return [
            transaction.to_transaction_schema(
                own_iban=self.iban,
            )
            for transaction in response_data.payments
        ]

    def get_balance(self) -> "BalanceSchema | None":
        accounts_response = self.make_request(
            method="POST",
            endpoint="/accounts-list",
            body=BaseABankRequestSchema(
                token=self.configuration.api_key,
            ),
        )

        accounts_response.raise_for_status()

        accounts_response_data = ABankAccountListResponseSchema.model_validate(
            accounts_response.json(),
        )

        filename = f"/tmp/abank_{self._account.id}_balance"

        try:
            with open(filename) as f:
                data = f.read()
                last_balance = Decimal(data) if data else Decimal(0)
        except FileNotFoundError:
            last_balance = Decimal(0)

        for company in accounts_response_data.companies:
            for account in company.accounts:
                if account.iban == self.iban:
                    with open(filename, "w") as f:
                        f.write(str(account.balance_available))

                    return BalanceSchema(
                        currency=980,  # Assuming UAH
                        start_balance=last_balance,
                        end_balance=account.balance_available,
                        deposited=None,
                        withdrawn=None,
                        at_time=datetime.datetime.now(tz=abank_timezone),
                    )

        return None
