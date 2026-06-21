"""Command-line entry point.

Without arguments, launches the tray application. ``--version``, ``--selftest``
and ``--sensors`` are non-GUI diagnostics.
"""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .core.logging_setup import configure_logging


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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging()

    if args.selftest:
        from .support.selftest import run_selftest

        print(run_selftest())
        return 0

    if args.sensors:
        from .support.sensors_dump import run_sensors_dump

        print(run_sensors_dump())
        return 0

    configure_window_identity()

    from .app.application import SysbarApplication

    return int(SysbarApplication().run(None))


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    sys.exit(main(sys.argv[1:]))
