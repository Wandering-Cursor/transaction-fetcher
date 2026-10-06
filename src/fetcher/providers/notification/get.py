from fetcher.enums.chat import ChatProvider
from fetcher.providers.notification.base import BaseChatProvider
from fetcher.providers.notification.telegram import TelegramChatProvider


def get_chat_provider_class(provider: ChatProvider) -> type[BaseChatProvider]:
    return {
        ChatProvider.TELEGRAM: TelegramChatProvider,
    }[provider]
