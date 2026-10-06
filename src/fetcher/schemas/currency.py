from fetcher.schemas.base import BaseSchema


class CurrencySchema(BaseSchema):
    numerical_code: int
    alpha3: str
    name: str
    symbol: str | None = None
