"""What the palette can show and what happens when it is chosen.

An entry is not a command. Commands are a fixed table (see
:mod:`sysbar.app.commands`); the palette also lists things whose number changes
with the session, such as clipboard entries and audio devices, which is exactly
why they may never reach the tray menu.

Whether an entry can be run is carried by the entry itself, as a
:class:`Runnable` or an :class:`Unavailable` with a reason. Not as a flag beside
an optional callback: that pair admits a state, "available with nothing to run",
that has no meaning and would have to be handled anyway.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum


class EntryKind(StrEnum):
    """Where an entry came from, used to group the results."""

    COMMAND = "command"
    SCENE = "scene"
    TOGGLE = "toggle"
    CLIPBOARD = "clipboard"
    SHELF = "shelf"
    DEVICE = "device"


@dataclass(frozen=True)
class Runnable:
    """The entry can be invoked."""

    invoke: Callable[[], None]


@dataclass(frozen=True)
class Unavailable:
    """The entry is shown but cannot be invoked, and says why."""

    reason: str


Activation = Runnable | Unavailable


@dataclass(frozen=True)
class PaletteEntry:
    """One row in the palette."""

    id: str
    title: str
    kind: EntryKind
    activation: Activation
    subtitle: str = ""
    #: Text the query is matched against. Defaults to the title, but is set
    #: separately for entries whose display form hides their content, so that a
    #: masked clipboard entry is still findable by typing what it contains.
    search_text: str = ""
    #: Whether the title is already a masked form of the underlying content.
    masked: bool = False
    #: Higher sorts first among equally good matches.
    weight: int = field(default=0)

    @property
    def is_runnable(self) -> bool:
        return isinstance(self.activation, Runnable)

    @property
    def haystack(self) -> str:
        """The text a query is matched against."""
        return self.search_text or self.title

    @property
    def unavailable_reason(self) -> str:
        """Why this entry cannot be run, empty when it can."""
        return self.activation.reason if isinstance(self.activation, Unavailable) else ""

    def activate(self) -> bool:
        """Run the entry. Returns whether anything was invoked."""
        match self.activation:
            case Runnable(invoke=invoke):
                invoke()
                return True
            case Unavailable():
                return False
