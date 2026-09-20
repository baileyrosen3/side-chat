import QtQuick
import Quickshell
import qs.Commons

// Local preview host for the same native popup used by the installed widget.
PanelWindow {
    id: window
    default property alias widgets: row.data
    property alias api: barApi
    color: Color.popups.background
    implicitHeight: Style.space(32)
    anchors { left: true; right: true; bottom: true }
    QtObject {
        id: barApi
        property string position: "bottom"
        property bool vertical: false
        property int barSize: window.height
        property color foreground: Color.foreground
        property color barForeground: Color.foreground
        property color background: Color.popups.background
        property color urgent: Color.urgent
        property string fontFamily: Style.font.family
        property bool foregroundAnimationEnabled: false
        property var activePopout: null
        property var clickTargets: []
        function showTooltip(item, text) {}
        function hideTooltip(item) {}
        function registerClickTarget(item) { clickTargets = clickTargets.concat([item]) }
        function unregisterClickTarget(item) { clickTargets = clickTargets.filter(p => p !== item) }
        function requestPopout(item) {
            if (activePopout && activePopout !== item) activePopout.close()
            activePopout = item
        }
        function releasePopout(item) { if (activePopout === item) activePopout = null }
        function targetBelongsToWindow(item, target) { return item.QsWindow.window === target }
    }
    Row {
        id: row
        anchors.centerIn: parent
        height: parent.height
    }
}
