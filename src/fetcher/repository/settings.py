from typing import Literal

import pydantic
import pydantic_settings
import pytz


class Settings(pydantic_settings.BaseSettings):
    DB_URL: pydantic.AnyUrl = pydantic.Field(
        default=pydantic.AnyUrl("sqlite:///./test.db"),
        description="Database URL. Can be a SQLite, PostgreSQL, or MySQL URL. Tested only with SQLite.",  # noqa: E501
    )

    TELEGRAM_MANAGEMENT_CHAT_ID: int = pydantic.Field(
        description="Chat ID of the manager. The one who's responsible for configuring the bot.",
    )
    TELEGRAM_BOT_TOKEN: str = pydantic.Field(
        description="Token for the telegram bot. You can get it from @BotFather.",
    )

    MAIN_LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = pydantic.Field(
        default="INFO",
        description="Log level for the main logger.",
    )
    DB_LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = pydantic.Field(
        default="WARNING",
        description="Log level for the database logger.",
    )

    @property
    def default_timezone(self):  # noqa: ANN201
        return pytz.timezone("Europe/Kyiv")

    model_config = pydantic_settings.SettingsConfigDict(
        env_prefix="transaction_fetcher_",
        env_file=".env",
    )


settings = Settings()  # pyright: ignore[reportCallIssue]
