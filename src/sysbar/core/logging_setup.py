"""Structured logging configuration.

JSON output in production (parseable by a log aggregator), human-readable in
development. Logger selection via ``SYSBAR_LOG_FORMAT`` / ``SYSBAR_LOG_LEVEL``.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

_STD_ATTRS = frozenset(logging.makeLogRecord({}).__dict__)


class JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "service": "sysbar",
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _STD_ATTRS and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str | None = None, fmt: str | None = None) -> None:
    """Configure the root logger once, based on environment or arguments.

    Parameters
    ----------
    level
        Log level name; defaults to ``SYSBAR_LOG_LEVEL`` or ``INFO``.
    fmt
        ``"json"`` or ``"human"``; defaults to ``SYSBAR_LOG_FORMAT`` or ``human``.
    """
    resolved_level = (level or os.environ.get("SYSBAR_LOG_LEVEL", "INFO")).upper()
    resolved_fmt = (fmt or os.environ.get("SYSBAR_LOG_FORMAT", "human")).lower()

    handler = logging.StreamHandler()
    if resolved_fmt == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s"))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(resolved_level)
