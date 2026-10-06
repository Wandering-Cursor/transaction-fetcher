from sqlalchemy import Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fetcher.enums.chat import ChatProvider
from fetcher.models.account_chat_model import AccountChatModel
from fetcher.models.base import BaseModel


class ChatModel(BaseModel):
    __tablename__ = "chats"

    name: Mapped[str] = mapped_column(
        nullable=False,
    )
    provider: Mapped[ChatProvider] = mapped_column(
        "provider",
        Enum(ChatProvider),
        nullable=False,
    )

    # ID of the chat in the provider's system
    external_id: Mapped[str] = mapped_column(
        nullable=False,
    )

    account_chats: Mapped[list[AccountChatModel]] = relationship(
        back_populates="chat",
    )
