"""Combined inhibition decisions using concrete in-memory ports."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import pytest

from sysbar.services.keep_awake.combined_inhibitor import CombinedInhibitor
from sysbar.services.keep_awake.ports import WHAT_IDLE_SLEEP


@dataclass
class FakeSleep:
    fd: int | None = 42
    acquired: list[str] = field(default_factory=list)
    released: list[int] = field(default_factory=list)

    def acquire(self, what: str) -> int | None:
        self.acquired.append(what)
        return self.fd

    def release(self, fd: int) -> None:
        self.released.append(fd)


@dataclass
class FakeScreenSaver:
    cookie: int | None = 7
    acquired: int = 0
    released: list[int] = field(default_factory=list)

    def acquire(self) -> int | None:
        self.acquired += 1
        return self.cookie

    def release(self, cookie: int) -> None:
        self.released.append(cookie)


def test_combined_idle_sleep_acquires_and_releases_both() -> None:
    sleep, screensaver = FakeSleep(), FakeScreenSaver()
    combined = CombinedInhibitor(sleep, screensaver)
    token = combined.acquire(what="idle:sleep")
    assert sleep.acquired == ["idle:sleep"]
    assert screensaver.acquired == 1
    assert token is not None
    combined.release(token)
    assert sleep.released == [42]
    assert screensaver.released == [7]


def test_combined_lid_only_acquires_and_releases_sleep() -> None:
    sleep, screensaver = FakeSleep(), FakeScreenSaver()
    combined = CombinedInhibitor(sleep, screensaver)
    token = combined.acquire(what="handle-lid-switch")
    assert sleep.acquired == ["handle-lid-switch"]
    assert screensaver.acquired == 0
    assert token is not None
    combined.release(token)
    assert sleep.released == [42]
    assert screensaver.released == []


def test_combined_both_unavailable_returns_none() -> None:
    sleep, screensaver = FakeSleep(fd=None), FakeScreenSaver(cookie=None)
    combined = CombinedInhibitor(sleep, screensaver)
    assert combined.acquire(what="idle:sleep") is None
    assert sleep.acquired == ["idle:sleep"]
    assert screensaver.acquired == 1


def test_combined_cookie_only_is_released_without_sleep() -> None:
    sleep, screensaver = FakeSleep(fd=None), FakeScreenSaver(cookie=0)
    combined = CombinedInhibitor(sleep, screensaver)
    token = combined.acquire(what="idle:sleep")
    assert token is not None
    combined.release(token)
    assert sleep.acquired == ["idle:sleep"]
    assert sleep.released == []
    assert screensaver.acquired == 1
    assert screensaver.released == [0]


def test_combined_sleep_only_is_released_without_screensaver() -> None:
    sleep, screensaver = FakeSleep(fd=0), FakeScreenSaver(cookie=None)
    combined = CombinedInhibitor(sleep, screensaver)
    token = combined.acquire(what="idle:sleep")
    assert token is not None
    combined.release(token)
    assert sleep.released == [0]
    assert screensaver.acquired == 1
    assert screensaver.released == []


def test_combined_unknown_token_does_not_release_held_parts() -> None:
    sleep, screensaver = FakeSleep(), FakeScreenSaver()
    combined = CombinedInhibitor(sleep, screensaver)
    token = combined.acquire(what="idle:sleep")
    combined.release(token=object())
    assert sleep.released == screensaver.released == []
    assert token is not None
    combined.release(token)
    assert sleep.released == [42]
    assert screensaver.released == [7]


def test_idle_sleep_without_logind_warns_that_the_system_can_still_sleep(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The token stays valid, so keep-awake reads as on: the log must say it is not whole."""
    combined = CombinedInhibitor(FakeSleep(fd=None), FakeScreenSaver())

    with caplog.at_level(logging.WARNING):
        token = combined.acquire(WHAT_IDLE_SLEEP)

    assert token is not None
    assert [record.message for record in caplog.records] == ["partial inhibition"]
    assert caplog.records[0].__dict__["missing"] == "sleep"


def test_idle_sleep_without_screensaver_warns_that_the_display_can_still_blank(
    caplog: pytest.LogCaptureFixture,
) -> None:
    combined = CombinedInhibitor(FakeSleep(), FakeScreenSaver(cookie=None))

    with caplog.at_level(logging.WARNING):
        combined.acquire(WHAT_IDLE_SLEEP)

    assert [record.message for record in caplog.records] == ["partial inhibition"]
    assert caplog.records[0].__dict__["missing"] == "screensaver"


def test_idle_sleep_with_both_parts_logs_nothing(caplog: pytest.LogCaptureFixture) -> None:
    combined = CombinedInhibitor(FakeSleep(), FakeScreenSaver())

    with caplog.at_level(logging.WARNING):
        combined.acquire(WHAT_IDLE_SLEEP)

    assert caplog.records == []


def test_lid_inhibition_never_counts_the_screensaver_as_missing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    combined = CombinedInhibitor(FakeSleep(), FakeScreenSaver(cookie=None))

    with caplog.at_level(logging.WARNING):
        combined.acquire("handle-lid-switch")

    assert caplog.records == []
