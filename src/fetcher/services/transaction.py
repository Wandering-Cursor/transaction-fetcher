import time
from typing import TYPE_CHECKING

from fetcher import db
from fetcher.exceptions import TransactionFetchError
from fetcher.logger import main_logger
from fetcher.repository import settings
from fetcher.repository.transaction import TransactionRepository
from fetcher.services.account import AccountService, get_account_service
from fetcher.services.chat import ChatService, get_chat_service
from fetcher.services.notification import get_notification_service
from fetcher.utils import handle_service_exception

if TYPE_CHECKING:
    from fetcher.models.transaction import TransactionModel
    from fetcher.schemas.account import BalanceSchema
    from fetcher.schemas.transaction import DBTransactionSchema


class TransactionService:
    def __init__(
        self,
        transaction_repository: TransactionRepository,
        account_service: AccountService,
        chat_service: ChatService,
    ) -> None:
        self.transaction_repository = transaction_repository
        self.account_service = account_service
        self.chat_service = chat_service

    def run(self) -> None:
        while True:
            self._run_iteration()
            time.sleep(60)

    @handle_service_exception("transaction service", main_logger)
    def _run_iteration(self) -> None:
        """Execute a single iteration of the transaction service."""
        main_logger.info("Fetching transactions...")
        transactions = self.fetch_transactions()
        for transaction in transactions:
            self.process_transaction(transaction)

    def get_transaction_by_id(self, transaction_id: int) -> "TransactionModel | None":
        return self.transaction_repository.get_transaction_by_id(
            transaction_id=transaction_id,
        )

    def fetch_transactions(self) -> list["DBTransactionSchema"]:
        new_transactions = []

        accounts = self.account_service.get_accounts(fetch_all=True)

        for account in accounts:
            try:
                account_transactions = self.transaction_repository.fetch_transaction_by_account(
                    account
                )
            except TransactionFetchError as exc:
                self._notify_fetch_error(exc)
                continue

            new_transactions.extend(
                self.transaction_repository.store_transactions(
                    account=account,
                    account_transactions=account_transactions,
                )
            )

        return new_transactions

    def _notify_fetch_error(self, error: TransactionFetchError) -> None:
        main_logger.warning(
            {
                "msg": "Skipping account after transaction fetch error",
                "account_id": error.account_id,
                "account_name": error.account_name,
                "provider": error.provider,
            }
        )

        try:
            self.chat_service.notify_management(
                text=(
                    "Could not fetch transactions for account "
                    f"{error.account_id} ({error.account_name}) via {error.provider}"
                ),
                exception=error.original_exception,
            )
        except Exception:  # noqa: BLE001
            main_logger.exception(
                "Failed to notify management about transaction fetch error for account %s",
                error.account_id,
            )

    def make_notification(self, transaction: "DBTransactionSchema") -> None:
        notification_service = get_notification_service()

        if notification_service.notification_exists(transaction):
            return

        notification_service.make_transaction_notifications(transaction)

    def process_transaction(self, transaction: "DBTransactionSchema") -> None:
        self.make_notification(transaction)

    def get_balance(
        self,
        account_id: int,
    ) -> "BalanceSchema | None":
        account = self.account_service.get_account_by_id(account_id=str(account_id))

        if not account:
            return None

        return self.transaction_repository.get_balance(
            account=account,
        )


def get_transaction_service() -> TransactionService:
    database = db.get_engine(settings.settings.DB_URL)
    transaction_repository = TransactionRepository(db=database)
    return TransactionService(
        transaction_repository=transaction_repository,
        account_service=get_account_service(),
        chat_service=get_chat_service(),
    )
