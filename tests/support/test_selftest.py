from collections.abc import Callable

import pytest

from sysbar import __version__
from sysbar.core.capabilities import Capabilities
from sysbar.support import selftest
from sysbar.support.selftest import run_selftest


def _const(value: bool) -> Callable[[], bool]:
    return lambda: value


def _capabilities(**values: bool) -> Capabilities:
    caps = Capabilities(detectors={name: _const(v) for name, v in values.items()})
    caps.refresh()
    return caps


def test_selftest_reports_version() -> None:
    report = run_selftest(_capabilities(session_x11=True))
    assert __version__ in report


def test_selftest_marks_available_capability() -> None:
    report = run_selftest(_capabilities(pipewire_pulse=True))
    line = next(line for line in report.splitlines() if "pipewire_pulse" in line)
    assert "[ok ]" in line


def test_selftest_marks_unavailable_capability() -> None:
    report = run_selftest(_capabilities(polkit=False))
    line = next(line for line in report.splitlines() if "polkit" in line)
    assert "[-- ]" in line


def test_selftest_lists_missing_capabilities() -> None:
    report = run_selftest(_capabilities(logind=False))
    assert "logind" in report.split("depend on:")[-1]


def test_selftest_all_available_reports_no_degradation() -> None:
    full = dict.fromkeys(selftest._FEATURE_HINTS, True)
    report = run_selftest(_capabilities(**full))
    assert "All capabilities available." in report


def test_selftest_probes_capabilities_when_none_provided(monkeypatch: pytest.MonkeyPatch) -> None:
    class StubCapabilities:
        def __init__(self) -> None:
            self.refreshed = False

        def refresh(self) -> bool:
            self.refreshed = True
            return True

        def snapshot(self) -> dict[str, bool]:
            return {"sensors": True}

    monkeypatch.setattr(selftest, "Capabilities", StubCapabilities)
    report = run_selftest()
    assert __version__ in report
    assert "sensors" in report
