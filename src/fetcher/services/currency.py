from fetcher.repository.currency import CurrencyRepository
from fetcher.schemas.currency import CurrencySchema


class CurrencyService:
    def __init__(self, repository: "CurrencyRepository") -> None:
        self.repository = repository

    def from_numerical(self, numerical_code: int) -> CurrencySchema:
        return self.repository.get_by_numerical(numerical_code)

    def from_alpha(self, alpha_code: str) -> CurrencySchema:
        return self.repository.get_by_alpha(alpha_code)


currency_service = CurrencyService(CurrencyRepository())


def get_currency_by_numerical_code(numerical_code: int) -> CurrencySchema:
    return currency_service.from_numerical(numerical_code)


def get_currency_by_alpha_code(alpha_code: str) -> CurrencySchema:
    return currency_service.from_alpha(alpha_code)
