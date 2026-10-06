"""Minimal process launcher for the bot and background services."""

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

import typer

from fetcher.bot import bot
from fetcher.db import get_engine
from fetcher.logger import main_logger
from fetcher.models.base import BaseModel
from fetcher.repository import settings
from fetcher.repository.account import AccountRepository
from fetcher.repository.notification import NotificationRepository
from fetcher.repository.transaction import TransactionRepository
from fetcher.services.account import AccountService
from fetcher.services.chat import get_chat_service
from fetcher.services.notification import NotificationService
from fetcher.services.transaction import TransactionService

app = typer.Typer()

RESTART_DELAY_SECONDS: Final[int] = 5
MAX_RESTART_DELAY_SECONDS: Final[int] = 600


@dataclass(frozen=True)
class Worker:
    name: str
    target: Callable[[], None]


def _next_restart_delay(delay: int) -> int:
    return min(delay * 2, MAX_RESTART_DELAY_SECONDS)


def _notify_worker_event(text: str, exception: Exception | None = None) -> None:
    try:
        get_chat_service().notify_management(
            text=text,
            exception=exception,
        )
    except Exception:  # noqa: BLE001
        main_logger.exception("Failed to send worker lifecycle notification")


def _run_worker_forever(worker: Worker) -> None:
    delay = RESTART_DELAY_SECONDS
    attempt = 0

    while True:
        attempt += 1
        action = "Starting" if attempt == 1 else "Restarting"

        try:
            main_logger.info("%s %s", action, worker.name)
            _notify_worker_event(f"{action} worker: {worker.name}")
            worker.target()
            main_logger.warning(
                "%s stopped unexpectedly; restarting in %s seconds",
                worker.name,
                delay,
            )
            _notify_worker_event(
                text=(f"Worker stopped unexpectedly: {worker.name}\nRestart in {delay} seconds."),
            )
        except Exception as exc:  # noqa: BLE001
            main_logger.exception("%s crashed; restarting in %s seconds", worker.name, delay)
            _notify_worker_event(
                text=(f"Worker crashed: {worker.name}\nRestart in {delay} seconds."),
                exception=exc,
            )

        time.sleep(delay)
        delay = _next_restart_delay(delay)


def _start_worker(worker: Worker) -> threading.Thread:
    thread = threading.Thread(
        target=_run_worker_forever,
        args=(worker,),
        daemon=True,
        name=worker.name,
    )
    thread.start()
    return thread


def _run_bot() -> None:
    bot.infinity_polling()


def _build_workers() -> list[Worker]:
    database = get_engine(settings.settings.DB_URL)
    chat_service = get_chat_service()

    account_service = AccountService(
        account_repository=AccountRepository(database),
    )
    transaction_service = TransactionService(
        transaction_repository=TransactionRepository(database),
        account_service=account_service,
        chat_service=chat_service,
    )
    notification_service = NotificationService(
        notification_repository=NotificationRepository(database),
    )

    return [
        Worker(name="transaction-service", target=transaction_service.run),
        Worker(name="notification-service", target=notification_service.run),
        Worker(name="account-service", target=account_service.run),
        Worker(name="telegram-bot", target=_run_bot),
    ]


@app.command(name="bot")
def run() -> None:
    """
    Run the bot.

    This command starts the bot and background services under a simple restart supervisor.
    """
    workers = _build_workers()

    for worker in workers[:-1]:
        _start_worker(worker)

    _run_worker_forever(workers[-1])


@app.command(name="migrate")
def migrate() -> None:
    """
    Run the migrations.
    """
    BaseModel.metadata.create_all(
        get_engine(settings.settings.DB_URL),
    )


if __name__ == "__main__":
    app()
