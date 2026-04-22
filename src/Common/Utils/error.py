"""Error handling utilities."""

import sys
from src.Common.Utils.logger import get_logger

logger = get_logger(__name__)


def print_error(message: str) -> None:
    """Print an error message and exit.

    Args:
        message: The error message to display.
    """
    logger.error(f"Application error: {message}")
    print(f"Error: {message}")
    sys.exit(1)
