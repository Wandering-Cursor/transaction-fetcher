from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fetcher.models.base import BaseModel

if TYPE_CHECKING:
    from fetcher.models.account import AccountModel
    from fetcher.models.chat import ChatModel
    from fetcher.models.notification_setting import NotificationSettingsModel


class AccountChatModel(BaseModel):
    __tablename__ = "account_chats"

    account_id: Mapped[int] = mapped_column(
        "account_id",
        ForeignKey("accounts.id"),
        nullable=False,
    )
    chat_id: Mapped[int] = mapped_column(
        "chat_id",
        ForeignKey("chats.id"),
        nullable=False,
    )

    notification_settings: Mapped[list["NotificationSettingsModel"]] = relationship(
        back_populates="account_chat",
    )

    account: Mapped["AccountModel"] = relationship(
        back_populates="account_chats",
    )
    chat: Mapped["ChatModel"] = relationship(
        back_populates="account_chats",
    )
