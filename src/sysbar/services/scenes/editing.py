"""Turning a scene into something an editor can show, and back again.

The editor renders what it understands: the name, the three system toggles, and
the default audio output. A scene may hold actions it does not render, either
because a built-in ships with them or because the manifest was written by hand.

Those are carried through untouched. Without that, editing a preset's name would
quietly drop the settings writes that make it useful, and the scene would keep
working in the list while doing less than it says. Rebuilding the action list
from only what the form shows is the obvious implementation and the wrong one.

The order of the rebuilt list is stable: toggles first in enum order, then the
output device, then whatever was preserved, so saving a scene twice without
changing anything produces the same file.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .actions import SceneAction, SetOutputDevice, SetToggle, SystemToggle
from .models import Scene

# A toggle the editor leaves alone: the scene simply does not touch it.
UNSET: None = None


@dataclass(frozen=True)
class SceneDraft:
    """What the editor holds while a scene is being written."""

    name: str
    toggles: dict[SystemToggle, bool | None] = field(default_factory=dict)
    output_device: str | None = None
    #: Actions the editor cannot render, kept so that saving does not drop them.
    preserved: tuple[SceneAction, ...] = ()

    def with_toggle(self, toggle: SystemToggle, value: bool | None) -> SceneDraft:
        updated = dict(self.toggles)
        if value is UNSET:
            updated.pop(toggle, None)
        else:
            updated[toggle] = value
        return SceneDraft(
            name=self.name,
            toggles=updated,
            output_device=self.output_device,
            preserved=self.preserved,
        )

    @property
    def preserved_count(self) -> int:
        """How many actions the form is carrying without showing them."""
        return len(self.preserved)


def draft_from(scene: Scene) -> SceneDraft:
    """Split a scene into what the editor renders and what it must carry."""
    toggles: dict[SystemToggle, bool | None] = {}
    output_device: str | None = None
    preserved: list[SceneAction] = []
    for action in scene.actions:
        match action:
            case SetToggle(toggle=toggle, value=value):
                toggles[toggle] = value
            case SetOutputDevice(device=device):
                output_device = device
            case _:
                preserved.append(action)
    return SceneDraft(
        name=scene.name,
        toggles=toggles,
        output_device=output_device,
        preserved=tuple(preserved),
    )


def actions_from(draft: SceneDraft) -> tuple[SceneAction, ...]:
    """Rebuild a scene's actions from the editor state, preserving the rest."""
    actions: list[SceneAction] = []
    for toggle in SystemToggle:
        value = draft.toggles.get(toggle)
        if value is not None:
            actions.append(SetToggle(toggle=toggle, value=value))
    if draft.output_device:
        actions.append(SetOutputDevice(device=draft.output_device))
    actions.extend(draft.preserved)
    return tuple(actions)


def apply_draft(scene: Scene, draft: SceneDraft) -> Scene:
    """The scene as edited: a user-owned copy, same id."""
    return scene.edited(name=draft.name, actions=actions_from(draft))
