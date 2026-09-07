import QtQuick
import Quickshell
import Quickshell.Hyprland
import Quickshell.Io
import qs.Commons
import "WindowBorder.js" as Parser

Scope {
    id: root
    property bool active: false
    property var windowGradient: null
    property real windowWidth: -1
    readonly property var themeBorder: Border.hyprlandActiveSpec(Color.popups.border, Style.normalBorderWidth)
    readonly property var colors: windowGradient ? windowGradient.colors
        : themeBorder.gradient.enabled ? themeBorder.gradient.colors : [Border.color(themeBorder)]
    readonly property real angle: windowGradient ? windowGradient.angle : themeBorder.gradient.angle
    readonly property real borderWidth: windowWidth >= 0 ? windowWidth
        : Math.max(Border.top(themeBorder), Border.right(themeBorder), Border.bottom(themeBorder), Border.left(themeBorder))

    function refresh() {
        if (!active) return
        if (colorProcess.running) colorProcess.pending = true
        else colorProcess.running = true
        if (widthProcess.running) widthProcess.pending = true
        else widthProcess.running = true
    }
    onActiveChanged: if (active) refresh()
    Connections {
        target: Hyprland
        function onRawEvent(event) {
            if (event.name === "configreloaded") root.refresh()
        }
    }
    Process {
        id: colorProcess
        property bool pending: false
        command: ["hyprctl", "-j", "getoption", "general:col.active_border"]
        stdout: StdioCollector { id: colorOutput; waitForEnd: true }
        onExited: exitCode => {
            try { root.windowGradient = exitCode === 0 ? Parser.parseGradient(JSON.parse(colorOutput.text).gradient) : null }
            catch (error) { root.windowGradient = null }
            if (pending) { pending = false; if (root.active) running = true }
        }
    }
    Process {
        id: widthProcess
        property bool pending: false
        command: ["hyprctl", "-j", "getoption", "general:border_size"]
        stdout: StdioCollector { id: widthOutput; waitForEnd: true }
        onExited: exitCode => {
            try { root.windowWidth = exitCode === 0 ? Parser.parseWidth(JSON.parse(widthOutput.text).int) : -1 }
            catch (error) { root.windowWidth = -1 }
            if (pending) { pending = false; if (root.active) running = true }
        }
    }
}
