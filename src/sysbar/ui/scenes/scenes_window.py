"""Scene management: the list, and the form for one scene.

Boundary code. What a scene is, what an edit preserves and what may be written
is decided in :mod:`sysbar.services.scenes`; this window renders rows and reads
widgets back into a draft.

Two rules from the model surface here. A built-in cannot be deleted, only
restored, because editing one produces an override and restoring is deleting
that override. And the form carries the actions it cannot show, announcing how
many, so that editing a preset's name does not silently drop what it does.
"""

from __future__ import annotations

from typing import Protocol
from uuid import uuid4

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from ...core.i18n import _  # noqa: E402
from ...services.audio.models import AudioDevice  # noqa: E402
from ...services.scenes.actions import SystemToggle  # noqa: E402
from ...services.scenes.editing import SceneDraft, apply_draft, draft_from  # noqa: E402
from ...services.scenes.models import PRESET_SCENE_IDS, Scene  # noqa: E402
from ..footer import build_footer  # noqa: E402

_WINDOW_WIDTH = 520
_WINDOW_HEIGHT = 620
_PAGE_LIST = "list"
_PAGE_EDIT = "edit"

# Combo order for a toggle: leave alone, turn on, turn off.
_TOGGLE_CHOICES: tuple[bool | None, ...] = (None, True, False)
_NO_DEVICE = 0

_TOGGLE_LABELS = {
    SystemToggle.KEEP_AWAKE: "Keep awake",
    SystemToggle.DO_NOT_DISTURB: "Do Not Disturb",
    SystemToggle.MICROPHONE_MUTED: "Mute microphone",
}


class SceneController(Protocol):
    """What the window needs from the scenes feature."""

    @property
    def scenes(self) -> list[Scene]: ...

    def save(self, scene: Scene) -> None: ...
    def delete(self, scene_id: str) -> bool: ...
    def outputs(self) -> list[AudioDevice]: ...


