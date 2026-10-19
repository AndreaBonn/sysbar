"""Boundaries for peripheral battery readings worth reporting."""

from __future__ import annotations

from typing import Any

import pytest

from sysbar.services.system_monitor.parsers import _is_reportable


@pytest.mark.parametrize(
    ("props", "expected"),
    [
        ({"Percentage": 0.0}, False),
        ({"Percentage": 0.1}, True),
        ({"Percentage": 50.0, "PowerSupply": True}, False),
        ({"Percentage": 50.0, "IsPresent": False}, False),
        ({}, False),
        ({"Percentage": -1.0}, False),
        ({"Percentage": 50.0, "PowerSupply": False, "IsPresent": True}, True),
    ],
)
def test_is_reportable_boundary(props: dict[str, Any], expected: bool) -> None:
    assert _is_reportable(props) == expected
