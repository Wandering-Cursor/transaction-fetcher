import json
import time

from fetcher import db
from fetcher.logger import db_logger
from fetcher.models.account import AccountModel
from fetcher.providers.account.get import get_provider_class
from fetcher.repository import settings
from fetcher.repository.account import AccountRepository
from fetcher.schemas.account import CreateAccountSchema
from fetcher.services.chat import send_error_to_management
from fetcher.utils import handle_service_exception


class AccountService:
    def __init__(
        self,
        account_repository: AccountRepository,
    ) -> None:
        self.account_repository = account_repository

    def run(self) -> None:
        """
        Run the account service.
        """
        db_logger.info("Starting account service")
        while True:
            self._run_iteration()
            time.sleep(60 * 60)  # 1 hour

    @handle_service_exception("account service", db_logger)
    def _run_iteration(self) -> None:
        """Execute a single iteration of the account service."""
        db_logger.info(
            {
                "msg": "Updating account data for all accounts",
            },
        )
        accounts = self.get_accounts(fetch_all=True)
        for account in accounts:
            try:
                self.update_account_data(account_id=account.id)
            except Exception as e:  # noqa: BLE001
                db_logger.error(
                    {
                        "msg": f"Failed to update account data for account {account.id}",
                        "error": str(e),
                    }
                )
                send_error_to_management(
                    f"Failed to update account data for account {account.id}",
                    exception=e,
                )
        db_logger.info(
            {
                "msg": "Finished updating account data for all accounts",
            }
        )

    def get_account_by_id(
        self,
        account_id: str,
    ) -> AccountModel | None:
        return self.account_repository.get_by_id(
            account_id=account_id,
        )

    def get_accounts(
        self,
        page: int = 1,
        page_size: int = 25,
        fetch_all: bool = False,
    ) -> list[AccountModel]:
        accounts, total = self.account_repository.get_all(
            page=page,
            page_size=page_size,
            fetch_all=fetch_all,
        )

        db_logger.info(
            {
                "msg": f"Showing {len(accounts)}/{total} accounts",
            },
        )
        db_logger.debug(
            {
                "msg": "Received the following accounts",
                "accounts": accounts,
            },
        )

        return accounts

    def create_account(
        self,
        account_data: CreateAccountSchema,
    ) -> AccountModel:
        return self.account_repository.create(
            account_data=account_data,
        )

    def edit_account(
        self,
        account_id: int,
        account_data: CreateAccountSchema,
    ) -> AccountModel:
        return self.account_repository.update(
            account_id=account_id,
            account_data=account_data,
        )

    def delete_account(
        self,
        account_id: int,
    ) -> bool:
        return self.account_repository.delete(
            account_id=account_id,
        )

    def update_account_data(
        self,
        account_id: int,
    ) -> AccountModel:
        """
        Update the account data.
        """
        account = self.get_account_by_id(account_id=account_id)

        provider = get_provider_class(
            provider_name=account.provider,
        )
        instance = provider(
            account=account,
        )

        updated_data = instance.update_account_data()

        if updated_data is not None:
            account.configuration_parameters = json.dumps(updated_data)

        return self.account_repository.update(
            account_id=account_id,
            account_data=account,
        )

    def get_accounts_per_chat(
        self,
        chat_id: int,
    ) -> list[AccountModel]:
        """
        Get all accounts for a given chat.
        """
        accounts = self.account_repository.get_all_accounts_for_chat(
            chat_id=chat_id,
        )

        db_logger.info(
            {
                "msg": f"Showing {len(accounts)} accounts for chat {chat_id}",
            },
        )
        db_logger.debug(
            {
                "msg": "Received the following accounts",
                "accounts": accounts,
            },
        )

        return accounts


def get_account_service() -> AccountService:
    """
    Get the account service instance.
    """
    database = db.get_engine(settings.settings.DB_URL)
    account_repository = AccountRepository(database)
    return AccountService(account_repository=account_repository)
