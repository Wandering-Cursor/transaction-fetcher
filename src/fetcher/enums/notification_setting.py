from enum import StrEnum
from typing import TYPE_CHECKING

from fetcher.enums.transaction import TransactionType

if TYPE_CHECKING:
    from fetcher.models.transaction import TransactionModel
    from fetcher.schemas.transaction import DBTransactionSchema


class NotificationType(StrEnum):
    BALANCE = "BALANCE"
    ACTIVE = "ACTIVE"
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    UNANSWERED = "UNANSWERED"

    @classmethod
    def from_transaction(
        cls,
        transaction: "DBTransactionSchema | TransactionModel",
    ) -> "NotificationType":
        if transaction.type == TransactionType.DEPOSIT:
            return cls.DEPOSIT
        if transaction.type == TransactionType.WITHDRAWAL:
            return cls.WITHDRAWAL

        raise NotImplementedError
