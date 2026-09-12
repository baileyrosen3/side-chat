import QtQuick
import QtTest
import "../.."
Rectangle {
 id:scene;width:400;height:600
 QtObject {
  id:chat
  property bool connected:true
  property string page:"notes"
  property string openScreen:"audit"
  property var commands:[]
  function request(c){commands=commands.concat([c])}
 }
 ThoughtsModel {id:model;chat:chat}
 QtObject {id:host;property string family:"sans-serif";property color fg:"white";property color dim:"gray";function px(n){return n}}
 Item {width:300; ToolActivity {id:activity;tools:[{name:"shell",status:"stopped",args:{},output:""}];host:host}}
 TestCase {
  name:"AuditReproductions";when:windowShown
  function init(){
   model.loading=true;model.saving=false;model.voicePhase="idle";model.kind="note";model.notes=[];model.drafts={};model.initialized=true;model.resetInput();chat.commands=[]
  }
  function test_stopped_tool_is_labeled_completed(){
   compare(activity.children[0].text,"1 action completed")
  }
  function test_erased_new_draft_remains_recoverable(){
   model.body="Deleted by the user";model.stash()
   var identity=model.key
   model.body="";model.stash()
   compare(model.drafts[identity].body,"Deleted by the user")
   verify(!chat.commands.some(c=>c.action==="thoughts_discard"))
  }
  function test_noon_can_save_before_date_preview(){
   model.kind="todo";model.body="Call Alex at noon"
   compare(model.dateCandidate,false)
   model.save(false)
   var command=chat.commands.find(c=>c.action==="thoughts_save")
   verify(!!command);compare(command.due,0);compare(command.body,"Call Alex at noon")
  }
 }
}
