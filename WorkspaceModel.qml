import QtQuick

Item {
    id:root
    required property var chat
    property string mode:""
    property string query:""
    property var results:[]
    property bool busy:false
    property bool capturing:false
    property bool exporting:false
    property string error:""
    property string exportNotice:""
    property string captureBody:""
    property var captureSource:({})
    property int serial:0
    property int searchSerial:0
    property int captureSerial:0
    property int restoreSerial:0
    property int exportSerial:0
    signal focusInput()

    function request(command) {
        if(!chat.connected) {error="Reconnecting. Please try again.";return false}
        chat.request(command);return true
    }
    function reveal(next) {
        mode=next;chat.show(chat.openScreen || chat.thoughtsScreen(),true)
        Qt.callLater(root.focusInput)
    }
    function dismiss() {mode="";searchTimer.stop();Qt.callLater(chat.focusWorkspace)}
    function toggleSearch() {
        if(mode==="search") {dismiss();return}
        query="";results=[];error="";reveal("search");search()
    }
    function showTrash() {query="";results=[];error="";reveal("trash");search()}
    function search() {
        searchTimer.stop()
        if(mode!=="search" && mode!=="trash") return
        searchSerial=++serial
        busy=request({action:"workspace_search",serial:searchSerial,query:query,trash:mode==="trash"})
    }
    function capture(clipboard) {
        if(capturing) return
        error="";captureSerial=++serial
        // The backend reads the source selection before this drawer takes focus.
        capturing=request({action:"workspace_capture",serial:captureSerial,clipboard:!!clipboard})
        if(!capturing) reveal("capture")
    }
    function useCapture(kind) {
        if(!captureBody.trim()) return
        if(chat.thoughts.recording || chat.thoughts.saving) {error="Finish your current note capture first.";return}
        if(kind==="chat") {
            chat.draft=(chat.draft.trim() ? chat.draft+"\n\n" : "")+captureBody
            chat.draftSource=captureSource
            dismiss();chat.openConversation()
        } else {
            chat.thoughts.switchKind(kind)
            chat.thoughts.newThought(captureBody,captureSource)
            dismiss();chat.openThoughts(kind)
        }
        captureBody=""
    }
    function activate(item) {
        if(item.kind==="warning") return
        if(mode==="trash") {
            if(busy) return
            restoreSerial=++serial
            busy=request({action:"workspace_restore",serial:restoreSerial,kind:item.kind,id:item.id,revision:item.revision || ""})
            return
        }
        if(item.kind==="chat") {
            if(chat.busy && (!chat.current || chat.current.id!==item.id)) {error="Finish or stop the reply before switching conversations.";return}
            dismiss();chat.revealMessage(item.id, item.messageIndex === undefined ? -1 : item.messageIndex)
        } else {
            if(chat.thoughts.recording || chat.thoughts.saving) {error="Finish your current note capture first.";return}
            if(request({action:"thoughts_open_id",id:item.id})) dismiss()
        }
    }
    function exportTo(path) {
        if(exporting) return
        exportNotice="";error="";exportSerial=++serial
        exporting=request({action:"workspace_export",serial:exportSerial,path:path})
    }
    function consume(event) {
        if(event.type==="workspace_results" && event.serial===searchSerial) {results=event.results;busy=false}
        else if(event.type==="workspace_capture" && event.serial===captureSerial) {
            capturing=false;captureBody=event.text;captureSource=event.source;error="";reveal("capture")
        } else if(event.type==="workspace_restored" && event.serial===restoreSerial) {error="";busy=false;search()}
        else if(event.type==="workspace_exported" && event.serial===exportSerial) {exporting=false;exportNotice="Backup saved to "+event.path}
        else if(event.type==="workspace_error") {
            if(event.action==="workspace_capture" && event.serial===captureSerial) {capturing=false;error=event.text;reveal("capture")}
            else if(event.action==="workspace_export" && event.serial===exportSerial) {exporting=false;error=event.text}
            else if(event.serial===searchSerial || event.serial===restoreSerial) {busy=false;error=event.text}
        }
    }
    onQueryChanged:if(mode==="search" || mode==="trash") {searchSerial=++serial;searchTimer.restart()}
    Timer {id:searchTimer;interval:130;onTriggered:root.search()}
    Connections {
        target:root.chat
        function onConnectedChanged() {
            if(!root.chat.connected) {root.busy=false;root.capturing=false;root.exporting=false}
            else if(root.mode==="search" || root.mode==="trash") root.search()
        }
    }
}
