from typing import TYPE_CHECKING

import telebot
import telebot.util

from fetcher.providers.notification.base import BaseChatProvider
from fetcher.repository import settings

if TYPE_CHECKING:
    from fetcher.models.chat import ChatModel


class TelegramChatProvider(BaseChatProvider):
    def __init__(self, chat: "ChatModel") -> None:
        super().__init__(chat)

        self.bot_token = settings.settings.TELEGRAM_BOT_TOKEN

    def send_message(
        self,
        text: str,
        parse_mode: str = "HTML",
    ) -> str:
        bot = telebot.TeleBot(
            self.bot_token,
            parse_mode=parse_mode,
            # May cause problems in the long run
            threaded=False,
        )

        message_id: int | None = None
        for chunk in telebot.util.smart_split(text):
            message = telebot.util.antiflood(
                bot.send_message,
                chat_id=self._chat.external_id,
                text=chunk,
                parse_mode=parse_mode,
            )

            message_id = getattr(message, "id", None)

        if message_id is None:
            raise ValueError("Failed to send message")

        return str(message_id)
