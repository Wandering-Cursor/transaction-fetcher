import json

import telebot
import telebot.types
import telebot.util
from telebot.storage import StateMemoryStorage

from fetcher.exceptions import NotAdminError
from fetcher.models.notification_setting import NotificationSettingsModel
from fetcher.repository import settings
from fetcher.schemas.account import AccountSchema, CreateAccountSchema
from fetcher.schemas.chat import ChatSchema, CreateChatSchema
from fetcher.schemas.notification import CreateNotificationSchema, UnansweredNotificationSchema
from fetcher.services.account import get_account_service
from fetcher.services.chat import get_chat_service
from fetcher.services.notification import get_notification_service
from fetcher.services.transaction import get_transaction_service


class CustomExceptionHandler(telebot.ExceptionHandler):
    def handle(self, exception: Exception) -> bool:  # pyright: ignore[reportIncompatibleMethodOverride]
        handled = super().handle(exception)

        if handled:
            return handled

        text_format = "Unhandled exception:\n{exception}"

        if isinstance(exception, NotAdminError):
            text_format = "Unauthorized access attempt detected:\n{exception.message}"

        text = text_format.format(exception=exception)

        for chunk in telebot.util.smart_split(text):
            telebot.util.antiflood(
                bot.send_message,
                chat_id=settings.settings.TELEGRAM_MANAGEMENT_CHAT_ID,
                text=chunk,
                parse_mode="HTML",
            )

        return True


storage = StateMemoryStorage()


bot = telebot.TeleBot(
    token=settings.settings.TELEGRAM_BOT_TOKEN,
    parse_mode="HTML",
    exception_handler=CustomExceptionHandler(),
    state_storage=storage,
)


def check_is_manager(message: telebot.types.Message) -> bool:
    """
    Check if the user is a manager.
    """
    if message.chat.id != settings.settings.TELEGRAM_MANAGEMENT_CHAT_ID:
        raise NotAdminError(
            message=message,
        )
    return True


@bot.message_handler(commands=["configure"])
def configure(message: telebot.types.Message) -> None:
    """
    Command handler for /configure command.
    """
    check_is_manager(message)

    markup = telebot.types.InlineKeyboardMarkup(
        keyboard=[
            [
                telebot.types.InlineKeyboardButton(
                    text="Account Settings",
                    callback_data="account_settings",
                )
            ],
            [
                telebot.types.InlineKeyboardButton(
                    text="Chat List",
                    callback_data="chat_list",
                )
            ],
            [
                telebot.types.InlineKeyboardButton(
                    text="Notification Settings",
                    callback_data="notification_settings",
                )
            ],
        ]
    )

    bot.send_message(
        chat_id=message.chat.id,
        text="Configure your bot settings here.",
        reply_markup=markup,
        parse_mode="HTML",
    )


def account_settings(call: telebot.types.CallbackQuery) -> None:
    """
    Handle account settings configuration.
    """
    message = call.message
    assert message is not None

    reply_markup = telebot.types.InlineKeyboardMarkup(
        keyboard=[
            [
                telebot.types.InlineKeyboardButton(
                    text="Add Account",
                    callback_data="add_account",
                )
            ],
            [
                telebot.types.InlineKeyboardButton(
                    text="List Accounts",
                    callback_data="list_accounts",
                ),
            ],
        ]
    )

    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=message.message_id,
        text="Account settings configuration.",
        parse_mode="HTML",
        reply_markup=reply_markup,
    )


def add_account(call: telebot.types.CallbackQuery) -> None:
    """
    Handle adding an account configuration.
    """
    message = call.message

    assert message is not None

    schema = json.dumps(
        CreateAccountSchema.model_json_schema(),
        indent=4,
    )

    bot_message = bot.send_message(
        chat_id=message.chat.id,
        text=(
            "Provide the JSON account configuration.\n\n"
            f'<pre><code class="language-json">{schema}</code></pre>'
        ),
        parse_mode="HTML",
    )
    bot.register_for_reply(
        message=bot_message,
        callback=handle_account_addition,
    )


