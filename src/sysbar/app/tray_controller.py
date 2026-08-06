"""The tray item: its label, its menu, and when either is rebuilt.

The menu tree itself is built by the pure :mod:`sysbar.app.tray.menu_builder`,
which has a hard invariant: the node count must not change between updates or
the dbusmenu host recycles ids and stale state bleeds across rows. Nothing here
may make the tree's shape depend on runtime data; this module only decides
*when* to hand a freshly valued tree over.
"""

from __future__ import annotations

import logging

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio  # noqa: E402

from . import tray_state  # noqa: E402
from .context import AppContext  # noqa: E402
from .features import Features  # noqa: E402
from .tray.menu_builder import MenuActions, build_menu_items  # noqa: E402
from .tray.menu_model import MenuModel  # noqa: E402
from .tray.tray import Tray  # noqa: E402
from .tray_renderer import render_tray_label  # noqa: E402

_LABEL_SEPARATOR = " · "

log = logging.getLogger(__name__)


class TrayController:
    """Owns the tray item and keeps its label and menu in step with state."""

    def __init__(self, context: AppContext, features: Features, actions: MenuActions) -> None:
        self._context = context
        self._features = features
        self._actions = actions
        self._tray: Tray | None = None

    def register(self, connection: Gio.DBusConnection | None) -> None:
        """Publish the tray item, or log and stay silent without a session bus."""
        if connection is None:
            log.warning("no session bus connection; tray unavailable")
            return
        self._tray = Tray(
            on_activate=self._actions.open_panel,
            on_menu_about_to_show=self._on_menu_about_to_show,
        )
        self._tray.register(connection)
        self.refresh_menu()

    def refresh_menu(self) -> None:
        if self._tray is not None:
            self._tray.set_menu(self._build_menu())

    def refresh_label(self) -> None:
        if self._tray is None:
            return
        segments = [
            segment
            for segment in (self._features.keep_awake.countdown_text(), self._metric_label())
            if segment
        ]
        self._tray.set_label(_LABEL_SEPARATOR.join(segments))

    def sync_sampling(self) -> None:
        """Tell the monitor whether the tray still needs samples, then redraw."""
        self._features.monitor.set_tray_active(tray_state.wants_tray_sampling(self._context.config))
        self.refresh_label()
        self.refresh_menu()

    def _metric_label(self) -> str:
        snapshot = self._features.monitor.latest
        if snapshot is None:
            return ""
        return render_tray_label(snapshot, tray_state.tray_options(self._context.config))

    def _build_menu(self) -> MenuModel:
        config = self._context.config
        features = self._features
        snapshot = features.monitor.latest
        return MenuModel(
            build_menu_items(
                tray_state.menu_metrics(snapshot, tray_state.tray_options(config)),
                device_rows=tray_state.menu_device_rows(config, snapshot),
                keep_awake_on=features.keep_awake.is_active,
                shelf_enabled=features.shelf.is_enabled,
                clipboard_enabled=features.clipboard.is_enabled,
                toggles=features.toggles.state(),
                actions=self._actions,
                scenes=features.scenes.menu_entries(),
            )
        )

    def _on_menu_about_to_show(self) -> bool:
        """Rebuild with fresh values just before the dropdown opens.

        Returning ``True`` only when the dropdown actually carries live content
        lets the host re-read the layout on demand instead of churning it on
        every sample.
        """
        config = self._context.config
        if (
            not tray_state.has_menu_metrics(config)
            and not self._features.toggles.any_available
            and not config.show_device_batteries
        ):
            return False
        self.refresh_menu()
        return True
