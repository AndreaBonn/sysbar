"""Boundary error logging without a live D-Bus connection."""

from __future__ import annotations

import logging

import gi
import pytest

gi.require_version("GLib", "2.0")
from gi.repository import GLib  # noqa: E402

from sysbar.services.keep_awake.inhibitor import ScreenSaverInhibitor  # noqa: E402


def test_screensaver_inhibit_failure_logs_context(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    error = GLib.Error("session bus unavailable")

    def unavailable_bus() -> None:
        raise error

    adapter = ScreenSaverInhibitor()
    monkeypatch.setattr(adapter, "_get_session_bus", unavailable_bus)
    with caplog.at_level(logging.WARNING):
        assert adapter.acquire() is None
    record = caplog.records[-1]
    assert record.message == "screensaver inhibit failed"
    assert record.__dict__["error"] == str(error)


def test_screensaver_uninhibit_failure_logs_the_cookie(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A failed UnInhibit leaves the display inhibited until the process exits."""

    class _FailingBus:
        def call_sync(self, *_args: object) -> None:
            raise GLib.Error("name has no owner")

    adapter = ScreenSaverInhibitor()
    monkeypatch.setattr(adapter, "_get_session_bus", _FailingBus)
    with caplog.at_level(logging.WARNING):
        adapter.release(cookie=7)

    assert [record.message for record in caplog.records] == ["screensaver uninhibit failed"]
    assert caplog.records[0].__dict__["cookie"] == 7
