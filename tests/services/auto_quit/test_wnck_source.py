import subprocess
import sys

from sysbar.services.auto_quit.wnck_source import WnckWindowSource


class _FakeWindow:
    def __init__(self, xid: int = 0, app_id: str = "", pid: int = 0) -> None:
        self._xid = xid
        self._app_id = app_id
        self._pid = pid

    def get_xid(self) -> int:
        return self._xid

    def get_class_group_name(self) -> str:
        return self._app_id

    def get_pid(self) -> int:
        return self._pid


def test_app_id_returns_class_group_name() -> None:
    window = _FakeWindow(app_id="org.gnome.Nautilus")
    assert WnckWindowSource._app_id(window) == "org.gnome.Nautilus"


def test_app_id_empty_string_returns_none() -> None:
    window = _FakeWindow(app_id="")
    assert WnckWindowSource._app_id(window) is None


def test_pid_returns_pid_when_positive() -> None:
    window = _FakeWindow(pid=4242)
    assert WnckWindowSource._pid(window) == 4242


def test_pid_zero_returns_none() -> None:
    window = _FakeWindow(pid=0)
    assert WnckWindowSource._pid(window) is None


def test_handle_opened_without_callback_is_noop() -> None:
    source = WnckWindowSource()
    source._handle_opened(None, _FakeWindow(xid=1, app_id="org.app", pid=9))
    # No callback registered: nothing to assert beyond not raising.


def test_handle_opened_forwards_xid_app_id_and_pid() -> None:
    source = WnckWindowSource()
    received: list[tuple[int, str | None, int | None]] = []
    source._on_opened = lambda xid, app_id, pid: received.append((xid, app_id, pid))

    source._handle_opened(None, _FakeWindow(xid=7, app_id="org.app", pid=4242))

    assert received == [(7, "org.app", 4242)]


def test_handle_opened_forwards_none_app_id_and_pid() -> None:
    source = WnckWindowSource()
    received: list[tuple[int, str | None, int | None]] = []
    source._on_opened = lambda xid, app_id, pid: received.append((xid, app_id, pid))

    source._handle_opened(None, _FakeWindow(xid=3, app_id="", pid=0))

    assert received == [(3, None, None)]


def test_handle_closed_without_callback_is_noop() -> None:
    source = WnckWindowSource()
    source._handle_closed(None, _FakeWindow(xid=1))
    # No callback registered: nothing to assert beyond not raising.


def test_handle_closed_forwards_xid() -> None:
    source = WnckWindowSource()
    received: list[int] = []
    source._on_closed = received.append

    source._handle_closed(None, _FakeWindow(xid=99))

    assert received == [99]


def test_import_does_not_load_gtk3() -> None:
    """Importing this module must leave GTK unloaded.

    The Wnck-3.0 typelib pulls in GTK 3, and gi allows one GTK version per
    process: a module-level Wnck import would make ``gi.require_version("Gtk",
    "4.0")`` fail for every GTK4 test collected afterwards. Runs in a subprocess
    because the check is about a fresh interpreter's global gi state.
    """
    code = (
        "import gi\n"
        "import sysbar.services.auto_quit.wnck_source\n"
        "gi.require_version('Gtk', '4.0')\n"
    )

    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr
