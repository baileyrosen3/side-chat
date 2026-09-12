# SPDX-License-Identifier: GPL-3.0-or-later
"""Keep desktop notification actions usable across a plugin restart."""
import subprocess
import sys
from gi.repository import Gio, GLib


def main():
    identity, due, body = sys.argv[1:4]
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        loop = GLib.MainLoop()
        notification = [0]

        def event(connection, sender, path, interface, signal, parameters, data):
            values = parameters.unpack()
            if values[0] != notification[0]:
                return
            if signal == 'ActionInvoked' and values[1] in ('open', 'snooze', 'done'):
                try:
                    subprocess.run(['omarchy-shell', 'blr.side-chat', 'reminderAction', identity, values[1], due], timeout=10)
                finally:
                    loop.quit()
            elif signal == 'NotificationClosed':
                loop.quit()

        bus.signal_subscribe('org.freedesktop.Notifications', 'org.freedesktop.Notifications', None,
                             '/org/freedesktop/Notifications', None, Gio.DBusSignalFlags.NONE, event, None)
        result = bus.call_sync('org.freedesktop.Notifications', '/org/freedesktop/Notifications',
                               'org.freedesktop.Notifications', 'Notify',
                               GLib.Variant('(susssasa{sv}i)', ('Side Chat', 0, 'appointment-soon', 'Task due',
                                   GLib.markup_escape_text(body[:500]),
                                   ['open', 'Open task', 'snooze', 'Snooze 10 min', 'done', 'Done'], {}, 0)),
                               GLib.VariantType.new('(u)'), Gio.DBusCallFlags.NONE, 2000, None)
        notification[0] = result.unpack()[0]
        print('ready', flush=True)
        sys.stdout.close()
        GLib.timeout_add_seconds(86400, lambda: (loop.quit(), False)[1])
        loop.run()
    except (OSError, subprocess.SubprocessError, GLib.Error):
        pass


if __name__ == '__main__':
    main()
