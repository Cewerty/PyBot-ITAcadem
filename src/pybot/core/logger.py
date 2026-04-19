# src/pybot/core/logger.py
from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from loguru import logger as loguru_logger

from .config import settings

if TYPE_CHECKING:
    from loguru import Logger

_HUMAN_FORMAT = (
    "<green>{time:DD-MM-YYYY HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)


def setup_logger() -> Logger:
    """Configure the application logger sink based on LOG_FORMAT setting.

    When LOG_FORMAT=json (recommended for production), emits structured
    newline-delimited JSON to stdout — suitable for log collectors such as
    Loki, CloudWatch, or ELK.

    When LOG_FORMAT=text (default, recommended for local development), emits
    coloured human-readable output to stdout.
    """
    loguru_logger.remove()

    if settings.log_format == "json":
        loguru_logger.add(
            sys.stdout,
            level=settings.log_level.upper(),
            serialize=True,
            colorize=False,
        )
    else:
        loguru_logger.add(
            sys.stdout,
            level=settings.log_level.upper(),
            format=_HUMAN_FORMAT,
            colorize=True,
        )

    return loguru_logger
