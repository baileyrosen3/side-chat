import "Markdown.js" as Markdown
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "Theme.js" as Theme
import qs.Commons

Item {
    id: root

    required property var message
    required property int messageIndex
    required property var chat
    required property var host
    property bool highlighted: false
    readonly property bool user: message.role === "user"
    readonly property bool streaming: message.status === "streaming" && chat.busy
    readonly property string body: streaming ? chat.streamingText : message.text
    readonly property var blocks: Markdown.blocks(body)
    readonly property var toolList: streaming ? chat.streamingTools : (message.tools || [])

    implicitHeight: messageLayout.implicitHeight + host.px(12)

    ChatStyle {
        id: ui
    }

    Rectangle {
        anchors.fill: parent
        color: root.user ? ui.secondary : "transparent"
        border.width: root.user || root.highlighted ? 1 : 0
        border.color: root.highlighted ? ui.accent : ui.border
        radius: ui.radius

        Rectangle {
            visible: root.user
            width: root.host.px(2)
            height: parent.height
            color: ui.accent
        }

    }

    HoverHandler {
        id: messageHover
    }

    Column {
        id: messageLayout

        x: root.host.px(6)
        y: root.host.px(6)
        width: root.width - root.host.px(12)
        spacing: root.host.px(3)

        Text {
            visible: root.highlighted
            text: "Search match"
            color: ui.accent; font.family: ui.family; font.pixelSize: ui.caption
        }

        ActionButton {
            visible:!!(root.message.source && root.message.source.kind)
            width:parent.width;glyph:"attach";subtle:true
            text:"From " + ((root.message.source || {}).label || "selection")
            enabled:!!(root.message.source && root.message.source.id)
            hint:"Open source";onClicked:chat.openSource(root.message.source)
        }

        RowLayout {
            width: parent.width

            Rectangle {
                implicitWidth: sender.implicitWidth + (root.user ? 0 : root.host.px(12))
                implicitHeight: sender.implicitHeight + root.host.px(4)
                color: "transparent"

                Rectangle {
                    visible: !root.user
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    width: root.host.px(4); height: width
                    color: ui.accent
                }

                Text {
                    id: sender

                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.user ? "You" : chat.agentName
                    color: root.user ? ui.muted : ui.accent
                    font.family: host.family
                    font.pixelSize: ui.caption
                    font.weight: Font.Bold
                    font.letterSpacing: 0
                }

            }

            Item {
                Layout.fillWidth: true
            }

            Text {
                opacity: messageHover.hovered ? 1 : 0
                text: (message.model ? message.model + " · " : "") + Qt.formatDateTime(new Date(message.time * 1000), "h:mm ap")
                Layout.maximumWidth: parent.width * 0.55
                elide: Text.ElideLeft
                color: host.dim
                font.family: host.family
                font.pixelSize: ui.small

                Behavior on opacity {
                    NumberAnimation {
                        duration: chat.peek.reducedMotion ? 0 : 130
                    }

                }

            }

            RowLayout {
                id: actions

                visible: !root.streaming
                opacity: messageHover.hovered || copyButton.activeFocus || thoughtButton.activeFocus || editButton.activeFocus || retryButton.activeFocus || !!message.error ? 1 : 0.65
                spacing: host.px(2)

                ActionButton {
                    id: copyButton

                    glyph: host.copied === String(root.messageIndex) ? "check" : "copy"
                    hint: host.copied === String(root.messageIndex) ? "Copied" : "Copy reply"
                    subtle: true
                    implicitHeight: ui.controlHeight
                    implicitWidth: ui.controlHeight
                    onClicked: host.copyText(root.body, String(root.messageIndex))
                }

                ActionButton {
                    id: thoughtButton
                    glyph: "thought"
                    hint: "Save as a thought"
                    subtle: true
                    implicitHeight: ui.controlHeight
                    implicitWidth: ui.controlHeight
                    enabled: !!root.body.trim()
                    onClicked: chat.saveThought(root.body)
                }

                ActionButton {
                    id: editButton

                    visible: root.user
                    glyph: "edit"
                    hint: chat.nativeSession ? "Edit and branch session · file changes remain" : "Edit message"
                    subtle: true
                    implicitHeight: ui.controlHeight
                    implicitWidth: ui.controlHeight
                    enabled: !chat.busy && !chat.terminalOpen
                    onClicked: chat.edit(root.messageIndex)
                }

                ActionButton {
                    id: retryButton

                    visible: !root.user && root.messageIndex === chat.messages.length - 1
                    glyph: "retry"
                    hint: chat.nativeSession ? "Retry from this prompt · may repeat actions" : "Regenerate reply"
                    subtle: true
                    implicitHeight: ui.controlHeight
                    implicitWidth: ui.controlHeight
                    enabled: !chat.busy && !chat.terminalOpen
                    onClicked: chat.retry()
                }

                Behavior on opacity {
                    NumberAnimation {
                        duration: chat.peek.reducedMotion ? 0 : 130
                    }

                }

            }

        }

        Column {
            width: parent.width
            spacing: host.px(6)

            Repeater {
                model: root.message.steering || []

                Text {
                    required property var modelData

                    width: parent.width
                    text: "You redirected · " + modelData.text
                    color: ui.emphasis
                    font.family: host.family
                    font.pixelSize: ui.small
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
                font.pixelSize: ui.small
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
                    readonly property int inset: modelData.code ? host.px(8) : 0
                    readonly property string copyKey: root.messageIndex + ":" + index

                    width: parent.width
                    height: blockColumn.implicitHeight + inset * 2
                    radius: 0
                    color: modelData.code ? ui.field : "transparent"
                    border.width: modelData.code ? 1 : 0
                    border.color: ui.border

                    Column {
                        id: blockColumn

                        x: block.inset
                        y: block.inset
                        width: parent.width - block.inset * 2
                        spacing: block.modelData.code ? host.px(4) : 0

                        RowLayout {
                            visible: block.modelData.code
                            width: parent.width

                            Text {
                                Layout.fillWidth: true
                                text: block.modelData.language || "code"
                                color: host.dim
                                font.family: host.family
                                font.pixelSize: ui.small
                            }

                            ActionButton {
                                glyph: host.copied === block.copyKey ? "check" : "copy"
                                hint: host.copied === block.copyKey ? "Copied" : "Copy code"
                                subtle: true
                                implicitHeight: ui.controlHeight
                                onClicked: host.copyText(block.modelData.text, block.copyKey)
                            }

                        }

                        Rectangle {
                            visible: block.modelData.code
                            width: parent.width
                            height: 1
                            color: Theme.alpha(host.fg, 0.07)
                        }

                        Flickable {
                            id: textViewport
                            width: parent.width
                            height: replyText.implicitHeight + (contentWidth > width ? host.px(8) : 0)
                            contentWidth: replyText.width
                            contentHeight: replyText.implicitHeight
                            clip: true
                            boundsBehavior: Flickable.StopAtBounds
                            flickableDirection: Flickable.HorizontalFlick
                            ScrollBar.horizontal: ChatScrollBar { policy: ScrollBar.AsNeeded }
                        TextEdit {
                            id: replyText
                            objectName: "message-text-" + root.messageIndex + "-" + block.index
                            width: block.modelData.code ? Math.max(textViewport.width, implicitWidth) : textViewport.width
                            text: block.modelData.text
                            textFormat: block.modelData.code || root.user ? TextEdit.PlainText : TextEdit.MarkdownText
                            readOnly: true
                            selectByMouse: true
                            wrapMode: block.modelData.code ? TextEdit.NoWrap : TextEdit.Wrap
                            color: host.fg
                            selectionColor: Theme.alpha(ui.emphasis, 0.35)
                            selectedTextColor: host.fg
                            font.family: host.family
                            font.pixelSize: host.textSize
                            Accessible.name: root.user ? "Your message" : "Assistant reply"
                            onLinkActivated: (url) => {
                                if (/^https?:\/\//i.test(url))
                                    Qt.openUrlExternally(url);
                                else
                                    chat.request({action:"open_link",url:String(url)});

                            }
                            onActiveFocusChanged: {
                                if (activeFocus)
                                    chat.pin();

                            }
                            Keys.onEscapePressed: host.pressEscape()
                        }
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
                        color: ui.emphasis
                        font.family: host.family
                        font.pixelSize: ui.small
                    }

                }

            }

            Text {
                visible: message.status === "stopped"
                text: "Reply stopped"
                color: host.dim
                font.family: host.family
                font.pixelSize: ui.small
            }

            Text {
                visible: !!message.error
                width: parent.width
                text: message.error || ""
                color: ui.danger
                font.family: host.family
                font.pixelSize: ui.small
                wrapMode: Text.WrapAnywhere
            }

        }

    }

}
