import logging
from pathlib import Path


def _basic_config(level: int) -> None:
    log_file = "./logs/aibot.log"

    # create log folder if not exists
    Path("./logs").mkdir(exist_ok=True)

    file_handler = logging.FileHandler(log_file)
    stream_handler = logging.StreamHandler()

    logging.basicConfig(
        level=level,
        # e.g. [2025-10-17 00:12:26 - target_file:496 - DEBUG] mesage
        format="[%(asctime)s - %(name)s:%(lineno)d - %(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[file_handler, stream_handler],
    )


def setup_logger(level: str) -> logging.Logger:
    """Set up and configure a logger with the specified log level.

    Parameters
    ----------
    level : str
        The logging level specified as a string (case-insensitive).
        Valid string values:
        - 'DEBUG'
        - 'INFO'
        - 'WARNING'
        - 'ERROR'
        - 'CRITICAL'

    Returns
    -------
    Logger
        Configured logger instance with the specified log level.

    Raises
    ------
    TypeError
        If the provided log level is not a valid string value.
    """
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        msg = f"Invalid log level: {level}"
        raise TypeError(msg)

    _basic_config(numeric_level)

    return logging.getLogger(__name__)
