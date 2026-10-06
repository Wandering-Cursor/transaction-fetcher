from typing import TYPE_CHECKING

from sqlalchemy.orm import Session, joinedload

from fetcher.exceptions import TransactionFetchError
from fetcher.logger import main_logger
from fetcher.models.transaction import TransactionModel
from fetcher.providers.account.get import get_provider_class
from fetcher.schemas.transaction import DBTransactionSchema

if TYPE_CHECKING:
    import sqlalchemy

    from fetcher.models.account import AccountModel
    from fetcher.schemas.account import BalanceSchema
    from fetcher.schemas.transaction import TransactionSchema


class TransactionRepository:
    def __init__(self, db: "sqlalchemy.engine.Engine") -> None:
        self.db = db

    def get_transaction_by_id(
        self,
        transaction_id: int,
        db_session: "Session | None" = None,
    ) -> "TransactionModel | None":
        session = db_session if db_session else Session(self.db)

        transaction = (
            session.query(TransactionModel)
            .options(
                joinedload(
                    TransactionModel.account,
                )
            )
            .get(transaction_id)
        )

        if not db_session:
            session.close()

        return transaction

    def transaction_exists(
        self,
        account: "AccountModel",
        transaction: "TransactionSchema",
        db_session: "Session | None" = None,
    ) -> bool:
        session = db_session if db_session else Session(self.db)

        exists = (
            session.query(TransactionModel)
            .filter(
                TransactionModel.account_id == account.id,
                TransactionModel.unique_id == transaction.unique_id,
            )
            .count()
            > 0
        )

        if not db_session:
            session.close()

        return exists

    def fetch_transaction_by_account(
        self,
        account: "AccountModel",
    ) -> list["TransactionSchema"]:
        provider_class = get_provider_class(account.provider)

        integration = provider_class(account)

        try:
            result = integration.get_transactions()

            main_logger.debug(
                {
                    "msg": "Fetched transactions",
                    "account.id": account.id,
                    "account.name": account.name,
                    "provider": account.provider,
                    "len(result)": len(result),
                    "result": result,
                }
            )

            return result
        except Exception as e:
            main_logger.exception(
                {
                    "msg": "Error fetching transactions",
                    "account": account,
                    "provider": account.provider,
                    "error": e,
                }
            )

            raise TransactionFetchError(
                account_id=account.id,
                account_name=account.name,
                provider=account.provider,
                original_exception=e,
            ) from e

    def store_transactions(
        self,
        account: "AccountModel",
        account_transactions: list["TransactionSchema"],
    ) -> list["DBTransactionSchema"]:
        new_transactions = []

        with Session(self.db) as session:
            for transaction in account_transactions:
                if self.transaction_exists(
                    account,
                    transaction,
                    db_session=session,
                ):
                    continue

                optional = {}
                if transaction.description:
                    optional["description"] = transaction.description
                if transaction.at_time:
                    optional["at_time"] = transaction.at_time

                # Default to UAH
                currency_code = 980
                if transaction.currency:
                    currency_code = transaction.currency.numerical_code

                transaction_model = TransactionModel(
                    account_id=account.id,
                    unique_id=transaction.unique_id,
                    currency=currency_code,
                    type=transaction.type,
                    amount=transaction.amount,
                    **optional,
                )
                session.add(transaction_model)

                session.commit()

                session.refresh(transaction_model)

                main_logger.debug(
                    {
                        "msg": "Inserted new transaction",
                        "account": {
                            "id": account.id,
                            "name": account.name,
                        },
                        "transaction": transaction,
                        "transaction_model": transaction_model,
                    }
                )

                new_transactions.append(DBTransactionSchema.model_validate(transaction_model))

        main_logger.info(
            {
                "msg": "Fetched transactions",
                "len(new_transactions)": len(new_transactions),
                "new_transactions": new_transactions,
            }
        )

        return new_transactions

    def get_balance(
        self,
        account: "AccountModel",
    ) -> "BalanceSchema | None":
        provider_class = get_provider_class(account.provider)
        integration = provider_class(account)

        try:
            balance = integration.get_balance()
        except NotImplementedError:
            main_logger.warning(
                {
                    "msg": "Balance fetching not implemented",
                    "account": account,
                    "provider": account.provider,
                }
            )
            return None

        if not balance:
            return None

        return balance
