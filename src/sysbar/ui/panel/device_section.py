"""Panel section to pick the default audio output and input device.

Two combo rows bound to a :class:`DeviceSwitcher`. Selecting a row applies the
choice immediately. Programmatic repopulation is guarded so refreshing the lists
never looks like a user selection (which would re-trigger a switch), and it is
deferred to idle: a switch emits ``devices-changed`` from inside the combo's own
``notify::selected`` handler, and replacing that combo's model there never
returns under GTK 4.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk  # noqa: E402

from ...app.device_choices import DeviceChoices, default_choices, name_at  # noqa: E402
from ...core.i18n import _  # noqa: E402
from ...services.audio.device_switcher import DeviceSwitcher  # noqa: E402
from ...services.audio.models import AudioDevice  # noqa: E402


class DeviceSection(Adw.PreferencesGroup):
    """Default output/input selectors driven by a :class:`DeviceSwitcher`."""

    def __init__(self) -> None:
        super().__init__(title=_("Audio devices"), visible=False)
        self._switcher: DeviceSwitcher | None = None
        self._output_choices = default_choices(devices=[])
        self._input_choices = default_choices(devices=[])
        self._updating = False
        self._repopulate_pending = False
        self._output_row = Adw.ComboRow(title=_("Output"))
        self._input_row = Adw.ComboRow(title=_("Input"))
        self.add(self._output_row)
        self.add(self._input_row)
        self._output_row.connect("notify::selected", self._on_output_selected)
        self._input_row.connect("notify::selected", self._on_input_selected)

    def bind(self, switcher: DeviceSwitcher) -> None:
        self._switcher = switcher
        switcher.connect("devices-changed", self._on_devices_changed)
        self._repopulate()

    def _on_devices_changed(self, _switcher: DeviceSwitcher) -> None:
        if self._repopulate_pending:
            return
        self._repopulate_pending = True
        GLib.idle_add(self._repopulate_when_idle)

    def _repopulate_when_idle(self) -> bool:
        self._repopulate_pending = False
        self._repopulate()
        return False

    def _repopulate(self) -> None:
        if self._switcher is None:
            return
        self._updating = True
        self._output_choices = self._fill(row=self._output_row, devices=self._switcher.outputs)
        self._input_choices = self._fill(row=self._input_row, devices=self._switcher.inputs)
        self._updating = False
        self.set_visible(bool(self._output_choices.names or self._input_choices.names))

    @staticmethod
    def _fill(row: Adw.ComboRow, devices: list[AudioDevice]) -> DeviceChoices:
        choices = default_choices(devices=devices)
        model = Gtk.StringList.new(strings=choices.labels)
        row.set_model(model)
        row.set_visible(bool(choices.names))
        if choices.selected is not None:
            row.set_selected(choices.selected)
        return choices

    def _on_output_selected(self, row: Adw.ComboRow, _param: object) -> None:
        if self._updating or self._switcher is None:
            return
        name = name_at(choices=self._output_choices, index=row.get_selected())
        if name is not None:
            self._switcher.set_default_output(name=name)

    def _on_input_selected(self, row: Adw.ComboRow, _param: object) -> None:
        if self._updating or self._switcher is None:
            return
        name = name_at(choices=self._input_choices, index=row.get_selected())
        if name is not None:
            self._switcher.set_default_input(name=name)
