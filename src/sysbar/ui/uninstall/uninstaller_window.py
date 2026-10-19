"""Uninstaller window: find an app, review what it left behind, move it to trash.

Boundary code wiring the uninstaller service to GTK. User residue always goes
to the trash; system package removal is an explicit, separate switch, shown
only when polkit allows it. Nothing is chosen or scanned until the user picks
an app (U1), and the destructive button stays off until there is something to
move (U2). Wording lives in :mod:`sysbar.app.uninstall_content`.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gio", "2.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, Gtk  # noqa: E402

from ...app.uninstall_content import (  # noqa: E402
    category_label,
    filter_apps,
    package_subtitle,
    removal_summary,
    short_path,
)
from ...core.i18n import _  # noqa: E402
from ...services.metrics import metric_format as mf  # noqa: E402
from ...services.uninstall.app_uninstaller import AppUninstaller  # noqa: E402
from ...services.uninstall.identifier import PackageQuery, identify  # noqa: E402
from ...services.uninstall.models import AppTarget, Leftover  # noqa: E402

_WINDOW_WIDTH = 560
_WINDOW_HEIGHT = 680
_APP_LIST_HEIGHT = 220
_GENERIC_APP_ICON = "application-x-executable-symbolic"


class UninstallerWindow(Adw.Window):
    """Select an installed application and remove its residue."""

    def __init__(self, uninstaller: AppUninstaller, query: PackageQuery) -> None:
        super().__init__(title=_("Remove an app"))
        self.set_default_size(_WINDOW_WIDTH, _WINDOW_HEIGHT)
        self._uninstaller = uninstaller
        self._query = query
        self._apps = sorted(
            (app for app in Gio.AppInfo.get_all() if app.should_show()),
            key=lambda app: app.get_display_name().lower(),
        )
        self._shown: list[Gio.AppInfo] = []
        self._target: AppTarget | None = None
        self._switches: list[tuple[Leftover, Adw.SwitchRow]] = []
        self._search = Gtk.SearchEntry(placeholder_text=_("Search installed apps…"))
        self._app_list = Gtk.ListBox(css_classes=["boxed-list"])
        self._residue_group = Adw.PreferencesGroup(title=_("Files left behind"))
        self._package_switch = Adw.SwitchRow(title=_("Also remove the system package"))
        self._status = Gtk.Label(wrap=True, justify=Gtk.Justification.CENTER)
        self._remove_button = Gtk.Button(css_classes=["destructive-action", "pill"])
        self._build_ui()
        self._fill_app_list()
        self._update_summary()

    def _build_ui(self) -> None:
        page = Adw.PreferencesPage()
        page.add(self._chooser_group())
        page.add(self._residue_group)
        self._package_group = Adw.PreferencesGroup(visible=False)
        self._package_group.add(self._package_switch)
        page.add(self._package_group)
        page.add(self._actions_group())
        self._residue_group.set_visible(False)
        self._package_switch.set_sensitive(False)
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())
        toolbar.set_content(page)
        self.set_content(toolbar)

    def _chooser_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title=_("App to remove"))
        self._search.connect("search-changed", lambda _entry: self._fill_app_list())
        self._app_list.connect("row-activated", self._on_app_chosen)
        scroller = Gtk.ScrolledWindow(
            min_content_height=_APP_LIST_HEIGHT, max_content_height=_APP_LIST_HEIGHT
        )
        scroller.set_child(self._app_list)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.append(self._search)
        box.append(scroller)
        group.add(box)
        return group

    def _actions_group(self) -> Adw.PreferencesGroup:
        self._remove_button.connect("clicked", self._on_remove)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin_top=8)
        box.append(self._status)
        box.append(self._remove_button)
        group = Adw.PreferencesGroup()
        group.add(box)
        return group

    # --- choosing an app ---------------------------------------------------

    def _fill_app_list(self) -> None:
        self._app_list.remove_all()
        names = [app.get_display_name() for app in self._apps]
        self._shown = [self._apps[i] for i in filter_apps(names, self._search.get_text())]
        for app in self._shown:
            # Plain text: an app name with "&" or "<" is not Pango markup.
            row = Adw.ActionRow(title=app.get_display_name(), activatable=True, use_markup=False)
            icon = app.get_icon()
            image = Gtk.Image(gicon=icon) if icon is not None else Gtk.Image()
            if icon is None:
                image.set_from_icon_name(_GENERIC_APP_ICON)
            row.add_prefix(image)
            self._app_list.append(row)

    def _on_app_chosen(self, _list: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
        index = row.get_index()
        if not 0 <= index < len(self._shown):
            return
        self._target = self._target_for(self._shown[index])
        self._populate_residue()

    def _target_for(self, app_info: Gio.AppInfo) -> AppTarget:
        app_id = app_info.get_id() or ""
        if app_id.endswith(".desktop"):
            app_id = app_id[:-8]
        executable = app_info.get_executable()
        exec_path = shutil.which(executable) if executable else None
        manager, ref = identify(exec_path, app_id or None, self._query)
        return AppTarget(
            name=app_info.get_display_name(),
            app_id=app_id or None,
            exec_path=exec_path,
            manager=manager,
            package_ref=ref,
        )

    # --- leftovers ---------------------------------------------------------

    def _populate_residue(self) -> None:
        if self._target is None:
            return
        for _leftover, row in self._switches:
            self._residue_group.remove(row)
        self._switches.clear()
        home = str(Path.home())
        for leftover in self._uninstaller.scan(self._target):
            row = Adw.SwitchRow(
                title=category_label(leftover.category),
                subtitle=f"{mf.format_bytes(leftover.size_bytes)} · "
                f"{short_path(str(leftover.path), home=home)}",
                active=True,
            )
            row.connect("notify::active", lambda _row, _param: self._update_summary())
            self._residue_group.add(row)
            self._switches.append((leftover, row))
        self._residue_group.set_visible(True)
        self._residue_group.set_description(
            _("Leftovers of {app}. They go to the Trash, so you can still restore them.").format(
                app=self._target.name
            )
        )
        self._show_package_row(self._target)
        self._update_summary()

    def _show_package_row(self, target: AppTarget) -> None:
        self._package_group.set_visible(True)
        removable = self._uninstaller.can_remove_package(target)
        self._package_switch.set_sensitive(removable)
        self._package_switch.set_active(False)
        self._package_switch.set_subtitle(
            package_subtitle(target.manager, target.package_ref, removable=removable)
        )

    def _selected(self) -> list[Leftover]:
        return [leftover for leftover, row in self._switches if row.get_active()]

    def _update_summary(self) -> None:
        selected = self._selected()
        summary = removal_summary(
            chosen=self._target is not None,
            count=len(selected),
            size_bytes=sum(leftover.size_bytes for leftover in selected),
        )
        self._status.set_label(summary.status)
        self._remove_button.set_label(summary.button)
        self._remove_button.set_sensitive(summary.can_remove)

    def _on_remove(self, _button: Gtk.Button) -> None:
        result = self._uninstaller.remove(self._selected(), self._package_switch.get_active())
        self._populate_residue()
        freed = mf.format_bytes(result.freed_bytes)
        if result.failed:
            message = _("Freed {size}; {count} items could not be moved").format(
                size=freed, count=len(result.failed)
            )
        else:
            message = _("Done: {size} moved to the Trash").format(size=freed)
        self._status.set_label(message)
