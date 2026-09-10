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
    property bool expanded: false
    readonly property real collapsedHeight: host.px(120)
    readonly property bool overflows: promptColumn.implicitHeight > collapsedHeight + 1

    function answer(values) {
        values.action = "agent_ui_response";
        values.id = request.id;
        values.chatId = chat.current ? chat.current.id : "";
        chat.request(values);
    }

    implicitHeight: layout.implicitHeight + host.px(16)
    radius: ui.radius
    color: ui.secondary
    border.width: ui.stroke
    border.color: ui.accent

    ChatStyle {
        id: ui
    }

    ColumnLayout {
        id: layout

        anchors.fill: parent
        anchors.margins: root.host.px(8)
        spacing: root.host.px(6)

        ChatSection { text: "Your approval"; Layout.topMargin: 0; Layout.bottomMargin: 0 }

        Text {
            Layout.fillWidth: true
            text: root.request.title || "Agent needs your input"
            wrapMode: Text.WordWrap
            color: ui.foreground
            font.family: ui.family
            font.pixelSize: ui.body
            font.weight: Font.Bold
        }

        Flickable {
            id: promptView

            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(root.expanded ? root.host.px(420) : root.collapsedHeight, promptColumn.implicitHeight)
            contentWidth: width
            contentHeight: promptColumn.implicitHeight
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            ColumnLayout {
                id: promptColumn

                width: parent.width
                spacing: root.host.px(4)

                TextEdit {
                    Layout.fillWidth: true
                    visible: !!root.request.message
                    text: root.request.message || ""
                    readOnly: true
                    selectByMouse: true
                    wrapMode: TextEdit.WrapAtWordBoundaryOrAnywhere
                    color: ui.foreground
                    font.family: ui.family
                    font.pixelSize: ui.small
                }

                Repeater {
                    model: root.request.method === "select" ? root.request.options : []

                    ActionButton {
                        required property string modelData

                        Layout.fillWidth: true
                        text: modelData
                        hint: modelData
                        onClicked: root.answer({
                            "value": modelData
                        })
                    }

                }

            }

            ScrollBar.vertical: ChatScrollBar {
                width: root.host.px(4)
            }

        }

        ActionButton {
            objectName: "prompt-expand"
            // Never ask for approval of a command the user cannot read in full.
            visible: root.overflows || root.expanded
            subtle: true
            glyph: root.expanded ? "chevron-up" : "chevron-down"
            text: root.expanded ? "Show less" : "Show the full request"
            textAlignment: Text.AlignLeft
            Layout.fillWidth: true
            implicitHeight: root.host.px(22)
            onClicked: {
                root.expanded = !root.expanded;
                if (!root.expanded)
                    promptView.contentY = 0;

            }
        }

        ChatField {
            id: answerField

            visible: root.request.method === "input" || root.request.method === "editor"
            Layout.fillWidth: true
            text: root.request.prefill || ""
            placeholderText: root.request.placeholder || "Your answer…"
            Accessible.name: root.request.title || "Your answer"
            onAccepted: root.answer({
                "value": text
            })
        }

        Flow {
            Layout.fillWidth: true
            spacing: root.host.px(4)

            ActionButton {
                objectName: "allow-once"
                visible: root.request.method === "confirm"
                text: "Allow"
                accent: true
                onClicked: root.answer({
                    "confirmed": true
                })
            }

            ActionButton {
                objectName: "allow-bash-always"
                visible: root.request.method === "confirm" && root.request.allowAlwaysBash === true
                text: "Always allow Bash"
                hint: "Allow all Bash commands in this conversation. Change this in Preferences."
                onClicked: root.answer({
                    "confirmed": true,
                    "alwaysAllowBash": true
                })
            }

            ActionButton {
                visible: answerField.visible
                text: "Send"
                accent: true
                onClicked: root.answer({
                    "value": answerField.text
                })
            }

            ActionButton {
                objectName: "deny-action"
                text: root.request.method === "confirm" ? "Deny" : "Cancel"
                subtle: true
                onClicked: root.answer({
                    "cancelled": true
                })
            }

        }

    }

}
