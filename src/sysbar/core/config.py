"""Typed wrapper over the GSettings schema.

Reads and writes are funnelled through this class so that constrained keys are
always sanitized (see :mod:`sysbar.core.validation`) and the rest of the code
never touches ``Gio.Settings`` directly.
"""

from __future__ import annotations

import gi

gi.require_version("Gio", "2.0")
gi.require_version("GLib", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

from . import validation  # noqa: E402
from .constants import APP_ID  # noqa: E402


class Config:
    """Typed accessor for the Sysbar GSettings schema."""

    def __init__(self, schema_id: str = APP_ID, backend: Gio.SettingsBackend | None = None) -> None:
        if backend is not None:
            self._settings = Gio.Settings(schema_id=schema_id, backend=backend)
        else:
            self._settings = Gio.Settings.new(schema_id)

    @property
    def settings(self) -> Gio.Settings:
        """Underlying ``Gio.Settings`` (for live UI binding)."""
        return self._settings

    def get_bool(self, key: str) -> bool:
        return bool(self._settings.get_boolean(key))

    def set_bool(self, key: str, value: bool) -> None:
        self._settings.set_boolean(key, value)

    def get_int(self, key: str) -> int:
        return int(self._settings.get_int(key))

    def get_string(self, key: str) -> str:
        return str(self._settings.get_string(key))

    def set_string(self, key: str, value: str) -> None:
        self._settings.set_string(key, value)

    @property
    def default_duration_minutes(self) -> int:
        return validation.sanitized_duration(self._settings.get_int("default-duration-minutes"))

    @property
    def battery_limit_percent(self) -> int:
        return validation.sanitized_battery_limit(self._settings.get_int("battery-limit-percent"))

    @property
    def monitor_interval_seconds(self) -> int:
        return validation.sanitized_monitor_interval(
            self._settings.get_int("monitor-interval-seconds")
        )

    @property
    def memory_style(self) -> str:
        return validation.sanitized_memory_style(self._settings.get_string("menu-bar-memory-style"))

    @property
    def temperature_unit(self) -> str:
        return validation.sanitized_temperature_unit(self._settings.get_string("temperature-unit"))

    @property
    def auto_quit_exceptions(self) -> list[str]:
        raw = list(self._settings.get_strv("auto-quit-exceptions"))
        return validation.sanitized_app_id_list(raw)

    @auto_quit_exceptions.setter
    def auto_quit_exceptions(self, values: list[str]) -> None:
        self._settings.set_strv("auto-quit-exceptions", validation.sanitized_app_id_list(values))

    def get_app_volumes(self) -> dict[str, float]:
        """Return persisted per-application volumes, each clamped to [0, 2]."""
        variant = self._settings.get_value("app-volumes")
        return {
            app_id: validation.sanitized_app_volume(volume)
            for app_id, volume in variant.unpack().items()
        }

    def set_app_volume(self, app_id: str, volume: float) -> None:
        """Persist one application's volume, clamped to [0, 2]."""
        volumes = self.get_app_volumes()
        volumes[app_id] = validation.sanitized_app_volume(volume)
        self._settings.set_value("app-volumes", GLib.Variant("a{sd}", volumes))
