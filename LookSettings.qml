import QtQuick
import QtQuick.Layouts
import qs.Commons
import "Theme.js" as Theme

ColumnLayout {
    id: root
    required property var chat
    readonly property bool outlineEnabled: !chat.meta.appearance || chat.meta.appearance.outline !== false
    spacing: Style.space(8)

    Text {
        text: "Look & Feel"
        color: Color.popups.text
        font.family: Style.font.family
        font.pixelSize: Style.font.body
        font.weight: Font.DemiBold
    }
    RowLayout {
        Layout.fillWidth: true
        Text {
            Layout.fillWidth: true
            text: "Outline"
            color: Theme.alpha(Color.popups.text, 0.57)
            font.family: Style.font.family
            font.pixelSize: Style.font.body
        }
        ActionButton {
            objectName: "outline-toggle"
            text: root.outlineEnabled ? "On" : "Off"
            selected: root.outlineEnabled
            checkable: true
            checked: root.outlineEnabled
            hint: "Follow desktop window borders. Keyboard focus stays outlined."
            enabled: root.chat.connected
            onClicked: root.chat.request({action: "appearance", settings: {outline: !root.outlineEnabled}})
        }
        ActionButton {
            objectName: "reset-look"
            text: "Reset look"
            subtle: true
            enabled: root.chat.connected
            onClicked: root.chat.request({action: "appearance", settings: {outline: true}})
        }
    }
    Text {
        Layout.fillWidth: true
        text: "Uses your desktop border. Saves automatically."
        color: Theme.alpha(Color.popups.text, 0.57)
        font.family: Style.font.family
        font.pixelSize: Style.font.body
        wrapMode: Text.WordWrap
    }
}
