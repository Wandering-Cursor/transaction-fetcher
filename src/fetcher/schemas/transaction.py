import datetime
from decimal import Decimal

from fetcher.enums.transaction import TransactionType
from fetcher.schemas.account import AccountSchema
from fetcher.schemas.base import BaseSchema
from fetcher.schemas.currency import CurrencySchema


class TransactionSchema(BaseSchema):
    unique_id: str | None = None

    type: TransactionType

    amount: Decimal
    currency: CurrencySchema | None = None
    description: str | None = None
    at_time: datetime.datetime | None = None

    base: BaseSchema | None = None


class DBTransactionSchema(BaseSchema):
    id: int
    unique_id: str

    account_id: int
    account: AccountSchema
    type: TransactionType
    amount: Decimal
    currency: int
    description: str
    at_time: datetime.datetime

    amount_as_string: str
