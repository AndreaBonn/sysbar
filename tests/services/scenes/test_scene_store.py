"""Persistence of user scenes, and how they combine with the built-in ones."""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from sysbar.services.scenes.actions import SetSetting, SetToggle, SystemToggle
from sysbar.services.scenes.models import PRESET_SCENES, Scene, SceneOrigin
from sysbar.services.scenes.store import SceneStore, merged
from sysbar.services.scenes.triggers import ExternalMonitorConnected, TriggerRule


def _store(tmp_path: Path) -> SceneStore:
    return SceneStore(tmp_path / "scenes" / "manifest.json")


def _user(scene_id: str = "mine", name: str = "Mia") -> Scene:
    return Scene(
        id=scene_id,
        name=name,
        actions=(SetToggle(toggle=SystemToggle.KEEP_AWAKE, value=True),),
        origin=SceneOrigin.USER,
    )


# --- merging --------------------------------------------------------------


def test_without_overrides_only_the_presets_are_listed() -> None:
    assert [scene.id for scene in merged(PRESET_SCENES, [])] == [
        preset.id for preset in PRESET_SCENES
    ]


def test_a_user_scene_is_appended_after_the_presets() -> None:
    result = merged(PRESET_SCENES, [_user()])

    assert result[-1].id == "mine"
    assert len(result) == len(PRESET_SCENES) + 1


def test_an_override_replaces_its_preset_in_place() -> None:
    override = Scene(id="focus", name="Concentrazione", origin=SceneOrigin.USER)

    result = merged(PRESET_SCENES, [override])

    assert len(result) == len(PRESET_SCENES)
    assert result[0].id == "focus"
    assert result[0].name == "Concentrazione"


def test_an_override_keeps_the_position_of_the_preset_it_replaces() -> None:
    override = Scene(id="power-saving", name="Risparmio", origin=SceneOrigin.USER)

    positions = [scene.id for scene in merged(PRESET_SCENES, [override, _user()])]

    assert positions.index("power-saving") == 2
    assert positions[-1] == "mine"


def test_merging_with_no_presets_yields_the_user_scenes() -> None:
    assert [scene.id for scene in merged([], [_user()])] == ["mine"]


# --- round trip -----------------------------------------------------------


def test_a_store_with_no_file_has_no_scenes(tmp_path: Path) -> None:
    store = _store(tmp_path)

    store.load()

    assert store.scenes == []


