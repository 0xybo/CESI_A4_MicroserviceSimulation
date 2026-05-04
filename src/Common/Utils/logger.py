"""
Centralized logging configuration for the Microservice Simulation framework.
Logs are saved to the .logs folder with fixed simulation and error files.
"""

import logging
from datetime import datetime
from pathlib import Path


class _MicrosecondFormatter(logging.Formatter):
    """Formatter that supports ``%f`` in ``datefmt``."""

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        if datefmt is None:
            return super().formatTime(record, datefmt)
        return datetime.fromtimestamp(record.created).strftime(datefmt)


class _AnsiColorFormatter(_MicrosecondFormatter):
    """Apply ANSI colors to console log records."""

    DATE_COLOR = "\033[90m"
    COLORS = {
        logging.DEBUG: "\033[36m",
        logging.INFO: "\033[32m",
        logging.WARNING: "\033[33m",
        logging.ERROR: "\033[31m",
        logging.CRITICAL: "\033[1;31m",
    }
    ORIGIN_COLOR = "\033[35m"
    MESSAGE_COLOR = "\033[37m"
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record, self.datefmt)
        level = record.levelname
        origin = record.name
        message = record.getMessage()

        if record.exc_info:
            message = f"{message}\n{self.formatException(record.exc_info)}"
        if record.stack_info:
            message = f"{message}\n{self.formatStack(record.stack_info)}"

        level_color = self.COLORS.get(record.levelno, "")
        timestamp_text = f"{self.DATE_COLOR}{timestamp}{self.RESET}"
        level_text = f"{level_color}{level}{self.RESET}" if level_color else level
        origin_text = f"{self.ORIGIN_COLOR}{origin}{self.RESET}"
        message_text = f"{self.MESSAGE_COLOR}{message}{self.RESET}"

        return f"{timestamp_text} - {level_text} - {origin_text} - {message_text}"


def _build_file_handler(path: Path, level: int, formatter: logging.Formatter) -> logging.Handler:
    handler = logging.FileHandler(path, mode="a", encoding="utf-8")
    handler.setLevel(level)
    handler.setFormatter(formatter)
    return handler


def setup_logger(name: str, log_level: str = "INFO") -> logging.Logger:
    """
    Set up a logger with both file and console handlers.

    Args:
        name: Logger name (typically __name__)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger()
    resolved_level = getattr(logging, log_level.upper(), logging.INFO)

    # Prevent duplicate handlers
    if logger.handlers:
        logger.setLevel(resolved_level)
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(
                handler, logging.FileHandler
            ):
                handler.setLevel(resolved_level)
        return logging.getLogger(name)

    logger.setLevel(resolved_level)

    # Create .logs directory if it doesn't exist
    logs_dir = Path.cwd() / ".logs"
    logs_dir.mkdir(exist_ok=True, parents=True)

    # Create formatters
    detailed_formatter = _MicrosecondFormatter(
        fmt=(
            "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d]"
            " - %(funcName)s() - %(message)s"
        ),
        datefmt="%Y-%m-%d %H:%M:%S.%f",
    )

    simple_format = "%(asctime)s - %(levelname)s - %(message)s"
    simple_datefmt = "%Y-%m-%d %H:%M:%S.%f"

    # Merged file handler - all logs in one file
    merged_handler = _build_file_handler(logs_dir / "app.log", logging.DEBUG, detailed_formatter)
    logger.addHandler(merged_handler)

    # Console handler - info and above
    console_handler = logging.StreamHandler()
    console_handler.setLevel(resolved_level)
    console_handler.setFormatter(_AnsiColorFormatter(fmt=simple_format, datefmt=simple_datefmt))
    logger.addHandler(console_handler)

    return logging.getLogger(name)


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Global logger for the application
app_logger = setup_logger(__name__)
