import argparse
from logging import Logger

from src.aibot.utils.logger import setup_logger


def _parse_args_and_setup_logging() -> Logger:
    """Parse command line arguments and set up logging configuration.

    This function initializes argument parsing for command line options
    and sets up the logging configuration for the application.

    Returns
    -------
    logging.Logger
        Configured logger instance with the log level specified
        by the --log command line argument.

    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--log",
        default="INFO",
    )

    args = parser.parse_args()

    # mypy cannot correctly infer this type
    return setup_logger(args.log)  # type: ignore[no-any-return]


logger = _parse_args_and_setup_logging()
