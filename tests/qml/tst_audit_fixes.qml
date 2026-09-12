import QtQuick
import QtTest
import qs.Commons
import "../.."

Rectangle {
    width:400;height:600
    QtObject {
        id:chat
        property bool connected:true
        property string page:"notes"
        property string openScreen:"fixture"
        property var commands:[]
        function request(c) {commands=commands.concat([c])}
    }
    ThoughtsModel {id:model;chat:chat}
    ThoughtsView {id:view;width:280;height:520;model:model;visible:false;active:visible;reducedMotion:true}
    QtObject {
        id:host
        property string family:"sans-serif"
        property color fg:"white"
        property color dim:"gray"
        function px(n) {return n}
    }
    Item {width:300;ToolActivity {id:activity;tools:[{name:"shell",status:"stopped",args:{},output:""}];host:host}}
    TestCase {
        name:"AuditFixes";when:windowShown
        function init() {
            failOnWarning(/.?/)
            model.loading=true;model.saving=false;model.voicePhase="idle";model.kind="note"
            model.notes=[];model.drafts={};model.clearedDrafts={};model.initialized=true
            model.resetInput();chat.commands=[]
            view.visible=false;Style.font={family:"sans-serif",body:12}
        }
        function test_stopped_tool_is_not_reported_as_completed() {
            compare(activity.children[0].text,"1 stopped")
        }
        function test_large_font_keeps_primary_action_inside_narrow_view() {
            Style.font={family:"sans-serif",body:22};view.visible=true;model.body="Keep my words"
            wait(20)
            var save=findChild(view,"thoughts-save"), point=save.mapToItem(view,0,0)
            verify(save.height>=24)
            verify(point.x>=0 && point.x+save.width<=view.width)
            verify(point.y>=0 && point.y+save.height<=view.height)
            compare(findChild(view,"thoughts-body").font.pixelSize,22)
        }
        function test_cleared_draft_stays_cleared_after_stale_snapshot() {
            model.body="Deleted by the user";model.stash()
            var identity=model.key, stale=model.drafts
            model.body="";model.stash()
            verify(!model.drafts[identity])
            verify(chat.commands.some(c=>c.action === "thoughts_draft" && c.discard && c.key===identity))
            model.consume({type:"thoughts",notes:[],drafts:stale,directory:"",warnings:[]})
            verify(!model.drafts[identity])
            model.body="Replacement";model.stash()
            compare(model.drafts[identity].body,"Replacement")
        }
        function test_noon_and_midnight_wait_for_reminder_preview_data() {
            return [{tag:"noon",text:"Call Alex at noon"},{tag:"midnight",text:"Leave at midnight"}]
        }
        function test_noon_and_midnight_wait_for_reminder_preview(data) {
            model.kind="todo";model.body=data.text
            verify(model.dateCandidate)
            model.save(false)
            verify(!chat.commands.some(c=>c.action === "thoughts_save"))
            var due=Date.now()/1000+3600
            model.consume({type:"thoughts_due_preview",serial:model.reminderSerial,due:due,body:"Call Alex",label:"Preview time"})
            model.save(false)
            var command=chat.commands.find(c=>c.action === "thoughts_save")
            verify(!!command);compare(command.due,due)
        }
    }
}
