"""Panel section to pick the default audio output and input device.

Two combo rows bound to a :class:`DeviceSwitcher`. Selecting a row applies the
choice immediately. Programmatic repopulation is guarded so refreshing the lists
never looks like a user selection (which would re-trigger a switch).
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from ...core.i18n import _  # noqa: E402
from ...services.audio.device_switcher import DeviceSwitcher  # noqa: E402
from ...services.audio.models import AudioDevice  # noqa: E402


class DeviceSection(Adw.PreferencesGroup):
    """Default output/input selectors driven by a :class:`DeviceSwitcher`."""

    def __init__(self) -> None:
        super().__init__(title=_("Audio devices"), visible=False)
        self._switcher: DeviceSwitcher | None = None
        self._output_names: list[str] = []
        self._input_names: list[str] = []
        self._updating = False
        self._output_row = Adw.ComboRow(title=_("Output"))
        self._input_row = Adw.ComboRow(title=_("Input"))
        self.add(self._output_row)
        self.add(self._input_row)
        self._output_row.connect("notify::selected", self._on_output_selected)
        self._input_row.connect("notify::selected", self._on_input_selected)

    def bind(self, switcher: DeviceSwitcher) -> None:
        self._switcher = switcher
        switcher.connect("devices-changed", lambda _src: self._repopulate())
        self._repopulate()

    def _repopulate(self) -> None:
        if self._switcher is None:
            return
        self._updating = True
        self._output_names = self._fill(self._output_row, self._switcher.outputs)
        self._input_names = self._fill(self._input_row, self._switcher.inputs)
        self._updating = False
        self.set_visible(bool(self._output_names or self._input_names))

    @staticmethod
    def _fill(row: Adw.ComboRow, devices: list[AudioDevice]) -> list[str]:
        model = Gtk.StringList()
        names: list[str] = []
        default_index = 0
        for index, device in enumerate(devices):
            model.append(device.description)
            names.append(device.name)
            if device.is_default:
                default_index = index
        row.set_model(model)
        row.set_visible(bool(devices))
        if devices:
            row.set_selected(default_index)
        return names

    def _on_output_selected(self, row: Adw.ComboRow, _param: object) -> None:
        if self._updating or self._switcher is None:
            return
        index = row.get_selected()
        if 0 <= index < len(self._output_names):
            self._switcher.set_default_output(self._output_names[index])

    def _on_input_selected(self, row: Adw.ComboRow, _param: object) -> None:
        if self._updating or self._switcher is None:
            return
        index = row.get_selected()
        if 0 <= index < len(self._input_names):
            self._switcher.set_default_input(self._input_names[index])
