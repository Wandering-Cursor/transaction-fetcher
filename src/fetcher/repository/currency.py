import json

from fetcher.logger import main_logger
from fetcher.schemas.currency import CurrencySchema


class CurrencyRepository:
    def __init__(self) -> None:
        try:
            currencies = json.load(open("currencies.json", encoding="utf-8"))  # noqa: SIM115
        except FileNotFoundError:
            currencies = {}

        self.currencies: list[CurrencySchema] = []
        for currency in currencies:
            try:
                self.currencies.append(CurrencySchema.model_validate(currency))
            except ValueError as e:
                main_logger.warning(
                    {
                        "msg": "Failed to load currency",
                        "currency": currency,
                        "error": e,
                    }
                )

        self.numerical_code_map = {c.numerical_code: c for c in self.currencies}
        self.alpha_code_map = {c.alpha3: c for c in self.currencies}

    def get_by_numerical(self, numerical_code: int) -> CurrencySchema:
        return self.numerical_code_map.get(numerical_code)

    def get_by_alpha(self, alpha_code: str) -> CurrencySchema:
        return self.alpha_code_map.get(alpha_code)
