"""Command-line entry point.

Without arguments, launches the tray application. ``--version``, ``--selftest``
and ``--sensors`` are non-GUI diagnostics.
"""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .core.logging_setup import configure_logging


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

    from .app.application import SysbarApplication

    return int(SysbarApplication().run(None))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
