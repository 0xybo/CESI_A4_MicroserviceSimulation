"""Error handling utilities."""

from src.Common.Utils.logger import get_logger

logger = get_logger(__name__)


def log_error(message: str) -> None:
    """Log an error message using the application logger.

    Args:
        message: The error message to display.
    """
    logger.error("Application error: %s", message)
