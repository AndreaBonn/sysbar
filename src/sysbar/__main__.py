"""Command-line entry point.

Without arguments, launches the tray application. ``--version``, ``--selftest``
and ``--sensors`` are non-GUI diagnostics.

With a command name, it does not launch anything: it forwards the command to the
instance already running, over the session bus, and exits. That path stays free
of any GTK import, both because a script has no use for a display and because
pulling in the UI would drag GTK3 in through libwnck alongside GTK4.
"""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .app.commands.catalogue import CATALOGUE, command_ids
from .core.logging_setup import configure_logging

EXIT_OK = 0
EXIT_NOT_RUNNING = 1
# argparse already exits with 2 on an unknown choice; reused here so that every
# "you asked for something that does not exist" failure looks the same.
EXIT_BAD_USAGE = 2


def configure_window_identity() -> None:
    """Pin the process name to ``APP_ID`` so the desktop shell shows the brand.

    On X11 GTK derives a window's ``WM_CLASS`` from the program name. Launched
    through the installed console script the interpreter name (``python3``)
    leaks in, so the shell cannot match the window to
    ``io.github.AndreaBonn.Sysbar.desktop`` and falls back to a generic icon.
    Forcing the program name to ``APP_ID`` before any window is realised makes
    the ``WM_CLASS`` match the desktop entry, restoring the branded icon in the
    dock and window switcher.
    """
    import gi

    gi.require_version("GLib", "2.0")
    from gi.repository import GLib

    from .core.constants import APP_ID, APP_NAME

    GLib.set_prgname(APP_ID)
    GLib.set_application_name(APP_NAME)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sysbar", description="Sysbar system tray toolkit.")
    parser.add_argument("--version", action="version", version=f"sysbar {__version__}")
    parser.add_argument(
        "--selftest", action="store_true", help="print a capability diagnostic and exit"
    )
    parser.add_argument("--sensors", action="store_true", help="dump sensor readings and exit")
    parser.add_argument(
        "--list-actions", action="store_true", help="list the commands that can be sent"
    )
    parser.add_argument(
        "action",
        nargs="?",
        choices=command_ids(),
        metavar="ACTION",
        help="send a command to the running instance instead of starting one",
    )
    parser.add_argument(
        "argument",
        nargs="?",
        metavar="ARGUMENT",
        help="argument for commands that take one, such as a scene id",
    )
    return parser


def format_action_list() -> str:
    """The catalogue, one command per line, widest name first for alignment."""
    width = max(len(command.id.value) for command in CATALOGUE)
    return "\n".join(f"{command.id.value.ljust(width)}  {command.title}" for command in CATALOGUE)


def send_action(action: str, argument: str | None) -> int:
    """Forward one command to the running instance and report the outcome."""
    from .app.remote import DBusRemoteControl, NotRunningError

    try:
        DBusRemoteControl().activate(action, argument)
    except NotRunningError:
        print(
            "Sysbar is not running. Start it first, then send the command again.",
            file=sys.stderr,
        )
        return EXIT_NOT_RUNNING
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging()

    if args.selftest:
        from .support.selftest import run_selftest

        print(run_selftest())
        return EXIT_OK

    if args.sensors:
        from .support.sensors_dump import run_sensors_dump

        print(run_sensors_dump())
        return EXIT_OK

    if args.list_actions:
        print(format_action_list())
        return EXIT_OK

    if args.action:
        return send_action(args.action, args.argument)

    configure_window_identity()

    from .app.application import SysbarApplication

    return int(SysbarApplication().run(None))


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    sys.exit(main(sys.argv[1:]))
