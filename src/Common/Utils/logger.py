"""
Centralized logging configuration for the Microservice Simulation framework.
Logs are saved to .logs folder with different levels: DEBUG, INFO, WARNING, ERROR
"""

import logging
import logging.handlers
from pathlib import Path
from datetime import datetime


def setup_logger(name: str, log_level: str = "INFO") -> logging.Logger:
    """
    Set up a logger with both file and console handlers.

    Args:
        name: Logger name (typically __name__)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Create .logs directory if it doesn't exist
    logs_dir = Path.cwd() / ".logs"
    logs_dir.mkdir(exist_ok=True, parents=True)

    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt=(
            "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d]"
            " - %(funcName)s() - %(message)s"
        ),
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    simple_formatter = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # File handler - all logs
    log_file = logs_dir / f"simulation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10_000_000, backupCount=5  # 10MB
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)

    # Error file handler - errors and warnings only
    error_log_file = logs_dir / f"errors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file, maxBytes=10_000_000, backupCount=5
    )
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(detailed_formatter)
    logger.addHandler(error_handler)

    # Console handler - info and above
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)

    return logger


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
app_logger = setup_logger("MicroserviceSimulation")
