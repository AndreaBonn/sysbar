"""Choosing an audio device from the panel must not freeze the application."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.ui

_SCENARIO = Path(__file__).with_name("device_switch_scenario.py")
_TIMEOUT_SECONDS = 20


def test_picking_an_output_device_switches_it_and_returns(gtk: object) -> None:
    """A switch refreshes the device list from inside the combo's own handler.

    Rebuilding the combo's model there never returned under GTK 4, so the whole
    tray froze on the first click. The scenario must finish, with the clicked
    device both applied and still shown as selected.
    """
    try:
        result = subprocess.run(
            [sys.executable, str(_SCENARIO)],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_SECONDS,
            env=os.environ.copy(),
            check=False,
        )
    except subprocess.TimeoutExpired:
        pytest.fail("selecting an output device froze the panel")

    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["1", "hdmi"]
