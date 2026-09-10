import QtQuick
import QtQuick.Layouts
import qs.Commons
import "Theme.js" as Theme

ColumnLayout {
    id: root
    required property var chat
    ChatStyle { id: ui }
    readonly property bool outlineEnabled: !chat.meta.appearance || chat.meta.appearance.outline !== false
    spacing: Style.space(4)
    RowLayout {
        Layout.fillWidth: true
        Text {
            Layout.fillWidth: true
            text: "Window outline"
            color: ui.muted
            font.family: Style.font.family
            font.pixelSize: ui.small
            font.weight: Font.DemiBold
        }
        ChatSwitch {
            objectName: "outline-toggle"
            checked: root.outlineEnabled
            Accessible.name: "Window outline: " + text
            enabled: root.chat.connected
            onClicked: root.chat.request({action: "appearance", settings: {outline: !root.outlineEnabled}})
        }
        ActionButton {
            objectName: "reset-look"
            text: "Reset"
            subtle: true
            enabled: root.chat.connected
            onClicked: root.chat.request({action: "appearance", settings: {outline: true, expanded: false}})
        }
    }
}
