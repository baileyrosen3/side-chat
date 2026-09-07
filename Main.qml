import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Hyprland
import qs.Commons

Scope {
    id: root
    property var shell: null
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
    property string draft: ""
    property string page: "chat"
    property string activity: "Thinking…"
    property string streamingText: ""
    property string streamingModel: ""
    property var streamingTools: []
    property var agentRequests: []
    property var jarvis: ({enabled:false,ready:false,listening:false,speaking:false,stage:"off",caption:"",partial:"",inputLevel:0,outputLevel:0,scope:"desktop",handsFree:true,muted:false,reducedMotion:false,voice:"alba",devices:[]})
    property var aiPointer: ({visible:false})
    readonly property bool nativeSession: (meta.nativeAgents || []).indexOf(current ? current.agent : meta.agent) >= 0
    readonly property bool terminalOpen: !!(current && current.terminalOpen)
    readonly property string agentName: current && current.agent ? agentLabel(current.agent) : meta.agentName
    readonly property var messages: current ? current.messages : []
    signal focusComposer()
    signal companionControlsRequested()

    function agentLabel(id) {
        return ({omp: "Oh My Pi", pi: "Pi", claude: "Claude", codex: "Codex", opencode: "OpenCode", gemini: "Gemini", copilot: "Copilot", crush: "Crush", grok: "Grok"})[id] || id
    }
    function request(data) {
        if (!connected) { error = "Reconnecting to chat…"; return }
        backend.write(JSON.stringify(data) + "\n")
    }
    function show(screenName, persistent) {
        dismiss.stop()
        openScreen = screenName
        if (persistent) { pinned = true; Qt.callLater(root.focusComposer) }
        request({action: "ping"})
    }
    function open() {
        var focused = Hyprland.focusedMonitor
        show(focused ? focused.name : Quickshell.screens[0].name, true)
    }
    function close() {
        openScreen = ""; pinned = false
    }
    function setJarvis(enabled, reopen) {
        if (enabled) {
            var focused=Hyprland.focusedMonitor
            companionScreen=openScreen || (focused ? focused.name : Quickshell.screens[0].name)
            close(); page="chat"
        } else if (reopen !== false) openConversation()
        request({action:"jarvis",enabled:enabled,accent:String(Color.accent)})
    }
    function openConversation() { show(companionScreen || (Hyprland.focusedMonitor ? Hyprland.focusedMonitor.name : Quickshell.screens[0].name),true); page="chat" }
    function openJarvisSettings() { openConversation(); page="jarvis_settings" }
    function toggle() { openScreen ? close() : open() }
    function hover(screenName, inside) {
        if (jarvis.enabled && !openScreen) return
        if (inside) {
            hoveredScreen = screenName
            show(screenName, false)
        } else if (hoveredScreen === screenName) {
            hoveredScreen = ""
            if (!pinned) dismiss.restart()
        }
    }
    function pin() { pinned = true; dismiss.stop() }
    function startNew() {
        if (busy) return
        draftSave.stop()
        draft = ""; attachments = []; editIndex = -1; page = "chat"; error = ""
        request({action: "new"})
        focusComposer()
    }
    function selectChat(id) {
        draftSave.stop()
        request({action: "draft", text: draft})
        attachments = []; editIndex = -1; page = "chat"; error = ""
        request({action: "open", id: id})
    }
    function submit() {
        if (jarvis.enabled && busy && draft.trim()) {
            request({action:"jarvis_say",text:draft}); draft=""; return
        }
        if (busy || terminalOpen || !draft.trim()) return
        pin(); draftSave.stop(); error = ""
        request({action: "send", text: draft, attachments: attachments, edit: editIndex})
    }
    function edit(index) {
        if (busy) return
        editIndex = index; draft = messages[index].text; attachments = []
        page = "chat"; focusComposer()
    }
    function retry() {
        if (busy) return
        for (var i = messages.length - 1; i >= 0; --i) {
            if (messages[i].role === "user") {
                error = ""
                request({action: "send", text: messages[i].text, attachments: [], edit: i})
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
        if (event.type === "jarvis_wake") {
            if (!companionScreen) companionScreen=Hyprland.focusedMonitor ? Hyprland.focusedMonitor.name : Quickshell.screens[0].name
        } else if (event.type === "jarvis_hide") {
            root.openScreen=""; root.pinned=false
        } else if (event.type === "jarvis") {
            jarvis = Object.assign({},jarvis,event.state)
        } else if (event.type === "jarvis_pointer") {
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
                attachments = []; editIndex = -1
            }
            if (began) { streamingText = ""; streamingModel = ""; streamingTools = []; activity = "Thinking…" }
            if (finished && !openScreen) { notice = "Reply ready" }
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
        } else if (event.type === "agent_draft") {
            draft = event.text
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
    onDraftChanged: if (!restoring && !busy && editIndex < 0) draftSave.restart()
    Timer { id: draftSave; interval: 500; onTriggered: root.request({action: "draft", text: root.draft}) }
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
        onStarted: { root.connected = true; root.error = ""; root.request({action:"jarvis_status"}) }
        stdout: SplitParser {
            onRead: data => {
                try { root.receive(JSON.parse(data)) }
                catch (e) { console.warn("Side Chat event:", e) }
            }
        }
        stderr: SplitParser { onRead: data => console.warn("Side Chat:", data) }
        onExited: {
            root.connected = false; root.busy = false; root.agentRequests = []
            root.jarvis = Object.assign({},root.jarvis,{enabled:false,ready:false,listening:false,speaking:false}); root.aiPointer = ({visible:false})
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
        function jarvis(): void { root.setJarvis(!root.jarvis.enabled) }
        function jarvisOnScreen(name: string): void {
            if(!Quickshell.screens.some(s=>s.name === name)) return
            if(!root.jarvis.enabled) root.setJarvis(true)
            root.companionScreen=name
        }
        function microphone(source: string): void { root.request({action:"jarvis_settings",settings:{source:source}}) }
        function jarvisListening(enabled: bool): void { root.request({action:"jarvis_listen",enabled:enabled}) }
        function jarvisPreferences(settings: string): void {
            try { root.request({action:"jarvis_settings",settings:JSON.parse(settings)}) }
            catch (e) { root.error="Invalid Jarvis preferences: " + e }
        }
        function jarvisSettings(): void { root.openJarvisSettings() }
        function companionControls(): void { if(root.jarvis.enabled) root.companionControlsRequested() }
        function stop(): void { root.request({action:"jarvis_stop"}) }
        function status(): string { return JSON.stringify({uiVersion:"1.9.3",uiSource:String(Qt.resolvedUrl("Main.qml")),connected: root.connected, busy: root.busy, agent: root.meta.agent, open: root.openScreen, page:root.page,companionScreen:root.companionScreen, appearance:root.meta.appearance || {outline:true}, bashApproval:root.current ? (root.current.bashApproval || "ask") : "ask", jarvis:root.jarvis}) }
    }
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
        }
    }
}
