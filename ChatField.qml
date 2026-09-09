import QtQuick
import QtQuick.Controls
import qs.Commons
import "Theme.js" as Theme

TextField {
    id: root
    property string glyph: ""

    implicitHeight: ui.controlHeight
    leftPadding: Style.space(glyph ? 28 : 8)
    rightPadding: Style.space(8)
    topPadding: Style.space(4)
    bottomPadding: Style.space(4)
    color: ui.foreground
    placeholderTextColor: ui.muted
    selectionColor: Theme.alpha(ui.accent, 0.35)
    selectedTextColor: ui.foreground
    font.family: ui.family
    font.pixelSize: ui.small
    selectByMouse: true
    opacity: enabled ? 1 : 0.45

    ChatStyle {
        id: ui
    }

    Icon {
        visible: root.glyph !== ""
        name: root.glyph
        ink: ui.muted
        x: Style.space(8)
        anchors.verticalCenter: parent.verticalCenter
        width: Style.space(12); height: width
    }

    background: Rectangle {
        radius: ui.radius
        color: root.activeFocus ? ui.secondary : ui.field
        border.width: root.activeFocus ? ui.stroke : 1
        border.color: root.activeFocus ? ui.accent : ui.border
    }

}
