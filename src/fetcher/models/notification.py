from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from fetcher.models.base import BaseModel


class NotificationModel(BaseModel):
    __tablename__ = "notification"

    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id"),
        nullable=False,
    )
    account_chat_id: Mapped[int] = mapped_column(
        ForeignKey("account_chats.id"),
        nullable=False,
    )

    external_message_id: Mapped[str] = mapped_column(
        nullable=False,
    )
    external_chat_id: Mapped[str] = mapped_column(
        nullable=False,
    )

    is_replied: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
    )
