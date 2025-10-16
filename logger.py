import logging
from typing import cast
from logging import Logger
from config import resource_path

LOG_FILE = resource_path("bucket/app.log")  # adjust path as needed
EXTENDED_LOG_FILE = resource_path("bucket/extended.log")



def legacy_get_logger(name: str) -> Logger:
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



class ExtendedLogger(logging.Logger):
    """
    Custom logger that behaves like a normal logger but provides
    an extra .extended_logging() method for large or raw data dumps.

    - Normal logs go to app.log
    - Extended logs go ONLY to extended.log
    """

    def __init__(self, name: str):
        super().__init__(name, level=logging.INFO)

        if not self.handlers:
            # ─── Normal app log ───
            main_handler = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
            console_handler = logging.StreamHandler()

            formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
            main_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)

            main_handler.setLevel(logging.INFO)
            console_handler.setLevel(logging.INFO)

            self.addHandler(main_handler)
            self.addHandler(console_handler)

            # ─── Extended log ───
            extended_handler = logging.FileHandler(EXTENDED_LOG_FILE, mode="a", encoding="utf-8")
            extended_handler.setLevel(logging.INFO)
            extended_formatter = logging.Formatter(
                "%(asctime)s %(levelname)s [%(name)s] EXTENDED LOG → %(message)s"
            )
            extended_handler.setFormatter(extended_formatter)
            self.extended_handler = extended_handler

    def extended_logging(self, msg: str, data=None, level: int = logging.INFO):
        """
        Logs extended information (raw text, bytes, or structured data)
        into a separate file `extended.log` ONLY.
        """
        # Convert any data type to safe string
        if data is not None:
            try:
                formatted = str(data)
            except Exception:
                formatted = repr(data)
            msg = f"{msg} {formatted} "

        # ✅ Only log to extended.log
        record = self.makeRecord(
            name=self.name,
            level=level,
            fn="",
            lno=0,
            msg=msg,
            args=(),  # empty tuple = type-safe
            exc_info=None
        )
        self.extended_handler.handle(record)



logging.setLoggerClass(ExtendedLogger)
def get_logger(name: str) -> ExtendedLogger:
    return cast(ExtendedLogger, logging.getLogger(name))
