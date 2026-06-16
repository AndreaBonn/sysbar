# Design decisions and assumptions

Decisions taken during implementation, with rationale. Where the specification
was ambiguous, the assumption made is recorded here.

## Identity

- App ID is `io.github.AndreaBonn.Sysbar` (the specification used
  `it.linkalab.Sysbar`, marked modifiable; the project belongs to AndreaBonn,
  not Linkalab). This drives the GSettings schema id and path, the D-Bus names,
  the desktop file names and the icon name.
- `GITHUB_OWNER = "AndreaBonn"`, repository `sysbar`. Used by the optional
  update check.

## Runtime and dependencies

- The development and packaged environments use a venv created on the system
  `python3` with `--system-site-packages`, so PyGObject/GTK come from the
  distribution (`python3-gi`). A uv-managed interpreter would not see the system
  GI typelibs. Only pure-Python dependencies (psutil, pulsectl, python-xlib,
  requests) are installed into the venv.
- `pygobject-stubs` is intentionally absent: it depends on PyGObject, which in a
  `--system-site-packages` venv would be rebuilt from source. mypy runs in
  `strict` mode and treats the GI namespaces as untyped
  (`ignore_missing_imports` plus `disallow_subclassing_any = false`). Type
  safety on the project's own code is preserved; GI calls are `Any`.

## Architecture

- The tray is a hand-rolled `org.kde.StatusNotifierItem` plus
  `com.canonical.dbusmenu` server over Gio.DBus. `libayatana-appindicator3` is
  linked against GTK3 and cannot share a process with GTK4, so the menu is
  exposed over D-Bus instead of through a `Gtk.Menu`.
- Every system boundary (procfs/sysfs, sensors, NVML, UPower, pulsectl, logind,
  ScreenSaver, libwnck, dpkg/snap/flatpak, pkexec, X11) sits behind a `Protocol`
  with a concrete adapter. Services receive the adapter by dependency injection,
  so the business logic is unit-tested without hardware or a live session.
- Test coverage is measured on the framework-agnostic business logic. GUI
  windows and D-Bus/subprocess adapters are excluded (they are verified
  manually, with no display in CI). Reported coverage (~85%) reflects the logic,
  not the glue.

## Feature-specific decisions

- Shake-to-open polls the global pointer with X11 `XQueryPointer` rather than
  XInput2 `RawMotion`: the same shake detection with far less fragile code,
  still X11-gated.
- The uninstaller always moves user residue to the trash (`Gio.File.trash`,
  never `rm`). System package removal is a separate, explicit switch, gated on
  polkit and never applied to manual installs.
- Auto-quit keeps a system whitelist (gnome-shell, the app itself, ...) that is
  inviolable, separate from the user-configurable exception list.
- i18n uses a runtime-rebindable `_` (`core/i18n.py`) so it is statically
  resolvable (no implicit `builtins._`) and the language can switch without a
  restart. `.mo` files are compiled by gettext at build time (CI and packaging);
  without them the UI falls back to English.

## Assumptions (ambiguous in the spec)

- Speed test endpoint: configurable, with no default, so no third-party service
  is hard-coded. The feature is shown but inactive until an endpoint is set.
- App ID namespace: `io.github.<user>` (GNOME convention for projects without an
  owned domain).

## Known limitations and deferred work

- Shelf: items are a flat list; batch/stack grouping is not implemented. The
  floating window is undecorated but precise cursor anchoring and keep-above on
  X11 are not wired (GTK4 lacks portable APIs for them).
- Uninstaller: selection is from the installed-app list; drag-and-drop of a
  `.desktop` onto the window and the "is a dependency of other packages" warning
  are not implemented.
- i18n: the translation infrastructure and Italian catalogue cover the primary
  surfaces (tray menu, onboarding, settings page titles, panel sections);
  wrapping the remaining widget strings is mechanical follow-up.
- Speed test has no historical graph yet.
- The tray uses a themed symbolic icon; a branded `io.github.AndreaBonn.Sysbar`
  icon is not yet shipped.
- The `.deb` packaging files are complete and conventional but the package was
  not built in the development environment (requires `debhelper` build deps and
  network for the venv).
