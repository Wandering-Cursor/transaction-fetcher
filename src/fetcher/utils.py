import functools
import logging
from collections.abc import Callable
from decimal import Decimal
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def handle_service_exception(
    service_name: str,
    logger: logging.Logger,
) -> Callable[[F], F]:
    """
    Decorator to handle exceptions in service run() methods.

    Args:
        service_name: The name of the service for logging purposes
        logger: The logger to use for error logging
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
            try:
                return func(*args, **kwargs)
            except Exception as e:
                from fetcher.services.chat import get_chat_service  # noqa: PLC0415

                logger.critical(
                    f"Error in {service_name}: {e}",
                    stack_info=True,
                    exc_info=True,
                )
                get_chat_service().notify_management(
                    text=f"Error in {service_name}",
                    exception=e,
                )
                raise

        return wrapper  # type: ignore[return-value]

    return decorator


def amount_with_spaces(amount: Decimal) -> str:
    """Format a decimal number with spaces as thousands separators."""
    return f"{amount:,.2f}".replace(",", " ")


def amount_with_sign_and_space(amount: Decimal) -> str:
    """Format a decimal number with a sign and space as thousands separators."""
    sign = "+" if amount >= 0 else "-"
    return f"{sign} {amount_with_spaces(abs(amount))}"


def amount_with_sign(amount: Decimal) -> str:
    """Format a decimal number with a sign as thousands separators."""
    sign = "+" if amount >= 0 else "-"
    return f"{sign} {abs(amount):.2f}"
