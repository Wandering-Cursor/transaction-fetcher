from fetcher.enums.chat import ChatProvider
from fetcher.schemas.base import BaseSchema


class CreateChatSchema(BaseSchema):
    name: str
    provider: ChatProvider = ChatProvider.TELEGRAM

    external_id: str


class ListChatSchema(BaseSchema):
    provider: ChatProvider | None = None

    page: int = 1
    page_size: int = 25


class ChatSchema(BaseSchema):
    id: int
    name: str
    provider: ChatProvider | None = None

    external_id: str | None = None
