"""Root entry point that delegates to src module."""

from src.__main__ import main
from src.Common.Utils.logger import setup_logger

logger = setup_logger(__name__)

if __name__ == "__main__":
    logger.info("Starting Microservice Simulation Application")
    try:
        main()
        logger.info("Application completed successfully")
    except Exception as e:
        logger.error(f"Application failed with error: {e}", exc_info=True)
        raise
