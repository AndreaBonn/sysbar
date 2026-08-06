"""Publishing the catalogue as a D-Bus action group.

``Gio.Application`` exports its actions on the session bus, so everything
registered here is callable by any process running as the same user, through
``org.gtk.Actions.Activate`` or ``org.freedesktop.Application.ActivateAction``.
Two consequences drive this module:

* Unavailable commands are registered and *disabled*, never omitted. A consumer
  needs stable names; an action that appears and disappears with the session is
  worse to script against than one that is always there and sometimes refuses.
* A parameter arriving over the bus is untrusted input. It is checked for
  presence and type here, at the receiving end, and a mismatch is refused with a
  log line rather than passed on or swallowed.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Protocol

import gi

gi.require_version("Gio", "2.0")
gi.require_version("GLib", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

from .catalogue import CATALOGUE  # noqa: E402
from .models import Command, CommandId, CommandState, is_available  # noqa: E402

log = logging.getLogger(__name__)


class ActionTarget(Protocol):
    """The slice of ``Gio.ActionMap`` this module needs."""

    def add_action(self, action: Gio.Action) -> None: ...


@dataclass(frozen=True)
class CommandHandlers:
    """What each command actually does, split by whether it takes an argument."""

    simple: Mapping[CommandId, Callable[[], None]]
    parametric: Mapping[CommandId, Callable[[str], None]]

    def missing(self) -> list[CommandId]:
        """Command ids with no handler at all."""
        wired = set(self.simple) | set(self.parametric)
        return [command_id for command_id in CommandId if command_id not in wired]

    def misplaced(self) -> list[CommandId]:
        """Commands wired to the wrong kind of handler for their signature."""
        wrong = [
            command.id
            for command in CATALOGUE
            if command.is_parametric and command.id in self.simple
        ]
        wrong += [
            command.id
            for command in CATALOGUE
            if not command.is_parametric and command.id in self.parametric
        ]
        return wrong


def install_actions(
    target: ActionTarget, handlers: CommandHandlers, state: CommandState
) -> dict[CommandId, Gio.SimpleAction]:
    """Register every catalogue command, disabling the unavailable ones.

    Raises
    ------
    ValueError
        If a command has no handler, or has one of the wrong shape. This is a
        wiring mistake: better to fail at startup than to publish an action on
        the bus that silently does nothing.
    """
    _reject_incomplete(handlers)
    actions: dict[CommandId, Gio.SimpleAction] = {}
    for command in CATALOGUE:
        action = _build_action(command, handlers)
        action.set_enabled(is_available(command, state))
        target.add_action(action)
        actions[command.id] = action
    return actions


def refresh_enabled(actions: Mapping[CommandId, Gio.SimpleAction], state: CommandState) -> None:
    """Re-apply availability after settings or capabilities change."""
    for command in CATALOGUE:
        action = actions.get(command.id)
        if action is not None:
            action.set_enabled(is_available(command, state))


def _reject_incomplete(handlers: CommandHandlers) -> None:
    missing = handlers.missing()
    if missing:
        raise ValueError(f"commands with no handler: {[c.value for c in missing]}")
    misplaced = handlers.misplaced()
    if misplaced:
        raise ValueError(
            f"commands wired to the wrong handler kind: {[c.value for c in misplaced]}"
        )


def _build_action(command: Command, handlers: CommandHandlers) -> Gio.SimpleAction:
    if command.is_parametric:
        action = Gio.SimpleAction.new(
            command.id.value, GLib.VariantType.new(command.parameter_type)
        )
        action.connect("activate", _parametric_dispatch(command, handlers.parametric[command.id]))
        return action
    action = Gio.SimpleAction.new(command.id.value, None)
    action.connect("activate", _simple_dispatch(handlers.simple[command.id]))
    return action


def _simple_dispatch(handler: Callable[[], None]) -> Callable[..., None]:
    def dispatch(_action: Gio.SimpleAction, _parameter: GLib.Variant | None) -> None:
        handler()

    return dispatch


def _parametric_dispatch(command: Command, handler: Callable[[str], None]) -> Callable[..., None]:
    def dispatch(_action: Gio.SimpleAction, parameter: GLib.Variant | None) -> None:
        value = _string_argument(command, parameter)
        if value is None:
            return
        handler(value)

    return dispatch


def _string_argument(command: Command, parameter: GLib.Variant | None) -> str | None:
    """Validate an argument off the bus, or refuse it with a reason.

    Anything on the session bus can call this action, so the argument is checked
    rather than trusted: missing, wrongly typed or empty is refused here and
    never reaches a feature.
    """
    if parameter is None:
        log.warning("action called without its argument", extra={"action": command.id.value})
        return None
    type_string = parameter.get_type_string()
    if type_string != command.parameter_type:
        log.warning(
            "action called with the wrong argument type",
            extra={
                "action": command.id.value,
                "expected": command.parameter_type,
                "got": type_string,
            },
        )
        return None
    value = str(parameter.get_string())
    if not value:
        log.warning("action called with an empty argument", extra={"action": command.id.value})
        return None
    return value
