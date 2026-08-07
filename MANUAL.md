**English** | [Italiano](MANUAL.it.md)

# Sysbar user manual

This manual covers Sysbar 1.2.0. It describes how to use every feature, one step
at a time. For a shorter overview of what Sysbar is and how to install it, read
the [README](./README.md).

Two things to know before anything else. Sysbar has no main window: it lives in
the tray, at the right of the GNOME top bar, and everything starts from that
icon. And every feature is off when you install it, so a fresh Sysbar shows
little more than the icon until you turn things on.

## Table of contents

- [First launch](#first-launch)
  - [The welcome screen](#the-welcome-screen)
  - [What each capability unlocks](#what-each-capability-unlocks)
  - [Running the welcome screen again](#running-the-welcome-screen-again)
- [The tray icon](#the-tray-icon)
  - [Reading the label](#reading-the-label)
  - [The dropdown menu](#the-dropdown-menu)
- [The preferences window](#the-preferences-window)
  - [General](#general)
  - [Monitor](#monitor)
  - [Alerts](#alerts)
  - [Keep Awake](#keep-awake-tab)
  - [Features](#features-tab)
  - [About](#about)
- [The metrics panel](#the-metrics-panel)
- [Keep awake](#keep-awake)
- [Volume mixer and audio devices](#volume-mixer-and-audio-devices)
- [Threshold alerts](#threshold-alerts)
- [Clipboard history](#clipboard-history)
- [The shelf](#the-shelf)
- [Auto-quit](#auto-quit)
- [The application uninstaller](#the-application-uninstaller)
- [Scenes](#scenes)
  - [Using a scene](#using-a-scene)
  - [Creating a scene](#creating-a-scene)
  - [Editing and deleting](#editing-and-deleting)
  - [Automatic triggers](#automatic-triggers)
  - [When a scene applies only in part](#when-a-scene-applies-only-in-part)
- [The command palette](#the-command-palette)
- [Global shortcuts](#global-shortcuts)
- [Command line and D-Bus](#command-line-and-d-bus)
- [Troubleshooting](#troubleshooting)
- [Where your data is kept](#where-your-data-is-kept)
- [Removing Sysbar](#removing-sysbar)

## First launch

Start Sysbar from the applications menu, or run `sysbar` in a terminal. If the
`.deb` installed the autostart entry, it also starts on its own at every login.

### The welcome screen

The first time it runs, Sysbar opens a window titled "Welcome to Sysbar" instead
of going straight to the tray. It has one job: tell you which features your
system can actually support, before you go looking for them in settings.

Under "Detected on this system" there is one row per capability, each with a
check mark or a crossed-out icon. Nothing here is a decision you have to make.
Read the list, then press **Get started**. The window closes and the tray icon
appears.

### What each capability unlocks

| Row | What it gates | If it is missing |
|---|---|---|
| X11 session (auto-quit, shelf shake) | Window tracking and shake-to-open on X11 | You are on Wayland; auto-quit needs the shell extension, and shake-to-open is unavailable |
| Wayland auto-quit (Sysbar shell extension) | Window tracking on Wayland | Enable the bundled extension, see [Troubleshooting](#troubleshooting) |
| Global keep-awake hotkey | All global shortcuts | Your session has no GlobalShortcuts portal; use the tray or the command line instead |
| Tray icon support | The tray icon itself | Install `gir1.2-ayatanaappindicator3-0.1`, or a shell extension that shows tray icons |
| Temperature sensors | CPU and system temperatures, temperature alerts | Your hardware exposes no sensors readable by `psutil` |
| Audio mixer and microphone toggle | Per-app mixer, device switcher, microphone mute | PipeWire or PulseAudio is not running |
| Do-not-disturb and dark-mode toggles | Those two quick toggles, and any scene using them | You are not on a GNOME desktop |
| Keep awake | Sleep and idle inhibition | `logind` is unreachable |
| Battery metrics | Battery readouts and battery alerts | No UPower, or a desktop machine with no battery |
| System uninstaller | Removing the system package of an app | polkit is unavailable; residue removal still works |

A missing capability never breaks the rest of Sysbar. The feature that depends on
it is disabled and says so, and the rest keeps working.

### Running the welcome screen again

Open the tray menu, choose **Settings**, go to the **About** tab and press
**Restart** next to "Run onboarding again". The welcome screen appears at the
next start. This is the quickest way to re-check capabilities after you have
installed a missing package or enabled the shell extension.

## The tray icon

### Reading the label

Next to the icon, Sysbar prints the metrics you placed in the bar (see
[Monitor](#monitor)). With a keep-awake session running, a `▶` marker is
prepended, followed by the remaining time if the session has a duration and the
countdown is enabled.

If you place no metric in the bar and turn peripheral batteries off, Sysbar
stops sampling for the tray entirely and shows the icon alone.

### The dropdown menu

Click the icon. The menu always has the same shape, in this order:

1. **Metric readouts** - one read-only line per metric placed in the menu.
2. **Peripheral batteries** - up to six lines for connected mice, keyboards,
   headsets, controllers and similar, when the option is on.
3. **Keep awake** - a check-marked entry that starts and ends the session.
4. **Quick toggles** - mute or unmute the microphone, turn do-not-disturb on or
   off, switch between light and dark. Each is present only if the session
   supports it. While another application is recording, the microphone row is
   replaced by a disabled "Microphone in use" line.
5. **Scenes** - a submenu listing your scenes plus a "None" entry that clears
   the active one. It holds up to eight scenes; beyond that, use the Scenes
   window, the palette or the command line.
6. **Open panel**, **Open shelf**, **Clipboard**, **Uninstall app…**,
   **Settings** - the shelf and clipboard rows appear only when those features
   are enabled.
7. **Quit**.

Rows that do not apply right now are hidden rather than removed. This is
deliberate: menu hosts on Ubuntu identify entries by position, and a menu that
changed length between updates would leave the wrong entries checked.

## The preferences window

Open it from the tray menu with **Settings**. It has six tabs down the side.
Changes take effect as you make them; there is no Save button.

### General

- **Language** - System, English or Italiano. Changing it shows a message asking
  you to restart Sysbar; windows already open keep the previous language.
- **Start at login** - writes or removes the autostart entry in
  `~/.config/autostart/`.
- **Check for updates** - asks GitHub Releases whether a newer version exists.
  It never downloads or installs anything.
- **Global shortcuts** - one switch per shortcut. See
  [Global shortcuts](#global-shortcuts) for how to assign the actual keys.
- **Automation** - a single switch, "Automatic scene triggers", which allows
  scene rules to change the active scene on their own. Off by default.

![Settings: general preferences](./assets/screenshots/settings-general.png)

### Monitor

- **Tray metrics** - CPU, GPU, memory, network, battery and power. Each has
  three positions: `Off`, `Bar` (in the always-visible label) or `Menu` (in the
  dropdown). Hardware not present on your machine is greyed out and reads "Not
  detected on this system".
- **Device batteries** - lists connected peripherals in the menu.
- **Sampling** - interval (1, 2 or 5 seconds), temperature unit (Celsius or
  Fahrenheit) and how memory is drawn in the bar (dot, percent or both).
- **History graphs** - one switch per metric. When on, the panel draws a
  sparkline of the last 120 samples next to that metric.

![Settings: tray metric placement](./assets/screenshots/settings-monitor.png)

### Alerts

Described in full under [Threshold alerts](#threshold-alerts).

### Keep Awake (tab)

Described in full under [Keep awake](#keep-awake).

![Settings: keep awake](./assets/screenshots/settings-keep-awake.png)

### Features (tab)

The master switches for the optional features: volume mixer, auto-quit, shelf,
shake to open the shelf, clipboard history. All off by default.

![Settings: feature toggles](./assets/screenshots/settings-features.png)

### About

The installed version, the button that replays the welcome screen, and the
project credit.

![Settings: about and onboarding](./assets/screenshots/settings-about.png)

## The metrics panel

Open it from **Open panel** in the tray menu, from the palette, or with
`sysbar open-panel`. It is a scrollable window with one group per topic:

- **System** - CPU load, CPU temperature, GPU, memory, uptime.
- **Network** - current speed and cumulative totals.
- **Power** - battery and power draw.
- **Fan Control (beta)** - fan speeds. It has no settings row yet; turn it on
  with `gsettings set io.github.AndreaBonn.Sysbar monitor-show-fan-control-beta true`
  and reopen the panel.
- **Top processes** - the five heaviest processes, each with a button that ends
  it. Sysbar asks for confirmation first, sends `SIGTERM`, and escalates to
  `SIGKILL` if the process is still alive after five seconds.
- **Network by process** - the five processes using the most bandwidth. It reads
  `/proc` and calls `ss`, so it needs `ss` installed and does not see every kind
  of traffic.
- **Audio devices** and the **volume mixer** - see the next section.

Metrics with their history graph enabled show a sparkline on the right of the
row. The panel only samples while it is open.

![Panel: system and network metrics](./assets/screenshots/panel-system.png)

## Keep awake

Keep awake stops the machine from sleeping, going idle or suspending when you
close the lid. Use it while a long build, a download or a video call is running.

To start a session, click **Keep awake** in the tray menu. A check mark appears
next to the entry and a `▶` marker next to the tray label. Click it again to
end the session.

Configure the behaviour in the **Keep Awake** tab of preferences:

- **Default duration** - Indefinite, 15 minutes, 30 minutes, 1 hour or 2 hours.
  A timed session ends by itself when the time is up.
- **Stop below battery** - Never, 5%, 10%, 15% or 20%. A watchdog checks the
  charge periodically and ends the session when it falls below the threshold, so
  keep awake cannot flatten the battery unattended.
- **Show countdown in tray** - prints the time left next to the `▶` marker.
- **Keep awake with lid closed** - also inhibits the lid switch. Turn it off if
  you want closing the lid to suspend even during a session.

You can also toggle it with a global shortcut, from the palette, or with
`sysbar toggle-keep-awake`.

## Volume mixer and audio devices

Enable **Volume mixer** in the Features tab, then open the panel. Two groups
appear at the bottom.

**Audio devices** has an Output row and an Input row, each a dropdown of the
devices the system knows about. Picking one makes it the default for the whole
desktop, the same as choosing it in GNOME's sound settings.

The **mixer** has one slider per application currently playing audio, with a
mute button. Volume goes up to 200%, so you can push a quiet application above
the system level. The list follows applications as they open and close audio
streams; an application that plays nothing is not listed.

Both need PipeWire or PulseAudio. Without them the group says the mixer is
unavailable rather than showing an empty list.

![Panel: power and per-app mixer](./assets/screenshots/panel-mixer.png)

## Threshold alerts

Sysbar can send a desktop notification when a metric crosses a limit. Open
preferences, go to **Alerts**, and turn on **Enable alerts** - that switch
gates all of them.

| Setting | Fires when | Range |
|---|---|---|
| CPU load (%) | CPU stays at or above this percentage | 0-100 |
| CPU sustained for (s) | How long the CPU must hold above the limit first | 0-3600 |
| Memory used (%) | Memory reaches this percentage | 0-100 |
| Disk used (%) | The root filesystem is this full | 0-100 |
| Temperature (°C) | Any sensor reaches this temperature | 0-150 |
| Battery low (%) | On battery, the charge falls to this percentage | 0-100 |

Setting a threshold to `0` turns off that alert alone, leaving the others
active.

Two behaviours worth knowing. An alert fires once, when the value crosses the
threshold, and rearms only after the value comes back down: a machine that sits
at 95% memory for an hour notifies once, not every two seconds. And the CPU
alert waits for the breach to last as long as "CPU sustained for" before it
notifies, which is what keeps a momentary spike during a build from being
reported. The default is 30 seconds.

## Clipboard history

Off by default, and stored in plain text on disk. If you routinely copy
passwords or tokens, leave it off.

Enable **Clipboard history** in the Features tab. From then on, Sysbar records
the text you copy. Open the history with **Clipboard** in the tray menu, from
the palette, or with a global shortcut.

In the window:

- **Search clipboard** filters the list as you type.
- Clicking an entry copies it back to the clipboard.
- **Pin** keeps an entry at the top and protects it from being dropped.
  **Unpin** releases it.
- **Remove** deletes one entry; **Clear unpinned** empties everything except the
  pinned ones.

The history keeps the last 50 entries. When it is full, the oldest unpinned
entry is dropped to make room; pinned entries are never dropped.

Entries that look like a secret - something beginning with `sk-`, `ghp_`, a URL
carrying a `token=` parameter, a long opaque string mixing character classes -
are shown masked in the command palette, with a **Reveal** action to see them.
The detection is a heuristic tuned to over-mask rather than under-mask, so it
will occasionally hide a long identifier that is not a secret at all.

## The shelf

The shelf is a temporary place to park things while you move them between
applications. Enable **Shelf** in the Features tab, then open it with **Open
shelf** in the tray menu, a global shortcut, or the palette.

Drag files, links, selected text or images onto the window and they become
items. Double-click an item to open it with the system default application.
**Clear shelf** empties it. The contents survive a restart: they are saved to a
JSON file, and dropped text and images are written into Sysbar's own data
directory so they stay available after the source application closes.

**Shelf: shake to open** in the Features tab opens the shelf when you shake the
pointer, a quick series of left-right reversals inside about half a second. It
works on X11 only, because it reads pointer motion through X.

## Auto-quit

Some applications keep running after you close their last window. Auto-quit
notices and shuts them down.

Turn on **Auto-quit closed apps** in the Features tab. When an application's
last window closes, Sysbar sends it `SIGTERM` after a two-second grace period,
and `SIGKILL` if it is still running five seconds later.

To spare an application, add its identifier to the exception list. There is no
settings row for it yet; use `gsettings`:

```bash
# read the current list
gsettings get io.github.AndreaBonn.Sysbar auto-quit-exceptions

# keep Spotify and Slack running
gsettings set io.github.AndreaBonn.Sysbar auto-quit-exceptions "['spotify', 'slack']"
```

The identifier is the application id, which matches the window's `WM_CLASS` in
lower case. The list starts with `org.gnome.Nautilus` already in it, because the
file manager is expected to outlive its windows.

Independently of that list, Sysbar never terminates the session itself:
`gnome-shell`, `gnome-session`, `Xorg`, `Xwayland`, `plasmashell` and Sysbar's
own process are excluded no matter what the settings say.

How windows are tracked depends on your session. On X11 Sysbar uses libwnck and
needs nothing extra. On Wayland it needs the bundled GNOME Shell extension; see
[Troubleshooting](#troubleshooting). If neither source works, auto-quit stays
off and says so instead of silently doing nothing.

## The application uninstaller

Open **Uninstall app…** from the tray menu, from the palette, or with
`sysbar open-uninstaller`.

1. Pick the application from the **Installed app** dropdown.
2. Sysbar scans your home directory and lists the files and folders it left
   behind under **Residue**, with the size of each. Untick anything you want to
   keep.
3. If the application came from a package and polkit is available, **Also
   remove the system package** appears. Leave it off to clean the residue only.
   It is absent for applications installed by hand, which have no package to
   remove.
4. Press **Move residue to Trash**. Files go to the Trash, not to permanent
   deletion, so a mistake is recoverable. The status line reports how much was
   freed and how many items failed.

Removing the package runs through polkit, so your desktop asks for your
password.

## Scenes

A scene applies several settings at once. Instead of muting the microphone,
turning on do-not-disturb and starting keep awake one after the other, you
activate Focus.

Sysbar ships three scenes that cannot be deleted:

| Scene | What it does |
|---|---|
| Focus | Keep awake on, do-not-disturb on, microphone muted, threshold alerts off |
| Presentation | Keep awake on with no time limit, do-not-disturb on, microphone unmuted, lid-close suspension left to the system |
| Power saving | Keep awake off, do-not-disturb off, microphone unmuted, sampling interval 5 seconds, low-battery alert at 20% |

### Using a scene

Open the tray menu, then the **Scenes** submenu, and pick one. The active scene
is marked. **None** clears it, which stops Sysbar from considering any scene
active; it does not undo the settings the scene applied.

Focus can also be bound to a global shortcut. Any scene can be activated from
the palette or with `sysbar activate-scene <id>`.

### Creating a scene

Open the Scenes window with **Manage scenes** in the palette or
`sysbar open-scenes`, then press **New scene**.

1. Give it a **Name**. This is the text you will see in the tray, so keep it
   short.
2. Under **What it does**, set each action. Every switch has three positions:
   **Turn on**, **Turn off** and **Leave unchanged**. Anything left unchanged is
   not touched when the scene activates.
   - Keep awake, do-not-disturb and microphone are the three system switches.
   - **Audio output** picks the device to switch to, or "Kept as it is".
3. Optionally set a trigger under **When to activate it**; see below.
4. Press **Save scene**.

Scenes can also write a small set of preference keys, the same ones the built-in
scenes use: whether alerts are enabled, the low-battery alert level, lid
behaviour, the default keep-awake duration, the sampling interval and the tray
countdown. The editor does not expose all of them, but an action it cannot draw
is preserved rather than discarded when you save, so editing a built-in scene
never silently drops part of it. The window shows a note saying how many further
actions the scene carries.

The whitelist is deliberate. A scene is a convenience, not a second way to
reconfigure Sysbar, so a hand-edited manifest cannot make a scene rewrite
arbitrary settings.

### Editing and deleting

In the Scenes window each row carries **Edit** and, for your own scenes,
**Delete**.

Editing a built-in scene does not overwrite it. Sysbar keeps your version as an
override and shows **Restore the built-in** on that row, which brings back the
original.

### Automatic triggers

A scene can activate on its own. Two conditions are available in the editor,
under **When to activate it**:

- **An external monitor is connected**. Sysbar waits two seconds after a display
  change before acting, because plugging in one monitor emits a burst of events.
- **Battery drops below a level**, with the level in **Below this charge (%)**,
  or **Running on battery** regardless of level.

**Undo when the condition ends** restores the scene that was active before, once
the condition no longer holds. Leave the trigger on **Never** for a scene you
only ever activate by hand.

Triggers are gated twice. The rule has to be set on the scene, and **Automatic
scene triggers** has to be on in the General tab; it is off by default. A scene
you activated by hand is never replaced by a trigger until you clear it. Sysbar
also leaves at least ten seconds between two trigger-driven changes.

### When a scene applies only in part

An action can fail for reasons outside Sysbar: muting the microphone needs
PipeWire, do-not-disturb needs the GNOME desktop interface, a settings write can
be refused. When that happens you get a "Scene partly applied" notification
naming the scene and saying how many of its actions took effect, rather than a
tray state you have to reverse-engineer.

## The command palette

The palette is one search box for everything Sysbar can do. It is off by
default: turn on **Open command palette** in the Global shortcuts group, then
assign a key (see the next section).

Once open:

- Type to search. Matching ignores case and accents and accepts letters out of
  order, so `opnl` finds "Open the metrics panel". Results are scored, closest
  first, and capped at 40.
- The arrow keys move the selection, Enter runs it, Esc closes the window. The
  cursor is already in the search box when it opens, and the window closes if it
  loses focus.
- An empty search box lists the main commands grouped by category: windows,
  toggles, scenes, application.

It searches more than commands. Scenes, clipboard entries, shelf items and audio
output devices are all in the same list, so `focus` can return both the Focus
scene and a clipboard entry containing the word.

Clipboard entries that look like a secret are masked; use the **Reveal** action
on the row to see one.

## Global shortcuts

Sysbar registers its shortcuts through the XDG GlobalShortcuts portal, which
works on both X11 and Wayland and lets the shortcut fire while another
application has focus.

There are two steps, and the second one happens outside Sysbar:

1. In preferences, **General** tab, **Global shortcuts** group, turn on the
   shortcuts you want: toggle keep awake, open shelf, open clipboard, toggle the
   Focus scene, open the command palette.
2. Assign the actual key combination in your desktop's keyboard settings. On
   GNOME that is Settings, Keyboard, Keyboard Shortcuts, where Sysbar's
   shortcuts appear once registered.

Sysbar deliberately does not ship default key combinations: it cannot know what
is already taken on your desktop.

If the "Global keep-awake hotkey" row was crossed out on the welcome screen,
your session provides no GlobalShortcuts portal and none of this will work. Use
the tray menu, or bind a custom GNOME shortcut to the `sysbar` command line
described below.

## Command line and D-Bus

With Sysbar already running, `sysbar <action>` forwards a command to it and
exits. It does not start a second instance.

```bash
sysbar open-panel
sysbar toggle-keep-awake
sysbar activate-scene focus
```

`sysbar --list-actions` prints all fifteen actions with a description:

| Action | Effect |
|---|---|
| `open-panel` | Open the metrics panel |
| `open-palette` | Open the command palette |
| `open-scenes` | Open the Scenes window |
| `open-settings` | Open preferences |
| `open-shelf` | Open the shelf |
| `open-clipboard` | Open clipboard history |
| `open-uninstaller` | Open the uninstaller |
| `toggle-keep-awake` | Start or end a keep-awake session |
| `toggle-microphone` | Mute or unmute the microphone |
| `toggle-dnd` | Turn do-not-disturb on or off |
| `toggle-dark-mode` | Switch between light and dark |
| `toggle-focus-scene` | Activate or clear the Focus scene |
| `activate-scene <id>` | Activate a scene by id |
| `clear-scene` | Clear the active scene |
| `quit` | Quit Sysbar |

Scene ids for the built-in scenes are `focus`, `presentation` and
`power-saving`. Scenes you create have the id shown in the Scenes window.

Exit codes: `0` on success, `1` when no instance is running, `2` for an unknown
action, in which case the valid ones are printed.

An action whose capability is missing in the current session, or whose feature
is off in settings, stays in the list but does nothing. The name is stable for
scripts either way.

The same actions are on the session bus as a GTK action group
(`org.gtk.Actions` on `io.github.AndreaBonn.Sysbar`, object path
`/io/github/AndreaBonn/Sysbar`), so a script, a systemd unit or a window manager
like sway or i3 can call them directly.

Three flags do not involve a running instance:

```bash
sysbar --version     # installed version
sysbar --selftest    # capability diagnostic
sysbar --sensors     # raw sensor readings
```

## Troubleshooting

**The tray icon does not appear.** Ubuntu's GNOME shows tray icons through an
extension. Check that `gir1.2-ayatanaappindicator3-0.1` is installed and that
the AppIndicator extension is enabled.

**A feature says it is unavailable.** Run `sysbar --selftest`. It prints the
same capability list as the welcome screen, from the current session, and tells
you which boundary is not answering.

**Auto-quit does nothing on Wayland.** The bundled GNOME Shell extension has to
be enabled once per user:

```bash
gnome-extensions enable sysbar-window-manager@andreabonn.github.io
```

Then log out and back in. Check your session type with
`echo $XDG_SESSION_TYPE`.

**Global shortcuts do not fire.** Confirm the switch is on in preferences, then
confirm a key is actually assigned in your desktop's keyboard settings. Both
steps are needed.

**No temperatures, no GPU, no battery.** Those rows are greyed out when the
hardware is not detected. `sysbar --sensors` dumps everything Sysbar can read,
which distinguishes "no sensor" from "sensor read incorrectly".

**Sysbar starts in the wrong language.** Set it in the General tab and restart
the application. If you installed the `.deb` before version 1.1.0, upgrade:
older packages flattened the translation directory and left the interface in
English.

**Scenes disappeared.** If the manifest could not be read, Sysbar moves it aside
to `~/.local/share/sysbar/scenes/manifest.json.corrupt` and starts from the
built-in scenes rather than overwriting your file. The path is named in the log.

**Reading the log.** Sysbar logs to standard output. Start it from a terminal
and raise the level:

```bash
SYSBAR_LOG_LEVEL=DEBUG sysbar
```

## Where your data is kept

| What | Where |
|---|---|
| All settings | GSettings, schema `io.github.AndreaBonn.Sysbar` |
| Scenes and their triggers | `~/.local/share/sysbar/scenes/manifest.json`, readable by your user only |
| Shelf items | `~/.local/share/sysbar/shelf/`, a JSON manifest plus the copied files |
| Clipboard history | `~/.local/share/sysbar/clipboard/`, plain text |
| Autostart entry | `~/.config/autostart/` |

Nothing leaves the machine. The only network request Sysbar ever makes is the
optional update check against GitHub Releases, and only if you leave "Check for
updates" on.

To export or reset your settings:

```bash
# back up
gsettings list-recursively io.github.AndreaBonn.Sysbar > sysbar-settings.txt

# reset everything to defaults
gsettings reset-recursively io.github.AndreaBonn.Sysbar
```

## Removing Sysbar

```bash
sudo apt remove sysbar
```

This leaves your settings and data in place, so reinstalling picks up where you
left off. To remove them too:

```bash
gsettings reset-recursively io.github.AndreaBonn.Sysbar
rm -rf ~/.local/share/sysbar
rm -f ~/.config/autostart/io.github.AndreaBonn.Sysbar.desktop
```
