"""Persistence for user scenes, and how they combine with the built-in ones.

Scenes live in a JSON manifest rather than in GSettings: a scene is a record
with a variable-length list of variant-shaped actions inside it, which the
schema cannot describe and which would have to be packed and unpacked by hand
anyway. Since the parser has to exist either way, it may as well produce a file
that can be read, diffed and shared. The same choice was already made for the
shelf and the clipboard history.

The file is created readable and writable by its owner only. It decides what the
application does when a scene is activated, so it is not something to leave at
whatever the umask happens to be.

A corrupt file degrades to "no user scenes" with a warning rather than taking
the application down, matching the shelf and the clipboard. The built-in scenes
still work in that state, which is the point of not merging them into the file.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from pathlib import Path

from .constants import SCENES_MANIFEST, SCENES_MANIFEST_MODE, SCENES_MANIFEST_VERSION
from .models import PRESET_SCENES, Scene, SceneError, SceneOrigin
from .triggers import TriggerError, TriggerRule

log = logging.getLogger(__name__)

_VERSION_KEY = "version"
_SCENES_KEY = "scenes"
_TRIGGERS_KEY = "triggers"


def merged(presets: Iterable[Scene], overrides: Iterable[Scene]) -> list[Scene]:
    """Built-in scenes with user overrides applied, then the user's own.

    An override is a stored scene sharing a built-in's id: it takes that
    built-in's place, keeping its position, so a customised Focus stays where
    the user expects it rather than jumping to the end of the list.
    """
    by_id = {scene.id: scene for scene in overrides}
    result = [by_id.pop(preset.id, preset) for preset in presets]
    result.extend(by_id.values())
    return result


class SceneStore:
    """Reads and writes the user's scenes."""

    def __init__(self, path: Path = SCENES_MANIFEST) -> None:
        self._path = path
        self._scenes: list[Scene] = []
        self._triggers: list[TriggerRule] = []

    @property
    def scenes(self) -> list[Scene]:
        """The stored scenes, overrides included."""
        return list(self._scenes)

    def all_scenes(self, presets: Iterable[Scene] = PRESET_SCENES) -> list[Scene]:
        """Everything the user can activate: built-ins, overridden, plus their own."""
        return merged(presets, self._scenes)

    @property
    def triggers(self) -> list[TriggerRule]:
        """The stored rules, in priority order."""
        return list(self._triggers)

    def load(self) -> None:
        if not self._path.is_file():
            return
        try:
            body = _manifest_body(json.loads(self._path.read_text(encoding="utf-8")))
            scenes = _read_scenes(body)
            triggers = _read_triggers(body)
        except (OSError, ValueError, KeyError, TypeError, SceneError, TriggerError):
            log.warning("could not read the scenes manifest", extra={"path": str(self._path)})
            self._scenes = []
            self._triggers = []
            return
        self._scenes = scenes
        self._triggers = triggers

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            _VERSION_KEY: SCENES_MANIFEST_VERSION,
            _SCENES_KEY: [scene.to_dict() for scene in self._scenes],
            _TRIGGERS_KEY: [trigger.to_dict() for trigger in self._triggers],
        }
        self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self._path.chmod(SCENES_MANIFEST_MODE)

    def upsert(self, scene: Scene) -> None:
        """Add a scene, or replace the one with the same id."""
        stored = scene if scene.origin is SceneOrigin.USER else scene.edited(actions=None)
        self._scenes = [existing for existing in self._scenes if existing.id != stored.id]
        self._scenes.append(stored)
        self.save()

    def remove(self, scene_id: str) -> bool:
        """Delete a stored scene. Returns whether there was one to delete.

        On a built-in's id this deletes the override, which is what restoring
        the built-in means: there is nothing else to put back.
        """
        remaining = [scene for scene in self._scenes if scene.id != scene_id]
        if len(remaining) == len(self._scenes):
            return False
        self._scenes = remaining
        self.save()
        return True

    def is_overridden(self, scene_id: str) -> bool:
        return any(scene.id == scene_id for scene in self._scenes)

    def upsert_trigger(self, trigger: TriggerRule) -> None:
        """Add a rule, or replace the one with the same id, keeping its place."""
        replaced = False
        rules: list[TriggerRule] = []
        for existing in self._triggers:
            if existing.id == trigger.id:
                rules.append(trigger)
                replaced = True
            else:
                rules.append(existing)
        if not replaced:
            rules.append(trigger)
        self._triggers = rules
        self.save()

    def remove_trigger(self, trigger_id: str) -> bool:
        """Delete a rule. Returns whether there was one to delete."""
        remaining = [rule for rule in self._triggers if rule.id != trigger_id]
        if len(remaining) == len(self._triggers):
            return False
        self._triggers = remaining
        self.save()
        return True


def _manifest_body(raw: object) -> dict[str, object]:
    """The manifest as an object, rejecting anything else."""
    if not isinstance(raw, dict):
        raise SceneError("manifest is not an object")
    return raw


def _read_triggers(body: dict[str, object]) -> list[TriggerRule]:
    """Parse the rules, rejecting anything malformed.

    Rules live in the same document as the scenes so that saving is one atomic
    write: there is never a moment where a rule points at a scene that has not
    been written yet.
    """
    entries = body.get(_TRIGGERS_KEY, [])
    if not isinstance(entries, list):
        raise TriggerError("manifest triggers are not a list")
    rules = [TriggerRule.from_dict(entry) for entry in entries]
    ids = [rule.id for rule in rules]
    if len(ids) != len(set(ids)):
        raise TriggerError("manifest contains duplicate trigger ids")
    return rules


def _read_scenes(body: dict[str, object]) -> list[Scene]:
    """Parse the stored scenes, rejecting anything malformed."""
    entries = body.get(_SCENES_KEY, [])
    if not isinstance(entries, list):
        raise SceneError("manifest scenes are not a list")
    scenes = [Scene.from_dict(entry) for entry in entries]
    ids = [scene.id for scene in scenes]
    if len(ids) != len(set(ids)):
        raise SceneError("manifest contains duplicate scene ids")
    return scenes
