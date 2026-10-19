from __future__ import annotations

from sysbar.app.whats_new import NOTES, notes_since, should_show_whats_new
from sysbar.core.constants import CURRENT_FEATURE_SET


def test_every_note_belongs_to_a_feature_set_that_exists() -> None:
    assert NOTES
    assert all(0 < note.feature_set <= CURRENT_FEATURE_SET for note in NOTES)


def test_notes_since_lists_only_what_is_newer_than_the_set_already_seen() -> None:
    newer = notes_since(seen=CURRENT_FEATURE_SET - 1, current=CURRENT_FEATURE_SET)

    assert newer
    assert all(note.feature_set == CURRENT_FEATURE_SET for note in newer)
    assert notes_since(seen=CURRENT_FEATURE_SET, current=CURRENT_FEATURE_SET) == ()


def test_an_updated_user_who_has_not_seen_the_current_set_gets_the_window() -> None:
    assert should_show_whats_new(onboarded=True, seen=CURRENT_FEATURE_SET - 1) is True


def test_a_user_on_the_current_set_does_not_see_it_again() -> None:
    assert should_show_whats_new(onboarded=True, seen=CURRENT_FEATURE_SET) is False


def test_a_first_run_gets_the_welcome_instead() -> None:
    # The welcome already covers everything; stacking a second window is noise.
    assert should_show_whats_new(onboarded=False, seen=0) is False
