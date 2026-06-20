import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from sysbar.core import capabilities
from sysbar.core.capabilities import (
    Capabilities,
    detect_gnome_desktop,
    detect_nvml,
    detect_pipewire_pulse,
    detect_polkit,
    detect_sensors,
    detect_session_x11,
)
from sysbar.core.constants import GNOME_INTERFACE_SCHEMA


def test_has_returns_false_before_refresh() -> None:
    caps = Capabilities(detectors={"session_x11": lambda: True})
    assert caps.has("session_x11") is False


def test_refresh_reflects_detector_results() -> None:
    caps = Capabilities(detectors={"session_x11": lambda: True, "polkit": lambda: False})
    caps.refresh()
    assert caps.has("session_x11") is True
    assert caps.has("polkit") is False


def test_refresh_emits_changed_when_state_flips() -> None:
    flag = {"value": True}
    caps = Capabilities(detectors={"sensors": lambda: flag["value"]})
    seen: list[bool] = []
    caps.connect("changed", lambda _obj: seen.append(True))

    caps.refresh()  # initial all-False -> True: flip
    flag["value"] = False
    caps.refresh()  # True -> False: flip

    assert len(seen) == 2


def test_refresh_does_not_emit_when_state_stable() -> None:
    caps = Capabilities(detectors={"sensors": lambda: True})
    seen: list[bool] = []
    caps.connect("changed", lambda _obj: seen.append(True))

    caps.refresh()
    caps.refresh()

    assert len(seen) == 1


def test_failing_detector_is_treated_as_unavailable() -> None:
    def boom() -> bool:
        raise RuntimeError("probe failed")

    caps = Capabilities(detectors={"upower": boom})
    caps.refresh()
    assert caps.has("upower") is False


def test_unknown_capability_reports_false() -> None:
    caps = Capabilities(detectors={"sensors": lambda: True})
    caps.refresh()
    assert caps.has("does_not_exist") is False


