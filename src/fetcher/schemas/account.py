import datetime
import json
from datetime import timedelta
from decimal import Decimal

import pydantic

from fetcher.enums.account import AccountProvider
from fetcher.schemas.base import BaseSchema
from fetcher.schemas.chat import ChatSchema


class CreateAccountSchema(BaseSchema):
    name: str
    provider: AccountProvider

    configuration_parameters: dict

    interval: timedelta = timedelta(days=1)


class AccountSchema(BaseSchema):
    id: int
    name: str
    provider: AccountProvider

    configuration_parameters: dict

    interval: timedelta = timedelta(days=1)

    @pydantic.field_validator("configuration_parameters", mode="before")
    @classmethod
    def validate_configuration_parameters(cls, value: dict) -> dict:
        if isinstance(value, str):
            value = json.loads(value)
        return value


class BalanceSchema(BaseSchema):
    currency: int | None = None

    start_balance: Decimal = pydantic.Field(
        default=Decimal(0),
    )
    end_balance: Decimal
    deposited: Decimal | None = None
    withdrawn: Decimal | None = None

    at_time: datetime.datetime | None = None


class AccountChatSchema(BaseSchema):
    id: int

    account_id: int
    chat_id: int

    account: AccountSchema
    chat: ChatSchema
