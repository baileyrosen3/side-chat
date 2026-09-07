import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.Commons
import "Theme.js" as Theme

PanelWindow {
    id: root
    required property var chat
    property var pointer: chat.aiPointer
    readonly property bool inOutput: pointer.visible && pointer.x >= screen.x && pointer.y >= screen.y && pointer.x < screen.x + screen.width && pointer.y < screen.y + screen.height
    anchors { top: true; bottom: true; left: true; right: true }
    color: "transparent"
    visible: inOutput
    exclusionMode: ExclusionMode.Ignore
    WlrLayershell.namespace: "omarchy-jarvis-pointer"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
    mask: Region {}
    Rectangle {
        visible: !!root.pointer.bounds
        x: (root.pointer.bounds ? root.pointer.bounds.x : 0)-root.screen.x
        y: (root.pointer.bounds ? root.pointer.bounds.y : 0)-root.screen.y
        width: root.pointer.bounds ? root.pointer.bounds.width : 0
        height: root.pointer.bounds ? root.pointer.bounds.height : 0
        radius: Style.space(4); color: Theme.alpha(Color.accent,0.08)
        border.width: 1; border.color: Theme.alpha(Color.accent,0.65)
    }
    Item {
        id: marker
        x: (root.pointer.x || 0) - root.screen.x
        y: (root.pointer.y || 0) - root.screen.y
        Behavior on x { NumberAnimation { duration: root.chat.jarvis.reducedMotion ? 0 : 100; easing.type: Easing.OutCubic } }
        Behavior on y { NumberAnimation { duration: root.chat.jarvis.reducedMotion ? 0 : 100; easing.type: Easing.OutCubic } }
        Rectangle {
            id: ripple
            anchors.centerIn: parent
            width: Style.space(22); height: width; radius: width/2
            color: "transparent"; border.color: Color.accent; border.width: 1.5
            opacity: 0
        }
        Canvas {
            width: Style.space(17); height: Style.space(22)
            property color ink: Color.accent
            onInkChanged: requestPaint()
            onPaint: {
                var c=getContext("2d");c.reset();c.scale(width/17,height/22)
                c.beginPath();c.moveTo(0,0);c.lineTo(3,18);c.lineTo(7,12);c.lineTo(14,11);c.closePath()
                c.fillStyle=String(ink);c.fill();c.strokeStyle=String(Color.popups.background);c.lineWidth=1.5;c.stroke()
            }
        }
        Rectangle {
            x: Style.space(17); y: Style.space(13)
            width: label.implicitWidth + Style.space(10); height: label.implicitHeight + Style.space(5)
            radius: Style.space(4); color: Color.popups.background
            border.width: 1; border.color: Theme.alpha(Color.accent,0.4)
            Text { id: label; anchors.centerIn: parent; text: "AI"; color: Color.accent; font.family: Style.font.family; font.pixelSize: Style.font.body; font.weight: Font.DemiBold }
        }
    }
    Connections { target: chat; function onAiPointerChanged() { if (root.pointer.phase === "click") pulse.restart() } }
    ParallelAnimation {
        id: pulse
        NumberAnimation { target: ripple; property: "scale"; from: 0.6; to: 2.4; duration: 420; easing.type: Easing.OutCubic }
        NumberAnimation { target: ripple; property: "opacity"; from: 0.9; to: 0; duration: 420 }
    }
}
