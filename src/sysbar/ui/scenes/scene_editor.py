"""The form for one scene: what it does, and when it activates itself.

Split from the list window when that file outgrew the project's line cap, which
turned out to be the right seam anyway: the list is about choosing among scenes,
the form is about the contents of one.

Two things here are model decisions showing through, not layout. The form keeps
the actions it cannot render and says how many, so editing a preset's name does
not silently drop what it does. And the trigger part offers a closed set of
conditions and gives each scene at most one rule: several rules per scene stay
expressible in the manifest and the engine has always handled them, so this is a
limit of the form, not of the model.
"""

from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from ...core.i18n import _  # noqa: E402
from ...services.scenes.actions import SystemToggle  # noqa: E402
from ...services.scenes.editing import (  # noqa: E402
    SceneDraft,
    TriggerChoice,
    TriggerDraft,
    apply_draft,
    draft_from,
    rule_from,
    trigger_draft_from,
)
from ...services.scenes.models import Scene  # noqa: E402
from .ports import SceneController  # noqa: E402

# Combo order for a toggle: leave alone, turn on, turn off.
_TOGGLE_CHOICES: tuple[bool | None, ...] = (None, True, False)
_NO_DEVICE = 0
_PERCENT_MIN = 5.0
_PERCENT_MAX = 95.0
_PERCENT_STEP = 5.0

# Combo order for the trigger condition; the index maps into this tuple.
_TRIGGER_CHOICES: tuple[TriggerChoice, ...] = (
    TriggerChoice.NEVER,
    TriggerChoice.EXTERNAL_MONITOR,
    TriggerChoice.ON_BATTERY,
    TriggerChoice.BATTERY_BELOW,
)

_TOGGLE_LABELS = {
    SystemToggle.KEEP_AWAKE: "Keep awake",
    SystemToggle.DO_NOT_DISTURB: "Do Not Disturb",
    SystemToggle.MICROPHONE_MUTED: "Mute microphone",
}


class SceneEditor:
    """The scene form, as a widget the window puts in its stack."""

    def __init__(self, controller: SceneController, on_saved: Callable[[], None]) -> None:
        self._controller = controller
        self._on_saved = on_saved
        self._editing: Scene | None = None
        self._name = Adw.EntryRow(title=_("Name"))
        self._toggle_rows: dict[SystemToggle, Adw.ComboRow] = {}
        self._device_row = Adw.ComboRow(title=_("Audio output"))
        self._device_names: list[str] = [""]
        self._preserved_row = Adw.ActionRow(subtitle=_("Kept as it is"))
        self._trigger_row = Adw.ComboRow(title=_("Activate automatically"))
        self._percent_row = Adw.SpinRow.new_with_range(_PERCENT_MIN, _PERCENT_MAX, _PERCENT_STEP)
        self._percent_row.set_title(_("Below this charge (%)"))
        self._restore_row = Adw.SwitchRow(
            title=_("Undo when the condition ends"),
            subtitle=_("A scene you chose by hand is never replaced"),
        )
        self.widget = self._build()

    # --- construction -----------------------------------------------------

    def _build(self) -> Gtk.Widget:
        page = Adw.PreferencesPage()
        details = Adw.PreferencesGroup(title=_("Scene"))
        details.add(self._name)
        page.add(details)
        page.add(self._actions_group())
        page.add(self._triggers_group())
        page.add(self._save_group())
        scroller = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        scroller.set_child(page)
        return scroller

    def _actions_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(
            title=_("What it does"),
            description=_("Anything left unchanged is not touched by the scene"),
        )
        for toggle, label in _TOGGLE_LABELS.items():
            row = Adw.ComboRow(title=_(label), model=_toggle_model())
            self._toggle_rows[toggle] = row
            group.add(row)
        group.add(self._device_row)
        group.add(self._preserved_row)
        return group

    def _triggers_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(
            title=_("When to activate it"),
            description=_("Leave on Never to activate this scene only by hand"),
        )
        self._trigger_row.set_model(_trigger_model())
        self._trigger_row.connect("notify::selected", lambda *_args: self._sync_trigger_rows())
        group.add(self._trigger_row)
        group.add(self._percent_row)
        group.add(self._restore_row)
        return group

    def _save_group(self) -> Adw.PreferencesGroup:
        save = Gtk.Button(label=_("Save scene"), halign=Gtk.Align.CENTER)
        save.add_css_class("suggested-action")
        save.connect("clicked", lambda _button: self._save())
        group = Adw.PreferencesGroup()
        group.add(save)
        return group

    # --- loading ----------------------------------------------------------

    def load(self, scene: Scene | None) -> None:
        """Fill the form from a scene, or blank it for a new one."""
        self._editing = scene
        draft = draft_from(scene) if scene is not None else SceneDraft(name=_("New scene"))
        self._name.set_text(draft.name)
        for toggle, row in self._toggle_rows.items():
            row.set_selected(_TOGGLE_CHOICES.index(draft.toggles.get(toggle)))
        self._load_devices(draft.output_device)
        self._load_trigger(scene)
        self._preserved_row.set_visible(draft.preserved_count > 0)
        self._preserved_row.set_title(
            _("{count} more actions in this scene").format(count=draft.preserved_count)
        )

    def _load_devices(self, selected: str | None) -> None:
        devices = self._controller.outputs()
        names = [_("Leave unchanged")] + [device.description or device.name for device in devices]
        self._device_names = [""] + [device.name for device in devices]
        self._device_row.set_model(Gtk.StringList.new(names))
        self._device_row.set_selected(
            self._device_names.index(selected) if selected in self._device_names else _NO_DEVICE
        )

    def _load_trigger(self, scene: Scene | None) -> None:
        rule = self._controller.trigger_for(scene.id) if scene is not None else None
        draft = trigger_draft_from(rule)
        self._trigger_row.set_selected(_TRIGGER_CHOICES.index(draft.choice))
        self._percent_row.set_value(draft.percent)
        self._restore_row.set_active(draft.restore_on_exit)
        self._sync_trigger_rows()

    def _sync_trigger_rows(self) -> None:
        """Only the threshold condition has a percentage to ask about."""
        choice = _TRIGGER_CHOICES[self._trigger_row.get_selected()]
        self._percent_row.set_visible(choice is TriggerChoice.BATTERY_BELOW)
        self._restore_row.set_visible(choice is not TriggerChoice.NEVER)

    # --- saving -----------------------------------------------------------

    def _save(self) -> None:
        base = self._editing or Scene(id=uuid4().hex, name=self._name.get_text() or _("Scene"))
        self._controller.save(apply_draft(base, self._current_draft(base)))
        self._controller.save_trigger(rule_from(self._current_trigger(), base.id), base.id)
        self._on_saved()

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

    def _current_trigger(self) -> TriggerDraft:
        return TriggerDraft(
            choice=_TRIGGER_CHOICES[self._trigger_row.get_selected()],
            percent=self._percent_row.get_value(),
            restore_on_exit=self._restore_row.get_active(),
        )


def _trigger_model() -> Gtk.StringList:
    return Gtk.StringList.new(
        [
            _("Never"),
            _("An external monitor is connected"),
            _("Running on battery"),
            _("Battery drops below a level"),
        ]
    )


def _toggle_model() -> Gtk.StringList:
    return Gtk.StringList.new([_("Leave unchanged"), _("Turn on"), _("Turn off")])
