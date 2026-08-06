# Changelog

All notable changes to Sysbar are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.2.0] - 2026-08-07

### Added
- Command line and D-Bus control: `sysbar <action> [argument]` forwards a
  command to the already-running instance and exits, covering all 15 actions
  (panel, command palette, scenes window, settings, shelf, clipboard history,
  uninstaller, keep awake, microphone, do-not-disturb, dark mode, Focus scene,
  activate a scene by id, clear the active scene, quit).
  `sysbar --list-actions` prints the full catalog. Actions are exposed as a
  GTK action group on the session bus (`org.gtk.Actions` on
  `io.github.AndreaBonn.Sysbar`), so they can also be driven directly over
  D-Bus.
- Command palette: a window opened with a global hotkey that searches
  commands, quick toggles, scenes, clipboard entries, shelf items and audio
  devices with a fuzzy, accent- and case-insensitive match. An empty query
  shows the main commands grouped by category. Clipboard entries flagged as a
  likely secret are masked by default. Off by default, behind the
  `hotkey-palette-enabled` setting.
- User-defined scenes: scenes can now be created, edited and deleted from the
  Scenes window, not just the three built-in presets (Focus, Presentation,
  Power saving). The presets cannot be deleted, but editing one creates a
  restorable override. Each scene is a list of typed actions: toggle a system
  switch, write a settings key from a fixed whitelist, or choose the audio
  output device. Scenes are stored in a JSON manifest under
  `~/.local/share/sysbar/scenes/manifest.json`, created with `0o600`
  permissions.
- Scene triggers: scenes can activate automatically from two sources, an
  external monitor being connected or the power/battery level. A scene
  activated manually is never overridden by a trigger, and restoring the
  previous scene when the condition ends is optional per rule. Off by
  default, behind the `scene-triggers-enabled` setting.

### Fixed
- Tray: the Scenes submenu now uses a fixed pool of rows, so the node count no
  longer shifts with the number of scenes and the menu host stops
  desynchronizing item state.
- Localization: scene names no longer go through the translation system, which
  was only correct as long as scenes were three, fixed and predefined.
- Scenes: a manifest that could not be read (corrupted or invalid JSON) was
  silently overwritten, discarding the user's scenes; it is now moved aside
  to `manifest.json.corrupt` and the path is named in the log.
- Scenes: a settings-key action was reported as applied even when the write
  failed, and a toggle action accepted a non-boolean value instead of being
  rejected.
- Scene triggers: a trigger could overwrite a scene the user had switched to
  by hand; a manually activated scene now takes precedence until cleared.
- Localization: a duplicate entry in the translation catalogue broke
  compilation of the message catalog.
- Startup: Sysbar failed to start when the window source used by auto-quit
  could not subscribe to window events; it now degrades instead of aborting
  startup.
- Localization: the built-in scene names (Focus, Presentation, Power saving)
  are now translated in the Scenes window instead of showing in English.

## [1.1.1] - 2026-06-21

### Fixed
- Window icon: the panel and settings windows showed GNOME's generic icon in
  the dock and window switcher. The window class now matches the desktop entry
  so the Sysbar icon is used.
- Version display: the About screen, `--version`, the self-test and the update
  check reported a stale `1.0.0`. The version is now derived from the installed
  package metadata, keeping `pyproject.toml` the single source of truth.

## [1.1.0] - 2026-06-21

### Added
- Tray: peripheral device batteries (mouse, keyboard, headset and more) in the
  menu, with a settings toggle to hide them.
- Shelf: open dropped items with the system default application on double-click.
- Branding: ship and register the Sysbar application icon, replacing the generic
  GNOME gear.

### Fixed
- Scenes submenu no longer collapses when opened.
- Italian: the remaining tray, scenes, settings and alert strings that rendered
  in English are now translated.
- Debian package: the Italian UI stayed in English even with `it` selected. The
  install rules copied `data/locale/*` into a not-yet-existing destination, so
  `cp` renamed the `it/` directory to `locale/`, flattening the language level
  that gettext needs. The destination is now created before the copy.

