// Sysbar Window Manager — GNOME Shell extension (Shell 45+, ESM).
//
// On Wayland there is no libwnck for an external process to watch windows, so
// this extension runs inside gnome-shell and re-publishes window open/close
// events over the session bus. Sysbar's ShellExtensionWindowSource consumes
// them; the auto-quit decision logic stays in Sysbar.
//
// D-Bus: name io.github.AndreaBonn.Sysbar.Shell,
//        object /io/github/AndreaBonn/Sysbar/Shell,
//        interface io.github.AndreaBonn.Sysbar.WindowManager.

import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

const BUS_NAME = 'io.github.AndreaBonn.Sysbar.Shell';
const OBJECT_PATH = '/io/github/AndreaBonn/Sysbar/Shell';

const IFACE = `
<node>
  <interface name="io.github.AndreaBonn.Sysbar.WindowManager">
    <method name="ListWindows">
      <arg type="a(tsu)" direction="out" name="windows"/>
    </method>
    <signal name="WindowOpened">
      <arg type="t" name="window_id"/>
      <arg type="s" name="wm_class"/>
      <arg type="u" name="pid"/>
    </signal>
    <signal name="WindowClosed">
      <arg type="t" name="window_id"/>
    </signal>
  </interface>
</node>`;

function windowId(metaWindow) {
    // Stable, session-unique sequence number; works on X11 and Wayland.
    return metaWindow.get_stable_sequence();
}

function windowClass(metaWindow) {
    return metaWindow.get_wm_class() || '';
}

function windowPid(metaWindow) {
    const pid = metaWindow.get_pid();
    return pid > 0 ? pid : 0;
}

export default class SysbarWindowManagerExtension extends Extension {
    enable() {
        this._tracked = new Map();
        this._dbus = Gio.DBusExportedObject.wrapJSObject(IFACE, this);
        this._dbus.export(Gio.DBus.session, OBJECT_PATH);
        this._nameId = Gio.bus_own_name(
            Gio.BusType.SESSION,
            BUS_NAME,
            Gio.BusNameOwnerFlags.NONE,
            null,
            null,
            null
        );
        this._createdId = global.display.connect('window-created', (_display, metaWindow) =>
            this._onWindowCreated(metaWindow)
        );
        for (const actor of global.get_window_actors())
            this._track(actor.meta_window, false);
    }

    disable() {
        if (this._createdId) {
            global.display.disconnect(this._createdId);
            this._createdId = 0;
        }
        for (const [metaWindow, handlerId] of this._tracked) {
            try {
                metaWindow.disconnect(handlerId);
            } catch (_e) {
                // window already gone
            }
        }
        this._tracked.clear();
        if (this._nameId) {
            Gio.bus_unown_name(this._nameId);
            this._nameId = 0;
        }
        if (this._dbus) {
            this._dbus.unexport();
            this._dbus = null;
        }
    }

    ListWindows() {
        const windows = [];
        for (const metaWindow of this._tracked.keys())
            windows.push([windowId(metaWindow), windowClass(metaWindow), windowPid(metaWindow)]);
        return windows;
    }

    _onWindowCreated(metaWindow) {
        this._track(metaWindow, true);
    }

    _track(metaWindow, emit) {
        if (this._tracked.has(metaWindow))
            return;
        const handlerId = metaWindow.connect('unmanaged', () => this._onWindowClosed(metaWindow));
        this._tracked.set(metaWindow, handlerId);
        if (emit)
            this._emitOpened(metaWindow);
    }

    _emitOpened(metaWindow) {
        this._dbus.emit_signal(
            'WindowOpened',
            new GLib.Variant('(tsu)', [
                windowId(metaWindow),
                windowClass(metaWindow),
                windowPid(metaWindow),
            ])
        );
    }

    _onWindowClosed(metaWindow) {
        const handlerId = this._tracked.get(metaWindow);
        if (handlerId === undefined)
            return;
        this._tracked.delete(metaWindow);
        this._dbus.emit_signal('WindowClosed', new GLib.Variant('(t)', [windowId(metaWindow)]));
    }
}
