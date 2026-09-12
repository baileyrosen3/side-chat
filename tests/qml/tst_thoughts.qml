import QtQuick
import QtQuick.Layouts
import QtTest
import "../.."

Rectangle {
    id:scene
    width:450;height:620
    QtObject {
        id:chat
        property bool connected:true
        property string draft:""
        property var draftSource:({})
        property string page:"notes"
        property string openScreen:"fixture"
        property var requests:[]
        function request(command) {requests=requests.concat([command])}
        function open() {openScreen="fixture"}
        function close() {openScreen=""}
        function openConversation() {page="chat";open()}
        function openThoughts(kind) {thoughts.switchKind(kind);page=kind === "todo" ? "todos" : "notes";open()}
        function navigate(section) {if(section === "chat") openConversation();else openThoughts(section === "todos" ? "todo" : "note")}
    }
    ThoughtsModel {id:thoughts;chat:chat}
    ColumnLayout {
        anchors.fill:parent;spacing:12
        WorkspaceTabs {id:tabs;Layout.fillWidth:true;section:chat.page;reducedMotion:true;onChosen:section=>chat.navigate(section)}
        ThoughtsView {id:view;Layout.fillWidth:true;Layout.fillHeight:true;model:thoughts;reducedMotion:true;active:!!thoughts.openScreen;visible:active}
        Item {visible:chat.page === "chat";Layout.fillWidth:true;Layout.fillHeight:true}
    }
    TestCase {
        name:"Thoughts"
        when:windowShown
        function note(id,body,kind,done) {return {id:id,body:body,title:"",tags:[],kind:kind || "note",done:!!done,created:"2026-09-11T12:00:00Z",revision:"r"+id,trashed:false}}
        function init() {
            failOnWarning(/.?/)
            thoughts.loading=true
            thoughts.notes=[note("a","First original"),note("b","Second original"),note("c","Get groceries","todo")]
            thoughts.drafts={};thoughts.kind="note";thoughts.query="";thoughts.key="";thoughts.body="";thoughts.title="";thoughts.tags=[];thoughts.savedBody=""
            thoughts.saving=false;thoughts.pendingId="";thoughts.voicePhase="idle";thoughts.error="";thoughts.notice="";thoughts.searching=false;thoughts.showCompleted=false
            thoughts.loading=false;thoughts.initialized=true
            chat.page="notes";chat.openScreen="fixture"
            chat.requests=[];chat.draft="";scene.width=450;scene.height=620
            thoughts.resetInput()
        }
        function test_shared_navigation_opens_notes_and_todos() {
            compare(findChild(tabs,"workspace-tab-notes").visible,true)
            mouseClick(findChild(tabs,"workspace-tab-todos"))
            compare(thoughts.kind,"todo");compare(thoughts.rows.length,1)
            compare(findChild(view,"thoughts-body").visible,true)
            compare(findChild(view,"thoughts-library").visible,true)
        }
        function test_global_new_note_always_targets_notes_and_keeps_task_draft() {
            chat.openThoughts("todo");thoughts.body="Unfinished task"
            var previous=thoughts.key
            thoughts.newNote()
            compare(chat.page,"notes");compare(thoughts.kind,"note");compare(thoughts.body,"")
            compare(thoughts.drafts[previous].body,"Unfinished task")
        }
        function test_global_dictation_is_a_note_and_early_release_stops_it() {
            chat.openThoughts("todo");thoughts.body="Keep this task"
            thoughts.startCapture("note");thoughts.stopCapture()
            compare(chat.page,"notes");compare(thoughts.kind,"note")
            verify(chat.requests.some(c=>c.action==="thoughts_voice_start" && c.kind==="note"))
            verify(chat.requests.some(c=>c.action==="thoughts_voice_stop"))
            verify(Object.values(thoughts.drafts).some(d=>d.body==="Keep this task"))
        }
        function test_tap_listening_data() {return [{tag:"note",kind:"note",page:"notes"},{tag:"todo",kind:"todo",page:"todos"}]}
        function test_tap_listening(data) {
            thoughts.body="Keep my unfinished writing"
            thoughts.toggleCapture(data.kind)
            compare(chat.page,data.page);compare(thoughts.kind,data.kind)
            compare(thoughts.voicePhase,"starting")
            var key=thoughts.key
            // The second tap must stop even before the recorder acknowledges startup.
            thoughts.toggleCapture(data.kind)
            compare(chat.requests.filter(c=>c.action==="thoughts_voice_start").length,1)
            compare(chat.requests.filter(c=>c.action==="thoughts_voice_stop").length,1)
            thoughts.consume({type:"thoughts_voice",phase:"transcribing"})
            thoughts.toggleCapture(data.kind)
            compare(chat.requests.filter(c=>c.action==="thoughts_voice_start").length,1)
            compare(chat.requests.filter(c=>c.action==="thoughts_voice_stop").length,1)
            thoughts.consume({type:"thoughts_transcript",key:key,kind:data.kind,body:"Captured words"})
            thoughts.consume({type:"thoughts_voice",phase:"idle"})
            compare(thoughts.body,"Captured words");compare(thoughts.kind,data.kind)
            verify(Object.values(thoughts.drafts).some(d=>d.body==="Keep my unfinished writing"))
            verify(!chat.requests.some(c=>c.action==="thoughts_save" || c.action==="send"))
        }
        function test_other_voice_key_finishes_original_capture_without_changing_destination() {
            thoughts.toggleCapture("note");var key=thoughts.key
            thoughts.consume({type:"thoughts_voice",phase:"recording"})
            thoughts.toggleCapture("todo")
            compare(thoughts.kind,"note");compare(thoughts.key,key);compare(chat.page,"notes")
            compare(chat.requests.filter(c=>c.action==="thoughts_voice_start").length,1)
            compare(chat.requests.filter(c=>c.action==="thoughts_voice_stop").length,1)
        }
        function test_reminder_preview_is_required_before_saving_and_old_results_ignored() {
            chat.openThoughts("todo");thoughts.body="Call Alex tomorrow at 3pm";chat.requests=[]
            thoughts.save(false)
            verify(!chat.requests.some(c=>c.action==="thoughts_save"))
            var pending=thoughts.reminderSerial
            thoughts.body="Call Alex Friday at 9am"
            thoughts.consume({type:"thoughts_due_preview",serial:pending,body:"Call Alex",due:Date.now()/1000+3600,label:"Wrong date",error:""})
            compare(thoughts.effectiveDue,0)
            var due=Date.now()/1000+86400
            thoughts.consume({type:"thoughts_due_preview",serial:thoughts.reminderSerial,body:"Call Alex",due:due,label:"Friday · 9am",error:""})
            compare(findChild(view,"thoughts-due-preview").text,"Friday · 9am")
            thoughts.save(false)
            var command=chat.requests.find(c=>c.action==="thoughts_save")
            verify(!!command);compare(command.body,"Call Alex");compare(command.due,due)
        }
        function test_existing_reminder_survives_body_edit_and_can_be_removed() {
            chat.openThoughts("todo")
            var task=Object.assign(note("due","Call Alex","todo"),{due:Date.now()/1000+3600})
            thoughts.select(task);thoughts.body="Call Alex about lunch"
            compare(thoughts.effectiveDue,task.due);verify(thoughts.dirty)
            thoughts.clearReminder();compare(thoughts.effectiveDue,0);verify(thoughts.dirty)
            thoughts.save(false)
            compare(chat.requests.filter(c=>c.action==="thoughts_save").pop().due,0)
        }
        function test_source_links_and_reminders_survive_draft_recovery() {
            chat.openThoughts("todo")
            thoughts.newThought("Call Alex",{kind:"chat",id:"conversation",label:"Planning"})
            thoughts.dueText="tomorrow at 3pm";thoughts.stash()
            var draft=thoughts.drafts[thoughts.key]
            thoughts.newThought();thoughts.select(draft)
            compare(thoughts.source.id,"conversation");compare(thoughts.dueText,"tomorrow at 3pm")
        }
        function test_open_search_result_keeps_unsaved_draft() {
            thoughts.body="Unfinished note";var key=thoughts.key
            thoughts.consume({type:"thoughts_open",kind:"todo",note:note("target","Found task","todo")})
            compare(chat.page,"todos");compare(thoughts.noteId,"target")
            compare(thoughts.drafts[key].body,"Unfinished note")
        }
        function test_chat_and_notes_share_navigation_and_preserve_both_drafts() {
            chat.draft="Unsent chat question";thoughts.body="Unfinished note"
            var originalKey=thoughts.key
            mouseClick(findChild(tabs,"workspace-tab-chat"))
            compare(chat.page,"chat");compare(thoughts.openScreen,"");compare(view.visible,false)
            verify(chat.requests.some(c=>c.action === "thoughts_draft" && c.body === "Unfinished note"))
            mouseClick(findChild(tabs,"workspace-tab-notes"))
            compare(thoughts.openScreen,"fixture");compare(view.visible,true)
            compare(thoughts.key,originalKey);compare(thoughts.body,"Unfinished note");compare(chat.draft,"Unsent chat question")
            verify(!chat.requests.some(c=>c.action === "send" || c.action === "new"))
        }
        function test_hidden_notes_do_not_handle_chat_shortcuts() {
            thoughts.body="Do not save from Chat"
            chat.openConversation();chat.requests=[]
            keyClick(Qt.Key_Return,Qt.ControlModifier)
            verify(!chat.requests.some(c=>c.action === "thoughts_save"))
        }
        function test_leaving_note_capture_cancels_only_note_recording() {
            thoughts.startCapture();compare(thoughts.voicePhase,"starting")
            chat.openConversation()
            verify(chat.requests.some(c=>c.action === "thoughts_voice_cancel"))
            verify(!chat.requests.some(c=>c.action === "peek" || c.action === "send"))
        }
        function test_peek_navigation_selects_the_requested_kind_and_keeps_search() {
            thoughts.consume({type:"thoughts_open",kind:"todo",query:"groceries"})
            compare(chat.page,"todos");compare(thoughts.kind,"todo");compare(thoughts.query,"groceries")
            thoughts.consume({type:"thoughts_open",kind:"note",query:"original"})
            compare(chat.page,"notes");compare(thoughts.kind,"note");compare(thoughts.query,"original")
        }
        function test_navigation_recovers_unsaved_edit_and_independent_new_draft() {
            thoughts.select(thoughts.notes[0]);thoughts.body="Unfinished edit"
            var originalKey=thoughts.key
            thoughts.select(thoughts.notes[1])
            compare(chat.requests[0].action,"thoughts_draft")
            compare(chat.requests[0].body,"Unfinished edit")
            thoughts.newThought("Another idea")
            var newKey=thoughts.key
            thoughts.select(thoughts.notes[0])
            compare(thoughts.body,"Unfinished edit");compare(thoughts.key,originalKey)
            verify(thoughts.dirty);compare(thoughts.drafts[newKey].body,"Another idea")
        }
        function test_new_draft_restores_after_tab_switch_and_restart() {
            thoughts.body="Keep this unfinished note"
            var originalKey=thoughts.key
            thoughts.switchKind("todo");thoughts.switchKind("note")
            compare(thoughts.key,originalKey);compare(thoughts.body,"Keep this unfinished note");verify(thoughts.dirty)
            var recovered=thoughts.drafts
            thoughts.loading=true;thoughts.key="";thoughts.body="";thoughts.loading=false;thoughts.initialized=false
            thoughts.consume({type:"thoughts",notes:[],drafts:recovered,directory:"/tmp/notes",warnings:[]})
            compare(thoughts.key,originalKey);verify(thoughts.dirty)
            verify(findChild(view,"thoughts-save").enabled)
        }
        function test_save_keeps_draft_until_ack_then_clears_composer() {
            thoughts.body="Changed"
            thoughts.save(false)
            compare(thoughts.saving,true);verify(thoughts.dirty)
            thoughts.consume({type:"thoughts_error",text:"Disk full",action:"thoughts_save"})
            compare(thoughts.saving,false);compare(thoughts.body,"Changed");verify(thoughts.dirty)
            thoughts.save(false)
            var saved=note("new","Changed")
            thoughts.consume({type:"thoughts",notes:thoughts.notes.concat([saved]),drafts:{},directory:"/tmp/notes",warnings:[],saved:saved,key:thoughts.key})
            compare(thoughts.body,"");compare(thoughts.saving,false)
            verify(thoughts.rows.some(n=>n.body==="Changed"))
        }
        function test_todo_enter_adds_and_note_enter_is_a_newline() {
            thoughts.switchKind("todo")
            var body=findChild(view,"thoughts-body")
            body.forceActiveFocus();keyClick(Qt.Key_A);keyClick(Qt.Key_B);keyClick(Qt.Key_C)
            keyClick(Qt.Key_Return)
            verify(chat.requests.some(c=>c.action === "thoughts_save" && c.body === "abc" && c.kind === "todo"))
            thoughts.saving=false;thoughts.resetInput();thoughts.switchKind("note");chat.requests=[]
            body.forceActiveFocus();keyClick(Qt.Key_A);keyClick(Qt.Key_Return);keyClick(Qt.Key_B)
            compare(thoughts.body,"a\nb")
            verify(!chat.requests.some(c=>c.action === "thoughts_save"))
        }
        function test_completed_task_moves_out_of_active_list_and_is_reversible() {
            thoughts.switchKind("todo")
            var task=thoughts.rows[0]
            thoughts.modify(task,"complete")
            compare(chat.requests[chat.requests.length-1].operation,"complete")
            var done=Object.assign({},task,{done:true,revision:"done"})
            thoughts.consume({type:"thoughts",notes:[done],drafts:{},directory:"/tmp/notes",warnings:[],modified:task.id,operation:"complete"})
            compare(thoughts.rows.length,0);compare(thoughts.completed.length,1)
            thoughts.modify(done,"complete")
            compare(chat.requests[chat.requests.length-1].revision,"done")
        }
        function test_discuss_prepares_composer_without_sending() {
            chat.draft="Existing question"
            thoughts.discuss(thoughts.notes[0])
            verify(chat.draft.indexOf("Existing question")===0)
            verify(chat.draft.indexOf("First original")>0)
            compare(chat.page,"chat");compare(chat.openScreen,"fixture");compare(view.visible,false)
            verify(!chat.requests.some(c=>c.action === "send"))
        }
        function test_phone_layout_keeps_save_inside_panel() {
            scene.width=336;scene.height=600;wait(50)
            thoughts.body="Quick note"
            var save=findChild(view,"thoughts-save")
            verify(save.visible);verify(save.enabled)
            var point=save.mapToItem(scene,0,0)
            verify(point.x>=0);verify(point.x+save.width<=scene.width)
        }
        function test_checkoff_animation_finishes_and_completed_item_remains() {
            view.reducedMotion=false
            thoughts.switchKind("todo");wait(260)
            var row=findChild(view,"thoughts-row-c")
            verify(row!==null)
            mouseClick(findChild(row,"thoughts-checkbox"))
            compare(row.checked,true)
            var done=note("c","Get groceries","todo",true)
            thoughts.consume({type:"thoughts",notes:[done],drafts:{},directory:"/tmp/notes",warnings:[],modified:"c",operation:"complete"})
            wait(500)
            compare(thoughts.rows.length,0);compare(thoughts.completed.length,1)
            view.reducedMotion=true
        }
    }
}
