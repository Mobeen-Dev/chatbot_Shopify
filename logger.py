import logging
from logging import Logger
from config import resource_path

LOG_FILE = resource_path("bucket/app.log")  # adjust path as needed

def get_logger(name: str) -> Logger:
    """
    Returns a logger that writes INFO+ to both console and a log file.

    - name: typically `__name__` of the module.
    - Creates handlers only once per logger to avoid duplicate lines.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # If the logger already has handlers, we assume it's already configured.
    if logger.handlers:
        return logger

    # 1) File handler
    file_handler = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.INFO)

    # 2) Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # 3) Shared formatter
    fmt = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    formatter = logging.Formatter(fmt)

    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # 4) Attach handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
