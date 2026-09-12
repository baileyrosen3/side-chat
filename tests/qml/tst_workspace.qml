import QtQuick
import QtTest
import "../.."

Rectangle {
    id:scene;width:360;height:520
    QtObject {
        id:chat
        property bool connected:true
        property bool busy:false
        property var current:({id:"active"})
        property string draft:""
        property var draftSource:({})
        property string page:"chat"
        property string openScreen:""
        property var requests:[]
        property var thoughts:notes
        function request(command) {requests=requests.concat([command])}
        function thoughtsScreen() {return "fixture"}
        function show(screen,pinned) {openScreen=screen}
        function focusWorkspace() {}
        function openConversation() {page="chat";openScreen="fixture"}
        function openThoughts(kind) {page=kind==="todo" ? "todos" : "notes";openScreen="fixture"}
        function selectChat(id) {request({action:"open",id:id})}
        function revealMessage(id,index) {selectChat(id);openConversation()}
    }
    QtObject {
        id:notes
        property bool recording:false
        property bool saving:false
        property string kind:"note"
        property string body:""
        property var source:({})
        function switchKind(next) {kind=next}
        function newThought(text,origin) {body=text;source=origin}
    }
    WorkspaceModel {id:workspace;chat:chat}
    WorkspaceOverlay {id:view;anchors.fill:parent;model:workspace;active:!!workspace.mode;visible:active;reducedMotion:true}
    TestCase {
        name:"Workspace";when:windowShown
        function init() {
            failOnWarning(/.?/)
            workspace.mode="";workspace.query="";workspace.results=[];workspace.captureBody="";workspace.captureSource=({})
            workspace.busy=false;workspace.capturing=false;workspace.error=""
            chat.requests=[];chat.openScreen="";chat.page="chat";chat.draft="Existing draft";chat.busy=false
            notes.recording=false;notes.saving=false;notes.body=""
        }
        function result(id,kind) {return {id:id,kind:kind,title:"A useful result",snippet:"Some matching text",revision:"r1"}}
        function test_capture_waits_for_selection_before_opening_drawer() {
            workspace.capture(false)
            compare(chat.openScreen,"");compare(workspace.mode,"");verify(workspace.capturing)
            workspace.consume({type:"workspace_capture",serial:workspace.captureSerial,text:"Selected passage",source:{kind:"selection",label:"Editor"}})
            compare(chat.openScreen,"fixture");compare(workspace.mode,"capture")
            compare(findChild(view,"workspace-capture-input").text,"Selected passage")
            workspace.useCapture("todo")
            compare(chat.page,"todos");compare(notes.body,"Selected passage");compare(notes.source.label,"Editor")
            compare(chat.draft,"Existing draft")
            verify(!chat.requests.some(c=>c.action==="send" || c.action==="thoughts_save"))
        }
        function test_ask_prepares_chat_without_sending() {
            workspace.captureBody="A passage";workspace.captureSource={kind:"selection",label:"Editor"};workspace.mode="capture"
            workspace.useCapture("chat")
            compare(chat.draft,"Existing draft\n\nA passage");compare(chat.draftSource.label,"Editor")
            verify(!chat.requests.some(c=>c.action==="send"))
        }
        function test_search_ignores_stale_results_and_enter_opens_choice() {
            workspace.toggleSearch()
            var old=workspace.searchSerial
            workspace.query="task";workspace.search()
            workspace.consume({type:"workspace_results",serial:old,results:[result("old","note")]})
            compare(workspace.results.length,0)
            workspace.consume({type:"workspace_results",serial:workspace.searchSerial,results:[result("first","note"),result("second","todo")]})
            var input=findChild(view,"workspace-search-input")
            input.forceActiveFocus();wait(20)
            keyClick(Qt.Key_Down);keyClick(Qt.Key_Return)
            verify(chat.requests.some(c=>c.action==="thoughts_open_id" && c.id==="second"))
        }
        function test_search_keeps_active_reply_and_draft_safe() {
            workspace.toggleSearch();chat.busy=true
            workspace.activate(result("different","chat"))
            verify(!!workspace.error);verify(!chat.requests.some(c=>c.action==="open"))
            compare(chat.draft,"Existing draft")
        }
        function test_recovery_uses_restore_and_refreshes_results() {
            workspace.showTrash()
            workspace.consume({type:"workspace_results",serial:workspace.searchSerial,results:[result("deleted","note")]})
            workspace.activate(workspace.results[0])
            verify(chat.requests.some(c=>c.action==="workspace_restore" && c.id==="deleted" && c.revision==="r1"))
            workspace.consume({type:"workspace_restored",serial:workspace.restoreSerial,id:"deleted"})
            compare(chat.requests[chat.requests.length-1].action,"workspace_search")
        }
        function test_escape_returns_to_current_page() {
            chat.page="notes";workspace.toggleSearch();wait(20)
            keyClick(Qt.Key_Escape)
            compare(workspace.mode,"");compare(chat.page,"notes");compare(chat.draft,"Existing draft")
        }
    }
}
