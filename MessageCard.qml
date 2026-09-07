import "Markdown.js" as Markdown
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "Theme.js" as Theme
import qs.Commons

Column {
    id: root

    required property var message
    required property int messageIndex
    required property var chat
    required property var host
    readonly property bool user: message.role === "user"
    readonly property bool streaming: message.status === "streaming" && chat.busy
    readonly property string body: streaming ? chat.streamingText : message.text
    readonly property var blocks: Markdown.blocks(body)
    readonly property var toolList: streaming ? chat.streamingTools : (message.tools || [])

    spacing: host.px(6)

    HoverHandler {
        id: messageHover
    }

    RowLayout {
        width: parent.width

        Text {
            Layout.fillWidth: true
            text: root.user ? "You" : chat.agentName
            color: root.user ? host.dim : Color.accent
            font.family: host.family
            font.pixelSize: host.textSize
            font.weight: Font.DemiBold
        }

        Text {
            opacity: messageHover.hovered ? 1 : 0
            text: Qt.formatDateTime(new Date(message.time * 1000), "h:mm ap")
            color: host.dim
            font.family: host.family
            font.pixelSize: host.textSize

            Behavior on opacity {
                NumberAnimation {
                    duration: 130
                }

            }

        }

        RowLayout {
            id: actions

            visible: !root.streaming
            opacity: messageHover.hovered || copyButton.activeFocus || editButton.activeFocus || retryButton.activeFocus || !!message.error ? 1 : 0
            spacing: host.px(2)

            ActionButton {
                id: copyButton

                glyph: host.copied === String(root.messageIndex) ? "check" : "copy"
                hint: host.copied === String(root.messageIndex) ? "Copied" : "Copy reply"
                subtle: true
                implicitHeight: host.px(18)
                implicitWidth: host.px(20)
                onClicked: host.copyText(root.body, String(root.messageIndex))
            }

            ActionButton {
                id: editButton

                visible: root.user
                glyph: "edit"
                hint: chat.nativeSession ? "Edit and branch session · file changes remain" : "Edit message"
                subtle: true
                implicitHeight: host.px(18)
                implicitWidth: host.px(20)
                enabled: !chat.busy && !chat.terminalOpen
                onClicked: chat.edit(root.messageIndex)
            }

            ActionButton {
                id: retryButton

                visible: !root.user && root.messageIndex === chat.messages.length - 1
                glyph: "retry"
                hint: chat.nativeSession ? "Retry from this prompt · may repeat actions" : "Regenerate reply"
                subtle: true
                implicitHeight: host.px(18)
                implicitWidth: host.px(20)
                enabled: !chat.busy && !chat.terminalOpen
                onClicked: chat.retry()
            }

            Behavior on opacity {
                NumberAnimation {
                    duration: 130
                }

            }

        }

    }

    Column {
        width: parent.width
        spacing: host.px(8)

        Repeater {
            model: root.message.steering || []

            Text {
                required property var modelData

                width: parent.width
                text: "You redirected · " + modelData.text
                color: Color.accent
                font.family: host.family
                font.pixelSize: host.textSize
                wrapMode: Text.Wrap
            }

        }

        ToolActivity {
            visible: root.toolList.length > 0
            tools: root.toolList
            host: root.host
        }

        Text {
            visible: root.streaming && !root.body
            text: chat.activity
            color: host.dim
            font.family: host.family
            font.pixelSize: host.textSize
        }

        Repeater {
            model: root.user ? [{
                "code": false,
                "language": "",
                "text": root.body
            }] : root.blocks

            Rectangle {
                id: block

                required property var modelData
                required property int index
                readonly property int inset: modelData.code ? host.px(10) : 0
                readonly property string copyKey: root.messageIndex + ":" + index

                width: root.width
                height: blockColumn.implicitHeight + inset * 2
                radius: host.px(3)
                color: modelData.code ? Theme.alpha(host.fg, 0.035) : "transparent"
                border.width: modelData.code ? 1 : 0
                border.color: Theme.alpha(host.fg, 0.055)

                Column {
                    id: blockColumn

                    x: block.inset
                    y: block.inset
                    width: parent.width - block.inset * 2
                    spacing: block.modelData.code ? host.px(7) : 0

                    RowLayout {
                        visible: block.modelData.code
                        width: parent.width

                        Text {
                            Layout.fillWidth: true
                            text: block.modelData.language || "code"
                            color: host.dim
                            font.family: host.family
                            font.pixelSize: host.textSize
                        }

                        ActionButton {
                            glyph: host.copied === block.copyKey ? "check" : "copy"
                            hint: host.copied === block.copyKey ? "Copied" : "Copy code"
                            subtle: true
                            implicitHeight: host.px(20)
                            onClicked: host.copyText(block.modelData.text, block.copyKey)
                        }

                    }

                    Rectangle {
                        visible: block.modelData.code
                        width: parent.width
                        height: 1
                        color: Theme.alpha(host.fg, 0.07)
                    }

                    TextEdit {
                        width: parent.width
                        text: block.modelData.text
                        textFormat: block.modelData.code || root.user ? TextEdit.PlainText : TextEdit.MarkdownText
                        readOnly: true
                        selectByMouse: true
                        wrapMode: TextEdit.Wrap
                        color: host.fg
                        selectionColor: Theme.alpha(Color.accent, 0.35)
                        selectedTextColor: host.fg
                        font.family: host.family
                        font.pixelSize: host.textSize
                        Accessible.name: root.user ? "Your message" : "Assistant reply"
                        onLinkActivated: (url) => {
                            if (/^https?:\/\//i.test(url))
                                Qt.openUrlExternally(url);

                        }
                        onActiveFocusChanged: {
                            if (activeFocus) {
                                chat.pin();
                            }
                        }
                        Keys.onEscapePressed: chat.close()
                    }

                }

            }

        }

        Repeater {
            model: root.message.attachments || []

            Column {
                required property var modelData

                width: parent.width
                spacing: host.px(5)

                Image {
                    visible: modelData.image
                    width: Math.min(parent.width, host.px(200))
                    height: visible ? host.px(110) : 0
                    source: modelData.image ? "file://" + modelData.path : ""
                    fillMode: Image.PreserveAspectFit
                    horizontalAlignment: Image.AlignLeft
                    asynchronous: true
                }

                Text {
                    width: parent.width
                    text: modelData.name
                    elide: Text.ElideMiddle
                    color: Color.accent
                    font.family: host.family
                    font.pixelSize: host.textSize
                }

            }

        }

        Text {
            visible: message.status === "stopped"
            text: "Reply stopped"
            color: host.dim
            font.family: host.family
            font.pixelSize: host.textSize
        }

        Text {
            visible: !!message.error
            width: parent.width
            text: message.error || ""
            color: Color.urgent
            font.family: host.family
            font.pixelSize: host.textSize
            wrapMode: Text.WrapAnywhere
        }

    }

    Text {
        opacity: messageHover.hovered ? 1 : 0
        visible: !root.user && !!message.model
        width: parent.width
        text: (message.model || "") + (message.elapsed ? " · " + message.elapsed + "s" : "")
        elide: Text.ElideLeft
        color: host.dim
        font.family: host.family
        font.pixelSize: host.textSize
    }

}
