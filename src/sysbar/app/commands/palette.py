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

from collections.abc import Callable, Mapping

from ...core.i18n import _
from ...services.palette.models import Activation, EntryKind, PaletteEntry, Runnable, Unavailable
from .actions import CommandHandlers
from .catalogue import CATALOGUE
from .models import (
    Category,
    Command,
    CommandState,
    Requirement,
    is_available,
    unavailable_reason,
)

_NO_HANDLER_REASON = "Not available in this session"
_FIX_LABEL = "Turn on"
# What a command does, in the words of someone choosing it; the scriptable name
# stays in the searchable text for those who know it.
_CATEGORY_SUBTITLES = {
    Category.WINDOW: "Opens a window",
    Category.TOGGLE: "Quick toggle",
    Category.SCENE: "Scenes",
    Category.APPLICATION: "Sysbar",
}

Enablers = Mapping[Requirement, Callable[[], None]]


def command_entries(
    handlers: CommandHandlers, state: CommandState, *, enablers: Enablers | None = None
) -> list[PaletteEntry]:
    """One row per non-parametric command, unavailable ones included.

    ``enablers`` maps a requirement the user can satisfy from here (a feature
    switched off in settings) to the call that satisfies it.
    """
    fixes = enablers or {}
    return [
        _entry(command, handlers, state, fixes)
        for command in CATALOGUE
        if not command.is_parametric
    ]


def _entry(
    command: Command, handlers: CommandHandlers, state: CommandState, fixes: Enablers
) -> PaletteEntry:
    title = _(command.title)
    return PaletteEntry(
        id=f"command:{command.id.value}",
        title=title,
        subtitle=_(_CATEGORY_SUBTITLES[command.category]),
        kind=EntryKind.COMMAND,
        activation=_activation(command, handlers, state, fixes),
        search_text=f"{title} {command.id.value}",
    )


def _activation(
    command: Command, handlers: CommandHandlers, state: CommandState, fixes: Enablers
) -> Activation:
    handler = handlers.simple.get(command.id)
    if handler is None:
        return Unavailable(reason=_(_NO_HANDLER_REASON))
    if not is_available(command, state):
        reason = _(unavailable_reason(command) or _NO_HANDLER_REASON)
        fix = fixes.get(command.requires)
        return Unavailable(reason=reason, fix=fix, fix_label=_(_FIX_LABEL) if fix else "")
    return Runnable(invoke=handler)
