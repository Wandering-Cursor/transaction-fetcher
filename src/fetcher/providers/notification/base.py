from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fetcher.models.chat import ChatModel


class BaseChatProvider:
    def __init__(self, chat: "ChatModel") -> None:
        self._chat = chat

    def send_message(
        self,
        text: str,
        parse_mode: str = "HTML",
    ) -> str:
        """Returns message ID"""
        raise NotImplementedError("send_message method not implemented")
