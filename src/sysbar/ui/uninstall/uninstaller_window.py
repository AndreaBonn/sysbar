"""Uninstaller window: pick an app, review residue, move it to trash.

Boundary code wiring the uninstaller service to GTK. User residue always goes
to the trash; system package removal is an explicit, separately-confirmed
switch, shown only when polkit allows it.
"""

from __future__ import annotations

import shutil

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gio", "2.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, Gtk  # noqa: E402

from ...services.metrics import metric_format as mf  # noqa: E402
from ...services.uninstall.app_uninstaller import AppUninstaller  # noqa: E402
from ...services.uninstall.identifier import PackageQuery, identify  # noqa: E402
from ...services.uninstall.models import AppTarget, Leftover  # noqa: E402

_WINDOW_WIDTH = 560
_WINDOW_HEIGHT = 620


class UninstallerWindow(Adw.Window):
    """Select an installed application and remove its residue."""

    def __init__(self, uninstaller: AppUninstaller, query: PackageQuery) -> None:
        super().__init__(title="Uninstall application")
        self.set_default_size(_WINDOW_WIDTH, _WINDOW_HEIGHT)
        self._uninstaller = uninstaller
        self._query = query
        self._apps = sorted(
            (app for app in Gio.AppInfo.get_all() if app.should_show()),
            key=lambda app: app.get_display_name().lower(),
        )
        self._target: AppTarget | None = None
        self._switches: list[tuple[Leftover, Adw.SwitchRow]] = []
        self._build_ui()

    def _build_ui(self) -> None:
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())
        self._page = Adw.PreferencesPage()

        chooser = Adw.PreferencesGroup(title="Application")
        self._dropdown = Gtk.DropDown.new_from_strings(
            [app.get_display_name() for app in self._apps]
        )
        self._dropdown.connect("notify::selected", self._on_selected)
        row = Adw.ActionRow(title="Installed app")
        row.add_suffix(self._dropdown)
        chooser.add(row)
        self._page.add(chooser)

        self._residue_group = Adw.PreferencesGroup(title="Residue")
        self._page.add(self._residue_group)

        self._package_switch = Adw.SwitchRow(title="Also remove the system package")
        self._package_group = Adw.PreferencesGroup()
        self._package_group.add(self._package_switch)
        self._page.add(self._package_group)

        self._status = Gtk.Label(label="")
        self._remove_button = Gtk.Button(
            label="Move residue to Trash", css_classes=["destructive-action"]
        )
        self._remove_button.connect("clicked", self._on_remove)
        actions = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin_top=8)
        actions.append(self._status)
        actions.append(self._remove_button)
        box = Adw.PreferencesGroup()
        box.add(actions)
        self._page.add(box)

        toolbar.set_content(self._page)
        self.set_content(toolbar)
        self._on_selected(self._dropdown, None)

    def _on_selected(self, dropdown: Gtk.DropDown, _param: object) -> None:
        index = dropdown.get_selected()
        if index < 0 or index >= len(self._apps):
            return
        self._target = self._target_for(self._apps[index])
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

    def _populate_residue(self) -> None:
        if self._target is None:
            return
        for _leftover, row in self._switches:
            self._residue_group.remove(row)
        self._switches.clear()

        leftovers = self._uninstaller.scan(self._target)
        for leftover in leftovers:
            row = Adw.SwitchRow(
                title=leftover.category.value,
                subtitle=f"{leftover.path} · {mf.format_bytes(leftover.size_bytes)}",
                active=True,
            )
            self._residue_group.add(row)
            self._switches.append((leftover, row))

        can_remove = self._uninstaller.can_remove_package(self._target)
        self._package_switch.set_sensitive(can_remove)
        self._package_switch.set_active(False)
        self._package_switch.set_subtitle(
            f"{self._target.manager.value}: {self._target.package_ref}"
            if can_remove
            else "Not available (manual install or no authorization)"
        )
        self._status.set_label(f"{len(leftovers)} item(s) found")

    def _on_remove(self, _button: Gtk.Button) -> None:
        selected = [leftover for leftover, row in self._switches if row.get_active()]
        result = self._uninstaller.remove(selected, self._package_switch.get_active())
        freed = mf.format_bytes(result.freed_bytes)
        if result.failed:
            self._status.set_label(f"Freed {freed}; {len(result.failed)} item(s) failed")
        else:
            self._status.set_label(f"Done. Freed {freed} (moved to Trash)")
        self._populate_residue()
