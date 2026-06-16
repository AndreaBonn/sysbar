import json
import logging

from sysbar.core.logging_setup import JsonFormatter


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
