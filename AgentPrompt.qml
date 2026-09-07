import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.Commons
import "Theme.js" as Theme

Rectangle {
    id: root
    required property var request
    required property var chat
    required property var host
    implicitHeight: Math.min(host.px(210), promptColumn.implicitHeight + host.px(18))
    radius: host.px(7)
    color: Theme.alpha(Color.accent, 0.07)
    border.width: 1; border.color: Theme.alpha(Color.accent, 0.25)
    function answer(values) {
        values.action = "agent_ui_response"; values.id = request.id
        values.chatId = chat.current ? chat.current.id : ""
        chat.request(values)
    }
    Flickable {
        anchors.fill: parent; anchors.margins: root.host.px(9)
        contentWidth: width; contentHeight: promptColumn.implicitHeight
        clip: true; boundsBehavior: Flickable.StopAtBounds
        ColumnLayout {
            id: promptColumn
            width: parent.width; spacing: root.host.px(7)
            Text { Layout.fillWidth: true; text: root.request.title || "Agent needs your input"; wrapMode: Text.WordWrap; color: root.host.fg; font.family: root.host.family; font.pixelSize: root.host.textSize; font.weight: Font.DemiBold }
            TextEdit {
                Layout.fillWidth: true; visible: !!root.request.message
                text: root.request.message || ""; readOnly: true; selectByMouse: true; wrapMode: TextEdit.WrapAnywhere
                color: root.host.fg; font.family: root.host.family; font.pixelSize: root.host.textSize
            }
            Repeater {
                model: root.request.method === "select" ? root.request.options : []
                ActionButton {
                    required property string modelData
                    Layout.fillWidth: true
                    text: modelData; onClicked: root.answer({value: modelData})
                }
            }
            TextField {
                id: answerField
                visible: root.request.method === "input" || root.request.method === "editor"
                Layout.fillWidth: true
                text: root.request.prefill || ""; placeholderText: root.request.placeholder || "Your answer…"
                color: root.host.fg; placeholderTextColor: root.host.dim; font.family: root.host.family; font.pixelSize: root.host.textSize
                onAccepted: root.answer({value: text})
                background: Rectangle { radius: root.host.px(5); color: Theme.alpha(root.host.fg, 0.05); border.color: parent.activeFocus ? Color.accent : root.host.line }
            }
            RowLayout {
                ActionButton { objectName: "allow-once"; visible: root.request.method === "confirm"; text: "Allow"; accent: true; onClicked: root.answer({confirmed: true}) }
                ActionButton {
                    objectName: "allow-bash-always"
                    visible: root.request.method === "confirm" && root.request.allowAlwaysBash === true
                    text: "Always allow Bash"
                    hint: "Allow all Bash commands in this conversation. Change this in Preferences."
                    onClicked: root.answer({confirmed: true, alwaysAllowBash: true})
                }
                ActionButton { visible: answerField.visible; text: "Send"; accent: true; onClicked: root.answer({value: answerField.text}) }
                ActionButton { objectName: "deny-action"; text: root.request.method === "confirm" ? "Deny" : "Cancel"; subtle: true; onClicked: root.answer({cancelled: true}) }
                Item { Layout.fillWidth: true }
            }
            Text {
                Layout.fillWidth: true
                visible: root.request.allowAlwaysBash === true
                text: "Always allow applies to Bash in this conversation."
                color: root.host.dim; font.family: root.host.family; font.pixelSize: root.host.textSize
                wrapMode: Text.WordWrap
            }
        }
    }
}
