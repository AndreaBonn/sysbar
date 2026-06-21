from __future__ import annotations

from sysbar.core.config import Config
from sysbar.services.scenes.adapters import CallbackSceneApplier, ConfigSceneWriter


def test_config_writer_dispatches_by_value_type(compiled_schema: str) -> None:
    config = Config()
    writer = ConfigSceneWriter(config)

    writer.set("alert-enabled", True)
    writer.set("monitor-interval-seconds", 5)
    writer.set("active-scene", "focus")

    assert config.get_bool("alert-enabled") is True
    assert config.get_int("monitor-interval-seconds") == 5
    assert config.get_string("active-scene") == "focus"


def test_config_writer_ignores_unsupported_value_type(compiled_schema: str) -> None:
    config = Config()
    writer = ConfigSceneWriter(config)
    config.settings.set_int("monitor-interval-seconds", 5)

    # A float matches none of bool/int/str, so the write is a silent no-op.
    writer.set("monitor-interval-seconds", 3.5)

    assert config.get_int("monitor-interval-seconds") == 5


def test_callback_applier_routes_each_toggle() -> None:
    calls: dict[str, bool] = {}
    applier = CallbackSceneApplier(
        keep_awake=lambda on: calls.__setitem__("awake", on),
        do_not_disturb=lambda on: calls.__setitem__("dnd", on),
        microphone_muted=lambda on: calls.__setitem__("mic", on),
    )

    applier.set_keep_awake(True)
    applier.set_do_not_disturb(False)
    applier.set_microphone_muted(True)

    assert calls == {"awake": True, "dnd": False, "mic": True}