def test_session_x11_true_for_x11_session(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    assert detect_session_x11() is True


def test_session_x11_false_under_wayland(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    assert detect_session_x11() is False


def test_session_x11_false_when_session_type_not_x11(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.setenv("XDG_SESSION_TYPE", "tty")
    assert detect_session_x11() is False


def test_sensors_true_when_hwmon_populated(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / "hwmon0").write_text("data")
    monkeypatch.setattr(capabilities, "HWMON_PATH", tmp_path)
    assert detect_sensors() is True


def test_sensors_falls_back_to_lm_sensors_binary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(capabilities, "HWMON_PATH", tmp_path)  # empty dir
    monkeypatch.setattr("sysbar.core.capabilities.shutil.which", lambda name: "/usr/bin/sensors")
    assert detect_sensors() is True


def test_sensors_false_without_hwmon_or_binary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(capabilities, "HWMON_PATH", tmp_path)
    monkeypatch.setattr("sysbar.core.capabilities.shutil.which", lambda name: None)
    assert detect_sensors() is False


def test_gnome_desktop_true_when_both_schemas_present(monkeypatch: pytest.MonkeyPatch) -> None:
    source = SimpleNamespace(lookup=lambda _schema, _recursive: object())
    monkeypatch.setattr(
        "sysbar.core.capabilities.Gio.SettingsSchemaSource.get_default", lambda: source
    )
    assert detect_gnome_desktop() is True


def test_gnome_desktop_false_when_a_schema_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    present = GNOME_INTERFACE_SCHEMA
    source = SimpleNamespace(
        lookup=lambda schema, _recursive: object() if schema == present else None
    )
    monkeypatch.setattr(
        "sysbar.core.capabilities.Gio.SettingsSchemaSource.get_default", lambda: source
    )
    assert detect_gnome_desktop() is False


def test_gnome_desktop_false_when_no_schema_source(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "sysbar.core.capabilities.Gio.SettingsSchemaSource.get_default", lambda: None
    )
    assert detect_gnome_desktop() is False


def test_polkit_true_when_pkexec_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sysbar.core.capabilities.shutil.which", lambda name: "/usr/bin/pkexec")
    assert detect_polkit() is True


def test_polkit_false_when_pkexec_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sysbar.core.capabilities.shutil.which", lambda name: None)
    assert detect_polkit() is False


def test_proc_net_stats_true_when_ss_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sysbar.core.capabilities.shutil.which", lambda name: "/usr/bin/ss")
    assert capabilities.detect_proc_net_stats() is True


def test_proc_net_stats_false_when_ss_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sysbar.core.capabilities.shutil.which", lambda name: None)
    assert capabilities.detect_proc_net_stats() is False


def test_nvml_false_when_module_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "pynvml", None)  # import raises -> caught
    assert detect_nvml() is False


def test_nvml_true_when_a_device_is_present(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = SimpleNamespace(
        nvmlInit=lambda: None,
        nvmlDeviceGetCount=lambda: 1,
        nvmlShutdown=lambda: None,
    )
    monkeypatch.setitem(sys.modules, "pynvml", fake)
    assert detect_nvml() is True


def test_nvml_false_when_no_devices(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = SimpleNamespace(
        nvmlInit=lambda: None,
        nvmlDeviceGetCount=lambda: 0,
        nvmlShutdown=lambda: None,
    )
    monkeypatch.setitem(sys.modules, "pynvml", fake)
    assert detect_nvml() is False


def test_pipewire_pulse_true_when_server_reachable(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Pulse:
        def __init__(self, _name: str) -> None:
            pass

        def __enter__(self) -> "_Pulse":
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

    monkeypatch.setitem(sys.modules, "pulsectl", SimpleNamespace(Pulse=_Pulse))
    assert detect_pipewire_pulse() is True


def test_pipewire_pulse_false_when_connection_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(_name: str) -> None:
        raise RuntimeError("no pulse server")

    monkeypatch.setitem(sys.modules, "pulsectl", SimpleNamespace(Pulse=_boom))
    assert detect_pipewire_pulse() is False


def test_dbus_name_available_true_when_owner_present(monkeypatch: pytest.MonkeyPatch) -> None:
    result = SimpleNamespace(unpack=lambda: (True,))
    bus = SimpleNamespace(call_sync=lambda *args, **kwargs: result)
    monkeypatch.setattr("sysbar.core.capabilities.Gio.bus_get_sync", lambda _type, _cancel: bus)
    # The mocked bus_get_sync ignores the bus type, so a sentinel suffices here.
    assert capabilities._dbus_name_available(None, "org.x") is True


def test_dbus_name_available_false_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(_type: object, _cancel: object) -> object:
        raise RuntimeError("no bus")

    monkeypatch.setattr("sysbar.core.capabilities.Gio.bus_get_sync", _boom)
    assert capabilities._dbus_name_available(None, "org.x") is False


def test_dbus_backed_detectors_return_false_when_bus_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(_type: object, _cancel: object) -> object:
        raise RuntimeError("no bus")

    monkeypatch.setattr("sysbar.core.capabilities.Gio.bus_get_sync", _boom)
    assert capabilities.detect_appindicator() is False
    assert capabilities.detect_logind() is False
    assert capabilities.detect_upower() is False
    assert capabilities.detect_wayland_window_source() is False
    assert capabilities.detect_global_shortcuts() is False


def test_wayland_window_source_true_when_extension_owns_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = SimpleNamespace(unpack=lambda: (True,))
    bus = SimpleNamespace(call_sync=lambda *args, **kwargs: result)
    monkeypatch.setattr("sysbar.core.capabilities.Gio.bus_get_sync", lambda _type, _cancel: bus)
    assert capabilities.detect_wayland_window_source() is True


def test_global_shortcuts_true_when_portal_present(monkeypatch: pytest.MonkeyPatch) -> None:
    result = SimpleNamespace(unpack=lambda: (True,))
    bus = SimpleNamespace(call_sync=lambda *args, **kwargs: result)
    monkeypatch.setattr("sysbar.core.capabilities.Gio.bus_get_sync", lambda _type, _cancel: bus)
    assert capabilities.detect_global_shortcuts() is True
