import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import uuid4
from xml.etree import ElementTree as ET

import pydantic
import pytz
from zeep import Client

from fetcher.enums.transaction import TransactionType
from fetcher.logger import main_logger
from fetcher.providers.account.base import BaseAccountProvider
from fetcher.schemas.account import BalanceSchema
from fetcher.schemas.base import BaseSchema
from fetcher.schemas.transaction import TransactionSchema
from fetcher.services.currency import get_currency_by_alpha_code

if TYPE_CHECKING:
    from fetcher.models.account import AccountModel

nova_pay_timezone = pytz.timezone("Europe/Kyiv")

CONDUCTED = 8


class ResponseError(Exception):
    response: dict
    message: str

    def __init__(self, response: dict, message: str) -> None:
        self.response = response
        self.message = message

        super().__init__(message)

    def __str__(self) -> str:
        return f"ResponseError({self.message=}, {self.response=})"


class NovaPayProviderConfiguration(BaseSchema):
    account_id: str
    login: str
    refresh_token: str
    public_certificate: str

    jwt: str | None = None
    expiration: str | None = None


class NovaPayPaymentType(StrEnum):
    DEBIT = "Debit"
    CREDIT = "Credit"

    @property
    def as_transaction_type(self) -> TransactionType:
        if self == NovaPayPaymentType.DEBIT:
            return TransactionType.WITHDRAWAL
        if self == NovaPayPaymentType.CREDIT:
            return TransactionType.DEPOSIT

        raise ValueError(f"Unknown payment type: {self}")


class NovaPayTransactionSchema(BaseSchema):
    amount: Decimal
    currency_name: str

    code: str
    purpose: str
    payment_type: NovaPayPaymentType
    status_document_id: int

    changed: datetime.datetime

    def to_transaction_schema(self) -> "TransactionSchema":
        currency = get_currency_by_alpha_code(
            alpha_code=self.currency_name,
        )

        return TransactionSchema(
            unique_id=self.code,
            amount=self.amount,
            currency=currency,
            type=self.payment_type.as_transaction_type,
            at_time=self.changed,
            description=self.purpose,
        )

    @pydantic.field_validator(
        "changed",
        mode="before",
    )
    @classmethod
    def validate_changed(cls, value: str) -> datetime.datetime:
        return nova_pay_timezone.localize(
            datetime.datetime.strptime(  # noqa: DTZ007
                value,
                "%d.%m.%Y %H:%M:%S",
            )
        )


class NovaPayProvider(BaseAccountProvider):
    def __init__(self, account: "AccountModel") -> None:
        super().__init__(account=account)

        self.client = Client("https://business.novapay.ua/Services/ClientAPIService.svc?wsdl")

    @property
    def base_url(self) -> str:
        return "https://business.novapay.ua"

    @property
    def configuration(self) -> "NovaPayProviderConfiguration":
        return self._configuration

    def get_configuration_type(self) -> "type[NovaPayProviderConfiguration]":
        return NovaPayProviderConfiguration

    def get_transactions(self) -> list["TransactionSchema"]:
        current_time = datetime.datetime.now(tz=nova_pay_timezone)
        date_from = current_time - datetime.timedelta(
            seconds=self._account.interval_seconds,
        )

        response = self.client.service.GetPaymentsList(
            {
                "request_ref": str(uuid4()),
                "jwt": self.configuration.jwt,
                # "account_id": self.configuration.account_id,
                "date_from": date_from.strftime("%d.%m.%Y"),
                "date_to": current_time.strftime("%d.%m.%Y"),
            }
        )

        transactions_data = response["payments"]

        if transactions_data is None:
            main_logger.warning(
                f"No transactions data received from NovaPay\nResponse: {str(response)[:256]}"
            )
            return []

        transactions = ET.fromstring(transactions_data)

        transactions = [
            NovaPayTransactionSchema.model_validate(
                {
                    "amount": document.attrib["Amount"],
                    "currency_name": document.attrib["CurrencyTag"],
                    "code": document.find("Code").text,
                    "purpose": document.find("Purpose").text,
                    "payment_type": NovaPayPaymentType(
                        document.find("PaymentType").text,
                    ),
                    "status_document_id": int(
                        document.find("StatusDocumentId").text,
                    ),
                    "changed": document.find("Changed").text,
                }
            )
            for document in transactions
        ]

        transactions = filter(
            lambda tr: tr.status_document_id == CONDUCTED,
            transactions,
        )

        return [transaction.to_transaction_schema() for transaction in transactions]

    def update_account_data(self) -> dict | None:
        refresh_response = self.client.service.UserAuthenticationJWT(
            {
                "request_ref": str(uuid4()),
                "refresh_token": self.configuration.refresh_token,
                "login": self.configuration.login,
                "public_certificate": self.configuration.public_certificate,
            }
        )

        if refresh_response["result"] != "ok":
            raise ResponseError(
                response=refresh_response,
                message="Failed to refresh authentication",
            )

        self.configuration.jwt = refresh_response["jwt"]
        self.configuration.refresh_token = refresh_response["refresh_token"]
        self.configuration.public_certificate = refresh_response["public_certificate"]
        self.configuration.expiration = refresh_response["expiration"]

        return self.configuration.model_dump()

    def get_balance(self) -> "BalanceSchema | None":
        now = datetime.datetime.now(tz=nova_pay_timezone)
        one_day_ago = now - datetime.timedelta(days=1)

        account_extract = self.client.service.GetAccountExtract(
            {
                "request_ref": str(uuid4()),
                "jwt": self.configuration.jwt,
                "account_id": self.configuration.account_id,
                "date_to": now.strftime("%d.%m.%Y"),
                "date_from": one_day_ago.strftime("%d.%m.%Y"),
            }
        )

        extract_data = account_extract["extract"]

        extract = ET.fromstring(extract_data)
        data = extract.find("ExtractHead/GetExtractForXML")

        return BalanceSchema(
            currency=980,
            start_balance=Decimal(data.find("InCome").text),
            end_balance=Decimal(data.find("OutCome").text),
            deposited=Decimal(data.find("CreditAmount").text),
            withdrawn=Decimal(data.find("DebitAmount").text),
        )
