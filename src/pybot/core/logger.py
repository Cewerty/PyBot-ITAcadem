# src/pybot/core/logger.py
from __future__ import annotations

import json
import sys
import traceback
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, TextIO

from loguru import logger as loguru_logger

from .config import AppSettings, get_settings

if TYPE_CHECKING:
    from loguru import Logger, Message

type JsonPrimitive = str | int | float | bool | None
type JsonValue = JsonPrimitive | list[JsonValue] | dict[str, JsonValue]


_HUMAN_FORMAT = (
    "<green>{time:DD-MM-YYYY HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)


def setup_logger(settings: AppSettings | None = None) -> Logger:
    """Configure the application logger sink based on LOG_FORMAT setting.

    When LOG_FORMAT=json (recommended for production), emits structured
    newline-delimited JSON to stdout — suitable for log collectors such as
    Loki, CloudWatch, or ELK.

    When LOG_FORMAT=text (default for local development), emits coloured
    human-readable output to stdout.

    If LOG_FORMAT is not set explicitly, AppSettings derives the default from
    BOT_MODE: text for test/dev and json for prod.
    """
    runtime_settings = settings or get_settings()
    loguru_logger.remove()

    if runtime_settings.log_format == "json":
        loguru_logger.add(
            _make_json_sink(sys.stdout),
            level=runtime_settings.log_level.upper(),
            colorize=False,
        )
    else:
        loguru_logger.add(
            sys.stdout,
            level=runtime_settings.log_level.upper(),
            format=_HUMAN_FORMAT,
            colorize=True,
        )

    return loguru_logger


def _make_json_sink(stream: TextIO) -> Callable[[Message], None]:
    def sink(message: Message) -> None:
        payload = json.dumps(_build_json_record(message.record), ensure_ascii=False, default=str)
        _write_json_line(stream, payload)

    return sink


def _build_json_record(record: Mapping[str, object]) -> dict[str, JsonValue]:
    level = record["level"]
    file = record["file"]
    process = record["process"]
    thread = record["thread"]
    elapsed = record["elapsed"]

    payload: dict[str, JsonValue] = {
        "timestamp": _format_timestamp(record["time"]),
        "level": _get_attr(level, "name"),
        "level_no": _get_int_attr(level, "no"),
        "record_level_name": _get_attr(level, "name"),
        "message": str(record["message"]),
        "logger": str(record["name"]),
        "module": str(record["module"]),
        "function": str(record["function"]),
        "line": _to_json_value(record["line"]),
        "file": _get_attr(file, "name"),
        "path": _get_attr(file, "path"),
        "process_id": _get_int_attr(process, "id"),
        "process_name": _get_attr(process, "name"),
        "thread_id": _get_int_attr(thread, "id"),
        "thread_name": _get_attr(thread, "name"),
        "elapsed_ms": _format_elapsed_ms(elapsed),
    }
    payload.update(_flatten_extra(record.get("extra")))
    payload.update(_format_exception(record.get("exception")))
    return payload


def _flatten_extra(extra: object) -> dict[str, JsonValue]:
    if not isinstance(extra, Mapping):
        return {}

    flattened: dict[str, JsonValue] = {"extra": _to_json_value(extra)}
    protected_keys = set(_build_json_base_keys())
    for key, value in extra.items():
        field_name = str(key)
        if field_name in protected_keys:
            field_name = f"extra_{field_name}"
        flattened[field_name] = _to_json_value(value)
    return flattened


def _build_json_base_keys() -> tuple[str, ...]:
    return (
        "timestamp",
        "level",
        "level_no",
        "record_level_name",
        "message",
        "logger",
        "module",
        "function",
        "line",
        "file",
        "path",
        "process_id",
        "process_name",
        "thread_id",
        "thread_name",
        "elapsed_ms",
        "exception_type",
        "exception_message",
        "exception_traceback",
    )


def _format_exception(exception: object) -> dict[str, JsonValue]:
    if exception is None:
        return {}

    exception_type = getattr(exception, "type", None)
    exception_value = getattr(exception, "value", None)
    exception_traceback = getattr(exception, "traceback", None)
    exception_type_name = getattr(exception_type, "__name__", None)
    traceback_lines = traceback.format_exception(exception_type, exception_value, exception_traceback)
    return {
        "exception_type": str(exception_type_name or exception_type),
        "exception_message": str(exception_value),
        "exception_traceback": "".join(traceback_lines),
    }


def _format_timestamp(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _format_elapsed_ms(value: object) -> JsonValue:
    if isinstance(value, timedelta):
        return round(value.total_seconds() * 1000, 3)
    return _to_json_value(value)


def _get_attr(value: object, name: str) -> str:
    return str(getattr(value, name))


def _get_int_attr(value: object, name: str) -> int:
    return int(getattr(value, name))


def _to_json_value(value: object) -> JsonValue:
    if value is None or isinstance(value, str | int | float | bool):
        result = value
    elif isinstance(value, datetime):
        result = value.isoformat()
    elif isinstance(value, timedelta):
        result = round(value.total_seconds() * 1000, 3)
    elif isinstance(value, Enum):
        result = _to_json_value(value.value)
    elif isinstance(value, Path):
        result = str(value)
    elif isinstance(value, Mapping):
        result = {str(key): _to_json_value(item) for key, item in value.items()}
    elif isinstance(value, list | tuple | set | frozenset):
        result = [_to_json_value(item) for item in value]
    else:
        result = str(value)

    return result


def _write_json_line(stream: TextIO, payload: str) -> None:
    line = f"{payload}\n"
    if stream is sys.stdout:
        stream.buffer.write(line.encode("utf-8"))
        stream.flush()
        return

    stream.write(line)
    stream.flush()
