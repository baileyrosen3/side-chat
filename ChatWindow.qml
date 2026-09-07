import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import Quickshell
import Quickshell.Hyprland
import Quickshell.Wayland
import "Theme.js" as Theme
import qs.Commons

PanelWindow {
    id: window

    required property var chat
    readonly property bool opened: chat.openScreen === screen.name
    readonly property bool pointerInside: edgeMouse.containsMouse || drawerHover.hovered
    readonly property color surface: Color.popups.background
    readonly property color fg: Color.popups.text
    readonly property color dim: Theme.alpha(fg, 0.57)
    readonly property color line: Theme.alpha(fg, 0.1)
    readonly property string family: Style.font.family
    readonly property int textSize: Style.font.body
    property real reveal: opened ? 1 : 0
    property bool expanded: false
    property string historySearch: ""
    property string deletingId: ""
    property string copied: ""
    property bool followBottom: true
    property string displayedChatId: ""

    WindowBorder { id: windowBorder; active: window.opened }

    function px(value) {
        return Style.space(value);
    }

    function copyText(text, key) {
        clipboard.text = text;
        clipboard.selectAll();
        clipboard.copy();
        clipboard.deselect();
        copied = key;
        copiedReset.restart();
    }

    function bottom() {
        if (followBottom)
            Qt.callLater(() => {
            return thread.contentY = Math.max(0, thread.contentHeight - thread.height);
        });

    }

    function showSettings() {
        modelField.text = chat.meta.settings.model || "";
        cwdField.text = chat.meta.settings.cwd || "";
        thinking.currentIndex = Math.max(0, ["default", "low", "medium", "high"].indexOf(chat.meta.settings.thinking));
        chat.page = "settings";
        chat.pin();
    }

    onPointerInsideChanged: chat.hover(screen.name, pointerInside)
    color: "transparent"
    margins.bottom: 0
    implicitWidth: Math.min(px(expanded ? 620 : 388), screen.width - px(12))
    implicitHeight: Math.min(screen.height - px(48), px(expanded ? 650 : ["settings", "jarvis_settings"].indexOf(chat.page) >= 0 ? 540 : chat.page === "history" ? 440 : chat.messages.length ? 480 : 350) + (chat.agentRequests.length ? px(135) : 0))
    onWidthChanged: {
        if (opened) {
            chat.panelWidth = width;
        }
    }
    exclusionMode: ExclusionMode.Ignore
    WlrLayershell.namespace: "omarchy-side-chat"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: opened && chat.pinned ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None
    onOpenedChanged: {
        if (opened) {
            chat.panelWidth = width;
            chat.notice = "";
            if (chat.pinned && !chat.jarvis.enabled)
                Qt.callLater(() => {
                return composer.forceActiveFocus();
            });

        }
    }

    anchors {
        left: true
        bottom: true
    }

    Connections {
        function onFocusComposer() {
            if (window.opened)
                composer.forceActiveFocus();

        }

        function onStreamingTextChanged() {
            window.bottom();
        }

        function onMessagesChanged() {
            window.bottom();
        }

        function onCurrentChanged() {
            var id = chat.current ? chat.current.id : "";
            if (id !== window.displayedChatId) {
                window.followBottom = true;
                window.displayedChatId = id;
            }
            window.bottom();
        }

        target: chat
    }

    Timer {
        id: copiedReset

        interval: 1800
        onTriggered: window.copied = ""
    }

    TextEdit {
        id: clipboard

        visible: false
    }

    FileDialog {
        id: attachmentDialog

        title: "Attach files to Side Chat"
        fileMode: FileDialog.OpenFiles
        onAccepted: {
            for (var i = 0; i < selectedFiles.length; i++) chat.addAttachment(selectedFiles[i])
            composer.forceActiveFocus();
        }
    }

    FileDialog {
        id: exportDialog

        title: "Export conversation"
        fileMode: FileDialog.SaveFile
        defaultSuffix: "md"
        nameFilters: ["Markdown (*.md)"]
        onAccepted: chat.request({
            "action": "export",
            "path": String(selectedFile)
        })
    }

    FolderDialog {
        id: folderDialog

        title: "Agent working folder"
        onAccepted: cwdField.text = decodeURIComponent(String(selectedFolder).replace("file://", ""))
    }

    HyprlandFocusGrab {
        active: window.opened && chat.pinned && !chat.jarvis.enabled && !attachmentDialog.visible && !exportDialog.visible && !folderDialog.visible
        windows: [window]
        onCleared: {
            if (!chat.jarvis.enabled) {
                chat.close();
            }
        }
    }
    // The only input region left when closed; it paints absolutely nothing.

    Item {
        id: edgeHotspot

        z: 10
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        width: window.px(4)
        height: Math.min(window.px(160), window.height)

        MouseArea {
            id: edgeMouse

            anchors.fill: parent
            hoverEnabled: true
            onClicked: chat.show(window.screen.name, true)
        }

    }

    Item {
        id: revealClip

        objectName: "chat-drawer"
        width: Math.round(window.width * window.reveal)
        height: parent.height
        clip: true

        HoverHandler {
            id: drawerHover
        }
        // One screen-connected silhouette: the chat itself is the edge drawer.

        DrawerSurface {
            id: bodySurface
            fill: window.surface
            corner: window.px(20)
            outlineEnabled: !chat.meta.appearance || chat.meta.appearance.outline !== false
            keyboardFocus: window.opened && chat.pinned
            borderColors: windowBorder.colors
            borderAngle: windowBorder.angle
            borderWidth: windowBorder.borderWidth
            width: revealClip.width
            height: parent.height - window.px(12)
        }

        Item {
            id: card

            width: window.width
            height: parent.height - window.px(12)
            x: -Math.round((1 - window.reveal) * window.px(12))
            opacity: Math.max(0, Math.min(1, (window.reveal - 0.16) / 0.84))
            Keys.onEscapePressed: (event) => {
                if (chat.page !== "chat") {
                    chat.page = "chat";
                } else if (chat.editIndex >= 0) {
                    chat.editIndex = -1;
                    chat.draft = "";
                } else {
                    chat.close();
                }
                event.accepted = true;
            }

            TapHandler {
                onTapped: chat.pin()
                gesturePolicy: TapHandler.WithinBounds
            }

            Shortcut {
                sequence: "Ctrl+N"
                enabled: window.opened
                onActivated: chat.startNew()
            }

            Shortcut {
                sequence: "Ctrl+H"
                enabled: window.opened
                onActivated: {
                    chat.page = chat.page === "history" ? "chat" : "history";
                    chat.pin();
                }
            }

            Shortcut {
                sequence: "Ctrl+Shift+C"
                enabled: window.opened
                onActivated: {
                    if (chat.messages.length) {
                        window.copyText(chat.messages[chat.messages.length - 1].text, "last");
                    }
                }
            }

            Shortcut {
                sequence: "Ctrl+Shift+V"
                enabled: window.opened
                onActivated: chat.request({
                    "action": "paste_image"
                })
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.leftMargin: window.px(20)
                anchors.rightMargin: window.px(20)
                anchors.topMargin: window.px(32)
                anchors.bottomMargin: window.px(30)
                spacing: 0

                RowLayout {
                    Layout.fillWidth: true
                    spacing: window.px(7)

                    Rectangle {
                        width: window.px(3)
                        height: window.px(17)
                        radius: width / 2
                        color: chat.connected ? Color.accent : window.dim
                    }

                    Text {
                        Layout.fillWidth: true
                        text: chat.page === "jarvis_settings" ? "Jarvis settings" : chat.page === "settings" ? "Preferences" : chat.agentName
                        color: window.fg
                        font.family: window.family
                        font.pixelSize: window.textSize
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }

                    ActionButton {
                        glyph: "new"
                        hint: "New conversation · Ctrl+N"
                        subtle: true
                        enabled: !chat.busy
                        onClicked: chat.startNew()
                    }

                    ActionButton {
                        glyph: "settings"
                        hint: "Preferences"
                        subtle: chat.page !== "settings"
                        enabled: !chat.busy
                        onClicked: {
                            if (chat.page === "settings")
                                chat.page = "chat";
                            else
                                window.showSettings();
                        }
                    }

                    ActionButton {
                        glyph: "close"
                        hint: "Hide panel · Esc"
                        subtle: true
                        onClicked: chat.close()
                    }

                }

                Item {
                    Layout.preferredHeight: window.px(14)
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: window.px(3)

                    ActionButton {
                        text: "Conversation"
                        selected: chat.page === "chat"
                        onClicked: {
                            chat.page = "chat";
                            chat.pin();
                        }
                    }

                    ActionButton {
                        text: "History"
                        selected: chat.page === "history"
                        onClicked: {
                            chat.page = "history";
                            chat.pin();
                        }
                    }

                    Item {
                        Layout.fillWidth: true
                    }

                    ActionButton {
                        glyph: "orb"
                        text: "Jarvis"
                        visible: chat.nativeSession
                        hint: "Floating voice companion"
                        ink: chat.jarvis.enabled ? Color.accent : window.fg
                        enabled: !chat.terminalOpen
                        onClicked: {
                            if (chat.jarvis.enabled)
                                chat.close();
                            else
                                chat.setJarvis(true);
                        }
                    }

                }

                Item {
                    Layout.preferredHeight: window.px(12)
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.alpha(window.fg, 0.07)
                }

                Item {
                    Layout.preferredHeight: window.px(14)
                }

                ColumnLayout {
                    visible: chat.page === "chat"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 0

                    Item {
                        visible: chat.messages.length === 0
                        Layout.fillWidth: true
                        Layout.fillHeight: true

                        Column {
                            anchors.verticalCenter: parent.verticalCenter
                            width: parent.width
                            spacing: window.px(12)

                            Text {
                                text: "Ready when you are."
                                font.weight: Font.DemiBold
                                color: window.fg
                                font.family: window.family
                                font.pixelSize: window.textSize
                            }

                            Text {
                                width: parent.width
                                text: chat.meta.available ? "Ask, build, or work on your desktop." : "Choose a default agent in Omarchy to get started."
                                wrapMode: Text.WordWrap
                                color: window.dim
                                font.family: window.family
                                font.pixelSize: window.textSize
                            }

                            Flow {
                                width: parent.width
                                spacing: window.px(5)

                                Repeater {
                                    model: ["Help with Omarchy", "Plan something"]

                                    ActionButton {
                                        required property string modelData

                                        text: modelData
                                        onClicked: {
                                            chat.draft = modelData;
                                            composer.forceActiveFocus();
                                            chat.pin();
                                        }
                                    }

                                }

                            }

                        }

                    }

                    Flickable {
                        id: thread

                        visible: chat.messages.length > 0
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        contentWidth: width
                        contentHeight: messageColumn.implicitHeight + 4
                        onHeightChanged: window.bottom()
                        clip: true
                        boundsBehavior: Flickable.StopAtBounds
                        onMovementStarted: window.followBottom = false
                        onMovementEnded: window.followBottom = contentY + height >= contentHeight - 30

                        Column {
                            id: messageColumn

                            width: thread.width - 5
                            spacing: window.px(18)
                            onImplicitHeightChanged: window.bottom()

                            Repeater {
                                model: chat.messages

                                MessageCard {
                                    required property var modelData
                                    required property int index

                                    width: messageColumn.width
                                    message: modelData
                                    messageIndex: index
                                    chat: window.chat
                                    host: window
                                }

                            }

                        }

                        ScrollBar.vertical: ScrollBar {
                            width: window.px(3)
                            policy: ScrollBar.AsNeeded
                        }

                    }

                    ActionButton {
                        visible: !window.followBottom && chat.messages.length > 0
                        Layout.alignment: Qt.AlignHCenter
                        glyph: "down"
                        text: "Latest"
                        subtle: true
                        implicitHeight: window.px(22)
                        onClicked: {
                            window.followBottom = true;
                            window.bottom();
                        }
                    }

                    Repeater {
                        model: chat.agentRequests.slice(0, 1)

                        AgentPrompt {
                            required property var modelData

                            Layout.fillWidth: true
                            Layout.topMargin: window.px(7)
                            request: modelData
                            chat: window.chat
                            host: window
                        }

                    }

                    Text {
                        visible: chat.terminalOpen
                        Layout.fillWidth: true
                        Layout.topMargin: window.px(7)
                        text: "Session open in terminal. Exit the agent there to continue here."
                        wrapMode: Text.WordWrap
                        color: Color.accent
                        font.family: window.family
                        font.pixelSize: window.textSize
                    }

                    RowLayout {
                        visible: chat.editIndex >= 0
                        Layout.fillWidth: true

                        Text {
                            Layout.fillWidth: true
                            text: "Editing · replaces later replies"
                            color: Color.accent
                            font.family: window.family
                            font.pixelSize: window.textSize
                        }

                        ActionButton {
                            text: "Cancel"
                            subtle: true
                            implicitHeight: window.px(24)
                            onClicked: {
                                chat.editIndex = -1;
                                chat.draft = "";
                            }
                        }

                    }

                    Flow {
                        visible: chat.attachments.length > 0
                        Layout.fillWidth: true
                        Layout.topMargin: window.px(5)
                        spacing: window.px(3)

                        Repeater {
                            model: chat.attachments

                            ActionButton {
                                required property string modelData
                                required property int index

                                text: decodeURIComponent(modelData.split("/").pop()).slice(0, 24) + "  ×"
                                hint: "Remove attachment"
                                implicitHeight: window.px(26)
                                onClicked: chat.removeAttachment(index)
                            }

                        }

                    }

                    Item {
                        Layout.preferredHeight: window.px(14)
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: composeLayout.implicitHeight + window.px(20)
                        color: "transparent"

                        Rectangle {
                            anchors.top: parent.top
                            width: parent.width
                            height: 1
                            color: composer.activeFocus ? Theme.alpha(Color.accent, 0.5) : Theme.alpha(window.fg, 0.12)

                            Behavior on color {
                                ColorAnimation {
                                    duration: 180
                                }

                            }

                        }

                        ColumnLayout {
                            id: composeLayout

                            anchors.fill: parent
                            anchors.topMargin: window.px(12)
                            anchors.bottomMargin: window.px(8)
                            spacing: window.px(8)

                            ScrollView {
                                Layout.fillWidth: true
                                Layout.preferredHeight: Math.min(window.px(100), Math.max(window.px(40), composer.contentHeight))
                                clip: true

                                TextArea {
                                    id: composer

                                    text: chat.draft
                                    onTextChanged: {
                                        if (chat.draft !== text) {
                                            chat.draft = text;
                                        }
                                    }
                                    onActiveFocusChanged: {
                                        if (activeFocus) {
                                            chat.pin();
                                        }
                                    }
                                    placeholderText: chat.terminalOpen ? "Session open in terminal…" : chat.busy ? (chat.jarvis.enabled ? "Correct or redirect…" : "Your next message…") : "Message " + chat.agentName + "…"
                                    placeholderTextColor: window.dim
                                    color: window.fg
                                    selectionColor: Theme.alpha(Color.accent, 0.4)
                                    selectedTextColor: window.fg
                                    font.family: window.family
                                    font.pixelSize: window.textSize
                                    wrapMode: TextEdit.Wrap
                                    padding: 0
                                    background: null
                                    Accessible.name: "Message " + chat.agentName
                                    Keys.onReturnPressed: (event) => {
                                        if (!(event.modifiers & Qt.ShiftModifier)) {
                                            chat.submit();
                                            event.accepted = true;
                                        } else {
                                            event.accepted = false;
                                        }
                                    }
                                    Keys.onEnterPressed: (event) => {
                                        if (!(event.modifiers & Qt.ShiftModifier)) {
                                            chat.submit();
                                            event.accepted = true;
                                        } else {
                                            event.accepted = false;
                                        }
                                    }
                                    Keys.onEscapePressed: chat.close()
                                }

                            }

                            RowLayout {
                                Layout.fillWidth: true
                                Layout.topMargin: window.px(4)
                                spacing: window.px(2)

                                ActionButton {
                                    glyph: "attach"
                                    hint: "Attach text, code, or images"
                                    subtle: true
                                    implicitHeight: window.px(26)
                                    onClicked: {
                                        chat.pin();
                                        attachmentDialog.open();
                                    }
                                }

                                ActionButton {
                                    glyph: "clipboard"
                                    hint: "Paste clipboard image · Ctrl+Shift+V"
                                    subtle: true
                                    implicitHeight: window.px(26)
                                    onClicked: chat.request({
                                        "action": "paste_image"
                                    })
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: chat.agentRequests.length ? "Needs your input" : chat.busy ? chat.activity : chat.nativeSession ? "Enter to send" : ""
                                    color: window.dim
                                    font.family: window.family
                                    font.pixelSize: window.textSize
                                    elide: Text.ElideRight
                                    horizontalAlignment: Text.AlignRight
                                }

                                ActionButton {
                                    visible: !!chat.current && chat.current.bashApproval === "always"
                                    text: "Bash: always"
                                    selected: true
                                    enabled: !chat.terminalOpen
                                    hint: "Bash commands are allowed in this conversation. Click to ask again."
                                    onClicked: chat.request({action: "bash_approval", chatId: chat.current.id, mode: "ask"})
                                }

                                ActionButton {
                                    glyph: window.expanded ? "collapse" : "expand"
                                    hint: window.expanded ? "Compact view" : "Expand view"
                                    subtle: true
                                    implicitHeight: window.px(26)
                                    implicitWidth: window.px(26)
                                    onClicked: window.expanded = !window.expanded
                                }

                                ActionButton {
                                    glyph: chat.busy && !(chat.jarvis.enabled && chat.draft.trim()) ? "stop" : "send"
                                    hint: chat.busy ? (chat.jarvis.enabled && chat.draft.trim() ? "Redirect agent · Enter" : "Stop generation") : "Send · Enter"
                                    accent: true
                                    implicitHeight: window.px(28)
                                    implicitWidth: window.px(30)
                                    enabled: !chat.terminalOpen && (chat.busy || (chat.connected && chat.draft.trim().length > 0))
                                    onClicked: chat.busy && !(chat.jarvis.enabled && chat.draft.trim()) ? chat.request({
                                        "action": "stop"
                                    }) : chat.submit()
                                }

                            }

                        }

                    }

                    RowLayout {
                        visible: chat.nativeSession
                        Layout.fillWidth: true
                        Layout.topMargin: window.px(7)

                        Icon {
                            name: "folder"
                            ink: window.dim
                            width: window.px(12)
                            height: width
                        }

                        Text {
                            Layout.fillWidth: true
                            text: String((chat.current ? chat.current.options.cwd : chat.meta.settings.cwd) || "Home").split("/").filter((p) => {
                                return p.length;
                            }).slice(-2).join("/")
                            elide: Text.ElideMiddle
                            color: window.dim
                            font.family: window.family
                            font.pixelSize: window.textSize
                        }

                        ActionButton {
                            glyph: "terminal"
                            text: "Terminal"
                            hint: "Continue this exact session in terminal"
                            subtle: true
                            implicitHeight: window.px(22)
                            enabled: !chat.busy && !chat.terminalOpen && !!(chat.current && chat.current.native)
                            onClicked: chat.request({
                                "action": "terminal"
                            })
                        }

                    }

                }

                ColumnLayout {
                    visible: chat.page === "history"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: window.px(10)

                    TextField {
                        Layout.fillWidth: true
                        placeholderText: "Search…"
                        color: window.fg
                        placeholderTextColor: window.dim
                        font.family: window.family
                        font.pixelSize: window.textSize
                        onTextChanged: window.historySearch = text

                        background: Rectangle {
                            radius: window.px(3)
                            color: Theme.alpha(window.fg, 0.04)
                            border.color: parent.activeFocus ? Color.accent : window.line
                        }

                    }

                    Text {
                        visible: chat.chats.length === 0
                        text: "Your conversations will appear here."
                        color: window.dim
                        font.family: window.family
                        font.pixelSize: window.textSize
                    }

                    Text {
                        visible: chat.chats.length > 0 && historyList.count === 0
                        text: "No matching conversations."
                        color: window.dim
                        font.family: window.family
                        font.pixelSize: window.textSize
                    }

                    ListView {
                        id: historyList

                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: window.px(4)
                        model: chat.chats.filter((c) => {
                            return c.title.toLowerCase().indexOf(window.historySearch.toLowerCase()) >= 0;
                        })

                        ScrollBar.vertical: ScrollBar {
                        }

                        delegate: ColumnLayout {
                            id: historyRow

                            required property var modelData

                            width: ListView.view.width
                            spacing: window.px(3)

                            RowLayout {
                                Layout.fillWidth: true

                                AbstractButton {
                                    Layout.fillWidth: true
                                    implicitHeight: window.px(50)
                                    enabled: !chat.busy
                                    Accessible.name: historyRow.modelData.title
                                    onClicked: chat.selectChat(historyRow.modelData.id)

                                    contentItem: Column {
                                        spacing: window.px(6)

                                        Text {
                                            width: parent.width
                                            text: historyRow.modelData.title
                                            color: window.fg
                                            font.family: window.family
                                            font.pixelSize: window.textSize
                                            elide: Text.ElideRight
                                        }

                                        Text {
                                            text: chat.agentLabel(historyRow.modelData.agent) + " · " + Qt.formatDateTime(new Date(historyRow.modelData.updated * 1000), "MMM d")
                                            color: window.dim
                                            font.family: window.family
                                            font.pixelSize: window.textSize
                                        }

                                    }

                                }

                                ActionButton {
                                    glyph: "close"
                                    hint: "Delete conversation"
                                    subtle: true
                                    enabled: !chat.busy
                                    onClicked: window.deletingId = historyRow.modelData.id
                                }

                            }

                            RowLayout {
                                visible: window.deletingId === historyRow.modelData.id

                                Text {
                                    Layout.fillWidth: true
                                    text: "Delete chat?"
                                    color: window.dim
                                    font.family: window.family
                                    font.pixelSize: window.textSize
                                }

                                ActionButton {
                                    text: "Keep"
                                    onClicked: window.deletingId = ""
                                }

                                ActionButton {
                                    text: "Delete"
                                    onClicked: {
                                        chat.request({
                                            "action": "delete",
                                            "id": historyRow.modelData.id
                                        });
                                        window.deletingId = "";
                                    }
                                }

                            }

                        }

                    }

                    ActionButton {
                        glyph: "back"
                        text: "Back to chat"
                        subtle: true
                        onClicked: chat.page = "chat"
                    }

                }

                Loader {
                    active: chat.page === "jarvis_settings"
                    visible: active
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    sourceComponent: Component {
                        JarvisSettings {
                            chat: window.chat
                            onDone: window.showSettings()
                        }

                    }

                }

                Flickable {
                    visible: chat.page === "settings"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    contentWidth: width
                    contentHeight: settingsColumn.implicitHeight
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds

                    ColumnLayout {
                        id: settingsColumn

                        width: parent.width
                        spacing: window.px(10)

                        LookSettings {
                            Layout.fillWidth: true
                            chat: window.chat
                        }

                        BashApprovalSettings {
                            Layout.fillWidth: true
                            chat: window.chat
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            color: window.line
                        }

                        RowLayout {
                            Text {
                                Layout.fillWidth: true
                                text: "Default agent"
                                color: window.dim
                                font.family: window.family
                                font.pixelSize: window.textSize
                            }

                            ActionButton {
                                text: chat.meta.agentName + " ↗"
                                subtle: true
                                onClicked: {
                                    chat.close();
                                    Quickshell.execDetached(["omarchy-menu", "summon", "setup.default.agent"]);
                                }
                            }

                        }

                        TextField {
                            visible: chat.messages.length > 0
                            Layout.fillWidth: true
                            text: chat.current ? chat.current.title : ""
                            placeholderText: "Conversation name"
                            color: window.fg
                            placeholderTextColor: window.dim
                            font.family: window.family
                            font.pixelSize: window.textSize
                            selectByMouse: true
                            Accessible.name: "Rename conversation"
                            onEditingFinished: {
                                if (chat.current && text.trim() && text !== chat.current.title) {
                                    chat.request({
                                    "action": "rename",
                                    "title": text
                                });
                                }
                            }

                            background: Rectangle {
                                radius: window.px(3)
                                color: Theme.alpha(window.fg, 0.04)
                                border.color: parent.activeFocus ? Color.accent : window.line
                            }

                        }

                        ActionButton {
                            text: "Jarvis · voice and control settings"
                            glyph: "settings"
                            subtle: true
                            onClicked: chat.page = "jarvis_settings"
                        }

                        Text {
                            text: "Model"
                            color: window.dim
                            font.family: window.family
                            font.pixelSize: window.textSize
                        }

                        TextField {
                            id: modelField

                            Layout.fillWidth: true
                            placeholderText: "Agent’s default model"
                            color: window.fg
                            placeholderTextColor: window.dim
                            font.family: window.family
                            font.pixelSize: window.textSize
                            selectByMouse: true

                            background: Rectangle {
                                radius: window.px(3)
                                color: Theme.alpha(window.fg, 0.04)
                                border.color: parent.activeFocus ? Color.accent : window.line
                            }

                        }

                        RowLayout {
                            Text {
                                Layout.fillWidth: true
                                text: "Thinking"
                                color: window.dim
                                font.family: window.family
                                font.pixelSize: window.textSize
                            }

                            ComboBox {
                                id: thinking

                                enabled: ["omp", "pi", "claude", "codex", "opencode"].indexOf(chat.current ? chat.current.agent : chat.meta.agent) >= 0
                                model: ["Default", "Low", "Medium", "High"]
                                palette.button: window.surface
                                palette.buttonText: window.fg
                                palette.text: window.fg
                                palette.base: window.surface
                                palette.highlight: Color.accent
                                font.family: window.family
                                font.pixelSize: window.textSize
                            }

                        }

                        Text {
                            text: "Working folder"
                            color: window.dim
                            font.family: window.family
                            font.pixelSize: window.textSize
                        }

                        RowLayout {
                            TextField {
                                id: cwdField

                                Layout.fillWidth: true
                                color: window.fg
                                font.family: window.family
                                font.pixelSize: window.textSize
                                selectByMouse: true

                                background: Rectangle {
                                    radius: window.px(3)
                                    color: Theme.alpha(window.fg, 0.04)
                                    border.color: parent.activeFocus ? Color.accent : window.line
                                }

                            }

                            ActionButton {
                                glyph: "folder"
                                hint: "Choose folder"
                                onClicked: folderDialog.open()
                            }

                        }

                        RowLayout {
                            ActionButton {
                                text: "Save"
                                accent: true
                                onClicked: {
                                    chat.request({
                                        "action": "settings",
                                        "settings": {
                                            "model": modelField.text,
                                            "thinking": thinking.currentText.toLowerCase(),
                                            "cwd": cwdField.text
                                        }
                                    });
                                    chat.page = "chat";
                                    composer.forceActiveFocus();
                                }
                            }

                            ActionButton {
                                glyph: "back"
                                text: "Back"
                                subtle: true
                                onClicked: chat.page = "chat"
                            }

                            Item {
                                Layout.fillWidth: true
                            }

                            ActionButton {
                                glyph: "export"
                                text: "Export"
                                subtle: true
                                enabled: chat.messages.length > 0
                                onClicked: exportDialog.open()
                            }

                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            color: window.line
                        }

                        ActionButton {
                            glyph: "terminal"
                            text: chat.nativeSession ? "Continue session in terminal" : "Open agent in terminal"
                            subtle: true
                            enabled: !chat.busy && !chat.terminalOpen && (!chat.nativeSession || !!(chat.current && chat.current.native))
                            onClicked: {
                                if (chat.nativeSession) {
                                    chat.request({
                                    "action": "terminal"
                                });
                                } else {
                                    chat.close();
                                    Quickshell.execDetached(["omarchy", "agent"]);
                                }
                            }
                        }

                        Text {
                            visible: chat.nativeSession
                            Layout.fillWidth: true
                            text: "Native tools, skills, and permissions. Commands and file edits appear in each reply’s activity."
                            color: window.dim
                            font.family: window.family
                            font.pixelSize: window.textSize
                            wrapMode: Text.WordWrap
                        }

                        Text {
                            Layout.fillWidth: true
                            text: "Uses your agent’s account and model. Chats stay on this computer; prompts go to your provider."
                            color: window.dim
                            font.family: window.family
                            font.pixelSize: window.textSize
                            wrapMode: Text.WordWrap
                        }

                        Text {
                            text: "Enter to send · Shift Enter for a new line\nCtrl N: new · Ctrl H: history · Esc: close"
                            color: window.dim
                            font.family: window.family
                            font.pixelSize: window.textSize
                            lineHeight: 1.3
                        }

                    }

                }

                RowLayout {
                    visible: chat.error !== "" || chat.notice !== ""
                    Layout.fillWidth: true
                    Layout.topMargin: window.px(7)

                    Text {
                        Layout.fillWidth: true
                        text: chat.error || chat.notice
                        color: chat.error ? Color.urgent : Color.accent
                        font.family: window.family
                        font.pixelSize: window.textSize
                        wrapMode: Text.WrapAnywhere
                        maximumLineCount: 4
                        elide: Text.ElideRight
                    }

                    ActionButton {
                        glyph: "close"
                        subtle: true
                        hint: "Dismiss"
                        onClicked: {
                            chat.error = "";
                            chat.notice = "";
                        }
                    }

                }

            }

            DropArea {
                anchors.fill: parent
                onDropped: (drop) => {
                    if (drop.hasUrls)
                        for (var i = 0; i < drop.urls.length; i++) chat.addAttachment(drop.urls[i]);

                }
            }

        }

    }

    mask: Region {
        Region {
            item: edgeHotspot
        }

        Region {
            item: revealClip
        }

    }

    Behavior on reveal {
        NumberAnimation {
            duration: window.opened ? 560 : 380
            easing.type: window.opened ? Easing.OutQuint : Easing.InOutCubic
        }

    }

}
