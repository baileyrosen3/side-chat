import QtQuick
import QtQuick.Layouts
import qs.Commons
import "Theme.js" as Theme

ColumnLayout {
    id: root
    required property var chat
    ChatStyle { id: ui }
    readonly property color foreground: ui.foreground
    readonly property bool supported: !!chat.current && ["claude", "codex"].indexOf(chat.current.agent) >= 0
    readonly property bool always: supported && chat.current.bashApproval === "always"
    visible: supported
    spacing: Style.space(4)

    function setMode(mode) {
        chat.request({action: "bash_approval", chatId: chat.current.id, mode: mode})
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Style.space(3)
        Text {
            Layout.fillWidth: true
            text: "Bash approvals"
            color: ui.muted
            font.family: ui.family
            font.pixelSize: ui.small
            font.weight: Font.DemiBold
        }
        ActionButton {
            objectName: "bash-ask"
            text: "Ask"
            selected: !root.always
            enabled: root.chat.connected && !root.chat.terminalOpen
            hint: "Ask when the agent requests command approval."
            onClicked: root.setMode("ask")
        }
        ActionButton {
            objectName: "bash-always"
            text: "Always allow"
            selected: root.always
            enabled: root.chat.connected && !root.chat.terminalOpen
            hint: "Allow all Bash commands for this conversation in Side Chat."
            onClicked: root.setMode("always")
        }
    }
    Text {
        Layout.fillWidth: true
        text: "This chat only. Bash can change files and run programs."
        color: ui.muted
        font.family: Style.font.family
        font.pixelSize: ui.small
        wrapMode: Text.WordWrap
    }
}
