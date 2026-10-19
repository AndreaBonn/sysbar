from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from sysbar.app.device_choices import DeviceChoices, default_choices, name_at
from sysbar.services.audio.models import AudioDevice


def _devices(*, defaults: tuple[bool, ...]) -> list[AudioDevice]:
    return [
        AudioDevice(
            index=index + 10,
            name=f"sink-{index}",
            description=f"Speaker {index}",
            kind="sink",
            is_default=is_default,
        )
        for index, is_default in enumerate(defaults)
    ]


def test_default_choices_no_default_selects_first_and_preserves_order() -> None:
    devices = _devices(defaults=(False, False, False))

    assert default_choices(devices=devices) == DeviceChoices(
        labels=("Speaker 0", "Speaker 1", "Speaker 2"),
        names=("sink-0", "sink-1", "sink-2"),
        selected=0,
    )


def test_default_choices_third_default_selects_two() -> None:
    assert default_choices(devices=_devices(defaults=(False, False, True))).selected == 2


def test_default_choices_two_defaults_selects_last() -> None:
    assert default_choices(devices=_devices(defaults=(True, False, True))).selected == 2


def test_default_choices_empty_returns_empty_choices_without_selection() -> None:
    assert default_choices(devices=_devices(defaults=(False,))).selected == 0
    assert default_choices(devices=[]) == DeviceChoices(labels=(), names=(), selected=None)


@pytest.mark.parametrize(("index", "expected"), [(0, "sink-0"), (1, "sink-1")])
def test_name_at_valid_index_returns_device_name(index: int, expected: str) -> None:
    choices = default_choices(devices=_devices(defaults=(False, True)))

    assert name_at(choices=choices, index=index) == expected


@pytest.mark.parametrize("index", [-1, 2, 3])
def test_name_at_invalid_index_returns_none(index: int) -> None:
    choices = default_choices(devices=_devices(defaults=(False, True)))

    assert name_at(choices=choices, index=1) == "sink-1"
    assert name_at(choices=choices, index=index) is None


def test_name_at_empty_choices_returns_none() -> None:
    assert name_at(choices=default_choices(devices=_devices(defaults=(True,))), index=0) == "sink-0"
    assert name_at(choices=default_choices(devices=[]), index=0) is None


def test_device_choices_frozen_rejects_selection_changes() -> None:
    choices = default_choices(devices=_devices(defaults=(True,)))

    with pytest.raises(FrozenInstanceError):
        choices.__setattr__("selected", 1)
    assert choices.selected == 0
