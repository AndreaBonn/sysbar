"""Behaviour of the shared feature-module context."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import Any, cast

import pytest

from sysbar.app.context import AppContext


class _FakeCapabilities:
    def __init__(self, present: set[str]) -> None:
        self._present = present

    def has(self, capability: str) -> bool:
        return capability in self._present


def _context(present: set[str]) -> AppContext:
    return AppContext(
        config=cast(Any, object()),
        capabilities=cast(Any, _FakeCapabilities(present)),
        notifier=cast(Any, object()),
        autostart=cast(Any, object()),
    )


def test_has_reports_true_for_a_detected_capability() -> None:
    assert _context({"pipewire_pulse"}).has("pipewire_pulse") is True


def test_has_reports_false_for_a_missing_capability() -> None:
    assert _context({"pipewire_pulse"}).has("session_x11") is False


def test_has_reports_false_when_nothing_is_detected() -> None:
    assert _context(set()).has("pipewire_pulse") is False


def test_context_is_frozen() -> None:
    context = _context(set())

    with pytest.raises(FrozenInstanceError):
        context.config = cast(Any, object())  # type: ignore[misc]


def test_collaborators_are_reachable_by_name() -> None:
    config = object()
    context = AppContext(
        config=cast(Any, config),
        capabilities=cast(Any, _FakeCapabilities(set())),
        notifier=cast(Any, object()),
        autostart=cast(Any, object()),
    )

    assert context.config is config
