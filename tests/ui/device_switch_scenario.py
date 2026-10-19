"""Pick an output device in a real DeviceSection, the way a click does.

Run as a separate process by ``test_device_section_reentrancy.py``: the hang it
guards against happens inside GTK, where no Python timeout can interrupt it,
so only a process boundary turns it into a failure instead of a stuck suite.
Prints ``<selected index> <default sink>`` and exits 0 when the switch returns.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib  # noqa: E402

from sysbar.services.audio.device_switcher import DeviceSwitcher  # noqa: E402
from sysbar.services.audio.models import AudioDevice, SinkInput  # noqa: E402
from sysbar.ui.panel.device_section import DeviceSection  # noqa: E402

_NAMES = ("spk", "hdmi", "usb")


class _Backend:
    """A sound server whose default sink follows ``set_default_sink``."""

    def __init__(self) -> None:
        self.default = _NAMES[0]

    def list_sinks(self) -> list[AudioDevice]:
        return [
            AudioDevice(index, name, name.upper(), "sink", name == self.default)
            for index, name in enumerate(_NAMES)
        ]

    def list_sources(self) -> list[AudioDevice]:
        return []

    def list_sink_inputs(self) -> list[SinkInput]:
        return []

    def set_default_sink(self, name: str) -> None:
        self.default = name

    def set_default_source(self, name: str) -> None: ...

    def move_sink_input(self, input_index: int, sink_index: int) -> None: ...


def _drain() -> None:
    context = GLib.MainContext.default()
    while context.iteration(False):
        pass


def main() -> None:
    Adw.init()
    backend = _Backend()
    switcher = DeviceSwitcher(backend)
    section = DeviceSection()
    section.bind(switcher=switcher)
    switcher.refresh()
    _drain()

    section._output_row.set_selected(1)
    _drain()

    print(section._output_row.get_selected(), backend.default)


if __name__ == "__main__":
    main()
