"""Concrete scene ports over Config and injected callables."""

from __future__ import annotations

import gi
import pytest

gi.require_version("Gio", "2.0")
from gi.repository import Gio  # noqa: E402

from sysbar.core.config import Config  # noqa: E402
from sysbar.services.scenes.actions import SystemToggle  # noqa: E402
from sysbar.services.scenes.adapters import (  # noqa: E402
    CallbackAudio,
    CallbackToggles,
    ConfigSettingsWriter,
    SettingWriteError,
    toggle_supported,
)


def _config() -> Config:
    """A config on its own memory backend, so no write survives into another test."""
    return Config(backend=Gio.memory_settings_backend_new())


def test_config_writer_writes_each_type_the_schema_declares(compiled_schema: str) -> None:
    config = _config()
    writer = ConfigSettingsWriter(config)

    writer.set("alert-enabled", True)
    writer.set("monitor-interval-seconds", 5)
    writer.set("active-scene", "focus")

    assert config.get_bool("alert-enabled") is True
    assert config.get_int("monitor-interval-seconds") == 5
    assert config.get_string("active-scene") == "focus"


def test_config_writer_refuses_a_value_type_the_key_cannot_hold(compiled_schema: str) -> None:
    """GSettings rejects the write and returns False without raising.

    Left unchecked that reads as success, and the scene reports an action as
    applied when nothing was written.
    """
    config = _config()
    writer = ConfigSettingsWriter(config)
    config.settings.set_int("monitor-interval-seconds", 5)

    with pytest.raises(SettingWriteError):
        writer.set("monitor-interval-seconds", "abc")

    assert config.get_int("monitor-interval-seconds") == 5


def test_config_writer_refuses_a_value_of_an_unsupported_type(compiled_schema: str) -> None:
    config = _config()
    writer = ConfigSettingsWriter(config)
    config.settings.set_int("monitor-interval-seconds", 5)

    with pytest.raises(SettingWriteError):
        writer.set("monitor-interval-seconds", 3.5)

    assert config.get_int("monitor-interval-seconds") == 5


def test_config_writer_refuses_a_key_the_schema_does_not_have(compiled_schema: str) -> None:
    writer = ConfigSettingsWriter(_config())

    with pytest.raises(SettingWriteError):
        writer.set("no-such-key", True)


def test_config_writer_refuses_a_key_whose_type_a_scene_cannot_write(
    compiled_schema: str,
) -> None:
    """A scene writes scalars; a string list is not one, and saying so beats guessing."""
    writer = ConfigSettingsWriter(_config())

    with pytest.raises(SettingWriteError):
        writer.set("auto-quit-exceptions", "firefox")


def _toggles(calls: dict[str, bool], available: set[SystemToggle]) -> CallbackToggles:
    return CallbackToggles(
        setters={
            SystemToggle.KEEP_AWAKE: lambda on: calls.__setitem__("awake", on),
            SystemToggle.DO_NOT_DISTURB: lambda on: calls.__setitem__("dnd", on),
            SystemToggle.MICROPHONE_MUTED: lambda on: calls.__setitem__("mic", on),
        },
        available=lambda toggle: toggle in available,
    )


def test_callback_toggles_route_each_setter() -> None:
    calls: dict[str, bool] = {}
    toggles = _toggles(calls, set(SystemToggle))

    toggles.set_keep_awake(True)
    toggles.set_do_not_disturb(False)
    toggles.set_microphone_muted(True)

    assert calls == {"awake": True, "dnd": False, "mic": True}


def test_a_toggle_is_supported_only_when_its_backend_is_there() -> None:
    toggles = _toggles({}, {SystemToggle.DO_NOT_DISTURB})

    assert toggles.supports(SystemToggle.DO_NOT_DISTURB) is True
    assert toggles.supports(SystemToggle.MICROPHONE_MUTED) is False


def test_a_toggle_with_no_setter_is_never_supported() -> None:
    toggles = CallbackToggles(setters={}, available=lambda _toggle: True)

    assert toggles.supports(SystemToggle.KEEP_AWAKE) is False


def test_setting_a_toggle_with_no_setter_does_nothing() -> None:
    toggles = CallbackToggles(setters={}, available=lambda _toggle: True)

    toggles.set_keep_awake(True)  # must not raise


def test_callback_audio_reports_what_the_callable_returns() -> None:
    assert CallbackAudio(set_output=lambda _device: True).set_output_device("hdmi") is True
    assert CallbackAudio(set_output=lambda _device: False).set_output_device("hdmi") is False


def test_callback_audio_passes_the_device_through() -> None:
    seen: list[str] = []

    def record(device: str) -> bool:
        seen.append(device)
        return True

    CallbackAudio(set_output=record).set_output_device("alsa.hdmi")

    assert seen == ["alsa.hdmi"]


@pytest.mark.parametrize("dnd_available", [False, True])
@pytest.mark.parametrize("mic_available", [False, True])
@pytest.mark.parametrize("toggle", list(SystemToggle))
def test_toggle_supported_capabilities_select_only_the_matching_backend(
    toggle: SystemToggle, dnd_available: bool, mic_available: bool
) -> None:
    expected = {
        SystemToggle.KEEP_AWAKE: True,
        SystemToggle.DO_NOT_DISTURB: dnd_available,
        SystemToggle.MICROPHONE_MUTED: mic_available,
    }

    assert (
        toggle_supported(toggle, dnd_available=dnd_available, mic_available=mic_available)
        is expected[toggle]
    )