def test_a_saved_scene_comes_back(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.upsert(_user())

    reopened = _store(tmp_path)
    reopened.load()

    assert reopened.scenes == [_user()]


def test_the_manifest_records_its_version(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.upsert(_user())

    payload = json.loads((tmp_path / "scenes" / "manifest.json").read_text(encoding="utf-8"))

    assert payload["version"] == 1


def test_the_manifest_is_readable_only_by_its_owner(tmp_path: Path) -> None:
    """It decides what runs when a scene is activated, so not group or world."""
    store = _store(tmp_path)
    store.upsert(_user())

    mode = (tmp_path / "scenes" / "manifest.json").stat().st_mode

    assert stat.S_IMODE(mode) == 0o600


# --- editing --------------------------------------------------------------


def test_upserting_twice_replaces_rather_than_duplicates(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.upsert(_user(name="Prima"))

    store.upsert(_user(name="Dopo"))

    assert [scene.name for scene in store.scenes] == ["Dopo"]


def test_storing_a_built_in_records_it_as_a_user_override(tmp_path: Path) -> None:
    store = _store(tmp_path)

    store.upsert(PRESET_SCENES[0])

    assert store.scenes[0].origin is SceneOrigin.USER
    assert store.scenes[0].id == PRESET_SCENES[0].id


def test_an_override_shows_up_in_the_merged_list(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.upsert(Scene(id="focus", name="Concentrazione", origin=SceneOrigin.USER))

    names = {scene.id: scene.name for scene in store.all_scenes()}

    assert names["focus"] == "Concentrazione"


def test_removing_an_override_restores_the_built_in(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.upsert(Scene(id="focus", name="Concentrazione", origin=SceneOrigin.USER))

    assert store.remove("focus") is True

    names = {scene.id: scene.name for scene in store.all_scenes()}
    assert names["focus"] == "Focus"


def test_removing_something_that_is_not_stored_reports_so(tmp_path: Path) -> None:
    assert _store(tmp_path).remove("ghost") is False


def test_a_removal_survives_a_reload(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.upsert(_user())
    store.remove("mine")

    reopened = _store(tmp_path)
    reopened.load()

    assert reopened.scenes == []


def test_is_overridden_reports_whether_a_preset_was_customised(tmp_path: Path) -> None:
    store = _store(tmp_path)

    assert store.is_overridden("focus") is False
    store.upsert(Scene(id="focus", name="Concentrazione", origin=SceneOrigin.USER))
    assert store.is_overridden("focus") is True


# --- corrupt data ---------------------------------------------------------


def _write(tmp_path: Path, content: str) -> SceneStore:
    manifest = tmp_path / "scenes" / "manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(content, encoding="utf-8")
    return SceneStore(manifest)


def test_invalid_json_degrades_to_no_user_scenes(tmp_path: Path) -> None:
    store = _write(tmp_path, "{not json")

    store.load()

    assert store.scenes == []


def test_a_manifest_that_is_not_an_object_degrades(tmp_path: Path) -> None:
    store = _write(tmp_path, "[1, 2, 3]")

    store.load()

    assert store.scenes == []


def test_scenes_that_are_not_a_list_degrade(tmp_path: Path) -> None:
    store = _write(tmp_path, json.dumps({"version": 1, "scenes": "focus"}))

    store.load()

    assert store.scenes == []


def test_one_unreadable_scene_degrades_the_whole_file(tmp_path: Path) -> None:
    """Whole-file, like the shelf and clipboard: a half-read manifest is worse."""
    payload = {
        "version": 1,
        "scenes": [
            _user().to_dict(),
            {"id": "broken", "name": "Rotta", "actions": [{"kind": "nope"}]},
        ],
    }
    store = _write(tmp_path, json.dumps(payload))

    store.load()

    assert store.scenes == []


def test_an_unreadable_manifest_is_moved_aside_instead_of_being_overwritten(
    tmp_path: Path,
) -> None:
    """The degraded state must not look like a legitimately empty one.

    Saving writes whatever is in memory, so without this the first edit after a
    failed read replaces every valid scene and rule with the single new one.
    """
    original = json.dumps({"version": 1, "scenes": [_user().to_dict()], "triggers": []})
    store = _write(tmp_path, original + "  trailing garbage")
    manifest = tmp_path / "scenes" / "manifest.json"

    store.load()
    store.upsert(_user("other", "Altra"))

    quarantined = tmp_path / "scenes" / "manifest.json.corrupt"
    assert quarantined.read_text(encoding="utf-8") == original + "  trailing garbage"
    assert [scene.id for scene in store.scenes] == ["other"]
    assert json.loads(manifest.read_text(encoding="utf-8"))["scenes"][0]["id"] == "other"


def test_a_readable_manifest_is_never_moved_aside(tmp_path: Path) -> None:
    payload = {"version": 1, "scenes": [_user().to_dict()], "triggers": []}
    store = _write(tmp_path, json.dumps(payload))

    store.load()

    assert not (tmp_path / "scenes" / "manifest.json.corrupt").exists()


def test_a_manifest_that_cannot_be_moved_aside_still_degrades(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Quarantine is best-effort: failing to rename must not take startup down."""
    store = _write(tmp_path, "{not json")

    def refuse(self: Path, target: object) -> None:
        raise OSError("read-only filesystem")

    monkeypatch.setattr(Path, "rename", refuse)

    store.load()

    assert store.scenes == []


def test_further_corrupt_manifests_do_not_bury_the_earlier_ones(tmp_path: Path) -> None:
    """Bad reads in a row must not leave the user with only the newest wreck."""
    store = _write(tmp_path, "{first wreck")
    manifest = tmp_path / "scenes" / "manifest.json"

    store.load()
    for wreck in ("{second wreck", "{third wreck"):
        manifest.write_text(wreck, encoding="utf-8")
        store.load()

    kept = {
        path.read_text(encoding="utf-8")
        for path in (tmp_path / "scenes").iterdir()
        if ".corrupt" in path.name
    }
    assert kept == {"{first wreck", "{second wreck", "{third wreck"}


def test_duplicate_ids_degrade(tmp_path: Path) -> None:
    payload = {"version": 1, "scenes": [_user().to_dict(), _user().to_dict()]}
    store = _write(tmp_path, json.dumps(payload))

    store.load()

    assert store.scenes == []


def test_the_built_in_scenes_still_work_with_a_corrupt_manifest(tmp_path: Path) -> None:
    store = _write(tmp_path, "{not json")

    store.load()

    assert [scene.id for scene in store.all_scenes()] == [preset.id for preset in PRESET_SCENES]


def test_a_scene_with_an_unwritable_setting_key_degrades_the_file(tmp_path: Path) -> None:
    """The whitelist holds when reading, not only in the editor."""
    payload = {
        "version": 1,
        "scenes": [
            {
                "id": "sneaky",
                "name": "Sneaky",
                "origin": "user",
                "actions": [{"kind": "setting", "key": "app-language", "value": "it"}],
            }
        ],
    }
    store = _write(tmp_path, json.dumps(payload))

    store.load()

    assert store.scenes == []


def test_a_valid_setting_key_loads_normally(tmp_path: Path) -> None:
    scene = Scene(
        id="ok",
        name="Ok",
        actions=(SetSetting(key="alert-enabled", value=False),),
        origin=SceneOrigin.USER,
    )
    store = _write(tmp_path, json.dumps({"version": 1, "scenes": [scene.to_dict()]}))

    store.load()

    assert store.scenes == [scene]


# --- trigger rules --------------------------------------------------------


def _rule(rule_id: str = "r1", scene_id: str = "focus") -> TriggerRule:
    return TriggerRule(
        id=rule_id,
        condition=ExternalMonitorConnected(),
        scene_id=scene_id,
        restore_on_exit=True,
    )


def test_a_new_store_has_no_rules(tmp_path: Path) -> None:
    assert _store(tmp_path).triggers == []


def test_a_saved_rule_comes_back(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.upsert_trigger(_rule())

    reopened = _store(tmp_path)
    reopened.load()

    assert reopened.triggers == [_rule()]


def test_rules_and_scenes_share_one_document(tmp_path: Path) -> None:
    """One atomic write, so a rule never points at an unsaved scene."""
    store = _store(tmp_path)
    store.upsert(_user())
    store.upsert_trigger(_rule(scene_id="mine"))

    payload = json.loads((tmp_path / "scenes" / "manifest.json").read_text(encoding="utf-8"))

    assert len(payload["scenes"]) == 1
    assert len(payload["triggers"]) == 1


def test_upserting_a_rule_twice_replaces_it(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.upsert_trigger(_rule(scene_id="focus"))

    store.upsert_trigger(_rule(scene_id="presentation"))

    assert [rule.scene_id for rule in store.triggers] == ["presentation"]


def test_replacing_a_rule_keeps_its_position(tmp_path: Path) -> None:
    """The list is the priority, so an edit must not reorder it."""
    store = _store(tmp_path)
    store.upsert_trigger(_rule("first"))
    store.upsert_trigger(_rule("second"))

    store.upsert_trigger(_rule("first", scene_id="power-saving"))

    assert [rule.id for rule in store.triggers] == ["first", "second"]


def test_removing_a_rule_reports_success(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.upsert_trigger(_rule())

    assert store.remove_trigger("r1") is True
    assert store.triggers == []


def test_removing_a_rule_that_is_not_there_reports_so(tmp_path: Path) -> None:
    assert _store(tmp_path).remove_trigger("ghost") is False


def test_triggers_that_are_not_a_list_degrade(tmp_path: Path) -> None:
    store = _write(tmp_path, json.dumps({"version": 1, "scenes": [], "triggers": "r1"}))

    store.load()

    assert store.triggers == []


def test_one_unreadable_rule_degrades_the_whole_file(tmp_path: Path) -> None:
    payload = {
        "version": 1,
        "scenes": [_user().to_dict()],
        "triggers": [{"id": "r1", "scene_id": "focus", "condition": {"kind": "moon-phase"}}],
    }
    store = _write(tmp_path, json.dumps(payload))

    store.load()

    assert store.triggers == []
    assert store.scenes == []


def test_duplicate_rule_ids_degrade(tmp_path: Path) -> None:
    payload = {"version": 1, "scenes": [], "triggers": [_rule().to_dict(), _rule().to_dict()]}
    store = _write(tmp_path, json.dumps(payload))

    store.load()

    assert store.triggers == []


def test_a_manifest_without_a_triggers_key_loads_its_scenes(tmp_path: Path) -> None:
    """Files written before rules existed must keep working."""
    store = _write(tmp_path, json.dumps({"version": 1, "scenes": [_user().to_dict()]}))

    store.load()

    assert store.scenes == [_user()]
    assert store.triggers == []


def test_a_manifest_with_wide_permissions_is_narrowed_on_load(tmp_path: Path) -> None:
    """Writing creates it private; a file restored from a backup arrives as it was."""
    payload = {"version": 1, "scenes": [_user().to_dict()], "triggers": []}
    store = _write(tmp_path, json.dumps(payload))
    manifest = tmp_path / "scenes" / "manifest.json"
    manifest.chmod(0o644)

    store.load()

    assert stat.S_IMODE(manifest.stat().st_mode) == 0o600
    assert [scene.id for scene in store.scenes] == ["mine"]


def test_an_already_private_manifest_is_left_alone(tmp_path: Path) -> None:
    payload = {"version": 1, "scenes": [], "triggers": []}
    store = _write(tmp_path, json.dumps(payload))
    manifest = tmp_path / "scenes" / "manifest.json"
    manifest.chmod(0o600)

    store.load()

    assert stat.S_IMODE(manifest.stat().st_mode) == 0o600


def test_a_manifest_whose_mode_cannot_be_narrowed_is_still_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tightening is best-effort: a filesystem that refuses it must not lose the scenes."""
    payload = {"version": 1, "scenes": [_user().to_dict()], "triggers": []}
    store = _write(tmp_path, json.dumps(payload))
    (tmp_path / "scenes" / "manifest.json").chmod(0o644)

    def refuse(self: Path, mode: int) -> None:
        raise OSError("read-only filesystem")

    monkeypatch.setattr(Path, "chmod", refuse)

    store.load()

    assert [scene.id for scene in store.scenes] == ["mine"]
