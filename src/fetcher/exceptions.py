class NotAdminError(Exception):
    """Exception raised when a user is not an admin."""

    def __init__(self, message: object) -> None:
        super().__init__(message)
        self.message = message


class TransactionFetchError(Exception):
    """Raised when transactions cannot be fetched for an account."""

    def __init__(
        self,
        account_id: int,
        account_name: str,
        provider: object,
        original_exception: Exception,
    ) -> None:
        self.account_id = account_id
        self.account_name = account_name
        self.provider = provider
        self.original_exception = original_exception
        super().__init__(
            f"Could not fetch transactions for account {account_id} ({account_name}) via {provider}"
        )
