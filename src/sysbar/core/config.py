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
from .constants import APP_ID, PLACEMENT_BAR, TRAY_METRICS  # noqa: E402


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
    def alert_enabled(self) -> bool:
        return self.get_bool("alert-enabled")

    @property
    def alert_cpu_percent(self) -> int:
        return validation.sanitized_alert_percent(self._settings.get_int("alert-cpu-percent"))

    @property
    def alert_cpu_seconds(self) -> int:
        return validation.sanitized_alert_cpu_seconds(self._settings.get_int("alert-cpu-seconds"))

    @property
    def alert_memory_percent(self) -> int:
        return validation.sanitized_alert_percent(self._settings.get_int("alert-memory-percent"))

    @property
    def alert_disk_percent(self) -> int:
        return validation.sanitized_alert_percent(self._settings.get_int("alert-disk-percent"))

    @property
    def alert_temperature_celsius(self) -> int:
        return validation.sanitized_alert_temperature(
            self._settings.get_int("alert-temperature-celsius")
        )

    @property
    def alert_battery_percent(self) -> int:
        return validation.sanitized_alert_percent(self._settings.get_int("alert-battery-percent"))

    def metric_placement(self, metric: str) -> str:
        """Return where a tray metric is shown: ``off``, ``bar`` or ``menu``."""
        raw = self._settings.get_string(f"menu-bar-{metric}-placement")
        return validation.sanitized_placement(raw)

    def migrate_legacy_placements(self) -> None:
        """Seed placement keys from the deprecated boolean tray keys, once.

        For each metric whose placement was never set by the user, a legacy
        ``menu-bar-<metric>`` set to ``true`` becomes ``bar``. Idempotent: a
        placement chosen by the user (including ``off``) is never overwritten.
        """
        for metric in TRAY_METRICS:
            placement_key = f"menu-bar-{metric}-placement"
            if self._settings.get_user_value(placement_key) is not None:
                continue
            if self._settings.get_boolean(f"menu-bar-{metric}"):
                self._settings.set_string(placement_key, PLACEMENT_BAR)

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
