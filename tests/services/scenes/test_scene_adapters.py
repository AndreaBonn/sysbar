"""Concrete scene ports over Config and injected callables."""

from __future__ import annotations

from sysbar.core.config import Config
from sysbar.services.scenes.actions import SystemToggle
from sysbar.services.scenes.adapters import CallbackAudio, CallbackToggles, ConfigSettingsWriter


def test_config_writer_dispatches_by_value_type(compiled_schema: str) -> None:
    config = Config()
    writer = ConfigSettingsWriter(config)

    writer.set("alert-enabled", True)
    writer.set("monitor-interval-seconds", 5)
    writer.set("active-scene", "focus")

    assert config.get_bool("alert-enabled") is True
    assert config.get_int("monitor-interval-seconds") == 5
    assert config.get_string("active-scene") == "focus"


def test_config_writer_ignores_unsupported_value_type(compiled_schema: str) -> None:
    config = Config()
    writer = ConfigSettingsWriter(config)
    config.settings.set_int("monitor-interval-seconds", 5)

    # A float matches none of bool/int/str, so the write is a silent no-op.
    writer.set("monitor-interval-seconds", 3.5)

    assert config.get_int("monitor-interval-seconds") == 5


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
