import QtQuick
import QtQuick.Layouts
import qs.Commons
import "Theme.js" as Theme

ColumnLayout {
    id: root
    required property var chat
    readonly property color foreground: Color.popups.text
    readonly property bool supported: !!chat.current && ["claude", "codex"].indexOf(chat.current.agent) >= 0
    readonly property bool always: supported && chat.current.bashApproval === "always"
    visible: supported
    spacing: Style.space(7)

    function setMode(mode) {
        chat.request({action: "bash_approval", chatId: chat.current.id, mode: mode})
    }

    Text {
        text: "Bash approvals"
        color: root.foreground
        font.family: Style.font.family
        font.pixelSize: Style.font.body
        font.weight: Font.DemiBold
    }
    RowLayout {
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
        Item { Layout.fillWidth: true }
    }
    Text {
        Layout.fillWidth: true
        text: "Saves for this conversation in Side Chat. Bash commands can modify files and run programs."
        color: Theme.alpha(root.foreground, 0.57)
        font.family: Style.font.family
        font.pixelSize: Style.font.body
        wrapMode: Text.WordWrap
    }
}
