"""Fixtures for GTK window smoke tests.

These tests instantiate real GTK4/libadwaita windows to catch construction-time
regressions (a renamed widget, a broken template) that pure-logic tests cannot.
They need a display, so the whole package skips itself when none is reachable;
CI runs them under ``xvfb-run`` (see ``.github/workflows/ci.yml``).
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
import pytest  # noqa: E402
from gi.repository import Adw, Gtk  # noqa: E402


@pytest.fixture(scope="session")
def gtk(compiled_schema: str) -> object:
    """Initialise GTK/libadwaita once; skip the suite when no display is present.

    Depends on ``compiled_schema`` so ``GSETTINGS_SCHEMA_DIR`` is exported *before*
    ``Adw.init()`` runs. Without a session bus (CI, headless), GTK reads GSettings
    eagerly during init and caches the default schema source; if that happens
    before the env var is set, the source resolves to a stale system schema and a
    later read of a newly added key aborts the process with a fatal GIO error.
    """
    if not Gtk.init_check():
        pytest.skip("no display available for GTK UI smoke tests")
    Adw.init()
    return Adw
