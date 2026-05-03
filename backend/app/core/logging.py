"""Structured stdout logging for the API and workers.

`configure_logging()` should run once at process startup (e.g. FastAPI lifespan
or `main` in a worker) before other modules emit logs. It applies
`EmojiFormatter` for quick visual scanning and sets the root level from
`settings.LOG_LEVEL`.

Use `get_logger(__name__)` in modules for hierarchical logger names.
"""

import logging
import sys
from logging.config import dictConfig

from app.core.config import settings


class EmojiFormatter(logging.Formatter):
    """Prefix log lines with a short emoji derived from `LogRecord.levelname`."""

    LEVEL_EMOJI: dict[int, str] = {
        logging.DEBUG: "🐛",
        logging.INFO: "ℹ️",
        logging.WARNING: "⚠️",
        logging.ERROR: "❌",
        logging.CRITICAL: "🔥",
    }

    def format(self, record: logging.LogRecord) -> str:
        record.levelemoji = self.LEVEL_EMOJI.get(record.levelno, "📌")
        return super().format(record)


def configure_logging() -> None:
    """Apply dictConfig: console handler, emoji format, uvicorn log levels."""

    log_config: dict = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": EmojiFormatter,
                "fmt": "%(asctime)s | %(levelemoji)s %(levelname)-8s | %(name)s | %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": sys.stdout,
            },
        },
        "root": {
            "level": settings.LOG_LEVEL,
            "handlers": ["console"],
        },
        "loggers": {
            "uvicorn": {"level": settings.LOG_LEVEL, "propagate": True, "handlers": []},
            "uvicorn.error": {"level": settings.LOG_LEVEL, "propagate": True, "handlers": []},
            "uvicorn.access": {"level": settings.LOG_LEVEL, "propagate": True, "handlers": []},
        },
    }
    dictConfig(log_config)


def get_logger(name: str) -> logging.Logger:
    """Return the standard library logger for `name` (typically `__name__`)."""

    return logging.getLogger(name)