def handle_account_addition(message: telebot.types.Message) -> None:
    """
    Handle the addition of an account configuration.
    """
    check_is_manager(message)

    try:
        create_account = CreateAccountSchema.model_validate_json(json_data=message.text)  # pyright: ignore[reportArgumentType]
    except ValueError as e:
        bot_message = bot.send_message(
            chat_id=message.chat.id,
            text=(
                "Could not validate the JSON configuration.\n\n"
                f"{e}\nReply with the correct JSON configuration."
            ),
            parse_mode="HTML",
        )
        bot.register_for_reply(
            message=bot_message,
            callback=handle_account_addition,
        )
        return

    account_service = get_account_service()

    account = account_service.create_account(
        account_data=create_account,
    )
    account_dto = AccountSchema.model_validate(account)

    bot.send_message(
        chat_id=message.chat.id,
        text=f"Created account:\n\n{account_dto.model_dump(mode='json')}",
        parse_mode="HTML",
    )
    configure(message)


def list_accounts(call: telebot.types.CallbackQuery) -> None:
    """
    Handle listing accounts configuration.
    """
    message = call.message

    assert message is not None

    account_service = get_account_service()
    accounts = account_service.get_accounts()
    accounts_keyboard = []

    for account in accounts:
        accounts_keyboard.append(
            [
                telebot.types.InlineKeyboardButton(
                    text=account.name,
                    callback_data=f"show_account_{account.id}",
                )
            ]
        )

    reply_markup = telebot.types.InlineKeyboardMarkup(
        keyboard=[
            *accounts_keyboard,
            [
                telebot.types.InlineKeyboardButton(
                    text="⤴️ Back",
                    callback_data="account_settings",
                )
            ],
        ]
    )

    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=message.message_id,
        text="List accounts configuration.",
        parse_mode="HTML",
        reply_markup=reply_markup,
    )


def show_account(call: telebot.types.CallbackQuery) -> None:
    """
    Handle editing an account configuration.
    """
    message = call.message

    assert message is not None
    assert call.data is not None

    account_id = call.data.split("_")[2]

    account_service = get_account_service()
    account = account_service.get_account_by_id(account_id=account_id)

    if not account:
        bot.send_message(
            chat_id=message.chat.id,
            text=f"Account with {account_id=} not found.",
            parse_mode="HTML",
        )
        return

    account_dto = AccountSchema.model_validate(account)

    text = "Viewing account:\n\n"

    for key, value in account_dto.model_dump().items():
        if isinstance(value, dict | list):
            value = "\n" + json.dumps(value, indent=4)  # noqa: PLW2901

        text += f"<b>{key.replace('_', ' ').capitalize()}</b>: {value}\n"

    reply_markup = telebot.types.InlineKeyboardMarkup(
        keyboard=[
            [
                telebot.types.InlineKeyboardButton(
                    text="📝 Edit",
                    callback_data=f"edit_account_{account_id}",
                )
            ],
            [
                telebot.types.InlineKeyboardButton(
                    text="🗑️ Delete",
                    callback_data=f"delete_account_{account_id}",
                )
            ],
            [
                telebot.types.InlineKeyboardButton(
                    text="⤴️ Back",
                    callback_data="list_accounts",
                )
            ],
        ]
    )

    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=message.message_id,
        text=text,
        parse_mode="HTML",
        reply_markup=reply_markup,
    )