class ScenesWindow(Adw.Window):
    """Browse, create, edit and remove scenes."""

    def __init__(self, controller: SceneController) -> None:
        super().__init__(title=_("Scenes"))
        self.set_default_size(_WINDOW_WIDTH, _WINDOW_HEIGHT)
        self._controller = controller
        self._stack = Gtk.Stack()
        self._group = Adw.PreferencesGroup()
        self._rows: list[Adw.ActionRow] = []
        self._editing: Scene | None = None
        self._name = Adw.EntryRow(title=_("Name"))
        self._toggle_rows: dict[SystemToggle, Adw.ComboRow] = {}
        self._device_row = Adw.ComboRow(title=_("Audio output"))
        self._device_names: list[str] = [""]
        self._preserved_row = Adw.ActionRow(subtitle=_("Kept as it is"))
        self._build_content()
        self._reload()

    # --- construction -----------------------------------------------------

    def _build_content(self) -> None:
        self._stack.add_named(self._build_list_page(), _PAGE_LIST)
        self._stack.add_named(self._build_edit_page(), _PAGE_EDIT)
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(self._build_header())
        toolbar.set_content(self._stack)
        toolbar.add_bottom_bar(build_footer())
        self.set_content(toolbar)
        self._show_list()

    def _build_header(self) -> Adw.HeaderBar:
        header = Adw.HeaderBar()
        self._new_button = Gtk.Button(icon_name="list-add-symbolic", tooltip_text=_("New scene"))
        self._new_button.connect("clicked", lambda _b: self._edit(None))
        header.pack_end(self._new_button)

        self._back_button = Gtk.Button(icon_name="go-previous-symbolic", tooltip_text=_("Back"))
        self._back_button.connect("clicked", lambda _b: self._show_list())
        header.pack_start(self._back_button)
        return header

    def _build_list_page(self) -> Gtk.Widget:
        page = Adw.PreferencesPage()
        page.add(self._group)
        scroller = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        scroller.set_child(page)
        return scroller

    def _build_edit_page(self) -> Gtk.Widget:
        page = Adw.PreferencesPage()
        details = Adw.PreferencesGroup(title=_("Scene"))
        details.add(self._name)
        page.add(details)

        actions = Adw.PreferencesGroup(
            title=_("What it does"),
            description=_("Anything left unchanged is not touched by the scene"),
        )
        for toggle, label in _TOGGLE_LABELS.items():
            row = Adw.ComboRow(title=_(label), model=_toggle_model())
            self._toggle_rows[toggle] = row
            actions.add(row)
        actions.add(self._device_row)
        actions.add(self._preserved_row)
        page.add(actions)

        save = Gtk.Button(label=_("Save scene"), halign=Gtk.Align.CENTER)
        save.add_css_class("suggested-action")
        save.connect("clicked", lambda _b: self._save())
        buttons = Adw.PreferencesGroup()
        buttons.add(save)
        page.add(buttons)

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
        row = Adw.ActionRow(title=scene.name, subtitle=_describe(scene))
        edit = Gtk.Button(
            icon_name="document-edit-symbolic",
            tooltip_text=_("Edit"),
            valign=Gtk.Align.CENTER,
        )
        edit.add_css_class("flat")
        edit.connect("clicked", lambda _b, target=scene: self._edit(target))
        row.add_suffix(edit)
        removal = self._build_removal_button(scene)
        if removal is not None:
            row.add_suffix(removal)
        return row

    def _build_removal_button(self, scene: Scene) -> Gtk.Button | None:
        """Delete for a user scene, restore for a customised built-in, else none."""
        if scene.is_built_in:
            return None
        # A customised built-in keeps its id, so it can be restored rather
        # than deleted: there is a shipped version to fall back to.
        restorable = scene.id in PRESET_SCENE_IDS
        button = Gtk.Button(
            icon_name="edit-undo-symbolic" if restorable else "user-trash-symbolic",
            tooltip_text=_("Restore the built-in") if restorable else _("Delete"),
            valign=Gtk.Align.CENTER,
        )
        button.add_css_class("flat")
        button.connect("clicked", lambda _b, target=scene.id: self._delete(target))
        return button

    def _delete(self, scene_id: str) -> None:
        self._controller.delete(scene_id)
        self._reload()

    # --- editing ----------------------------------------------------------

    def _edit(self, scene: Scene | None) -> None:
        self._editing = scene
        draft = draft_from(scene) if scene is not None else SceneDraft(name=_("New scene"))
        self._name.set_text(draft.name)
        for toggle, row in self._toggle_rows.items():
            row.set_selected(_TOGGLE_CHOICES.index(draft.toggles.get(toggle)))
        self._load_devices(draft.output_device)
        self._preserved_row.set_visible(draft.preserved_count > 0)
        self._preserved_row.set_title(
            _("{count} more actions in this scene").format(count=draft.preserved_count)
        )
        self._show_edit()

    def _load_devices(self, selected: str | None) -> None:
        devices = self._controller.outputs()
        names = [_("Leave unchanged")] + [device.description or device.name for device in devices]
        self._device_names = [""] + [device.name for device in devices]
        self._device_row.set_model(Gtk.StringList.new(names))
        self._device_row.set_selected(
            self._device_names.index(selected) if selected in self._device_names else _NO_DEVICE
        )

    def _save(self) -> None:
        base = self._editing or Scene(id=uuid4().hex, name=self._name.get_text() or _("Scene"))
        draft = self._current_draft(base)
        self._controller.save(apply_draft(base, draft))
        self._reload()
        self._show_list()

    def _current_draft(self, base: Scene) -> SceneDraft:
        toggles = {
            toggle: _TOGGLE_CHOICES[row.get_selected()] for toggle, row in self._toggle_rows.items()
        }
        index = self._device_row.get_selected()
        return SceneDraft(
            name=self._name.get_text().strip() or base.name,
            toggles={key: value for key, value in toggles.items() if value is not None},
            output_device=self._device_names[index] if index < len(self._device_names) else "",
            preserved=draft_from(base).preserved,
        )

    # --- navigation -------------------------------------------------------

    def _show_list(self) -> None:
        self._stack.set_visible_child_name(_PAGE_LIST)
        self._back_button.set_visible(False)
        self._new_button.set_visible(True)

    def _show_edit(self) -> None:
        self._stack.set_visible_child_name(_PAGE_EDIT)
        self._back_button.set_visible(True)
        self._new_button.set_visible(False)


def _toggle_model() -> Gtk.StringList:
    return Gtk.StringList.new([_("Leave unchanged"), _("Turn on"), _("Turn off")])


def _describe(scene: Scene) -> str:
    count = len(scene.actions)
    if scene.is_built_in:
        return _("Built in, {count} actions").format(count=count)
    return _("Custom, {count} actions").format(count=count)


