import json
from datetime import timedelta

from sqlalchemy import Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fetcher.enums.account import AccountProvider
from fetcher.models.account_chat_model import AccountChatModel
from fetcher.models.base import BaseModel
from fetcher.models.transaction import TransactionModel


class AccountModel(BaseModel):
    __tablename__ = "accounts"

    name: Mapped[str] = mapped_column(
        nullable=False,
    )
    provider: Mapped[AccountProvider] = mapped_column(
        "provider",
        Enum(AccountProvider),
        nullable=False,
    )

    # JSON configuration parameters for the account
    configuration_parameters: Mapped[str] = mapped_column(
        nullable=False,
    )

    @property
    def configuration(self) -> dict:
        """
        Convert the JSON string to a dictionary.
        """
        return json.loads(self.configuration_parameters)

    # How far back in time to look for new data
    interval_seconds: Mapped[int] = mapped_column(
        default=24 * 60 * 60,  # default to 24 hours in seconds
        nullable=False,
    )

    account_chats: Mapped[list[AccountChatModel]] = relationship(
        back_populates="account",
    )
    transactions: Mapped[list[TransactionModel]] = relationship(
        back_populates="account",
    )

    @property
    def interval(self) -> timedelta:
        """
        Convert the interval in seconds to a timedelta object.
        """
        return timedelta(seconds=self.interval_seconds)
