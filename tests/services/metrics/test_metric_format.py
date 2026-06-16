from sysbar.services.metrics import metric_format as mf


def test_celsius_to_fahrenheit_freezing() -> None:
    assert mf.celsius_to_fahrenheit(0.0) == 32.0


def test_celsius_to_fahrenheit_boiling() -> None:
    assert mf.celsius_to_fahrenheit(100.0) == 212.0


def test_format_temperature_celsius_rounds() -> None:
    assert mf.format_temperature(54.4, "celsius") == "54°C"


def test_format_temperature_fahrenheit() -> None:
    assert mf.format_temperature(100.0, "fahrenheit") == "212°F"


def test_format_bytes_zero() -> None:
    assert mf.format_bytes(0) == "0 B"


def test_format_bytes_kilobytes() -> None:
    assert mf.format_bytes(2048) == "2.0 KB"


def test_format_bytes_megabytes() -> None:
    assert mf.format_bytes(int(2.1 * 1024 * 1024)) == "2.1 MB"


def test_format_rate_appends_per_second() -> None:
    assert mf.format_rate(2.1 * 1024 * 1024) == "2.1 MB/s"


def test_format_percent_rounds() -> None:
    assert mf.format_percent(22.6) == "23%"


def test_format_uptime_days_hours_minutes() -> None:
    assert mf.format_uptime(2 * 86400 + 3 * 3600 + 15 * 60) == "2d 3h 15m"


def test_format_uptime_minutes_only() -> None:
    assert mf.format_uptime(45 * 60) == "45m"


def test_format_uptime_zero() -> None:
    assert mf.format_uptime(0) == "0m"