def edit_account(call: telebot.types.CallbackQuery) -> None:
    """
    Handle editing an account configuration.
    """
    message = call.message

    assert message is not None
    assert call.data is not None

    account_id = call.data.split("_")[2]

    account_service = get_account_service()
    account = account_service.get_account_by_id(account_id=account_id)

    if not account:
        bot.send_message(
            chat_id=message.chat.id,
            text=f"Account with {account_id=} not found.",
            parse_mode="HTML",
        )
        return

    account_dto = AccountSchema.model_validate(account)

    schema = json.dumps(
        AccountSchema.model_json_schema(),
        indent=4,
    )

    bot_message = bot.send_message(
        chat_id=message.chat.id,
        text=(
            "Provide the JSON account configuration.\n\n"
            f'<pre><code class="language-json">{schema}</code></pre>\n\nCurrent value:\n\n'
            f'<pre><code class="language-json">{account_dto.model_dump_json(indent=4)}</code></pre>'
        ),
        parse_mode="HTML",
    )
    bot.register_for_reply(
        message=bot_message,
        callback=handle_account_editing,
    )


def handle_account_editing(message: telebot.types.Message) -> None:
    """
    Handle the editing of an account configuration.
    """
    check_is_manager(message)

    assert message.text is not None

    try:
        account = AccountSchema.model_validate_json(json_data=message.text)
    except ValueError as e:
        bot_message = bot.send_message(
            chat_id=message.chat.id,
            text=(
                "Could not validate the JSON configuration.\n\n"
                f"{e}\nReply with the correct JSON configuration."
            ),
            parse_mode="HTML",
        )
        bot.register_for_reply(
            message=bot_message,
            callback=handle_account_editing,
        )
        return

    account_service = get_account_service()
    account_service.edit_account(
        account_id=account.id,
        account_data=CreateAccountSchema.model_validate(account),
    )

    bot.send_message(
        chat_id=message.chat.id,
        text=f"Updated account:\n\n{account.model_dump(mode='json')}",
        parse_mode="HTML",
    )
    configure(message)


def delete_account(call: telebot.types.CallbackQuery) -> None:
    """
    Handle deleting an account configuration.
    """
    message = call.message

    assert message is not None
    assert call.data is not None

    account_id = int(call.data.split("_")[2])

    account_service = get_account_service()
    is_deleted = account_service.delete_account(
        account_id=account_id,
    )

    text = f"Deleted account with {account_id=}"

    if not is_deleted:
        text = f"Could not delete account with {account_id=}"

    bot.send_message(
        chat_id=message.chat.id,
        text=text,
        parse_mode="HTML",
    )
    list_accounts(call)


def reply_to_bot_message_filter(
    message: telebot.types.Message,
) -> bool:
    if not message.reply_to_message:
        return False
    if not message.reply_to_message.from_user:
        return False
    return message.reply_to_message.from_user.id == bot.bot_id


def list_chats(
    call: telebot.types.CallbackQuery,
) -> None:
    message = call.message

    assert message is not None

    chat_service = get_chat_service()

    chats = chat_service.get_chats()

    chats_keyboard = []
    for chat in chats:
        chats_keyboard.append(
            [
                telebot.types.InlineKeyboardButton(
                    text=f"{chat.id} - {chat.name}",
                    callback_data=f"show_chat_{chat.id}",
                )
            ]
        )

    chats_keyboard.append(
        [
            telebot.types.InlineKeyboardButton(
                text="⤴️ Back",
                callback_data="configure",
            )
        ]
    )

    reply_markup = telebot.types.InlineKeyboardMarkup(
        keyboard=[
            *chats_keyboard,
        ]
    )

    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=message.message_id,
        text="List chats configuration.",
        parse_mode="HTML",
        reply_markup=reply_markup,
    )


