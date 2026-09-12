import QtQuick
import "Thoughts.js" as Logic

Item {
    id: root
    required property var chat
    readonly property string openScreen: (chat.page === "notes" || chat.page === "todos") ? chat.openScreen : ""
    property string kind: "note"
    property var notes: []
    property var drafts: ({})
    property var clearedDrafts: ({})
    property string directory: ""
    property string query: ""
    property bool searching: false
    property bool showCompleted: false
    property string key: ""
    property string noteId: ""
    property string revision: ""
    property string body: ""
    property string title: ""
    property var tags: []
    property string savedBody: ""
    property real due: 0
    property real savedDue: 0
    property string dueText: ""
    property bool reminderEditing: false
    property var source: ({})
    property var duePreview: ({})
    property string dueError: ""
    property int reminderSerial: 0
    property int previewSerial: -1
    readonly property bool dateCandidate: kind === "todo" && (!!dueText.trim() || (!noteId && !due && /\b(today|tomorrow|noon|midnight|monday|tuesday|wednesday|thursday|friday|saturday|sunday|\d{4}-\d{2}-\d{2}|at\s+\d|in\s+\d)/i.test(body)))
    readonly property real effectiveDue: previewSerial === reminderSerial && duePreview.due ? duePreview.due : due
    readonly property string dueLabel: effectiveDue ? (duePreview.due === effectiveDue ? duePreview.label : Qt.formatDateTime(new Date(effectiveDue*1000), "ddd, MMM d · h:mm ap")) : ""
    property bool loading: false
    property bool initialized: false
    property bool saving: false
    property string pendingId: ""
    property int serial: 0
    property string saveStatus: ""
    property string error: ""
    property string notice: ""
    property string undoId: ""
    property string voicePhase: "idle"
    property real voiceLevel: 0
    property int voiceSeconds: 0
    property real savedAt: 0
    readonly property bool recording: voicePhase === "starting" || voicePhase === "recording" || voicePhase === "transcribing"
    readonly property bool dirty: !!key && (body !== savedBody || due !== savedDue || !!dueText.trim())
    readonly property var rows: Logic.rows(notes,drafts,kind,query,false).filter(n=>n.id || n.key!==key)
    readonly property var completed: kind === "todo" ? Logic.rows(notes,drafts,kind,query,true) : []
    readonly property var counts: ({notes:notes.filter(n=>!n.trashed && n.kind !== "todo").length,
        todo:notes.filter(n=>!n.trashed && n.kind === "todo" && !n.done).length})
    signal focusEditor()

    function freshKey() { return "draft-" + Date.now() + "-" + Math.random().toString(16).slice(2) }
    function draftData() { return {key:key,id:noteId,title:title,body:body,tags:tags,revision:revision,kind:kind,due:due,dueText:dueText,source:source} }
    function changedReminder() {
        if(loading) return
        reminderSerial++;duePreview=({});dueError=""
        if(kind === "todo" && (dueText.trim() || (!noteId && !due))) reminderTimer.restart()
    }
    function clearReminder() {
        if(duePreview.due && !dueText.trim()) body=duePreview.body
        due=0;dueText="";duePreview=({});dueError="";reminderEditing=false
    }
    function request(command) {
        if (!chat.connected) {error="Reconnecting. Your draft is still here.";return false}
        chat.request(command);return true
    }
    function show() {
        chat.openThoughts(kind)
        request({action:"thoughts_list"})
        Qt.callLater(root.focusEditor)
    }
    function toggle() { if (openScreen) close(); else show() }
    function close() {
        stash()
        if (recording) request({action:"thoughts_voice_cancel"})
        chat.close()
    }
    function resetInput() {
        loading=true;key=freshKey();noteId="";revision="";body="";title="";tags=[];savedBody=""
        due=0;savedDue=0;dueText="";source=({});duePreview=({});dueError="";reminderEditing=false;reminderSerial++;reminderTimer.stop()
        saveStatus="";serial=0;loading=false
    }
    function newThought(text, origin) {
        if (recording || saving) return
        stash();resetInput();error=""
        if (text) body=String(text)
        source=origin || ({})
        Qt.callLater(root.focusEditor)
    }
    function newNote() {
        if(recording || saving) return
        switchKind("note");newThought();show()
    }
    function switchKind(next) {
        if (kind===next || recording || saving) return
        stash();resetInput();kind=next;query="";error="";showCompleted=false
        var recovered=Object.values(drafts).filter(d=>!d.id && (d.kind || "note")===next).sort((a,b)=>b.updated-a.updated)
        if(recovered.length) select(recovered[0])
        Qt.callLater(root.focusEditor)
    }
    function select(note) {
        if (recording || saving) return
        stash();loading=true
        var recovered=note.isDraft || (note.key && drafts[note.key]) ? note : Object.values(drafts).find(d=>d.id && d.id===note.id)
        var selected=recovered || note
        key=recovered ? selected.key : freshKey();noteId=selected.id || "";revision=selected.revision || ""
        body=selected.body || "";title=selected.title || "";tags=selected.tags || []
        due=Number(selected.due)||0;savedDue=due;dueText=selected.dueText || "";source=selected.source || ({})
        duePreview=({});reminderEditing=!!dueText
        savedBody=recovered ? "" : body
        saveStatus=recovered ? "Draft recovered" : "Editing";error="";serial=0;loading=false
        changedReminder()
        Qt.callLater(root.focusEditor)
    }
    function stash() {
        draftTimer.stop()
        if (!key || recording || saving) return
        if (!body.trim() && !noteId) {
            if (drafts[key] || clearedDrafts[key]) {
                var cleared=Object.assign({},clearedDrafts);cleared[key]=true;clearedDrafts=cleared
                var remaining=Object.assign({},drafts);delete remaining[key];drafts=remaining
                if(request({action:"thoughts_draft",key:key,discard:true,serial:serial})) saveStatus="Draft cleared"
            }
            return
        }
        if (!dirty) return
        var retained=Object.assign({},clearedDrafts);delete retained[key];clearedDrafts=retained
        var d=Object.assign(draftData(),{updated:Date.now()/1000})
        var next=Object.assign({},drafts);next[key]=d;drafts=next
        if (request(Object.assign({},d,{action:"thoughts_draft",serial:serial}))) saveStatus="Saving draft…"
    }
    function save(copy) {
        if (recording || saving || !body.trim()) return
        if(dateCandidate && previewSerial!==reminderSerial) {reminderTimer.restart();error="Check the reminder time below, then save.";return}
        if(dateCandidate && dueError) {error=dueError;return}
        stash()
        var command=Object.assign(draftData(),{action:"thoughts_save",due:effectiveDue})
        if(effectiveDue && duePreview.due && !dueText.trim()) command.body=duePreview.body
        if(!command.body.trim()) {error="Add what you need to do before the reminder time.";return}
        if(effectiveDue && effectiveDue!==savedDue && effectiveDue*1000<=Date.now()) {error="That time has passed. Choose another reminder.";return}
        if(copy) {command.id="";command.revision=""}
        saving=request(command)
        if(saving) {saveStatus="Saving…";error=""}
    }
    function modify(note, operation) {
        if (!note || pendingId || recording || saving) return
        if (note.isDraft && !note.id) {
            if(operation === "trash") {
                if(request(Object.assign({},note,{action:"thoughts_discard"}))) pendingId=note.key
            }
            return
        }
        if (note.isDraft || (note.id === noteId && dirty)) {error="Save your edit first.";return}
        if(request({action:"thoughts_modify",id:note.id,revision:note.revision,operation:operation})) pendingId=note.id
    }
    function undoTrash() {
        var note=notes.find(n=>n.id===undoId && n.trashed)
        if(note) modify(note,"restore")
    }
    function discuss(note) {
        if(recording || saving) return
        stash()
        var text=note ? note.body : body
        chat.draft=(chat.draft.trim() ? chat.draft+"\n\n" : "")+"Discuss this note with me:\n\n"+text
        chat.draftSource={kind:"note",id:note ? (note.id || "") : noteId,label:text.split("\n")[0].slice(0,80)}
        chat.openConversation()
    }
    function startCapture(captureKind) {
        if(recording || saving) return
        if(captureKind) switchKind(captureKind)
        newThought();show();voiceSeconds=0;voiceLevel=0
        if(request({action:"thoughts_voice_start",key:key,kind:kind})) voicePhase="starting"
    }
    function stopCapture() { if(recording) request({action:"thoughts_voice_stop"}) }
    function toggleCapture(captureKind) {
        if(recording) {
            if(voicePhase!=="transcribing") stopCapture()
            return
        }
        startCapture(captureKind)
    }
    function consume(event) {
        if(event.type === "thoughts") {
            notes=event.notes;directory=event.directory
            var local=Object.assign({},event.drafts || {})
            Object.keys(drafts).forEach(function(k) {
                if(k!==event.key && (!local[k] || drafts[k].updated>local[k].updated)) local[k]=drafts[k]
            })
            Object.keys(clearedDrafts).forEach(k=>delete local[k])
            drafts=local
            if(event.saved) {
                savedAt=Date.now()/1000
                saving=false;notice=event.saved.kind === "todo" ? "To-do added" : "Note saved"
                if(event.key===key) {draftTimer.stop();resetInput();Qt.callLater(root.focusEditor)}
                noticeTimer.restart()
            }
            if(event.modified) {
                pendingId=""
                if(event.operation === "trash") {undoId=event.modified;notice="Deleted";noticeTimer.restart()}
                else if(event.operation === "restore") {undoId="";notice="Restored";noticeTimer.restart()}
                if(event.modified===noteId && !dirty) resetInput()
            }
            if(!initialized) {
                initialized=true
                if(!key) {
                    resetInput()
                    var recovered=Object.values(drafts).filter(d=>!d.id && (d.kind || "note")===kind).sort((a,b)=>b.updated-a.updated)
                    if(recovered.length) select(recovered[0])
                }
            }
            if(event.warnings.length) error=event.warnings[0]
        } else if(event.type === "thoughts_due_preview") {
            if(event.serial===reminderSerial) {duePreview=event;previewSerial=event.serial;dueError=event.error || ""}
        } else if(event.type === "thoughts_draft_saved") {
            if(event.key===key && event.serial===serial && !saving) saveStatus="Draft saved"
        } else if(event.type === "thoughts_error") {
            error=event.text
            if(event.action === "thoughts_open_id") {chat.error=event.text;chat.open()}
            if(event.action === "thoughts_save") {saving=false;saveStatus="Save needs attention"}
            if(event.action === "thoughts_modify" || event.action === "thoughts_discard") pendingId=""
            if(event.action === "thoughts_voice_start" && voicePhase === "starting") voicePhase="idle"
        } else if(event.type === "thoughts_voice") {
            voicePhase=event.phase
            if(event.phase === "idle") {voiceLevel=0;draftTimer.restart()}
        } else if(event.type === "thoughts_level") {voiceLevel=event.level;voiceSeconds=event.seconds}
        else if(event.type === "thoughts_transcript") {
            if(event.key===key) {body=event.body;saveStatus="Draft saved";Qt.callLater(root.focusEditor)}
            var next=Object.assign({},drafts);next[event.key]=Object.assign({},event,{updated:Date.now()/1000});drafts=next
        } else if(event.type === "thoughts_open") {
            if(recording || saving) {error="Finish your current capture, then open this item.";return}
            switchKind(event.kind || "note");query=event.query || "";searching=!!query
            if(event.note) select(event.note)
            show()
        }
    }
    onBodyChanged: {
        if(!loading && key) {serial++;saveStatus=dirty ? "" : "Saved";draftTimer.restart();changedReminder()}
    }
    onDueTextChanged:if(!loading) {changedReminder();serial++;draftTimer.restart()}
    onDueChanged:if(!loading) {changedReminder();serial++;draftTimer.restart()}
    Timer {id:reminderTimer;interval:160;onTriggered:root.request({action:"thoughts_parse_due",text:root.dueText.trim() || root.body,separate:!!root.dueText.trim(),serial:root.reminderSerial})}
    onOpenScreenChanged: {
        if(openScreen) request({action:"thoughts_list"})
        else {
            stash()
            if(recording) request({action:"thoughts_voice_cancel"})
        }
    }
    Timer { id:draftTimer;interval:650;onTriggered:root.stash() }
    Timer { id:noticeTimer;interval:7000;onTriggered:{root.notice="";root.undoId=""} }
    Timer { interval:5000;repeat:true;running:!!root.openScreen && !root.recording && !root.saving && !root.pendingId;onTriggered:root.request({action:"thoughts_list"}) }
    Connections {
        target:root.chat
        function onConnectedChanged() {
            if(root.chat.connected) {
                Object.keys(root.clearedDrafts).forEach(k=>root.request({action:"thoughts_draft",key:k,discard:true}))
                root.stash();if(root.openScreen) root.request({action:"thoughts_list"})
            }
            else {root.saving=false;root.pendingId="";root.voicePhase="idle"}
        }
    }
}
