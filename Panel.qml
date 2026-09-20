import QtQuick
import Quickshell
import qs.Commons
import qs.Ui as Ui
import "ChatBridge.js" as Bridge

Ui.Panel {
    id: root
    moduleName: "blr.side-chat"
    ipcTarget: "blr.side-chat"
    manageIpc: false // Main owns the existing IPC routes and the single backend.
    property var chat: null
    readonly property var hostWindow: root.QsWindow.window
    readonly property string screenName: hostWindow && hostWindow.screen ? hostWindow.screen.name : ""
    readonly property bool available: !!hostWindow && hostWindow.visible && !!screenName
    implicitWidth: button.implicitWidth
    implicitHeight: button.implicitHeight

    Component.onCompleted: Bridge.add(root)
    Component.onDestruction: {
        if (chat && opened) chat.panelClosed(root)
        Bridge.remove(root)
    }
    onOpenedChanged: {
        if (!chat) return
        if (opened) chat.panelOpened(root)
        else chat.panelClosed(root)
    }
    onChatChanged: if (chat && opened) chat.panelOpened(root)

    Ui.BarIconButton {
        id: button
        objectName: "side-chat-button"
        anchors.fill: parent
        bar: root.bar
        text: "󰭹"
        tooltipText: !root.chat || !root.chat.connected ? "Side Chat · Connecting…"
            : root.chat.busy ? "Side Chat · " + root.chat.activity
            : root.chat.notice ? "Side Chat · " + root.chat.notice : "Side Chat"
        onPressed: function(buttonCode) {
            if (buttonCode === Qt.LeftButton && root.chat) root.toggle()
        }
        Rectangle {
            visible: !!root.chat && (root.chat.busy || !!root.chat.notice || root.chat.agentRequests.length > 0)
            width: Style.space(5)
            height: width
            radius: width / 2
            color: root.chat && root.chat.agentRequests.length ? Color.urgent : Color.accent
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: Style.space(3)
        }
    }

    Ui.KeyboardPanel {
        id: popup
        anchorItem: button
        owner: root
        bar: root.bar
        open: root.opened && !!root.chat
        focusTarget: content.item
        contentWidth: fittedContentWidth(content.item ? content.item.implicitWidth : Style.space(460))
        contentHeight: fittedContentHeight(content.item ? content.item.implicitHeight : Style.space(320))

        Loader {
            id: content
            // Keep the editor alive on close; drafts and background work belong
            // to Main and also survive a bar instance being recreated.
            active: !!root.chat
            anchors.fill: parent
            sourceComponent: ChatWindow {
                chat: root.chat
                opened: root.opened
            }
        }
    }
}
