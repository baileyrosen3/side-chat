import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.Commons

AbstractButton {
    id: root
    property string onText: "On"
    property string offText: "Off"
    text: checked ? onText : offText
    checkable: true
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    padding: Style.space(5)
    implicitHeight: ui.controlHeight
    implicitWidth: content.implicitWidth + padding * 2
    opacity: enabled ? 1 : .45
    Accessible.role: Accessible.CheckBox
    Accessible.name: text
    ChatStyle { id: ui }
    HoverHandler { cursorShape: root.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor }
    contentItem: RowLayout {
        id: content
        spacing: Style.space(6)
        Rectangle {
            Layout.preferredWidth: Style.space(14)
            Layout.preferredHeight: Style.space(14)
            color: root.checked ? ui.accent : ui.field
            border.width: 1
            border.color: root.checked ? ui.accent : ui.border
            Icon { anchors.fill: parent; anchors.margins: Style.space(2); name: "check"; visible: root.checked; ink: ui.accentInk }
        }
        Text {
            text: root.text
            color: root.checked ? ui.foreground : ui.muted
            font.family: ui.family
            font.pixelSize: ui.small
        }
    }
    background: Rectangle {
        color: root.hovered ? ui.secondary : "transparent"
        border.width: root.activeFocus ? ui.stroke : 0
        border.color: ui.accent
    }
}