## [1.0.0] - 2026-06-20

First stable release.

### Added
- Clipboard history manager: search, pin and re-copy entries, persisted across sessions.
  Accessible from the tray and via a configurable global hotkey. Disabled by default;
  must be enabled explicitly in Settings (history is stored in plain text on disk).
- History sparklines for CPU, GPU, memory, network, power and battery in the panel,
  toggleable per metric.
- Per-process network throughput section in the panel, best-effort via `ss`.
- Default audio output and input device switcher in the panel.
- Configurable global shortcuts for keep-awake, shelf, clipboard manager and Focus scene,
  replacing the single hardcoded keep-awake hotkey. Registered through the XDG
  GlobalShortcuts portal, so they work on both X11 and Wayland.
- Wayland support for auto-quit through a bundled GNOME Shell extension
  (`sysbar-window-manager@andreabonn.github.io`) that exposes window open/close
  events over D-Bus. The extension is installed by the `.deb` and enabled once
  per user; on X11, libwnck is used and the extension is not needed.
- Composable scenes (Focus, Presentation, Power saving) applied from a tray Scenes
  submenu: each scene sets keep-awake, do-not-disturb, mic mute and display settings
  in a single action.
- Window construction smoke tests run under `xvfb` in CI.

## [0.3.0] - 2026-06-18

### Changed
- Settings: tray metric placement combos for hardware not detected on the
  system (GPU, battery, power) are now disabled with an explanatory subtitle,
  instead of silently showing nothing in the bar or menu.

## [0.2.2] - 2026-06-18

### Fixed
- Tray dropdown desync (greyed or duplicated entries): the menu now has a fixed
  shape with stable ids, and hidden rows use the visible flag.

## [0.2.1] - 2026-06-18

### Fixed
- Corrupted or duplicated tray menu entries: dropdown metrics now refresh on
  open via `AboutToShow` instead of rebuilding the menu on every sample.

## [0.2.0] - 2026-06-18

### Added
- Each tray metric can be placed individually in the always-visible bar, in the
  dropdown menu, or hidden.

### Changed
- Existing boolean visibility settings migrate automatically on first start.

## [0.1.0] - 2026-06-16

### Added
- Initial release. A single Ubuntu/GNOME system tray application that bundles
  six opt-in utilities:
  - **System monitor**: live CPU, RAM, disk, network, temperature and power
    metrics, placed in the always-visible bar or the dropdown menu.
  - **Per-application volume mixer**: independent volume and mute per running
    app, over PipeWire or PulseAudio.
  - **Keep awake**: inhibits sleep, idle and lid suspension, with an optional
    timer and a battery watchdog.
  - **Auto-quit**: closes tracked applications automatically, with a graceful
    `SIGTERM` then `SIGKILL` escalation and an exception list.
  - **Uninstaller**: removes desktop applications and their leftover files,
    with package removal gated behind polkit.
  - **Shelf**: a temporary drop area for files, links, text and images, with
    JSON persistence across sessions.
- Local only: no account, no telemetry. Every feature is opt-in and degrades
  gracefully when a dependency, extension or session capability is missing.

[1.2.0]: https://github.com/AndreaBonn/sysbar/releases/tag/v1.2.0
[1.1.1]: https://github.com/AndreaBonn/sysbar/releases/tag/v1.1.1
[1.1.0]: https://github.com/AndreaBonn/sysbar/releases/tag/v1.1.0
[1.0.0]: https://github.com/AndreaBonn/sysbar/releases/tag/v1.0.0
[0.3.0]: https://github.com/AndreaBonn/sysbar/releases/tag/v0.3.0
[0.2.2]: https://github.com/AndreaBonn/sysbar/releases/tag/v0.2.2
[0.2.1]: https://github.com/AndreaBonn/sysbar/releases/tag/v0.2.1
[0.2.0]: https://github.com/AndreaBonn/sysbar/releases/tag/v0.2.0
[0.1.0]: https://github.com/AndreaBonn/sysbar/releases/tag/v0.1.0
