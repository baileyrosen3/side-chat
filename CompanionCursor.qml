// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Hyprland

// Hyprland waits synchronously for a connected client's request. Keep the
// entire transaction outside the GUI/render loop, including connect + send.
Scope {
    id: root
    property bool enabled: false
    property string socketPath: Hyprland.requestSocketPath
    property point position: Qt.point(0, 0)
    property bool valid: false

    function receive(data) {
        if (!enabled) return;
        var point;
        try { point = JSON.parse(data); } catch (error) { valid = false; return; }
        if (!point || point.valid !== true || typeof point.x !== "number"
                || typeof point.y !== "number" || !isFinite(point.x) || !isFinite(point.y)) {
            valid = false;
            return;
        }
        if (position.x !== point.x || position.y !== point.y)
            position = Qt.point(point.x, point.y);
        valid = true;
    }
    onEnabledChanged: {
        valid = false;
        if (!enabled) retry.stop();
    }
    Process {
        id: worker
        command: ["python3", "-B", "-u",
                  decodeURIComponent(Qt.resolvedUrl("companion_cursor.py").toString().replace("file://", "")),
                  root.socketPath]
        stdinEnabled: true
        running: root.enabled && !!root.socketPath && !retry.running
        stdout: SplitParser { onRead: data => root.receive(data) }
        onExited: {
            root.valid = false;
            if (root.enabled && root.socketPath) retry.restart();
        }
    }
    Timer { id: retry; interval: 2000 }
}
