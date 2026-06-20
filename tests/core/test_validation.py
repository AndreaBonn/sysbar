import pytest

from sysbar.core import validation


@pytest.mark.parametrize("value", [0, 15, 30, 60, 120, 240, 480])
def test_sanitized_duration_allowed_kept(value: int) -> None:
    assert validation.sanitized_duration(value) == value


@pytest.mark.parametrize("value", [-1, 7, 45, 1000])
def test_sanitized_duration_invalid_returns_default(value: int) -> None:
    assert validation.sanitized_duration(value) == 0


@pytest.mark.parametrize("value", [0, 5, 10, 15, 20])
def test_sanitized_battery_limit_allowed_kept(value: int) -> None:
    assert validation.sanitized_battery_limit(value) == value


@pytest.mark.parametrize("value", [1, 3, 25, 100])
def test_sanitized_battery_limit_invalid_returns_default(value: int) -> None:
    assert validation.sanitized_battery_limit(value) == 10


@pytest.mark.parametrize("value", [1, 2, 5])
def test_sanitized_monitor_interval_allowed_kept(value: int) -> None:
    assert validation.sanitized_monitor_interval(value) == value


def test_sanitized_monitor_interval_invalid_returns_default() -> None:
    assert validation.sanitized_monitor_interval(3) == 2


@pytest.mark.parametrize("value", [0, 1, 50, 100])
def test_sanitized_alert_percent_in_range_kept(value: int) -> None:
    assert validation.sanitized_alert_percent(value) == value


@pytest.mark.parametrize(("value", "expected"), [(-5, 0), (150, 100), (101, 100)])
def test_sanitized_alert_percent_clamped(value: int, expected: int) -> None:
    assert validation.sanitized_alert_percent(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"), [(-1, 0), (0, 0), (30, 30), (3600, 3600), (9999, 3600)]
)
def test_sanitized_alert_cpu_seconds_clamped(value: int, expected: int) -> None:
    assert validation.sanitized_alert_cpu_seconds(value) == expected


@pytest.mark.parametrize(("value", "expected"), [(-10, 0), (85, 85), (200, 150)])
def test_sanitized_alert_temperature_clamped(value: int, expected: int) -> None:
    assert validation.sanitized_alert_temperature(value) == expected


@pytest.mark.parametrize("value", ["dot", "percent", "both"])
def test_sanitized_memory_style_allowed_kept(value: str) -> None:
    assert validation.sanitized_memory_style(value) == value


def test_sanitized_memory_style_invalid_returns_default() -> None:
    assert validation.sanitized_memory_style("rainbow") == "percent"


@pytest.mark.parametrize("value", ["celsius", "fahrenheit"])
def test_sanitized_temperature_unit_allowed_kept(value: str) -> None:
    assert validation.sanitized_temperature_unit(value) == value


def test_sanitized_temperature_unit_invalid_returns_default() -> None:
    assert validation.sanitized_temperature_unit("kelvin") == "celsius"


@pytest.mark.parametrize("value", ["off", "bar", "menu"])
def test_sanitized_placement_allowed_kept(value: str) -> None:
    assert validation.sanitized_placement(value) == value


def test_sanitized_placement_invalid_returns_default() -> None:
    assert validation.sanitized_placement("statusbar") == "off"


def test_sanitized_app_volume_clamps_low() -> None:
    assert validation.sanitized_app_volume(-0.5) == 0.0


def test_sanitized_app_volume_clamps_high() -> None:
    assert validation.sanitized_app_volume(3.0) == 2.0


def test_sanitized_app_volume_keeps_in_range() -> None:
    assert validation.sanitized_app_volume(1.25) == 1.25


def test_sanitized_app_id_list_trims_dedupes_drops_empty() -> None:
    result = validation.sanitized_app_id_list([" org.gnome.Nautilus ", "", "a", "a", "  "])
    assert result == ["org.gnome.Nautilus", "a"]


def test_sanitized_app_id_list_preserves_order() -> None:
    assert validation.sanitized_app_id_list(["c", "a", "b", "a"]) == ["c", "a", "b"]