def show_chat(call: telebot.types.CallbackQuery) -> None:
    message = call.message

    assert message is not None
    assert call.data is not None

    chat_id = call.data.split("_")[2]

    chat_service = get_chat_service()

    chat = chat_service.get_chat_by_id(chat_id=int(chat_id))

    if not chat:
        bot.send_message(
            chat_id=message.chat.id,
            text=f"Chat with {chat_id=} not found.",
            parse_mode="HTML",
        )
        return

    chat_dto = ChatSchema.model_validate(chat)

    text = "Viewing chat:\n\n"

    for key, value in chat_dto.model_dump().items():
        if isinstance(value, dict | list):
            value = "\n" + json.dumps(value, indent=4)  # noqa: PLW2901

        text += f"<b>{key.replace('_', ' ').capitalize()}</b>: {value}\n"

    reply_markup = telebot.types.InlineKeyboardMarkup(
        keyboard=[
            [
                telebot.types.InlineKeyboardButton(
                    text="➕ Add Account",  # noqa: RUF001
                    callback_data=f"add_account_{chat_id}",
                ),
            ],
            [
                telebot.types.InlineKeyboardButton(
                    text="👁️ View Accounts",
                    callback_data=f"view_accounts_{chat_id}",
                )
            ],
            [
                telebot.types.InlineKeyboardButton(
                    text="⤴️ Back",
                    callback_data="chat_list",
                )
            ],
        ]
    )

    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=message.message_id,
        text=text,
        parse_mode="HTML",
        reply_markup=reply_markup,
    )


def add_account_to_chat(call: telebot.types.CallbackQuery) -> None:
    message = call.message

    assert message is not None
    assert call.data is not None

    chat_id = call.data.split("_")[2]

    account_service = get_account_service()

    accounts = account_service.get_accounts(fetch_all=True)

    accounts_string = "\n".join([f"{account.id} - {account.name}" for account in accounts])

    bot.set_state(user_id=call.from_user.id, state="add_account_to_chat", chat_id=message.chat.id)
    bot.add_data(
        user_id=call.from_user.id,
        chat_id=message.chat.id,
        kwargs={"chat_id": chat_id},
    )

    msg = bot.send_message(
        chat_id=message.chat.id,
        text=f"Reply with the account ID to add to chat {chat_id}.\n\n{accounts_string}",
        parse_mode="HTML",
        reply_markup=telebot.types.ForceReply(),
    )

    bot.register_for_reply(
        message=msg,
        callback=handle_account_addition_to_chat,
    )


def handle_account_addition_to_chat(message: telebot.types.Message) -> None:
    check_is_manager(message)

    assert message.from_user is not None

    context = bot.retrieve_data(
        user_id=message.from_user.id,
        chat_id=message.chat.id,
    )

    assert context is not None

    chat_id = context.data["kwargs"]["chat_id"]

    account_service = get_account_service()

    try:
        account_id = int(message.text)  # pyright: ignore[reportArgumentType]
    except ValueError:
        bot.send_message(
            chat_id=message.chat.id,
            text="Invalid account ID.",
            parse_mode="HTML",
        )
        return

    account = account_service.get_account_by_id(account_id=str(account_id))

    if not account:
        bot.send_message(
            chat_id=message.chat.id,
            text=f"Account with {account_id=} not found.",
            parse_mode="HTML",
        )
        return

    chat_service = get_chat_service()
    chat_service.add_account_to_chat(
        chat_id=chat_id,
        account_id=account_id,
    )

    bot.send_message(
        chat_id=message.chat.id,
        text=f"Added account {account.name} to chat {chat_id}.",
        parse_mode="HTML",
    )

    bot.delete_state(user_id=message.from_user.id, chat_id=message.chat.id)
    configure(message)


def view_chat_accounts(call: telebot.types.CallbackQuery) -> None:
    assert call.data

    message = call.message
    assert message is not None

    chat_id = call.data.split("_")[2]

    chat_service = get_chat_service()

    chat = chat_service.get_chat_by_id(chat_id=int(chat_id))

    if not chat:
        bot.send_message(
            chat_id=message.chat.id,
            text=f"Chat with {chat_id=} not found.",
            parse_mode="HTML",
        )
        return

    account_chats = chat_service.get_accounts_by_chat(chat=chat)

    account_chats_buttons = [
        [
            telebot.types.InlineKeyboardButton(
                text=f"{account_chat.account.id} - {account_chat.account.name}",
                callback_data=f"show_accountchat_{account_chat.id}",
            )
        ]
        for account_chat in account_chats
    ]

    reply_markup = telebot.types.InlineKeyboardMarkup(
        keyboard=[
            *account_chats_buttons,
            [
                telebot.types.InlineKeyboardButton(
                    text="⤴️ Back",
                    callback_data=f"show_chat_{chat_id}",
                )
            ],
        ]
    )

    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=message.message_id,
        text=f"Accounts in chat {chat.name}:",
        parse_mode="HTML",
        reply_markup=reply_markup,
    )


