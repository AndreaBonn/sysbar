from __future__ import annotations

from sysbar.app.uninstall_content import (
    category_label,
    filter_apps,
    package_subtitle,
    removal_summary,
    short_path,
)
from sysbar.services.uninstall.models import LeftoverCategory, PackageManager


def test_every_leftover_category_has_a_readable_name() -> None:
    labels = {category_label(category) for category in LeftoverCategory}

    assert len(labels) == len(LeftoverCategory)
    assert category_label(LeftoverCategory.DESKTOP_ENTRY) == "Menu shortcut"
    assert all("_" not in label for label in labels)


def test_filter_apps_returns_positions_so_same_named_apps_stay_distinct() -> None:
    names = ["GIMP", "Terminal", "Éditeur", "Terminal", "gedit"]

    assert filter_apps(names, "") == [0, 1, 2, 3, 4]
    assert filter_apps(names, "term") == [1, 3]
    assert filter_apps(names, "EDIT") == [2, 4]
    assert filter_apps(names, "zzz") == []


def test_short_path_replaces_the_home_directory_with_a_tilde() -> None:
    assert short_path("/home/ann/.config/gimp", home="/home/ann") == "~/.config/gimp"
    assert short_path("/var/lib/x", home="/home/ann") == "/var/lib/x"
    assert short_path("/home/annex/x", home="/home/ann") == "/home/annex/x"


def test_summary_before_an_app_is_chosen_asks_for_one() -> None:
    summary = removal_summary(chosen=False, count=0, size_bytes=0)

    assert summary.can_remove is False
    assert summary.status == "Choose an app to see what it left behind"


def test_summary_with_nothing_found_disables_the_button() -> None:
    summary = removal_summary(chosen=True, count=0, size_bytes=0)

    assert summary.can_remove is False
    assert summary.status == "Nothing left to clean up for this app"


def test_summary_with_leftovers_names_count_and_size_on_the_button() -> None:
    summary = removal_summary(chosen=True, count=3, size_bytes=2_500_000)

    assert summary.can_remove is True
    assert summary.button == "Move 3 items (2.4 MB) to the Trash"


def test_package_subtitle_names_the_installer_or_why_it_is_unavailable() -> None:
    assert (
        package_subtitle(PackageManager.APT, "gimp", removable=True) == "Installed with apt: gimp"
    )
    assert package_subtitle(PackageManager.MANUAL, None, removable=False) == (
        "Not available: installed by hand, or no administrator rights"
    )
