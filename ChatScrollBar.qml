import QtQuick
import QtQuick.Controls
import qs.Commons

ScrollBar {
    id: root
    ChatStyle { id: ui }
    implicitWidth: Style.space(4)
    implicitHeight: Style.space(4)
    padding: 0
    minimumSize: .08
    policy: ScrollBar.AsNeeded
    contentItem: Rectangle {
        implicitWidth: Style.space(3)
        implicitHeight: Style.space(3)
        color: root.pressed || root.hovered ? ui.accent : ui.border
        opacity: root.size < 1 ? 1 : 0
    }
    background: Rectangle {
        color: ui.line
        opacity: root.size < 1 ? .35 : 0
    }
}
