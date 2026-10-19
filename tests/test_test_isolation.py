"""The suite must never write to the desktop session of whoever runs it."""

from __future__ import annotations

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio  # noqa: E402

from sysbar.core.config import Config  # noqa: E402


def test_default_settings_backend_is_in_memory_not_dconf() -> None:
    """A ``Config()`` built without a backend must not reach the user's dconf.

    Several tests construct the default ``Config()`` (scene adapters, window
    smoke tests). Against dconf they would overwrite the developer's real
    Sysbar settings and leak values from one run into the next.
    """
    backend = Gio.SettingsBackend.get_default()

    assert type(backend).__gtype__.name == "GMemorySettingsBackend"


def test_writes_through_a_default_config_stay_in_process(compiled_schema: str) -> None:
    config = Config()

    config.set_int("monitor-interval-seconds", 7)

    assert Config().get_int("monitor-interval-seconds") == 7
    config.settings.reset("monitor-interval-seconds")
