import QtQuick
import QtTest
import qs.Commons
import "../.."
import "../../CompanionGaze.js" as Gaze

Rectangle {
    id: scene
    width: 500; height: 560; color: Color.background
    QtObject {
        id: chat
        property var jarvis: ({})
        property bool busy: false
        property string error: ""
        property var agentRequests: []
        property var lastRequest: ({})
        function request(command) { lastRequest=command }
        function openConversation() { lastRequest={action:"conversation"} }
        function openJarvisSettings() { }
        function setJarvis(enabled,reopen) { }
    }
    Item {
        id: host
        width: parent.width; height: parent.height
        CompanionSurface { id:surface;width:implicitWidth;height:implicitHeight;chat:chat }
    }
    TestCase {
        name:"TaskSurface"
        when:windowShown
        function init() {
            failOnWarning(/.?/)
            chat.busy=false;chat.error="";chat.agentRequests=[];chat.lastRequest={}
            chat.jarvis={stage:"idle",ready:true,preview:true,previewScenario:true,reducedMotion:true,expressiveness:1,scope:"desktop",task:{state:"idle",total:0,steps:[]}}
            mouseMove(scene,scene.width-1,scene.height-1)
            host.visible=true;surface.present=true;surface.hideControls();surface.desktopPointer=null
        }
        function task(state) {
            return {turn:"fixture",state:state,label:state === "running" ? "Update settings" : "Actions verified",detail:"File contents matched the update.",total:2,checked:state === "verified" ? 1 : 0,steps:[{label:"Read settings",state:"observed",evidence:""},{label:"Update settings",state:state === "verified" ? "verified" : "running",evidence:"File contents checked after the update"}]}
        }
        function test_task_target_takes_priority_and_interruption_returns_to_user() {
            var voice={stage:"acting",expressiveness:1}
            var mouse={x:100,y:100}, target={x:900,y:400}
            compare(Gaze.attention(voice,true,mouse,target).source,"task")
            compare(Gaze.attention(voice,true,mouse,target).point,target)
            voice.hearing=true;compare(Gaze.attention(voice,true,mouse,target).source,"user")
            voice.hearing=false;voice.stage="needs_input";compare(Gaze.attention(voice,true,mouse,target).source,"user")
            voice.stage="acting";compare(Gaze.attention(voice,true,mouse,null).source,"rest")
            compare(Gaze.attention(voice,false,mouse,target).source,"cursor")
            voice.reducedMotion=true;compare(Gaze.attention(voice,true,mouse,target).source,"rest")
        }
        function test_controls_only_appear_on_hover_and_stay_usable() {
            var dock=surface.panelRegion
            compare(dock.visible,false)
            mouseMove(dock,20,20)
            wait(300);compare(dock.visible,false)
            mouseMove(surface.bodyRegion,30,50)
            tryCompare(dock,"visible",true)
            // Cross the small transparent gap before entering the controls.
            mouseMove(surface,(surface.bodyRegion.width+dock.x)/2,dock.y+20)
            wait(70);compare(dock.visible,true)
            mouseMove(dock,20,20)
            wait(350);compare(dock.visible,true)
            mouseClick(findChild(surface,"companion-more"))
            compare(surface.controlsPinned,true)
            mouseMove(scene,scene.width-1,scene.height-1)
            tryCompare(dock,"visible",false,600)
            compare(surface.controlsPinned,false)
        }
        function test_hiding_jarvis_resets_controls_before_reopening() {
            surface.showControls()
            compare(surface.panelRegion.visible,true)
            host.visible=false
            compare(surface.controlsVisible,false)
            host.visible=true
            compare(surface.panelRegion.visible,false)
            compare(surface.controlsPinned,false)
        }
        function test_exit_keeps_rendering_until_the_robot_is_offscreen() {
            surface.showControls()
            chat.jarvis=Object.assign({},chat.jarvis,{reducedMotion:false})
            surface.present=false
            compare(surface.controlsVisible,false);compare(surface.interactive,false)
            compare(surface.visible,true)
            tryCompare(surface,"visible",false,700)
            var motion=findChild(surface,"companion-body").animation
            var phase=motion.phase;wait(100);compare(motion.phase,phase)
            surface.present=true
            compare(surface.visible,true)
            tryCompare(surface.reveal,"progress",1,850)
            compare(surface.controlsVisible,false)
        }
        function test_stop_is_available_on_hover_without_expansion() {
            chat.busy=true
            chat.jarvis=Object.assign({},chat.jarvis,{stage:"acting",task:task("running"),taskCaption:"Update settings"})
            var stop=findChild(surface,"companion-stop")
            compare(stop.visible,false)
            mouseMove(surface.bodyRegion,30,50)
            tryCompare(stop,"visible",true)
            verify(stop.visible);verify(stop.enabled);compare(surface.controlsPinned,false)
            mouseClick(stop)
            compare(chat.lastRequest.action,"jarvis_stop")
            compare(findChild(surface,"companion-headline").text,"Update settings")
        }
        function test_keyboard_can_expand_details_and_escape_collapses_everything() {
            chat.jarvis=Object.assign({},chat.jarvis,{task:task("verified")})
            mouseMove(surface.bodyRegion,30,50)
            tryCompare(surface.panelRegion,"visible",true)
            compare(findChild(surface,"companion-headline").text,"Actions verified")
            compare(findChild(surface,"companion-caption").text,"File contents matched the update.")
            var toggle=findChild(surface,"task-details-toggle")
            toggle.forceActiveFocus();keyClick(Qt.Key_Space)
            compare(surface.details.expanded,true)
            var more=findChild(surface,"companion-more")
            more.forceActiveFocus();keyClick(Qt.Key_Space)
            compare(surface.controlsPinned,true)
            keyClick(Qt.Key_Escape)
            compare(surface.controlsPinned,false);compare(surface.details.expanded,false)
            compare(surface.panelRegion.visible,false)
        }
        function test_speech_and_question_take_priority_over_task_caption() {
            chat.busy=true
            chat.jarvis=Object.assign({},chat.jarvis,{stage:"acting",task:task("running"),taskCaption:"Update settings",speaking:true,caption:"I found the setting."})
            compare(findChild(surface,"companion-caption").text,"I found the setting.")
            chat.agentRequests=[{title:"Apply these settings?"}]
            chat.jarvis=Object.assign({},chat.jarvis,{stage:"needs_input",speaking:false})
            compare(findChild(surface,"companion-caption").text,"Apply these settings?")
            chat.busy=false;chat.error="Voice worker disconnected"
            chat.jarvis=Object.assign({},chat.jarvis,{stage:"error",task:task("verified")})
            compare(findChild(surface,"companion-headline").text,"Needs attention")
            compare(findChild(surface,"companion-caption").text,"Voice worker disconnected")
        }
        function test_voice_readiness_and_hearing_reach_the_face() {
            chat.jarvis=Object.assign({},chat.jarvis,{ready:false,stage:"warming",reducedMotion:false})
            var buddy=findChild(surface,"companion-body")
            chat.jarvis=Object.assign({},chat.jarvis,{ready:true,stage:"listening"})
            compare(buddy.currentAction,"ready")
            chat.jarvis=Object.assign({},chat.jarvis,{hearing:true,inputLevel:.04})
            compare(buddy.currentAction,"hearing")
            chat.jarvis=Object.assign({},chat.jarvis,{hearing:false,stage:"thinking"})
            compare(buddy.currentAction,"thinking")
        }
        function test_expanded_layout_contains_controls_and_reduced_motion_is_still() {
            chat.jarvis=Object.assign({},chat.jarvis,{task:task("verified"),listening:true,inputLevel:.9})
            surface.showControls();surface.details.expanded=true
            wait(200)
            var dock=findChild(surface,"companion-dock"), stop=findChild(surface,"companion-stop")
            verify(dock.x+dock.width<=surface.width)
            verify(dock.y+dock.height<=surface.height)
            verify(stop.mapToItem(surface,0,stop.height).y<=surface.height)
            var before=grabImage(surface);wait(150)
            verify(before.equals(grabImage(surface)))
            before.save("/tmp/jarvis-unified-test.png")
        }
    }
}
