"""Scene management: the list of scenes, and navigation to the form.

Boundary code. What a scene is, what an edit preserves and what may be written
is decided in :mod:`sysbar.services.scenes`; this window renders rows and moves
between the two pages. The form itself lives in
:mod:`sysbar.ui.scenes.scene_editor`.

One rule from the model surfaces here: a built-in cannot be deleted, only
restored. Editing one produces an override that keeps its id and its place in
the list, so restoring is deleting that override, and the button changes both
icon and meaning accordingly.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from ...core.i18n import _  # noqa: E402
from ...services.scenes.models import (  # noqa: E402
    PRESET_SCENE_IDS,
    Scene,
    scene_display_name,
)
from ..footer import build_footer  # noqa: E402
from .ports import SceneController  # noqa: E402
from .scene_editor import SceneEditor  # noqa: E402

_WINDOW_WIDTH = 520
_WINDOW_HEIGHT = 620
_PAGE_LIST = "list"
_PAGE_EDIT = "edit"


class ScenesWindow(Adw.Window):
    """Browse, create, edit and remove scenes."""

    def __init__(self, controller: SceneController) -> None:
        super().__init__(title=_("Scenes"))
        self.set_default_size(_WINDOW_WIDTH, _WINDOW_HEIGHT)
        self._controller = controller
        self._stack = Gtk.Stack()
        self._group = Adw.PreferencesGroup()
        self._rows: list[Adw.ActionRow] = []
        self._editor = SceneEditor(controller, self._on_saved)
        self._build_content()
        self._reload()

    # --- construction -----------------------------------------------------

    def _build_content(self) -> None:
        self._stack.add_named(self._build_list_page(), _PAGE_LIST)
        self._stack.add_named(self._editor.widget, _PAGE_EDIT)
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(self._build_header())
        toolbar.set_content(self._stack)
        toolbar.add_bottom_bar(build_footer())
        self.set_content(toolbar)
        self._show_list()

    def _build_header(self) -> Adw.HeaderBar:
        header = Adw.HeaderBar()
        self._new_button = Gtk.Button(icon_name="list-add-symbolic", tooltip_text=_("New scene"))
        self._new_button.connect("clicked", lambda _button: self._edit(None))
        header.pack_end(self._new_button)

        self._back_button = Gtk.Button(icon_name="go-previous-symbolic", tooltip_text=_("Back"))
        self._back_button.connect("clicked", lambda _button: self._show_list())
        header.pack_start(self._back_button)
        return header

    def _build_list_page(self) -> Gtk.Widget:
        page = Adw.PreferencesPage()
        page.add(self._group)
        scroller = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        scroller.set_child(page)
        return scroller

    # --- list -------------------------------------------------------------

    def _reload(self) -> None:
        for row in self._rows:
            self._group.remove(row)
        self._rows.clear()
        for scene in self._controller.scenes:
            row = self._build_scene_row(scene)
            self._group.add(row)
            self._rows.append(row)

    def _build_scene_row(self, scene: Scene) -> Adw.ActionRow:
        row = Adw.ActionRow(title=scene_display_name(scene), subtitle=_describe(scene))
        edit = Gtk.Button(
            icon_name="document-edit-symbolic",
            tooltip_text=_("Edit"),
            valign=Gtk.Align.CENTER,
        )
        edit.add_css_class("flat")
        edit.connect("clicked", lambda _button, target=scene: self._edit(target))
        row.add_suffix(edit)
        removal = self._build_removal_button(scene)
        if removal is not None:
            row.add_suffix(removal)
        return row

    def _build_removal_button(self, scene: Scene) -> Gtk.Button | None:
        """Delete for a user scene, restore for a customised built-in, else none."""
        if scene.is_built_in:
            return None
        # A customised built-in keeps its id, so it can be restored rather than
        # deleted: there is a shipped version to fall back to.
        restorable = scene.id in PRESET_SCENE_IDS
        button = Gtk.Button(
            icon_name="edit-undo-symbolic" if restorable else "user-trash-symbolic",
            tooltip_text=_("Restore the built-in") if restorable else _("Delete"),
            valign=Gtk.Align.CENTER,
        )
        button.add_css_class("flat")
        button.connect("clicked", lambda _button, target=scene.id: self._delete(target))
        return button

    def _delete(self, scene_id: str) -> None:
        self._controller.delete(scene_id)
        self._reload()

    # --- navigation -------------------------------------------------------

    def _edit(self, scene: Scene | None) -> None:
        self._editor.load(scene)
        self._show_edit()

    def _on_saved(self) -> None:
        self._reload()
        self._show_list()

    def _show_list(self) -> None:
        self._stack.set_visible_child_name(_PAGE_LIST)
        self._back_button.set_visible(False)
        self._new_button.set_visible(True)

    def _show_edit(self) -> None:
        self._stack.set_visible_child_name(_PAGE_EDIT)
        self._back_button.set_visible(True)
        self._new_button.set_visible(False)


def _describe(scene: Scene) -> str:
    count = len(scene.actions)
    if scene.is_built_in:
        return _("Built in, {count} actions").format(count=count)
    return _("Custom, {count} actions").format(count=count)
