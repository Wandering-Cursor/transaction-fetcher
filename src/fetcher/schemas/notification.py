import datetime
from typing import TYPE_CHECKING

import pydantic

from fetcher.enums.notification_setting import NotificationType
from fetcher.repository import settings
from fetcher.schemas.account import AccountChatSchema, BalanceSchema
from fetcher.schemas.base import BaseSchema
from fetcher.services.currency import get_currency_by_numerical_code
from fetcher.utils import amount_with_sign_and_space, amount_with_spaces

if TYPE_CHECKING:
    from fetcher.models.transaction import TransactionModel


class CreateNotificationSchema(BaseSchema):
    schedule: str | None = pydantic.Field(
        default=None,
        description="Schedule for the notification. Can be a cron expression or null",
    )
    notification_type: NotificationType


class NotificationSettingsSchema(BaseSchema):
    id: int

    account_chat_id: int
    account_chat: AccountChatSchema

    schedule: str | None = pydantic.Field(
        default=None,
    )
    notification_type: NotificationType

    last_sent_at: str | None

    def transaction_message(
        self,
        transaction: "TransactionModel",
    ) -> str:
        currency = get_currency_by_numerical_code(
            numerical_code=transaction.currency,
        )

        message = f"""
{self.account_chat.account.name}: <b>{transaction.amount_as_string} {currency.alpha3}</b>

Комментарий: {transaction.description}

<b>{transaction.at_time.strftime("%Y-%m-%d | %H:%M")}</b>
"""
        return message.strip()

    def balance_message(
        self,
        balance_data: "BalanceSchema",
    ) -> str:
        at_time = balance_data.at_time or datetime.datetime.now(
            tz=settings.settings.default_timezone,
        )
        currency = get_currency_by_numerical_code(
            numerical_code=balance_data.currency,
        )

        deposit_withdrawal_stats = ""

        if balance_data.deposited and balance_data.withdrawn:
            deposit_withdrawal_stats = f"""
Приход: <b>{amount_with_spaces(balance_data.deposited)} {currency.alpha3}</b>
Расход: <b>{amount_with_spaces(balance_data.withdrawn)} {currency.alpha3}</b>
"""

        message = f"""
{self.account_chat.account.name}

Начало дня: <b>{amount_with_spaces(balance_data.start_balance)} {currency.alpha3}</b>
Конец дня: <b>{amount_with_spaces(balance_data.end_balance)} {currency.alpha3}</b>
{deposit_withdrawal_stats}
Итого: <b>{amount_with_sign_and_space(balance_data.end_balance - balance_data.start_balance)} {currency.alpha3}</b>
<b>{at_time.strftime("%Y-%m-%d | %H:%M")}</b>
"""  # noqa: E501

        return message.strip()

    def active_message(
        self,
    ) -> str:
        return f"""
{self.account_chat.account.name}: <b>Активен</b>
""".strip()

    @property
    def last_sent_at_dt(self) -> datetime.datetime | None:
        if not self.last_sent_at:
            return None

        return datetime.datetime.fromisoformat(self.last_sent_at)

    def set_last_sent_at(self, dt: datetime.datetime) -> None:
        self.last_sent_at = dt.isoformat()

    @classmethod
    def unanswered_message(
        cls,
        notifications: list["UnansweredNotificationSchema"],
    ) -> str:
        message = "Не отвеченные сообщения:\n\n"  # noqa: RUF001

        unanswered = []
        for notification in notifications:
            tmp = f"{notification.account_name}: {notification.amount} | {notification.at_time}"
            unanswered.append(
                notification.message_link.format(
                    msg=tmp,
                )
            )

        message += "\n".join(unanswered)
        return message.strip()


class UnansweredNotificationSchema(BaseSchema):
    account_name: str
    # Converted
    amount: str
    at_time: str

    message_link: str
