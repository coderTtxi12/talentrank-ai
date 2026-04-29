import logging
import sys
from logging.config import dictConfig

from app.core.config import settings


class EmojiFormatter(logging.Formatter):
    """Adds a per-level emoji to each log line."""

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
    """Configure application-wide logging."""

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
    return logging.getLogger(name)
