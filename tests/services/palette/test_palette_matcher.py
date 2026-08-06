"""Ranking behaviour of the palette matcher."""

from __future__ import annotations

from sysbar.services.palette.matcher import group_by_kind, normalize, rank, score
from sysbar.services.palette.models import (
    EntryKind,
    PaletteEntry,
    Runnable,
    Unavailable,
)


def _entry(
    title: str,
    *,
    kind: EntryKind = EntryKind.COMMAND,
    runnable: bool = True,
    search_text: str = "",
    weight: int = 0,
) -> PaletteEntry:
    return PaletteEntry(
        id=title,
        title=title,
        kind=kind,
        activation=Runnable(invoke=lambda: None) if runnable else Unavailable(reason="nope"),
        search_text=search_text,
        weight=weight,
    )


# --- normalize ------------------------------------------------------------


def test_normalize_folds_case() -> None:
    assert normalize("Open Panel") == "open panel"


def test_normalize_strips_accents() -> None:
    assert normalize("però") == "pero"


def test_normalize_leaves_plain_text_alone() -> None:
    assert normalize("shelf") == "shelf"


# --- score ----------------------------------------------------------------


def test_an_empty_query_matches_everything() -> None:
    assert score("", "anything") == 0


def test_a_query_longer_than_the_text_cannot_match() -> None:
    assert score("abcdef", "abc") is None


def test_characters_out_of_order_do_not_match() -> None:
    assert score("cba", "abc") is None


def test_a_subsequence_matches() -> None:
    assert score("opcl", "Open clipboard history") is not None


def test_a_missing_character_does_not_match() -> None:
    assert score("opz", "Open clipboard history") is None


def test_matching_is_case_insensitive() -> None:
    assert score("OPEN", "open panel") is not None


def test_matching_ignores_accents() -> None:
    assert score("pero", "Però adesso") is not None


def test_a_contiguous_match_scores_above_a_scattered_one() -> None:
    contiguous = score("open", "open panel")
    scattered = score("open", "o p e n")

    assert contiguous is not None and scattered is not None
    assert contiguous > scattered


def test_a_word_start_match_scores_above_a_mid_word_one() -> None:
    word_start = score("cl", "open clipboard")
    mid_word = score("cl", "oscilloscope")

    assert word_start is not None and mid_word is not None
    assert word_start > mid_word


def test_a_prefix_match_scores_above_a_late_match() -> None:
    prefix = score("set", "settings")
    late = score("set", "reset the counter")

    assert prefix is not None and late is not None
    assert prefix > late


# --- rank -----------------------------------------------------------------


def test_rank_drops_entries_that_do_not_match() -> None:
    entries = [_entry("Open panel"), _entry("Quit")]

    assert [entry.title for entry in rank(entries, "panel", limit=10)] == ["Open panel"]


def test_rank_returns_everything_for_an_empty_query() -> None:
    entries = [_entry("Open panel"), _entry("Quit")]

    assert len(rank(entries, "", limit=10)) == 2


def test_rank_respects_the_limit() -> None:
    entries = [_entry(f"Command {index}") for index in range(20)]

    assert len(rank(entries, "command", limit=5)) == 5


def test_rank_puts_the_better_match_first() -> None:
    entries = [_entry("Reset the counter"), _entry("Settings")]

    assert rank(entries, "set", limit=10)[0].title == "Settings"


def test_runnable_entries_outrank_unavailable_ones_with_the_same_text() -> None:
    entries = [_entry("Open shelf", runnable=False), _entry("Open shelf", runnable=True)]

    assert rank(entries, "open shelf", limit=10)[0].is_runnable is True


def test_weight_breaks_a_tie_between_equal_matches() -> None:
    entries = [_entry("Open shelf", weight=0), _entry("Open shelf", weight=5)]

    assert rank(entries, "open shelf", limit=10)[0].weight == 5


def test_ranking_is_stable_across_runs() -> None:
    entries = [_entry("Alpha command"), _entry("Beta command"), _entry("Gamma command")]

    first = [entry.title for entry in rank(entries, "command", limit=10)]
    second = [entry.title for entry in rank(entries, "command", limit=10)]

    assert first == second


def test_rank_matches_the_search_text_not_the_displayed_title() -> None:
    """A masked entry must still be findable by what it actually contains."""
    entries = [_entry("ghp_••••", search_text="ghp_realtokenvalue")]

    assert len(rank(entries, "realtoken", limit=10)) == 1


def test_a_query_matching_nothing_returns_an_empty_list() -> None:
    assert rank([_entry("Open panel")], "zzzz", limit=10) == []


# --- grouping -------------------------------------------------------------


def test_grouping_buckets_by_kind() -> None:
    entries = [
        _entry("Open panel", kind=EntryKind.COMMAND),
        _entry("Focus", kind=EntryKind.SCENE),
        _entry("Open shelf", kind=EntryKind.COMMAND),
    ]

    grouped = group_by_kind(entries)

    assert [entry.title for entry in grouped["command"]] == ["Open panel", "Open shelf"]
    assert [entry.title for entry in grouped["scene"]] == ["Focus"]


def test_grouping_preserves_the_ranking_within_a_bucket() -> None:
    ranked = rank(
        [_entry("Reset the counter"), _entry("Settings")],
        "set",
        limit=10,
    )

    grouped = group_by_kind(ranked)

    assert grouped["command"][0].title == "Settings"


def test_grouping_an_empty_result_is_empty() -> None:
    assert group_by_kind([]) == {}


# --- selection movement ---------------------------------------------------


def test_moving_down_from_nothing_selected_lands_on_the_first_row() -> None:
    from sysbar.services.palette.matcher import next_index

    assert next_index(current=-1, count=5, step=1) == 0


def test_moving_down_advances_by_one() -> None:
    from sysbar.services.palette.matcher import next_index

    assert next_index(current=2, count=5, step=1) == 3


def test_moving_up_goes_back_by_one() -> None:
    from sysbar.services.palette.matcher import next_index

    assert next_index(current=2, count=5, step=-1) == 1


def test_moving_down_past_the_end_stays_on_the_last_row() -> None:
    from sysbar.services.palette.matcher import next_index

    assert next_index(current=4, count=5, step=1) == 4


def test_moving_up_past_the_start_stays_on_the_first_row() -> None:
    from sysbar.services.palette.matcher import next_index

    assert next_index(current=0, count=5, step=-1) == 0


def test_there_is_nowhere_to_move_in_an_empty_list() -> None:
    from sysbar.services.palette.matcher import next_index

    assert next_index(current=-1, count=0, step=1) == -1


def test_a_single_row_list_stays_put_in_both_directions() -> None:
    from sysbar.services.palette.matcher import next_index

    assert next_index(current=0, count=1, step=1) == 0
    assert next_index(current=0, count=1, step=-1) == 0
