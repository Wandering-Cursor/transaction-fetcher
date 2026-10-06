from typing import TYPE_CHECKING, TypeVar

import httpx

from fetcher.schemas.base import BaseSchema

if TYPE_CHECKING:
    from fetcher.models.account import AccountModel
    from fetcher.schemas.account import BalanceSchema
    from fetcher.schemas.transaction import TransactionSchema


class BaseAccountProviderConfiguration(BaseSchema):
    pass


ProviderConfigurationType = TypeVar(
    "ProviderConfigurationType",
    bound=BaseAccountProviderConfiguration,
)


class BaseAccountProvider:
    def get_configuration_type(self) -> ProviderConfigurationType:
        return BaseAccountProviderConfiguration

    def __init__(self, account: "AccountModel") -> None:
        self._account = account
        self._configuration = self.get_configuration_type().model_validate(
            account.configuration,
        )

        self.http_client = self._make_http_client()

    @property
    def base_url(self) -> str:
        raise NotImplementedError()

    def _make_http_client(self) -> "httpx.Client":
        return httpx.Client(
            base_url=self.base_url,
            timeout=30,
            headers={
                "User-Agent": "CardInfoBot/3.0",
            },
        )

    def get_transactions(self) -> list["TransactionSchema"]:
        raise NotImplementedError("Method not implemented")

    def get_balance(self) -> "BalanceSchema | None":
        raise NotImplementedError("Method not implemented")

    def update_account_data(self) -> dict | None:
        return None
