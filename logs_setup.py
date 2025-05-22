import logging
import logging.config

from enum import Enum

from datetime import datetime


class LogFiles(Enum):
    ALL = "logs/all.log"  # путь до файла debug логирования
    INFO = "logs/info.log"  # путь до файла info логирования
    ERROR = "logs/err_warn.log"  # путь до файла логирования ошибок


# уровень логирования в консоль
CONSOLE_LOGGING_LEVEL = "DEBUG"
# Настройка формата логирования
LOGGING_SETUP = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "log_formatter": {
            "format": "[{asctime}][{levelname}] ::: {filename}({lineno}) -> {message}",
            "style": "{",
        },
    },
    "handlers": {
        "all_file": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": LogFiles.ALL.value,
            "formatter": "log_formatter",
        },
        "info_file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": LogFiles.INFO.value,
            "formatter": "log_formatter",
        },
        "error_file": {
            "level": "WARNING",
            "class": "logging.FileHandler",
            "filename": LogFiles.ERROR.value,
            "formatter": "log_formatter",
        },
        "console": {
            "level": CONSOLE_LOGGING_LEVEL,
            "class": "logging.StreamHandler",
            "formatter": "log_formatter",
        },
    },
    "loggers": {
        "logger": {
            "handlers": ["all_file", "info_file", "error_file", "console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}


# Logging setup
logging.config.dictConfig(LOGGING_SETUP)
logging.basicConfig(
    format="[%(asctime)s][%(levelname)s] ::: %(filename)s(%(lineno)d) -> %(message)s",
    level="DEBUG",
    filename=LogFiles.ALL.value,
)
logger = logging.getLogger("logger")


def new_session_log():
    for log_file in (LogFiles.ALL.value, LogFiles.INFO.value, LogFiles.ERROR.value):
        with open(log_file, "a") as log:
            log.write(f"{'=' * 25}\nNew app session\n[{datetime.now()}]\n{'=' * 25}\n")
