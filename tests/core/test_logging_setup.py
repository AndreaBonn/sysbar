import json
import logging
import sys
from collections.abc import Iterator

import pytest

from sysbar.core.logging_setup import JsonFormatter, configure_logging


def _record(**kwargs: object) -> logging.LogRecord:
    record = logging.LogRecord(
        name="sysbar.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello %s",
        args=("world",),
        exc_info=None,
    )
    for key, value in kwargs.items():
        setattr(record, key, value)
    return record


def test_json_formatter_emits_core_fields() -> None:
    payload = json.loads(JsonFormatter().format(_record()))
    assert payload["level"] == "INFO"
    assert payload["service"] == "sysbar"
    assert payload["logger"] == "sysbar.test"
    assert payload["message"] == "hello world"
    assert "timestamp" in payload


def test_json_formatter_includes_extra_fields() -> None:
    payload = json.loads(JsonFormatter().format(_record(request_id="abc-123")))
    assert payload["request_id"] == "abc-123"


def test_json_formatter_is_single_line() -> None:
    formatted = JsonFormatter().format(_record())
    assert "\n" not in formatted


def test_json_formatter_includes_exception_traceback() -> None:
    try:
        raise ValueError("explode")
    except ValueError:
        exc_info = sys.exc_info()
    record = _record()
    record.exc_info = exc_info
    payload = json.loads(JsonFormatter().format(record))
    assert "ValueError: explode" in payload["exception"]


@pytest.fixture
def _restore_root_logger() -> Iterator[None]:
    root = logging.getLogger()
    saved_handlers = root.handlers[:]
    saved_level = root.level
    yield
    root.handlers[:] = saved_handlers
    root.setLevel(saved_level)


def test_configure_logging_json_format_uses_json_formatter(
    _restore_root_logger: None,
) -> None:
    configure_logging(level="DEBUG", fmt="json")
    handler = logging.getLogger().handlers[0]
    assert isinstance(handler.formatter, JsonFormatter)
    assert logging.getLogger().level == logging.DEBUG


def test_configure_logging_human_format_uses_plain_formatter(
    _restore_root_logger: None,
) -> None:
    configure_logging(level="WARNING", fmt="human")
    handler = logging.getLogger().handlers[0]
    assert isinstance(handler.formatter, logging.Formatter)
    assert not isinstance(handler.formatter, JsonFormatter)
    assert logging.getLogger().level == logging.WARNING


def test_configure_logging_reads_level_and_format_from_env(
    monkeypatch: pytest.MonkeyPatch, _restore_root_logger: None
) -> None:
    monkeypatch.setenv("SYSBAR_LOG_LEVEL", "error")
    monkeypatch.setenv("SYSBAR_LOG_FORMAT", "json")
    configure_logging()
    assert isinstance(logging.getLogger().handlers[0].formatter, JsonFormatter)
    assert logging.getLogger().level == logging.ERROR


def test_configure_logging_replaces_existing_handlers(_restore_root_logger: None) -> None:
    configure_logging(level="INFO", fmt="human")
    configure_logging(level="INFO", fmt="human")
    assert len(logging.getLogger().handlers) == 1
