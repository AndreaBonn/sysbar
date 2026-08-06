"""Structural size limits on the source tree, enforced as a ratchet.

The project caps file length, function length and positional parameter count
(see code-standards). Those caps are convention until something fails when they
are breached, so they are asserted here.

Pre-existing breaches are frozen in the allowlists below rather than fixed in
passing: most are callback signatures imposed by the GIO vtables (``_handle_method``,
``_get_property``, portal responses), which cannot be narrowed, and the rest is
working code whose refactor is not in the scope that introduced this gate. The
allowlists are a ratchet: new code cannot join them, and an entry that stops
breaching must be removed, so the freeze cannot silently outlive the breach.
"""

from __future__ import annotations

import ast
from pathlib import Path

MAX_FILE_LINES = 300
MAX_FUNCTION_LINES = 30
MAX_POSITIONAL_PARAMS = 4

_SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"

# Functions longer than MAX_FUNCTION_LINES at the time the gate was introduced.
_LONG_FUNCTION_ALLOWLIST = frozenset(
    {
        "sysbar/app/tray/menu_builder.py::build_menu_items",
        "sysbar/services/hotkey/portal.py::PortalGlobalShortcuts._create_session",
        "sysbar/services/system_monitor/parsers.py::parse_upower_devices",
        "sysbar/ui/onboarding/onboarding_window.py::OnboardingWindow.__init__",
        "sysbar/ui/panel/panel_window.py::PanelWindow._build_content",
        "sysbar/ui/settings/settings_window.py::SettingsWindow._monitor_page",
        "sysbar/ui/uninstall/uninstaller_window.py::UninstallerWindow._build_ui",
    }
)

# Functions taking more than MAX_POSITIONAL_PARAMS positional parameters at the
# time the gate was introduced. The D-Bus and portal entries have signatures
# dictated by GIO and are not narrowable.
_WIDE_SIGNATURE_ALLOWLIST = frozenset(
    {
        "sysbar/app/tray/dbus_menu.py::DBusMenuServer._handle_method",
        "sysbar/app/tray/status_notifier.py::StatusNotifierItem._handle_method",
        "sysbar/app/tray/status_notifier.py::StatusNotifierItem._get_property",
        "sysbar/services/auto_quit/service.py::AutoQuitService.__init__",
        "sysbar/services/auto_quit/shell_extension_source.py::ShellExtensionWindowSource._handle_opened",
        "sysbar/services/auto_quit/shell_extension_source.py::ShellExtensionWindowSource._handle_closed",
        "sysbar/services/hotkey/portal.py::PortalGlobalShortcuts._on_session_response",
        "sysbar/services/hotkey/portal.py::PortalGlobalShortcuts._on_activated",
        "sysbar/services/system_monitor/sampler.py::SystemSampler.__init__",
        "sysbar/ui/settings/widgets.py::bound_spin",
        "sysbar/ui/settings/widgets.py::ComboBinding.__init__",
    }
)


def _source_files() -> list[Path]:
    return sorted(path for path in _SOURCE_ROOT.rglob("*.py") if "__pycache__" not in path.parts)


def _relative(path: Path) -> str:
    return path.relative_to(_SOURCE_ROOT).as_posix()


def _functions(path: Path) -> list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]]:
    """Return every function in ``path`` keyed by ``<relative path>::<qualname>``."""
    found: list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]] = []

    def walk(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                walk(child, f"{prefix}{child.name}.")
            elif isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                found.append((f"{_relative(path)}::{prefix}{child.name}", child))
                walk(child, f"{prefix}{child.name}.")

    walk(ast.parse(path.read_text(encoding="utf-8")), "")
    return found


def _function_length(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    return (node.end_lineno or node.lineno) - node.lineno + 1


def _positional_count(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Positional parameters, excluding ``self``/``cls`` and keyword-only ones.

    Keyword-only parameters are excluded deliberately: the cap exists to stop
    long positional argument lists, which are the ones callers get wrong. A
    builder taking eight named keywords is explicit at every call site.
    """
    args = node.args
    count = len(args.posonlyargs) + len(args.args)
    if args.args and args.args[0].arg in {"self", "cls"}:
        count -= 1
    return count


def test_no_source_file_exceeds_the_line_cap() -> None:
    oversized = {
        _relative(path): len(path.read_text(encoding="utf-8").splitlines())
        for path in _source_files()
        if len(path.read_text(encoding="utf-8").splitlines()) > MAX_FILE_LINES
    }

    assert not oversized, (
        f"Files over {MAX_FILE_LINES} lines must be split into modules: {oversized}"
    )


def test_no_function_exceeds_the_line_cap_outside_the_allowlist() -> None:
    oversized = {
        name: _function_length(node)
        for path in _source_files()
        for name, node in _functions(path)
        if _function_length(node) > MAX_FUNCTION_LINES and name not in _LONG_FUNCTION_ALLOWLIST
    }

    assert not oversized, (
        f"Functions over {MAX_FUNCTION_LINES} lines: {oversized}. Extract a helper "
        "rather than adding an allowlist entry."
    )


def test_no_function_exceeds_the_positional_parameter_cap_outside_the_allowlist() -> None:
    wide = {
        name: _positional_count(node)
        for path in _source_files()
        for name, node in _functions(path)
        if _positional_count(node) > MAX_POSITIONAL_PARAMS and name not in _WIDE_SIGNATURE_ALLOWLIST
    }

    assert not wide, (
        f"Functions over {MAX_POSITIONAL_PARAMS} positional parameters: {wide}. Group "
        "them into a dataclass or make them keyword-only."
    )


def test_allowlists_contain_no_stale_entries() -> None:
    """An allowlisted function that no longer breaches must leave the allowlist.

    Without this the freeze would outlive the breach and quietly re-authorise a
    future regression on the same function.
    """
    long_names = {
        name
        for path in _source_files()
        for name, node in _functions(path)
        if _function_length(node) > MAX_FUNCTION_LINES
    }
    wide_names = {
        name
        for path in _source_files()
        for name, node in _functions(path)
        if _positional_count(node) > MAX_POSITIONAL_PARAMS
    }

    stale_long = sorted(_LONG_FUNCTION_ALLOWLIST - long_names)
    stale_wide = sorted(_WIDE_SIGNATURE_ALLOWLIST - wide_names)

    assert not stale_long, f"Remove from _LONG_FUNCTION_ALLOWLIST, no longer over cap: {stale_long}"
    assert not stale_wide, (
        f"Remove from _WIDE_SIGNATURE_ALLOWLIST, no longer over cap: {stale_wide}"
    )