def show_account_chat(call: telebot.types.CallbackQuery) -> None:
    assert call.data

    message = call.message
    assert message is not None

    account_chat_id = int(call.data.split("_")[2])

    chat_service = get_chat_service()
    account_chat = chat_service.get_account_chat_by_id(account_chat_id=account_chat_id)

    if not account_chat:
        bot.send_message(
            chat_id=message.chat.id,
            text=f"AccountChat with {account_chat_id=} not found.",
            parse_mode="HTML",
        )
        return

    text = "Viewing account chat:\n\n{account_name} - {chat_name}"
    text = text.format(
        account_name=account_chat.account.name,
        chat_name=account_chat.chat.name,
    )

    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=message.message_id,
        text=text,
        parse_mode="HTML",
        reply_markup=telebot.types.InlineKeyboardMarkup(
            keyboard=[
                [
                    telebot.types.InlineKeyboardButton(
                        text="➕ Add Notification",  # noqa: RUF001
                        callback_data=f"add_notification_{account_chat.id}",
                    )
                ],
                [
                    telebot.types.InlineKeyboardButton(
                        text="👁️ View Notifications",
                        callback_data=f"view_notifications_{account_chat.id}",
                    )
                ],
                [
                    telebot.types.InlineKeyboardButton(
                        text="🗑️ Delete",
                        callback_data=f"delete_accountchat_{account_chat.id}",
                    )
                ],
                [
                    telebot.types.InlineKeyboardButton(
                        text="⤴️ Back",
                        callback_data=f"view_accounts_{account_chat.chat.id}",
                    )
                ],
            ]
        ),
    )


def delete_account_chat(call: telebot.types.CallbackQuery) -> None:
    """
    Handle deleting an account chat configuration.
    """
    assert call.data

    message = call.message
    assert message is not None

    account_chat_id = int(call.data.split("_")[2])

    chat_service = get_chat_service()
    is_deleted = chat_service.delete_account_chat(
        account_chat_id=account_chat_id,
    )

    text = f"Deleted account chat with {account_chat_id=}"

    if not is_deleted:
        text = f"Could not delete account chat with {account_chat_id=}"

    bot.send_message(
        chat_id=message.chat.id,
        text=text,
        parse_mode="HTML",
    )
    list_chats(call)


def add_notification(call: telebot.types.CallbackQuery) -> None:
    assert call.data

    message = call.message
    assert message is not None

    account_chat_id = call.data.split("_")[2]

    schema = json.dumps(
        CreateNotificationSchema.model_json_schema(),
        indent=4,
    )

    bot_message = bot.send_message(
        chat_id=message.chat.id,
        text=(
            "Provide the JSON notification configuration.\n\n"
            f'<pre><code class="language-json">{schema}</code></pre>'
        ),
        parse_mode="HTML",
    )

    bot.set_state(
        user_id=call.from_user.id,
        state="add_notification",
        chat_id=message.chat.id,
    )
    bot.add_data(
        user_id=call.from_user.id,
        chat_id=message.chat.id,
        kwargs={"account_chat_id": account_chat_id},
    )

    bot.register_for_reply(
        message=bot_message,
        callback=handle_notification_addition,
    )


