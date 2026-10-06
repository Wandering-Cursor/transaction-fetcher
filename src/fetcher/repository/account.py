import json
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from fetcher.models.account import AccountModel
from fetcher.models.account_chat_model import AccountChatModel
from fetcher.schemas.account import CreateAccountSchema

if TYPE_CHECKING:
    import sqlalchemy


class AccountRepository:
    def __init__(
        self,
        db: "sqlalchemy.engine.Engine",
    ) -> None:
        self.db = db

    def create(
        self,
        account_data: CreateAccountSchema,
    ) -> AccountModel:
        entity = AccountModel(
            name=account_data.name,
            provider=account_data.provider,
            configuration_parameters=json.dumps(
                account_data.configuration_parameters,
                indent=4,
            ),
            interval_seconds=account_data.interval.total_seconds(),
        )

        with Session(self.db) as session:
            session.add(entity)
            session.commit()
            session.refresh(entity)

        return entity

    def get_by_id(self, account_id: int) -> AccountModel | None:
        with Session(self.db) as session:
            return (
                session.query(AccountModel)
                .filter_by(
                    id=account_id,
                )
                .first()
            )

    def get_all(
        self,
        page: int = 1,
        page_size: int = 25,
        fetch_all: bool = False,
    ) -> tuple[list[AccountModel], int]:
        with Session(self.db) as session:
            query = session.query(AccountModel)

            total_count = query.count()

            if fetch_all:
                accounts = query.all()
            else:
                accounts = (
                    query.offset(
                        (page - 1) * page_size,
                    )
                    .limit(
                        page_size,
                    )
                    .all()
                )

            return accounts, total_count

    def update(
        self,
        account_id: int,
        account_data: AccountModel | CreateAccountSchema,
    ) -> AccountModel:
        with Session(self.db) as session:
            account = session.query(AccountModel).filter_by(id=account_id).first()
            if not account:
                raise ValueError(f"Account with id {account_id} not found")

            account.name = account_data.name
            account.provider = account_data.provider

            if isinstance(account_data.configuration_parameters, dict):
                account.configuration_parameters = json.dumps(
                    account_data.configuration_parameters,
                    indent=4,
                )
            else:
                account.configuration_parameters = account_data.configuration_parameters

            account.interval_seconds = account_data.interval.total_seconds()

            session.commit()
            session.refresh(account)

            return account

    def delete(self, account_id: int) -> bool:
        with Session(self.db) as session:
            account = session.query(AccountModel).filter_by(id=account_id).first()
            if not account:
                return False

            session.delete(account)
            session.commit()
            return True

    def get_all_accounts_for_chat(
        self,
        chat_id: int,
    ) -> list[AccountModel]:
        with Session(self.db) as session:
            account_chats = (
                session.query(AccountChatModel)
                .filter_by(
                    chat_id=chat_id,
                )
                .all()
            )
            account_ids = [account_chat.account_id for account_chat in account_chats]

            if not account_ids:
                return []

            return (
                session.query(AccountModel)
                .filter(
                    AccountModel.id.in_(account_ids),
                )
                .all()
            )
