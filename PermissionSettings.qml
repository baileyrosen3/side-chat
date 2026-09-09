import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.Commons
import "Theme.js" as Theme

ColumnLayout {
    id: root

    required property var chat
    readonly property color foreground: ui.foreground
    readonly property string agent: chat.current ? chat.current.agent : chat.meta.agent
    readonly property var modes: (chat.meta.permissionModes || {
    })[agent] || []
    readonly property string selectedMode: chat.current ? (chat.current.permissionMode || "default") : "default"
    readonly property bool canChange: chat.connected && !chat.busy && !chat.terminalOpen && !chat.agentRequests.length

    signal revealRequested(var item)

    spacing: Style.space(8)

    ChatStyle {
        id: ui
    }

    ChatSection { text: root.chat.agentName + " access" }

    Text {
        Layout.fillWidth: true
        text: root.chat.terminalOpen ? "Return from the terminal to change modes." : root.chat.busy ? "Finish or stop the current reply to change modes." : "Applies to your next message and terminal handoff."
        color: ui.muted
        font.family: Style.font.family
        font.pixelSize: ui.small
        wrapMode: Text.WordWrap
    }

    Repeater {
        model: root.modes

        delegate: AbstractButton {
            id: option

            required property var modelData

            objectName: "permission-" + modelData.id
            Layout.fillWidth: true
            implicitHeight: description.implicitHeight + Style.space(20)
            opacity: enabled ? 1 : 0.6
            enabled: root.canChange
            hoverEnabled: true
            focusPolicy: Qt.StrongFocus
            Accessible.name: modelData.label + ". " + modelData.description
            Accessible.role: Accessible.RadioButton
            Accessible.checkable: true
            Accessible.checked: root.selectedMode === modelData.id
            onActiveFocusChanged: {
                if (activeFocus) {
                    root.revealRequested(option);
                }
            }
            onClicked: root.chat.request({
                "action": "permission_mode",
                "chatId": root.chat.current ? root.chat.current.id : null,
                "mode": modelData.id
            })
            padding: Style.space(10)
            HoverHandler { cursorShape: option.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor }

            contentItem: RowLayout {
                spacing: Style.space(8)

                Rectangle {
                    Layout.preferredWidth: Style.space(14)
                    Layout.preferredHeight: Style.space(14)
                    Layout.alignment: Qt.AlignTop
                    Layout.topMargin: Style.space(2)
                    radius: 0
                    color: root.selectedMode === option.modelData.id ? ui.accent : "transparent"
                    border.color: root.selectedMode === option.modelData.id ? ui.accent : ui.muted

                    Icon {
                        visible: root.selectedMode === option.modelData.id
                        anchors.centerIn: parent
                        width: Style.space(10)
                        height: width
                        name: "check"
                        ink: ui.accentInk
                    }

                }

                ColumnLayout {
                    id: description

                    Layout.fillWidth: true
                    spacing: Style.space(3)

                    Text {
                        Layout.fillWidth: true
                        text: option.modelData.label
                        color: ui.foreground
                        font.family: ui.family
                        font.pixelSize: ui.body
                        font.weight: Font.Bold
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        Layout.fillWidth: true
                        text: option.modelData.description
                        color: ui.muted
                        font.family: ui.family
                        font.pixelSize: ui.small
                        wrapMode: Text.WordWrap
                    }

                }

            }

            background: Rectangle {
                radius: ui.radius
                color: root.selectedMode === option.modelData.id || option.hovered ? ui.secondary : ui.field
                border.width: option.activeFocus || root.selectedMode === option.modelData.id ? ui.stroke : 1
                border.color: option.activeFocus || root.selectedMode === option.modelData.id ? ui.accent : ui.border
            }

        }

    }

    Text {
        visible: !root.modes.length
        Layout.fillWidth: true
        text: "This CLI does not expose permission modes in Side Chat yet."
        color: ui.muted
        font.family: Style.font.family
        font.pixelSize: ui.small
        wrapMode: Text.WordWrap
    }

    Text {
        Layout.fillWidth: true
        text: "New chats start with CLI defaults."
        color: ui.muted
        font.family: Style.font.family
        font.pixelSize: ui.small
        wrapMode: Text.WordWrap
    }

    Text {
        visible: !!root.chat.current && root.chat.current.bashApproval === "always"
        Layout.fillWidth: true
        text: "Bash is set to always allow. Changing modes clears that override."
        color: ui.emphasis
        font.family: Style.font.family
        font.pixelSize: ui.small
        wrapMode: Text.WordWrap
    }

    ActionButton {
        id: backButton

        text: "Back to chat"
        glyph: "back"
        onActiveFocusChanged: {
            if (activeFocus) {
                root.revealRequested(backButton);
            }
        }
        onClicked: root.chat.page = "chat"
    }

}