def handle_notification_addition(message: telebot.types.Message) -> None:
    check_is_manager(message)

    assert message.text
    assert message.from_user

    try:
        create_notification = CreateNotificationSchema.model_validate_json(
            json_data=message.text,
        )
    except ValueError as e:
        bot_message = bot.send_message(
            chat_id=message.chat.id,
            text=(
                "Could not validate the JSON configuration.\n\n"
                f"{e}\nReply with the correct JSON configuration."
            ),
            parse_mode="HTML",
        )
        bot.register_for_reply(
            message=bot_message,
            callback=handle_notification_addition,
        )
        return

    context = bot.retrieve_data(
        user_id=message.from_user.id,
        chat_id=message.chat.id,
    )

    account_chat_id = context.data["kwargs"]["account_chat_id"]

    notification_service = get_notification_service()
    notification_service.create_notification(
        account_chat_id=account_chat_id,
        notification_data=create_notification,
    )

    bot.send_message(
        chat_id=message.chat.id,
        text="Created notification.",
        parse_mode="HTML",
    )
    configure(message)


def view_notifications(call: telebot.types.CallbackQuery) -> None:
    assert call.data

    message = call.message
    assert message is not None

    account_chat_id = int(call.data.split("_")[2])

    notification_service = get_notification_service()

    notification_settings = notification_service.get_notification_settings_by_account_chat_id(
        account_chat_id=account_chat_id,
    )

    notifications_keyboard = []

    for notification in notification_settings:
        notifications_keyboard.append(
            [
                telebot.types.InlineKeyboardButton(
                    text=f"{notification.notification_type} - {notification.schedule}",
                    callback_data=f"delete_notification_{notification.id}",
                )
            ]
        )

    reply_markup = telebot.types.InlineKeyboardMarkup(
        keyboard=[
            *notifications_keyboard,
            [
                telebot.types.InlineKeyboardButton(
                    text="⤴️ Back",
                    callback_data=f"show_accountchat_{account_chat_id}",
                )
            ],
        ]
    )

    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=message.message_id,
        text="List notifications configuration.",
        parse_mode="HTML",
        reply_markup=reply_markup,
    )


def delete_notification_setting(call: telebot.types.CallbackQuery) -> None:
    """
    Handle deleting a notification configuration.
    """
    assert call.data

    message = call.message
    assert message is not None

    notification_setting_id = int(call.data.split("_")[2])

    notification_service = get_notification_service()
    is_deleted = notification_service.delete_notification_setting(
        notification_setting_id=notification_setting_id,
    )

    text = f"Deleted notification with {notification_setting_id=}"

    if not is_deleted:
        text = f"Could not delete notification with {notification_setting_id=}"

    bot.send_message(
        chat_id=message.chat.id,
        text=text,
        parse_mode="HTML",
    )

    list_chats(call)


@bot.callback_query_handler(func=lambda call: True)  # noqa: ARG005
def handle_callback_query(  # noqa: C901, PLR0911, PLR0912
    call: telebot.types.CallbackQuery,
) -> None:
    """
    Handle callback queries from inline buttons.
    """
    if isinstance(call.message, telebot.types.Message):
        check_is_manager(call.message)

    assert call.data

    if call.data == "account_settings":
        return account_settings(call)
    if call.data == "add_account":
        return add_account(call)
    if call.data == "list_accounts":
        return list_accounts(call)
    if call.data.startswith("show_account_"):
        return show_account(call)
    if call.data.startswith("edit_account_"):
        return edit_account(call)
    if call.data.startswith("delete_account_"):
        return delete_account(call)

    if call.data == "chat_list":
        return list_chats(call)
    if call.data.startswith("show_chat_"):
        return show_chat(call)
    if call.data.startswith("add_account_"):
        return add_account_to_chat(call)
    if call.data.startswith("view_accounts_"):
        return view_chat_accounts(call)

    if call.data.startswith("show_accountchat_"):
        return show_account_chat(call)
    if call.data.startswith("delete_accountchat_"):
        return delete_account_chat(call)

    if call.data.startswith("add_notification_"):
        return add_notification(call)
    if call.data.startswith("view_notifications_"):
        return view_notifications(call)
    if call.data.startswith("delete_notification_"):
        return delete_notification_setting(call)

    if call.data == "configure" and isinstance(call.message, telebot.types.Message):
        return configure(call.message)

    if not call.message:
        bot.answer_callback_query(
            callback_query_id=call.id,
            text="No message associated with this callback.",
        )
        return None

    bot.send_message(
        chat_id=call.message.chat.id,
        text="Unknown command.",
        parse_mode="HTML",
    )

    return None


