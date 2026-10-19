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
