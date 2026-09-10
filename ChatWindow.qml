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
    readonly property color surface: ui.surface
    readonly property color fg: ui.foreground
    readonly property color dim: ui.muted
    readonly property color line: ui.line
    readonly property string family: Style.font.family
    readonly property int textSize: Style.font.body
    readonly property real drawerCorner: px(16)
    readonly property real contentInset: px(14)
    property real reveal: opened ? 1 : 0
    readonly property bool expanded: !!(chat.meta.appearance && chat.meta.appearance.expanded)
    property bool settingsPending: false
    readonly property bool nativeFolderLocked: !!(chat.current && chat.current.native)
    property string historySearch: ""
    property string deletingId: ""
    property string copied: ""
    property bool followBottom: true
    property string displayedChatId: ""

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
        // Show what this conversation actually runs with, not the global defaults.
        var source = chat.current && chat.current.options ? chat.current.options : chat.meta.settings;
        modelField.text = source.model || "";
        cwdField.text = source.cwd || "";
        thinking.currentIndex = Math.max(0, ["default", "low", "medium", "high"].indexOf(source.thinking));
        settingsPending = false;
        chat.page = "settings";
        chat.pin();
    }

    function setExpanded(value) {
        chat.request({
            "action": "appearance",
            "settings": {
                "expanded": !!value
            }
        });
    }

    // Leave the current page toward where the user came from.
    function leavePage() {
        if (chat.page === "peek_settings" && chat.returnPage === "settings")
            showSettings();
        else
            chat.page = "chat";
    }

    // One Escape ladder for every focus target: leave a page, cancel an edit, then hide.
    function pressEscape() {
        if (chat.page !== "chat") {
            leavePage();
        } else if (chat.editIndex >= 0) {
            chat.editIndex = -1;
            chat.draft = "";
        } else {
            chat.close();
        }
    }

    function when(seconds) {
        var date = new Date(seconds * 1000), now = new Date();
        if (date.toDateString() === now.toDateString())
            return Qt.formatDateTime(date, "h:mm ap");
        return Qt.formatDateTime(date, date.getFullYear() === now.getFullYear() ? "MMM d" : "MMM d, yyyy");
    }

    onPointerInsideChanged: chat.hover(screen.name, pointerInside)
    color: "transparent"
    margins.bottom: 0
    implicitWidth: Math.min(px(expanded ? 620 : 368), screen.width - px(12))
    implicitHeight: Math.min(screen.height - px(24), panelLayout.implicitHeight + 2 * (drawerCorner + contentInset) + px(8))
    onWidthChanged: {
        if (opened)
            chat.panelWidth = width;

    }
    exclusionMode: ExclusionMode.Ignore
    WlrLayershell.namespace: "omarchy-side-chat"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: opened && chat.pinned ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None
    onOpenedChanged: {
        if (opened) {
            chat.panelWidth = width;
            chat.settleNotice();
            if (chat.pinned && !chat.peek.enabled)
                Qt.callLater(() => {
                return composer.forceActiveFocus();
            });

        }
    }

    ChatStyle {
        id: ui
    }

    WindowBorder {
        id: windowBorder

        active: window.opened
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

        function onSettingsSaved() {
            if (!window.settingsPending)
                return;

            window.settingsPending = false;
            chat.page = "chat";
            composer.forceActiveFocus();
        }

        function onErrorChanged() {
            if (chat.error)
                window.settingsPending = false;

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
        active: window.opened && chat.pinned && !chat.peek.enabled && !attachmentDialog.visible && !exportDialog.visible && !folderDialog.visible
        windows: [window]
        onCleared: {
            if (!chat.peek.enabled)
                chat.close();

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
        // Keep the desktop's screen-connected outline around the angular controls.

        DrawerSurface {
            x: window.px(3)
            y: window.px(4)
            width: Math.max(0, revealClip.width - window.px(4))
            height: parent.height - window.px(8)
            corner: window.drawerCorner
            fill: Theme.mix(ui.surface, ui.accent, 0.22)
            borderColors: [Theme.mix(ui.surface, ui.accent, 0.65)]
            borderWidth: window.px(0.8)
        }

        DrawerSurface {
            id: bodySurface

            fill: window.surface
            corner: window.drawerCorner
            outlineEnabled: !chat.meta.appearance || chat.meta.appearance.outline !== false
            keyboardFocus: window.opened && chat.pinned
            borderColors: windowBorder.colors
            borderAngle: windowBorder.angle
            borderWidth: windowBorder.borderWidth
            width: Math.max(0, revealClip.width - window.px(4))
            height: parent.height - window.px(8)
        }

        Item {
            id: card

            width: window.width - window.px(4)
            height: parent.height - window.px(8)
            x: -Math.round((1 - window.reveal) * window.px(12))
            opacity: Math.max(0, Math.min(1, (window.reveal - 0.16) / 0.84))
            Keys.onEscapePressed: (event) => {
                window.pressEscape();
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
                    if (chat.messages.length)
                        window.copyText(chat.messages[chat.messages.length - 1].text, "last");

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
                id: panelLayout

                anchors.fill: parent
                anchors.leftMargin: window.contentInset
                anchors.rightMargin: window.contentInset
                // The painted top/bottom edges sit one corner radius inward.
                anchors.topMargin: window.drawerCorner + window.contentInset
                anchors.bottomMargin: window.drawerCorner + window.contentInset
                spacing: 0

                RowLayout {
                    id: headerRow

                    Layout.fillWidth: true
                    spacing: window.px(3)

                    ActionButton {
                        visible: chat.page !== "chat"
                        glyph: "back"
                        hint: (chat.page === "peek_settings" && chat.returnPage === "settings" ? "Back to preferences" : "Back to chat") + " · Esc"
                        subtle: true
                        onClicked: window.leavePage()
                    }

                    Rectangle {
                        visible: chat.page === "chat"
                        Layout.preferredWidth: window.px(6)
                        Layout.preferredHeight: window.px(6)
                        color: chat.connected ? ui.accent : ui.danger
                    }

                    Text {
                        id: pageTitle

                        Layout.fillWidth: true
                        Layout.minimumWidth: 0
                        text: chat.page === "permissions" ? "Permissions" : chat.page === "peek_settings" ? "Peek settings" : chat.page === "settings" ? "Preferences" : chat.page === "history" ? "History" : chat.current && chat.messages.length ? chat.current.title || "Conversation" : "New chat"
                        color: ui.foreground
                        font.family: window.family
                        font.pixelSize: window.textSize
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }

                    Text {
                        visible: chat.page === "chat"
                        Layout.maximumWidth: window.px(72)
                        text: chat.connected ? chat.agentName : "Offline"
                        color: ui.muted
                        font.family: ui.family
                        font.pixelSize: ui.caption
                        elide: Text.ElideRight
                    }

                    ActionButton {
                        visible: chat.page === "chat"
                        glyph: "history"
                        hint: "Conversation history · Ctrl+H"
                        subtle: true
                        onClicked: {
                            chat.page = "history";
                            chat.pin();
                        }
                    }

                    ActionButton {
                        visible: chat.page === "chat" || chat.page === "history"
                        glyph: "new"
                        hint: "New conversation · Ctrl+N"
                        subtle: true
                        enabled: !chat.busy
                        onClicked: chat.startNew()
                    }

                    ActionButton {
                        glyph: window.expanded ? "collapse" : "expand"
                        hint: window.expanded ? "Compact view" : "Expand view"
                        subtle: true
                        enabled: chat.connected
                        onClicked: window.setExpanded(!window.expanded)
                    }

                    ActionButton {
                        visible: chat.page === "chat"
                        glyph: "settings"
                        hint: "Preferences"
                        subtle: true
                        enabled: !chat.busy
                        onClicked: window.showSettings()
                    }

                    ActionButton {
                        glyph: "close"
                        hint: "Hide panel · Esc"
                        subtle: true
                        onClicked: chat.close()
                    }

                }

                Item { Layout.preferredHeight: window.px(8) }

                ColumnLayout {
                    visible: chat.page === "chat"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 0

                    Column {
                        visible: chat.messages.length === 0
                        Layout.fillWidth: true
                        spacing: window.px(6)

                        Text {
                            width: parent.width
                            text: chat.meta.available ? "What do you want to work on?" : "No agent is configured."
                            wrapMode: Text.WordWrap
                            color: window.fg
                            font.family: window.family
                            font.pixelSize: window.textSize
                            font.weight: Font.DemiBold
                        }
                        Text {
                            visible: !chat.meta.available
                            width: parent.width
                            text: "Set a default CLI agent in Omarchy to begin."
                            wrapMode: Text.WordWrap
                            color: ui.muted
                            font.family: ui.family
                            font.pixelSize: ui.small
                        }

                        ActionButton {
                            visible: !chat.meta.available
                            glyph: "external"
                            text: "Choose default agent"
                            accent: true
                            hint: "Opens the Omarchy agent setup menu"
                            onClicked: {
                                chat.close();
                                Quickshell.execDetached(["omarchy-menu", "summon", "setup.default.agent"]);
                            }
                        }

                        Flow {
                            width: parent.width
                            spacing: window.px(4)

                            Repeater {
                                model: chat.meta.available ? ["Explain this project", "Plan a change"] : []

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

                    Flickable {
                        id: thread
                        objectName: "message-thread"

                        Layout.preferredHeight: Math.min(contentHeight, window.px(window.expanded ? 460 : 300))
                        Layout.minimumHeight: 0
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
                            spacing: window.px(8)
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

                        ScrollBar.vertical: ChatScrollBar {
                            width: window.px(3)
                            policy: ScrollBar.AsNeeded
                        }

                        ActionButton {
                            // Parent to the viewport, outside both the scroll content and page layout.
                            parent: thread
                            objectName: "jump-to-latest"
                            visible: !window.followBottom && chat.messages.length > 0 && thread.contentHeight > thread.height + 1
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            anchors.margins: window.px(6)
                            z: 2
                            glyph: "down"
                            text: "Latest"
                            accent: true
                            hint: "Jump to the latest reply"
                            onClicked: {
                                window.followBottom = true;
                                window.bottom();
                            }
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
                        color: ui.emphasis
                        font.family: window.family
                        font.pixelSize: window.textSize
                    }

                    RowLayout {
                        visible: chat.editIndex >= 0
                        Layout.fillWidth: true

                        Text {
                            Layout.fillWidth: true
                            text: "Editing · replaces later replies"
                            color: ui.emphasis
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

                                readonly property string fileName: decodeURIComponent(modelData.split("/").pop())

                                text: fileName
                                trailingGlyph: "close"
                                Layout.maximumWidth: window.px(170)
                                hint: "Remove " + fileName
                                implicitHeight: ui.controlHeight
                                onClicked: chat.removeAttachment(index)
                            }

                        }

                    }

                    Item {
                        Layout.preferredHeight: window.px(6)
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: composeLayout.implicitHeight + window.px(12)
                        color: ui.field
                        border.width: ui.stroke
                        border.color: composer.activeFocus ? ui.accent : ui.border

                        ColumnLayout {
                            id: composeLayout

                            anchors.fill: parent
                            anchors.margins: window.px(6)
                            spacing: window.px(3)

                            ScrollView {
                                Layout.fillWidth: true
                                Layout.preferredHeight: Math.min(window.px(96), Math.max(window.px(22), composer.contentHeight))
                                clip: true

                                TextArea {
                                    id: composer
                                    objectName: "chat-composer"

                                    text: chat.draft
                                    onTextChanged: {
                                        if (chat.draft !== text)
                                            chat.draft = text;

                                    }
                                    onActiveFocusChanged: {
                                        if (activeFocus)
                                            chat.pin();

                                    }
                                    placeholderText: chat.terminalOpen ? "Session open in terminal…" : chat.busy ? (chat.peek.enabled ? "Correct or redirect…" : "Draft your next message…") : "Message " + chat.agentName + "…"
                                    placeholderTextColor: window.dim
                                    color: window.fg
                                    selectionColor: Theme.alpha(ui.emphasis, 0.4)
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
                                    Keys.onEscapePressed: window.pressEscape()
                                }

                            }

                            Text {
                                visible: chat.agentRequests.length > 0 || chat.busy
                                Layout.fillWidth: true
                                text: chat.agentRequests.length ? "Needs your input" : chat.activity
                                color: window.dim
                                font.family: window.family
                                font.pixelSize: ui.small
                                elide: Text.ElideRight
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: window.px(2)

                                ActionButton {
                                    glyph: "attach"
                                    hint: "Attach a file · paste an image with Ctrl+Shift+V"
                                    subtle: true
                                    implicitHeight: ui.controlHeight
                                    onClicked: {
                                        chat.pin();
                                        attachmentDialog.open();
                                    }
                                }

                                ActionButton {
                                    objectName: "permission-selector"
                                    glyph: "shield"
                                    visible: chat.permissionModes.length > 0
                                    Layout.maximumWidth: window.px(160)
                                    Layout.minimumWidth: 0
                                    text: chat.permissionLabel === "CLI default" ? "Default" : chat.permissionLabel
                                    selected: !!chat.current && !!chat.current.permissionMode && chat.current.permissionMode !== "default"
                                    subtle: true
                                    trailingGlyph: "chevron-down"
                                    hint: "Access: " + chat.permissionLabel + " · /permissions"
                                    onClicked: {
                                        chat.page = "permissions";
                                        chat.pin();
                                    }
                                }

                                Item {
                                    Layout.fillWidth: true
                                }

                                ActionButton {
                                    visible: !!chat.current && chat.current.bashApproval === "always"
                                    glyph: "check"
                                    text: "Bash"
                                    selected: true
                                    enabled: !chat.terminalOpen
                                    hint: "Bash commands are allowed in this conversation. Click to ask again."
                                    onClicked: chat.request({
                                        "action": "bash_approval",
                                        "chatId": chat.current.id,
                                        "mode": "ask"
                                    })
                                }

                                ActionButton {
                                    glyph: chat.busy && !(chat.peek.enabled && chat.draft.trim()) ? "stop" : "send"
                                    hint: chat.busy ? (chat.peek.enabled && chat.draft.trim() ? "Redirect agent · Enter" : "Stop generation") : "Send · Enter"
                                    accent: true
                                    implicitHeight: ui.controlHeight
                                    implicitWidth: ui.controlHeight
                                    enabled: !chat.terminalOpen && (chat.busy || (chat.connected && chat.draft.trim().length > 0))
                                    onClicked: chat.busy && !(chat.peek.enabled && chat.draft.trim()) ? chat.request({
                                        "action": "stop"
                                    }) : chat.submit()
                                }

                            }

                        }

                    }

                    RowLayout {
                        visible: chat.nativeSession
                        Layout.fillWidth: true
                        Layout.topMargin: window.px(5)
                        spacing: window.px(2)

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
                            font.pixelSize: ui.small
                        }

                        ActionButton {
                            glyph: "orb"
                            text: "Peek"
                            hint: "Open the floating voice companion"
                            subtle: true
                            implicitHeight: window.px(22)
                            enabled: !chat.terminalOpen
                            onClicked: {
                                if (chat.peek.enabled)
                                    chat.close();
                                else
                                    chat.setPeek(true);
                            }
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
                    spacing: window.px(8)

                    ChatField {
                        Layout.fillWidth: true
                        glyph: "search"
                        placeholderText: "Search conversations…"
                        Accessible.name: "Search conversations"
                        onTextChanged: window.historySearch = text
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

                        Layout.preferredHeight: Math.min(contentHeight, window.px(window.expanded ? 460 : 300))
                        Layout.minimumHeight: 0
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: window.px(4)
                        model: chat.chats.filter((c) => {
                            return c.title.toLowerCase().indexOf(window.historySearch.toLowerCase()) >= 0;
                        })

                        ScrollBar.vertical: ChatScrollBar {
                        }

                        delegate: ColumnLayout {
                            id: historyRow

                            required property var modelData

                            width: ListView.view.width - window.px(6)
                            spacing: window.px(3)
                            HoverHandler { id: historyHover }

                            RowLayout {
                                Layout.fillWidth: true

                                AbstractButton {
                                    Layout.fillWidth: true
                                    implicitHeight: window.px(52)
                                    padding: window.px(10)
                                    hoverEnabled: true
                                    enabled: !chat.busy
                                    Accessible.name: historyRow.modelData.title
                                    onClicked: chat.selectChat(historyRow.modelData.id)

                                    background: Rectangle {
                                        radius: ui.radius
                                        color: parent.hovered ? ui.secondary : ui.field
                                        border.width: parent.activeFocus ? ui.stroke : 1
                                        border.color: ui.border
                                    }

                                    contentItem: Column {
                                        spacing: window.px(3)

                                        Text {
                                            width: parent.width
                                            text: historyRow.modelData.title
                                            color: window.fg
                                            font.family: window.family
                                            font.pixelSize: window.textSize
                                            elide: Text.ElideRight
                                        }

                                        Text {
                                            text: chat.agentLabel(historyRow.modelData.agent) + " · " + window.when(historyRow.modelData.updated)
                                            color: window.dim
                                            font.family: window.family
                                            font.pixelSize: ui.small
                                            elide: Text.ElideRight
                                            width: parent.width
                                        }

                                    }

                                }

                                ActionButton {
                                    glyph: "trash"
                                    hint: "Delete conversation"
                                    opacity: historyHover.hovered || activeFocus || window.deletingId === historyRow.modelData.id ? 1 : 0
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
                                    danger: true
                                    hint: "Deletes this conversation permanently"
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

                }

                Flickable {
                    id: permissionsView

                    Layout.preferredHeight: Math.min(contentHeight, window.px(window.expanded ? 500 : 360))
                    visible: chat.page === "permissions"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    contentWidth: width
                    contentHeight: permissionSettings.implicitHeight
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds

                    ScrollBar.vertical: ChatScrollBar {}

                    PermissionSettings {
                        id: permissionSettings

                        width: parent.width - window.px(6)
                        chat: window.chat
                        onRevealRequested: (item) => {
                            var top = item.mapToItem(permissionSettings, 0, 0).y;
                            var bottom = top + item.height;
                            if (top < permissionsView.contentY)
                                permissionsView.contentY = top;
                            else if (bottom > permissionsView.contentY + permissionsView.height)
                                permissionsView.contentY = Math.max(0, bottom - permissionsView.height);
                        }
                    }

                }

                Loader {
                    active: chat.page === "peek_settings"
                    Layout.preferredHeight: Math.min(item ? item.implicitHeight : 0, window.px(window.expanded ? 500 : 360))
                    visible: active
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    sourceComponent: Component {
                        PeekSettings {
                            chat: window.chat
                            onDone: window.leavePage()
                        }

                    }

                }

                Flickable {
                    visible: chat.page === "settings"
                    Layout.preferredHeight: Math.min(contentHeight, window.px(window.expanded ? 500 : 340))
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    contentWidth: width
                    contentHeight: settingsColumn.implicitHeight
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds

                    ScrollBar.vertical: ChatScrollBar {}

                    ColumnLayout {
                        id: settingsColumn

                        width: parent.width - window.px(6)
                        spacing: window.px(8)
                        ChatSection { text: "Conversation" }

                        SettingLabel {
                            Layout.fillWidth: true
                            text: "Changes in this section apply immediately."
                            font.weight: Font.Normal
                            wrapMode: Text.WordWrap
                        }

                        SettingLabel { visible: chat.messages.length > 0; text: "Conversation name" }
                        ChatField {
                            visible: chat.messages.length > 0
                            Layout.fillWidth: true
                            text: chat.current ? chat.current.title : ""
                            placeholderText: "Conversation name"
                            Accessible.name: "Rename conversation"
                            onEditingFinished: {
                                if (chat.current && text.trim() && text !== chat.current.title)
                                    chat.request({
                                    "action": "rename",
                                    "title": text
                                });

                            }
                        }

                        RowLayout {
                            visible: chat.permissionModes.length > 0
                            Layout.fillWidth: true

                            SettingLabel {
                                text: "Permissions"
                                Layout.fillWidth: true
                            }

                            ActionButton {
                                text: chat.permissionLabel
                                Layout.maximumWidth: window.px(200)
                                hint: "Change this conversation’s permission mode"
                                onClicked: {
                                    chat.page = "permissions";
                                    chat.pin();
                                }
                            }

                        }

                        BashApprovalSettings {
                            Layout.fillWidth: true
                            chat: window.chat
                        }

                        ChatSection { text: "Agent" }

                        SettingLabel {
                            Layout.fillWidth: true
                            text: window.nativeFolderLocked ? "Saved with the Save button. Saving restarts this native session before the next message." : "Saved with the Save button. Changing the folder resets this conversation’s permission choices."
                            font.weight: Font.Normal
                            wrapMode: Text.WordWrap
                        }

                        RowLayout {
                            Layout.fillWidth: true

                            SettingLabel {
                                text: "Default agent"
                                Layout.fillWidth: true
                            }

                            ActionButton {
                                text: chat.meta.agentName
                                glyph: "external"
                                hint: "Opens the Omarchy agent setup menu"
                                onClicked: {
                                    chat.close();
                                    Quickshell.execDetached(["omarchy-menu", "summon", "setup.default.agent"]);
                                }
                            }

                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: window.px(4)

                            SettingLabel {
                                text: "Model"
                            }

                            ChatField {
                                id: modelField

                                Layout.fillWidth: true
                                placeholderText: "Agent’s default model"
                                Accessible.name: "Model"
                            }

                        }

                        RowLayout {
                            Layout.fillWidth: true

                            SettingLabel {
                                text: "Thinking"
                                Layout.fillWidth: true
                            }

                            ChatComboBox {
                                id: thinking

                                enabled: ["omp", "pi", "claude", "codex", "opencode"].indexOf(chat.current ? chat.current.agent : chat.meta.agent) >= 0
                                model: ["Default", "Low", "Medium", "High"]
                                Accessible.name: "Thinking level"
                            }

                        }

                        SettingLabel {
                            visible: !thinking.enabled
                            Layout.fillWidth: true
                            text: chat.agentName + " does not expose a thinking level here."
                            font.weight: Font.Normal
                            wrapMode: Text.WordWrap
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: window.px(4)

                            SettingLabel {
                                text: "Working folder"
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: window.px(4)

                                ChatField {
                                    id: cwdField

                                    Layout.fillWidth: true
                                    enabled: !window.nativeFolderLocked
                                    Accessible.name: "Working folder"
                                }

                                ActionButton {
                                    glyph: "folder"
                                    hint: window.nativeFolderLocked ? "This native session keeps its folder" : "Choose folder"
                                    enabled: !window.nativeFolderLocked
                                    onClicked: folderDialog.open()
                                }

                            }

                            SettingLabel {
                                visible: window.nativeFolderLocked
                                Layout.fillWidth: true
                                text: "A native session keeps its folder. Start a new conversation to work elsewhere."
                                font.weight: Font.Normal
                                wrapMode: Text.WordWrap
                            }

                        }

                        ChatSection { text: "Desktop" }
                        LookSettings {
                            Layout.fillWidth: true
                            chat: window.chat
                        }

                        ActionButton {
                            text: "Peek settings"
                            glyph: "orb"
                            subtle: true
                            onClicked: chat.openPeekSettings("settings")
                        }

                        ActionButton {
                            // Native sessions already have Terminal in the chat footer.
                            visible: !chat.nativeSession
                            glyph: "terminal"
                            text: "Open agent in terminal"
                            subtle: true
                            enabled: !chat.busy && !chat.terminalOpen
                            onClicked: {
                                chat.close();
                                Quickshell.execDetached(["omarchy", "agent"]);
                            }
                        }

                        SettingLabel {
                            Layout.fillWidth: true
                            text: "Chats saved locally. Prompts use your agent’s account."
                            wrapMode: Text.WordWrap
                        }

                        SettingLabel {
                            Layout.fillWidth: true
                            text: "Enter: send · Shift+Enter: new line\nCtrl+N: new · Ctrl+H: history · Esc: back or close\nWhile Peek is on, open chat from Peek or your keybinding; edge hover is off."
                            wrapMode: Text.WordWrap
                        }

                        SettingLabel {
                            Layout.fillWidth: true
                            text: "Side Chat " + chat.uiVersion + " · blr.side-chat"
                            Accessible.name: "Installed Side Chat version " + chat.uiVersion
                        }

                    }

                }

                RowLayout {
                    visible: chat.page === "settings"
                    Layout.fillWidth: true
                    Layout.topMargin: window.px(8)
                    spacing: window.px(4)

                    ActionButton {
                        objectName: "save-settings"
                        text: window.settingsPending ? "Saving…" : "Save"
                        accent: true
                        enabled: chat.connected && !chat.busy && !window.settingsPending
                        hint: chat.busy ? "Wait for the reply to finish" : "Save agent settings"
                        onClicked: {
                            // Stay on the page until the backend confirms; errors land in the notice row below.
                            window.settingsPending = true;
                            chat.error = "";
                            chat.request({
                                "action": "settings",
                                "settings": {
                                    "model": modelField.text,
                                    "thinking": thinking.currentText.toLowerCase(),
                                    "cwd": cwdField.text
                                }
                            });
                        }
                    }

                    ActionButton {
                        text: "Back"
                        subtle: true
                        hint: "Leave without saving agent settings"
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

                RowLayout {
                    visible: chat.error !== "" || chat.notice !== ""
                    Layout.fillWidth: true
                    Layout.topMargin: window.px(7)

                    Text {
                        Layout.fillWidth: true
                        text: chat.error || chat.notice
                        color: chat.error ? ui.danger : ui.emphasis
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

    component SettingLabel: Text {
        color: window.dim
        font.family: window.family
        font.pixelSize: ui.small
        font.weight: Font.DemiBold
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