@bot.message_handler(commands=["unanswered"])
def unanswered(message: telebot.types.Message) -> None:
    notification_service = get_notification_service()
    transaction_service = get_transaction_service()

    notifications = notification_service.unanswered_notifications(
        external_chat_id=str(message.chat.id),
    )

    items = []

    for notification in notifications:
        transaction = transaction_service.get_transaction_by_id(
            transaction_id=notification.transaction_id,
        )

        if not transaction:
            continue

        items.append(
            UnansweredNotificationSchema(
                account_name=transaction.account.name,
                amount=transaction.amount_as_string,
                at_time=transaction.at_time.strftime("%d.%m %H:%M"),
                message_link=f"<a href='https://t.me/c/{notification.external_chat_id.replace('-100', '')}/{notification.external_message_id}'>{'{msg}'}</a>",  # noqa: E501
            )
        )

    text = NotificationSettingsModel.unanswered_message(
        notifications=items,
    )

    for chunk in telebot.util.smart_split(text):
        telebot.util.antiflood(
            bot.reply_to,
            message=message,
            text=chunk,
        )


@bot.message_handler(commands=["balances"])
def balances(message: telebot.types.Message) -> None:
    chat_service = get_chat_service()
    account_service = get_account_service()
    transaction_service = get_transaction_service()

    chat = chat_service.get_chat_by_external_id(
        external_id=str(message.chat.id),
    )

    if not chat:
        bot.send_message(
            chat_id=message.chat.id,
            text="Chat not found.",
            parse_mode="HTML",
        )
        return

    accounts = account_service.get_accounts_per_chat(
        chat_id=chat.id,
    )

    balances = [
        transaction_service.get_balance(
            account_id=account.id,
        )
        for account in accounts
    ]

    balances_text = "Балансы:\n\n"

    for balance, account in zip(balances, accounts, strict=False):
        if not balance:
            balances_text += f"Информация отсутствует ({account.name})\n\n"
            continue

        balances_text += NotificationSettingsModel.balance_message_base(
            balance_data=balance,
            account_name=account.name,
        )

        balances_text += "\n--------------------------\n"

    for chunk in telebot.util.smart_split(balances_text):
        telebot.util.antiflood(
            bot.reply_to,
            message=message,
            text=chunk,
        )


@bot.message_handler(func=reply_to_bot_message_filter)
def handle_replies(
    message: telebot.types.Message,
) -> None:
    notification_service = get_notification_service()

    assert message.reply_to_message is not None

    notification_service.mark_as_replied(
        external_chat_id=str(message.chat.id),
        external_message_id=str(message.reply_to_message.message_id),
    )


def new_member_message_filter(
    message: telebot.types.Message,
) -> bool:
    return message.content_type == "new_chat_members"


def bot_joined_group_message_filter(
    message: telebot.types.Message,
) -> bool:
    assert bot.bot_id

    if message.new_chat_members is None:
        return False

    new_members = message.new_chat_members

    return bot.bot_id in (member.id for member in new_members)


@bot.message_handler(
    func=bot_joined_group_message_filter,
    content_types=["new_chat_members"],
)
def bot_joined_group(
    message: telebot.types.Message,
) -> None:
    """
    Handle the bot joining a group.
    """
    chat_service = get_chat_service()

    chat = chat_service.add_chat(
        CreateChatSchema(
            name=message.chat.title or "Unnamed Chat",
            external_id=str(message.chat.id),
        )
    )

    bot.send_message(
        chat_id=message.chat.id,
        text=f"ID этого чата: <code>{chat.external_id}</code>",
    )
