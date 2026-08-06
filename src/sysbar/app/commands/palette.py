"""Catalogue commands, as palette rows.

Unavailable commands are listed rather than dropped, with the reason attached:
the palette is where a user goes to ask "can I do X from here", and answering
"the shelf is turned off in settings" is more useful than showing nothing and
letting them conclude the feature does not exist.

Parametric commands are left out. ``activate-scene`` needs a scene id, and the
scenes are already listed one row each by the scene source, each carrying its
own id, so listing the bare command too would only add a row that cannot run.
"""

from __future__ import annotations

from ...services.palette.models import Activation, EntryKind, PaletteEntry, Runnable, Unavailable
from .actions import CommandHandlers
from .catalogue import CATALOGUE
from .models import Command, CommandState, is_available, unavailable_reason

_NO_HANDLER_REASON = "Not available in this session"


def command_entries(handlers: CommandHandlers, state: CommandState) -> list[PaletteEntry]:
    """One row per non-parametric command, unavailable ones included."""
    return [_entry(command, handlers, state) for command in CATALOGUE if not command.is_parametric]


def _entry(command: Command, handlers: CommandHandlers, state: CommandState) -> PaletteEntry:
    return PaletteEntry(
        id=f"command:{command.id.value}",
        title=command.title,
        subtitle=command.id.value,
        kind=EntryKind.COMMAND,
        activation=_activation(command, handlers, state),
    )


def _activation(command: Command, handlers: CommandHandlers, state: CommandState) -> Activation:
    handler = handlers.simple.get(command.id)
    if handler is None:
        return Unavailable(reason=_NO_HANDLER_REASON)
    if not is_available(command, state):
        return Unavailable(reason=unavailable_reason(command) or _NO_HANDLER_REASON)
    return Runnable(invoke=handler)
