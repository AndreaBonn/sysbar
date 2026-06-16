from collections.abc import Callable

from sysbar import __version__
from sysbar.core.capabilities import Capabilities
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
