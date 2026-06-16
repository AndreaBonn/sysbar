import gi

gi.require_version("Gio", "2.0")
import pytest  # noqa: E402
from gi.repository import Gio  # noqa: E402

from sysbar.core.config import Config  # noqa: E402
from sysbar.core.constants import APP_ID  # noqa: E402


@pytest.fixture
def config(compiled_schema: str) -> Config:
    return Config(backend=Gio.memory_settings_backend_new())


def test_defaults_match_schema(config: Config) -> None:
    assert config.battery_limit_percent == 10
    assert config.monitor_interval_seconds == 2
    assert config.memory_style == "percent"
    assert config.temperature_unit == "celsius"
    assert config.auto_quit_exceptions == ["org.gnome.Nautilus"]


def test_invalid_stored_interval_is_sanitized_on_read(config: Config) -> None:
    config.settings.set_int("monitor-interval-seconds", 3)
    assert config.monitor_interval_seconds == 2


def test_invalid_stored_battery_limit_is_sanitized_on_read(config: Config) -> None:
    config.settings.set_int("battery-limit-percent", 7)
    assert config.battery_limit_percent == 10


def test_set_app_volume_persists_clamped(config: Config) -> None:
    config.set_app_volume("org.example.App", 3.0)
    assert config.get_app_volumes() == {"org.example.App": 2.0}


def test_set_app_volume_round_trips_multiple_apps(config: Config) -> None:
    config.set_app_volume("a", 0.5)
    config.set_app_volume("b", 1.5)
    assert config.get_app_volumes() == {"a": 0.5, "b": 1.5}


def test_auto_quit_exceptions_setter_sanitizes(config: Config) -> None:
    config.auto_quit_exceptions = [" org.gnome.Nautilus ", "", "x", "x"]
    assert config.auto_quit_exceptions == ["org.gnome.Nautilus", "x"]


def test_get_bool_round_trips(config: Config) -> None:
    config.set_bool("hotkey-enabled", True)
    assert config.get_bool("hotkey-enabled") is True
    config.set_bool("hotkey-enabled", False)
    assert config.get_bool("hotkey-enabled") is False


def test_get_int_reads_stored_value(config: Config) -> None:
    config.settings.set_int("onboarding-step", 4)
    assert config.get_int("onboarding-step") == 4


def test_get_string_round_trips(config: Config) -> None:
    config.set_string("app-language", "it")
    assert config.get_string("app-language") == "it"


def test_default_duration_minutes_is_sanitized(config: Config) -> None:
    config.settings.set_int("default-duration-minutes", 30)
    assert config.default_duration_minutes == 30


def test_constructs_without_backend_from_installed_schema(compiled_schema: str) -> None:
    # Exercises the no-backend branch: the schema resolves via GSETTINGS_SCHEMA_DIR.
    config = Config(schema_id=APP_ID)
    assert isinstance(config.settings, Gio.Settings)
