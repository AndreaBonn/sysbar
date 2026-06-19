from dataclasses import dataclass

import psutil
import pytest

from sysbar.support.sensors_dump import run_sensors_dump


@dataclass
class _Reading:
    label: str
    current: float


def test_dump_includes_header(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(psutil, "sensors_temperatures", lambda: {})
    monkeypatch.setattr(psutil, "sensors_fans", lambda: {})
    report = run_sensors_dump()
    assert report.startswith("Sysbar sensors dump")


def test_temperatures_rendered_with_chip_label_and_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        psutil,
        "sensors_temperatures",
        lambda: {"coretemp": [_Reading(label="Core 0", current=54.0)]},
    )
    monkeypatch.setattr(psutil, "sensors_fans", lambda: {})
    report = run_sensors_dump()
    assert "  coretemp/Core 0: 54.0 C" in report


def test_temperature_without_label_uses_chip_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        psutil, "sensors_temperatures", lambda: {"acpitz": [_Reading(label="", current=40.0)]}
    )
    monkeypatch.setattr(psutil, "sensors_fans", lambda: {})
    report = run_sensors_dump()
    assert "  acpitz/acpitz: 40.0 C" in report


def test_fans_rendered_with_rpm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(psutil, "sensors_temperatures", lambda: {})
    monkeypatch.setattr(
        psutil, "sensors_fans", lambda: {"thinkpad": [_Reading(label="fan1", current=1200.0)]}
    )
    report = run_sensors_dump()
    assert "  thinkpad/fan1: 1200.0 RPM" in report


def test_empty_temperatures_reports_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(psutil, "sensors_temperatures", lambda: {})
    monkeypatch.setattr(psutil, "sensors_fans", lambda: {})
    report = run_sensors_dump()
    assert "Temperatures: none reported" in report
    assert "Fans: none reported" in report


def test_missing_sensors_api_reports_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delattr(psutil, "sensors_temperatures", raising=False)
    monkeypatch.delattr(psutil, "sensors_fans", raising=False)
    report = run_sensors_dump()
    assert "Temperatures: none reported" in report
    assert "Fans: none reported" in report
