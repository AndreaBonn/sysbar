# Changelog

All notable changes to Sysbar are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
  replacing the single hardcoded keep-awake hotkey.
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

[0.3.0]: https://github.com/AndreaBonn/sysbar/releases/tag/v0.3.0
[0.2.2]: https://github.com/AndreaBonn/sysbar/releases/tag/v0.2.2
[0.2.1]: https://github.com/AndreaBonn/sysbar/releases/tag/v0.2.1
[0.2.0]: https://github.com/AndreaBonn/sysbar/releases/tag/v0.2.0
[0.1.0]: https://github.com/AndreaBonn/sysbar/releases/tag/v0.1.0
