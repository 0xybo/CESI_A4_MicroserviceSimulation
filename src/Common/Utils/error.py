"""Error handling utilities."""

import sys


def print_error(message: str) -> None:
    """Print an error message and exit.

    Args:
        message: The error message to display.
    """
    print(f"Error: {message}")
    sys.exit(1)
