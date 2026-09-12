import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Hyprland
import qs.Commons
import "Keypad.js" as Keypad

Scope {
    id: root
    property var shell: null
    property alias thoughts: thoughtsModel
    property alias workspace: workspaceModel
    property var manifest: ({})
    readonly property string uiVersion: String(manifest && manifest.version ? manifest.version : "development")
    property var meta: ({agent: "", agentName: "Connecting…", available: false, settings: {model: "", thinking: "default", cwd: ""}})
    property var chats: []
    property var current: null
    property bool busy: false
    property bool connected: false
    property string error: ""
    property string notice: ""
    property string openScreen: ""
    property string companionScreen: ""
    property real panelWidth: 360
    property string hoveredScreen: ""
    property bool pinned: false
    property bool restoring: false
    property var attachments: []
    property int editIndex: -1
    property var editBackup: null
    property string draft: ""
    property var draftSource: ({})
    property bool excludeScreen: false
    readonly property bool screenWillBeShared: !excludeScreen && peek.enabled && peek.scope === "desktop" &&
        (peek.screenContext === "always" || (peek.screenContext === "on-request" && !!meta.screenContextPattern && new RegExp(meta.screenContextPattern,"i").test(draft)))
    property string page: "chat"
    property string returnPage: "chat"
    property var pageHistory: []
    property var messageTarget: null
    property string activity: "Thinking…"
    property string streamingText: ""
    property string streamingModel: ""
    property var streamingTools: []
    property var agentRequests: []
    property var peek: ({enabled:false,ready:false,listening:false,speaking:false,stage:"off",caption:"",partial:"",inputLevel:0,outputLevel:0,scope:"desktop",handsFree:false,muted:false,reducedMotion:false,voice:"alba",asrModel:"voxtype",voxtypeAvailable:false,devices:[]})
    property var aiPointer: ({visible:false})
    readonly property bool nativeSession: (meta.nativeAgents || []).indexOf(current ? current.agent : meta.agent) >= 0
    readonly property bool terminalOpen: !!(current && current.terminalOpen)
    readonly property string agentName: current && current.agent ? agentLabel(current.agent) : meta.agentName
    readonly property var messages: current ? current.messages : []
    readonly property var permissionModes: (meta.permissionModes || {})[current ? current.agent : meta.agent] || []
    readonly property string permissionLabel: {
        var mode = current ? (current.permissionMode || "default") : "default"
        var entry = permissionModes.find(m => m.id === mode)
        return entry ? entry.label : "Permissions"
    }
    signal focusComposer()
    signal companionControlsRequested()
    signal settingsSaved()
    signal preferencesRequested()

    function agentLabel(id) {
        return ({omp: "Oh My Pi", pi: "Pi", claude: "Claude", codex: "Codex", opencode: "OpenCode", gemini: "Gemini", copilot: "Copilot", crush: "Crush", grok: "Grok"})[id] || id
    }
    function request(data) {
        if (!connected) { error = "Reconnecting. Your draft is still here."; return false }
        backend.write(JSON.stringify(data) + "\n")
        return true
    }
    function show(screenName, persistent) {
        dismiss.stop()
        openScreen = screenName
        if (persistent) { pinned = true; Qt.callLater(root.focusWorkspace) }
        request({action: "ping"})
    }
    function open() {
        var focused = Hyprland.focusedMonitor
        show(focused ? focused.name : Quickshell.screens[0].name, true)
    }
    function close() {
        saveDraft()
        openScreen = ""; pinned = false; workspaceModel.mode=""
    }
    function showCompanion() {
        var focused=Hyprland.focusedMonitor
        companionScreen=openScreen || (focused ? focused.name : Quickshell.screens[0].name)
        close(); page="chat"
    }
    function setPeek(enabled, reopen) {
        if (enabled) showCompanion()
        else if (reopen !== false) openConversation()
        request({action:"peek",enabled:enabled,accent:String(Color.accent)})
    }
    function visit(next) {
        if (page === next) return
        pageHistory = pageHistory.concat([page])
        returnPage = page
        page = next
    }
    function back() {
        var history = pageHistory.slice()
        page = history.length ? history.pop() : "chat"
        pageHistory = history
        returnPage = history.length ? history[history.length - 1] : "chat"
    }
    function openConversation() { workspaceModel.mode="";pageHistory=[];page="chat"; show(openScreen || companionScreen || thoughtsScreen(),true) }
    function focusWorkspace() {
        if (!openScreen) return
        if (workspaceModel.mode) workspaceModel.focusInput()
        else if (page === "notes" || page === "todos") thoughtsModel.focusEditor()
        else focusComposer()
    }
    function navigate(section) {
        workspaceModel.mode=""
        if (section === "notes" || section === "todos") openThoughts(section === "todos" ? "todo" : "note")
        else openConversation()
    }
    function openWorkspacePeek() {
        companionScreen=openScreen || thoughtsScreen()
        if (!peek.enabled) request({action:"peek",enabled:true,accent:String(Color.accent)})
        else companionControlsRequested()
    }
    function openPeekSettings(from) { workspaceModel.mode="";visit("peek_settings");show(openScreen || companionScreen || thoughtsScreen(),true) }
    function openHistory() {workspaceModel.mode="";visit("history");open()}
    function openPreferences() {workspaceModel.mode="";open();preferencesRequested()}
    function toggleMicrophone() {
        if(!peek.enabled) showCompanion()
        request({action:"peek_toggle_listen",accent:String(Color.accent)})
    }
    function toggleChatListening() {
        if(thoughtsModel.recording) {
            thoughtsModel.stopCapture()
            thoughtsModel.error="Finishing this capture. Press Numpad 1 again to listen in Chat."
            return
        }
        openConversation()
        companionScreen=openScreen
        request({action:"peek_toggle_listen",accent:String(Color.accent)})
    }
    function stopWorkspace() {
        if(thoughtsModel.recording) request({action:"thoughts_voice_cancel"})
        request({action:"stop"})
    }
    function settleNotice() { if (notice) noticeClear.restart() }
    function announce(title, body) {
        Quickshell.execDetached(["notify-send", "-a", "Side Chat", "-i", "dialog-information", String(title), String(body || "")])
    }
    function toggle() { openScreen ? close() : open() }
    function openThoughts(kind) {
        if (kind && kind !== thoughtsModel.kind) {
            if (thoughtsModel.recording || thoughtsModel.saving) return
            thoughtsModel.switchKind(kind)
        }
        workspaceModel.mode="";pageHistory=[];page=thoughtsModel.kind === "todo" ? "todos" : "notes"
        show(openScreen || (peek.enabled ? companionScreen : "") || thoughtsScreen(),true)
    }
    function thoughtsScreen() { return Hyprland.focusedMonitor ? Hyprland.focusedMonitor.name : Quickshell.screens[0].name }
    function saveThought(text) {
        if(thoughtsModel.recording || thoughtsModel.saving) {thoughtsModel.error="Finish this capture first.";thoughtsModel.show();return}
        thoughtsModel.switchKind("note");thoughtsModel.show();thoughtsModel.newThought(text,{kind:"chat",id:current ? current.id : "",label:current ? current.title : "Conversation"})
    }
    function openSource(source) {
        if(!source || !source.id) return
        workspaceModel.activate({kind:source.kind === "chat" ? "chat" : "note",id:source.id})
    }
    function hover(screenName, inside) {
        if (peek.enabled && !openScreen) return
        if (inside) {
            hoveredScreen = screenName
            show(screenName, false)
        } else if (hoveredScreen === screenName) {
            hoveredScreen = ""
            if (!pinned) dismiss.restart()
        }
    }
    function pin() { pinned = true; dismiss.stop() }
    function saveDraft() {
        draftSave.stop()
        if (!connected) return false
        var value = editBackup || {text:draft, source:draftSource, attachments:attachments}
        return request({action:"draft", id:current ? current.id : "", text:value.text,
            source:value.source, attachments:value.attachments,
            editDraft:editIndex < 0 ? null : {index:editIndex,messageId:messages[editIndex].id || "",text:draft,source:draftSource,attachments:attachments}})
    }
    function cancelEdit() {
        if (editIndex < 0) return
        var value = editBackup || {text:"",source:{},attachments:[]}
        restoring = true
        draft=value.text;draftSource=value.source;attachments=value.attachments
        editIndex=-1;editBackup=null;restoring=false
        saveDraft();focusComposer()
    }
    function startNew() {
        if (busy || !saveDraft()) return
        messageTarget=null;pageHistory=[];page = "chat"; error = ""
        request({action: "new"})
        focusComposer()
    }
    function selectChat(id, keepTarget) {
        if (busy || !saveDraft()) return
        if (!keepTarget) messageTarget=null
        pageHistory=[];page = "chat"; error = ""
        request({action: "open", id: id})
    }
    function revealMessage(id, index) {
        messageTarget={chatId:id,index:index}
        if (!current || current.id !== id) selectChat(id, true)
        openConversation()
    }
    function submit() {
        if (draft.trim() === "/permissions") {
            draftSave.stop(); draft = ""; visit("permissions"); pin(); return
        }
        if (peek.enabled && busy && draft.trim()) {
            saveDraft()
            request({action:"peek_redirect",text:draft})
            return
        }
        if (busy && draft.trim()) {
            notice = "Reply still running. Press Stop to interrupt, or wait to send."; noticeClear.restart(); return
        }
        if (busy || terminalOpen || !draft.trim()) return
        pin(); draftSave.stop(); error = ""
        request({action: "send", text: draft, source:draftSource,attachments: attachments, edit: editIndex,
            replaceAttachments:editIndex >= 0,nextDraft:editBackup,excludeScreen:excludeScreen})
    }
    function edit(index) {
        if (busy) return
        if (editIndex === index) {focusComposer();return}
        if (editIndex >= 0) {notice="Finish or cancel your current edit first.";noticeClear.restart();return}
        if (editIndex < 0) {
            saveDraft()
            editBackup = {text:draft,source:draftSource,attachments:attachments.slice()}
        }
        editIndex = index; draft = messages[index].text
        attachments = (messages[index].attachments || []).map(a=>a.path)
        draftSource=messages[index].source || ({})
        page = "chat"; focusComposer()
    }
    function retry() {
        if (busy) return
        for (var i = messages.length - 1; i >= 0; --i) {
            if (messages[i].role === "user") {
                error = ""
                request({action: "send", text: messages[i].text, source:messages[i].source || ({}),attachments: [], edit: i})
                return
            }
        }
    }
    function addAttachment(path) {
        if (attachments.length >= 8) { error = "Attach up to 8 files per message."; return }
        var value = String(path)
        if (attachments.indexOf(value) < 0) attachments = attachments.concat([value])
        pin()
    }
    function removeAttachment(index) { var list = attachments.slice(); list.splice(index, 1); attachments = list }
    function receive(event) {
        if (event.type && event.type.indexOf("workspace_") === 0) {
            workspaceModel.consume(event)
        } else if (event.type && event.type.indexOf("thoughts") === 0) {
            thoughtsModel.consume(event)
        } else if (event.type === "peek_wake") {
            if (!companionScreen) companionScreen=Hyprland.focusedMonitor ? Hyprland.focusedMonitor.name : Quickshell.screens[0].name
        } else if (event.type === "peek_hide") {
            root.openScreen=""; root.pinned=false
        } else if (event.type === "peek") {
            peek = Object.assign({},peek,event.state)
        } else if (event.type === "peek_pointer") {
            aiPointer = event.pointer
            if (aiPointer.visible) pointerClear.restart()
        } else if (event.type === "state") {
            var changed = (!current && event.current) || (current && event.current && current.id !== event.current.id)
            var began = !busy && event.busy
            var finished = busy && !event.busy
            restoring = true
            meta = event.meta; chats = event.chats; current = event.current; busy = event.busy
            if (changed || began) {
                draft = current ? (current.draft || "") : ""
                draftSource=current ? (current.draftSource || ({})) : ({})
                attachments = current ? (current.draftAttachments || []) : []; editIndex = -1; editBackup = null
                excludeScreen=false
                var savedEdit=current && current.draftEdit
                if (savedEdit && !busy) {
                    var index=savedEdit.messageId ? messages.findIndex(m=>m.id === savedEdit.messageId) : savedEdit.index
                    if (index>=0 && index<messages.length && messages[index].role === "user") {
                        editBackup={text:draft,source:draftSource,attachments:attachments.slice()}
                        editIndex=index;draft=savedEdit.text;draftSource=savedEdit.source || ({})
                        attachments=savedEdit.attachments || []
                    }
                }
            }
            if (began) { streamingText = ""; streamingModel = ""; streamingTools = []; activity = "Thinking…" }
            if (finished && !openScreen) {
                notice = "Reply ready"
                var last = messages.length ? messages[messages.length - 1] : null
                if (!peek.enabled && last && last.role === "assistant" && !last.error && last.status !== "stopped")
                    announce("Reply ready", current ? current.title : "")
            }
            restoring = false
            if (finished && draft.length) draftSave.restart()
        } else if (event.type === "delta") {
            if (current && current.id === event.id) {
                streamingText = event.text; streamingModel = event.model; activity = event.status
                streamingTools = event.tools || []
            }
        } else if (event.type === "agent_ui") {
            agentRequests = event.requests
            if (agentRequests.length && openScreen) pin()
        } else if (event.type === "settings_saved") {
            settingsSaved()
        } else if (event.type === "agent_draft") {
            draft = event.text
        } else if (event.type === "redirect_accepted") {
            if (draft === event.text) {draft="";draftSource=({});saveDraft()}
        } else if (event.type === "meta") {
            meta = event.meta
        } else if (event.type === "error") {
            error = event.text
        } else if (event.type === "notice") {
            notice = event.text; noticeClear.restart()
        } else if (event.type === "attachment") {
            addAttachment(event.path)
        }
    }
    onDraftChanged: if (!restoring) draftSave.restart()
    onDraftSourceChanged: if (!restoring) draftSave.restart()
    onAttachmentsChanged: if (!restoring) draftSave.restart()
    onEditIndexChanged: if (!restoring) draftSave.restart()
    Timer { id: draftSave; interval: 500; onTriggered: root.saveDraft() }
    Timer { id: dismiss; interval: 420; onTriggered: if (!root.pinned && !root.hoveredScreen) root.close() }
    Timer { id: noticeClear; interval: 3000; onTriggered: root.notice = "" }
    Timer { id: pointerClear; interval: 1800; onTriggered: root.aiPointer = ({visible:false}) }
    Timer { interval: 3000; repeat: true; running: root.connected; onTriggered: root.request({action: "ping"}) }
    Timer { id: restart; interval: 2000; onTriggered: backend.running = true }

    Process {
        id: backend
        command: ["env", "PYTHONDONTWRITEBYTECODE=1", "python3", "-B", "-u", decodeURIComponent(Qt.resolvedUrl("backend.py").toString().replace("file://", ""))]
        stdinEnabled: true
        running: true
        onStarted: { root.connected = true; root.error = ""; root.request({action:"peek_status"}) }
        stdout: SplitParser {
            onRead: data => {
                try { root.receive(JSON.parse(data)) }
                catch (e) { console.warn("Side Chat event:", e) }
            }
        }
        stderr: SplitParser { onRead: data => console.warn("Side Chat:", data) }
        onExited: {
            root.connected = false; root.busy = false; root.agentRequests = []
            root.peek = Object.assign({},root.peek,{enabled:false,ready:false,listening:false,speaking:false}); root.aiPointer = ({visible:false})
            root.error = "The chat connection closed. Reconnecting…"
            restart.restart()
        }
    }
    IpcHandler {
        target: "blr.side-chat"
        function open(): void { root.open() }
        function openOnScreen(name: string): void { root.show(name, true) }
        function close(): void { root.close() }
        function toggle(): void { root.toggle() }
        function newChat(): void { root.open(); root.startNew() }
        function thoughts(): void { thoughtsModel.toggle() }
        function thoughtsTodos(): void { thoughtsModel.switchKind("todo");thoughtsModel.show() }
        function thoughtsNew(): void { thoughtsModel.newNote() }
        function thoughtsCaptureStart(): void { thoughtsModel.startCapture("note") }
        function thoughtsCaptureStop(): void { thoughtsModel.stopCapture() }
        function thoughtsCaptureCancel(): void { thoughtsModel.close() }
        function captureSelection(): void { workspaceModel.capture(false) }
        function workspaceSearch(): void { workspaceModel.toggleSearch() }
        function keypad(action:string): void {Keypad.run(root,action)}
        function reminderAction(identity:string, operation:string, due:string): void {root.request({action:"thoughts_reminder_action",id:identity,operation:operation,due:due})}
        function peek(): void { root.setPeek(!root.peek.enabled, false) }
        function peekOpen(): void { root.setPeek(true) }
        function peekOnScreen(name: string): void {
            if(!Quickshell.screens.some(s=>s.name === name)) return
            if(!root.peek.enabled) root.setPeek(true)
            root.companionScreen=name
        }
        function microphone(source: string): void { root.request({action:"peek_settings",settings:{source:source}}) }
        function peekListening(enabled: bool): void { root.request({action:"peek_listen",enabled:enabled}) }
        function peekToggleMicrophone(): void {
            root.toggleMicrophone()
        }
        function peekPreferences(settings: string): void {
            try { root.request({action:"peek_settings",settings:JSON.parse(settings)}) }
            catch (e) { root.error="Invalid Peek preferences: " + e }
        }
        function peekSettings(): void { root.openPeekSettings() }
        function companionControls(): void { if(root.peek.enabled) root.companionControlsRequested() }
        function stop(): void { root.request({action:"peek_stop"}) }
        function status(): string { return JSON.stringify({uiVersion:root.uiVersion,uiSource:String(Qt.resolvedUrl("Main.qml")),connected: root.connected, busy: root.busy, agent: root.meta.agent, conversationAgent:root.current ? root.current.agent : "", agentLabel:root.agentName, open: root.openScreen, page:root.page,companionScreen:root.companionScreen, appearance:root.meta.appearance || {outline:true}, bashApproval:root.current ? (root.current.bashApproval || "ask") : "ask", peek:root.peek, thoughts:{open:thoughtsModel.openScreen,phase:thoughtsModel.voicePhase,counts:thoughtsModel.counts}}) }
    }
    ThoughtsModel { id:thoughtsModel;chat:root }
    WorkspaceModel {id:workspaceModel;chat:root}
    Variants {
        model: Quickshell.screens
        ChatWindow { required property var modelData; screen: modelData; chat: root }
    }
    Variants {
        model: Quickshell.screens
        AgentPointer { required property var modelData; screen: modelData; chat: root }
    }
    Variants {
        model: Quickshell.screens
        CompanionWindow { required property var modelData; screen: modelData; chat: root }
    }
    Connections {
        target: Quickshell
        function onScreensChanged() {
            if (!Quickshell.screens.some(s=>s.name === root.companionScreen) && Quickshell.screens.length)
                root.companionScreen=Quickshell.screens[0].name
            if (root.openScreen && !Quickshell.screens.some(s=>s.name === root.openScreen) && Quickshell.screens.length)
                root.openScreen=Quickshell.screens[0].name
        }
    }
}
