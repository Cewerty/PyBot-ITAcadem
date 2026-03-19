# src/pybot/core/logger.py
from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from loguru import logger as loguru_logger

from .config import settings

if TYPE_CHECKING:
    from loguru import Logger


def setup_logger() -> Logger:
    """Настроить единый человекочитаемый sink для логов приложения."""
    loguru_logger.remove()
    loguru_logger.add(
        sys.stdout,
        level=settings.log_level.upper(),
        format=(
            "<green>{time:DD-MM-YYYY HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        colorize=True,
    )
    return loguru_logger
