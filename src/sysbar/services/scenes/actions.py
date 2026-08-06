"""What a scene does, as a closed set of typed actions.

A scene used to be three booleans plus a ``dict[str, object]`` of settings. Once
the user can build one, the actions stop being homogeneous: flipping a system
toggle, writing a settings key and choosing an audio output have nothing in
common but the fact that a scene performs them.

Modelled as a discriminated union, one frozen dataclass per variant with a
``kind`` tag, so that ``match`` is exhaustive and mypy rejects a handler that
forgets a variant. The alternative, a single class with every field optional,
would make ``SetOutputDevice`` with a boolean value representable, and then
something would have to decide what that means at runtime.

The set is deliberately closed and small. Notably absent is "run a command":
it carries almost all of the security risk of the feature and little of its
value, and the union accepts it later at the cost of one dataclass.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final, Literal

from ...core.constants import SCENE_WRITABLE_KEYS

KIND_TOGGLE: Final = "toggle"
KIND_SETTING: Final = "setting"
KIND_OUTPUT_DEVICE: Final = "output-device"


class SystemToggle(StrEnum):
    """A system state a scene can drive."""

    KEEP_AWAKE = "keep-awake"
    DO_NOT_DISTURB = "do-not-disturb"
    MICROPHONE_MUTED = "microphone-muted"


class SceneActionError(ValueError):
    """Raised when stored action data cannot be read back."""


@dataclass(frozen=True)
class SetToggle:
    """Drive one system toggle to a target state."""

    toggle: SystemToggle
    value: bool
    kind: Literal["toggle"] = KIND_TOGGLE

    def to_dict(self) -> dict[str, object]:
        return {"kind": self.kind, "toggle": self.toggle.value, "value": self.value}

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> SetToggle:
        try:
            toggle = SystemToggle(str(data["toggle"]))
        except (KeyError, ValueError) as error:
            raise SceneActionError(f"unknown toggle: {data.get('toggle')!r}") from error
        return cls(toggle=toggle, value=bool(data.get("value", False)))


@dataclass(frozen=True)
class SetSetting:
    """Write one settings key, restricted to the scene whitelist."""

    key: str
    value: bool | int | str
    kind: Literal["setting"] = KIND_SETTING

    def __post_init__(self) -> None:
        if self.key not in SCENE_WRITABLE_KEYS:
            raise SceneActionError(f"setting not writable by a scene: {self.key!r}")

    def to_dict(self) -> dict[str, object]:
        return {"kind": self.kind, "key": self.key, "value": self.value}

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> SetSetting:
        try:
            key = str(data["key"])
            value = data["value"]
        except KeyError as error:
            raise SceneActionError("setting action missing key or value") from error
        if not isinstance(value, bool | int | str):
            raise SceneActionError(f"unsupported setting value: {value!r}")
        return cls(key=key, value=value)


@dataclass(frozen=True)
class SetOutputDevice:
    """Make one audio device the default output."""

    device: str
    kind: Literal["output-device"] = KIND_OUTPUT_DEVICE

    def __post_init__(self) -> None:
        if not self.device:
            raise SceneActionError("output device action needs a device name")

    def to_dict(self) -> dict[str, object]:
        return {"kind": self.kind, "device": self.device}

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> SetOutputDevice:
        try:
            return cls(device=str(data["device"]))
        except KeyError as error:
            raise SceneActionError("output device action missing device") from error


SceneAction = SetToggle | SetSetting | SetOutputDevice

_BY_KIND: dict[str, type[SetToggle] | type[SetSetting] | type[SetOutputDevice]] = {
    KIND_TOGGLE: SetToggle,
    KIND_SETTING: SetSetting,
    KIND_OUTPUT_DEVICE: SetOutputDevice,
}


def action_from_dict(data: dict[str, object]) -> SceneAction:
    """Rebuild one action from stored data.

    Raises
    ------
    SceneActionError
        On an unknown kind or malformed payload. Raising rather than skipping is
        deliberate: the caller reading a whole manifest decides what a corrupt
        file means, and can say so once instead of silently dropping actions
        until a scene quietly stops doing half of what it used to.
    """
    kind = str(data.get("kind", ""))
    variant = _BY_KIND.get(kind)
    if variant is None:
        raise SceneActionError(f"unknown action kind: {kind!r}")
    return variant.from_dict(data)


def action_to_dict(action: SceneAction) -> dict[str, object]:
    """Serialise one action. Total over the union by construction."""
    return action.to_dict()
