from __future__ import annotations

import gi

gi.require_version("Gio", "2.0")
import pytest  # noqa: E402
from gi.repository import Gio  # noqa: E402

from sysbar.app.onboarding_content import (  # noqa: E402
    AUTO_QUIT,
    TOP_BAR_ICON,
    describe_capabilities,
    set_top_bar_metrics,
    top_bar_metrics_shown,
    tray_icon_blocked,
)
from sysbar.core.capabilities import (  # noqa: E402
    APPINDICATOR,
    GLOBAL_SHORTCUTS,
    GNOME_DESKTOP,
    LOGIND,
    PIPEWIRE_PULSE,
    POLKIT,
    SENSORS,
    SESSION_X11,
    UPOWER,
    WAYLAND_WINDOW_SOURCE,
)
from sysbar.core.config import Config  # noqa: E402

_EVERYTHING = {
    SESSION_X11: True,
    WAYLAND_WINDOW_SOURCE: False,
    APPINDICATOR: True,
    SENSORS: True,
    PIPEWIRE_PULSE: True,
    GNOME_DESKTOP: True,
    LOGIND: True,
    UPOWER: True,
    GLOBAL_SHORTCUTS: True,
    POLKIT: True,
}


def test_a_complete_system_lists_every_feature_as_ready_and_nothing_missing() -> None:
    report = describe_capabilities(_EVERYTHING)

    assert TOP_BAR_ICON in report.ready
    assert AUTO_QUIT in report.ready
    assert len(report.ready) == 9
    assert report.missing == ()


def test_a_missing_feature_comes_with_a_reason_and_leaves_the_ready_list() -> None:
    report = describe_capabilities({**_EVERYTHING, SENSORS: False})

    assert "Temperatures" not in report.ready
    assert [item.title for item in report.missing] == ["Temperatures"]
    assert report.missing[0].hint


def test_auto_quit_is_ready_on_wayland_with_the_shell_extension() -> None:
    state = {**_EVERYTHING, SESSION_X11: False, WAYLAND_WINDOW_SOURCE: True}

    assert AUTO_QUIT in describe_capabilities(state).ready


def test_auto_quit_on_wayland_without_the_extension_says_how_to_enable_it() -> None:
    state = {**_EVERYTHING, SESSION_X11: False, WAYLAND_WINDOW_SOURCE: False}

    missing = describe_capabilities(state).missing

    assert [item.title for item in missing] == [AUTO_QUIT]
    assert "gnome-extensions enable" in missing[0].hint


def test_an_unknown_state_counts_as_missing_rather_than_ready() -> None:
    report = describe_capabilities({})

    assert report.ready == ()
    assert len(report.missing) == 9


def test_tray_icon_is_blocked_only_without_a_status_notifier_host() -> None:
    assert tray_icon_blocked({APPINDICATOR: False}) is True
    assert tray_icon_blocked({APPINDICATOR: True}) is False


@pytest.fixture
def config(compiled_schema: str) -> Config:
    return Config(backend=Gio.memory_settings_backend_new())


def test_starter_metrics_follow_the_new_install_default(config: Config) -> None:
    assert top_bar_metrics_shown(config) is True


def test_turning_starter_metrics_off_hides_cpu_and_memory_only(config: Config) -> None:
    config.settings.set_string("menu-bar-network-placement", "menu")

    set_top_bar_metrics(config, shown=False)

    assert config.metric_placement("cpu") == "off"
    assert config.metric_placement("memory") == "off"
    assert config.metric_placement("network") == "menu"
    assert top_bar_metrics_shown(config) is False


def test_turning_starter_metrics_on_puts_both_in_the_bar(config: Config) -> None:
    set_top_bar_metrics(config, shown=False)

    set_top_bar_metrics(config, shown=True)

    assert config.metric_placement("cpu") == "bar"
    assert config.metric_placement("memory") == "bar"
