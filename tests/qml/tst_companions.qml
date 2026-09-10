import QtQuick
import QtTest
import qs.Commons
import "../.."
import "../../RobotExpressions.js" as Expressions

Rectangle {
    color: "#12151b"
    width: 420; height: 640
    PeekBuddy { id: buddy; width: 400; height: 400 }
    RobotAppearance { id: appearance; width: 320; visible: false }
    QtObject {
        id: chat
        property var peek: ({stage:"idle",ready:false,preview:true,expressiveness:1,listening:false,speaking:false,muted:false})
        property bool busy: false
        property string error: ""
        property var commands: []
        function request(command) { commands=commands.concat([command]) }
        function openConversation() { }
        function openPeekSettings() { }
        function setPeek(enabled,reopen) { }
    }
    CompanionSurface { id: surface; width: 326; height: 248; chat: chat; visible: false }
    TestCase {
        name: "RobotCompanion"
        when: windowShown
        function init() {
            failOnWarning(/.?/);
            Color.background="#14171d"; Color.foreground="#e2e6ef"; Color.accent="#8cbbec";
            buddy.visible=true;
            buddy.reducedMotion=false; buddy.expressiveness=1;
            buddy.mood="idle"; buddy.dragging=false; buddy.engaged=false;
            buddy.voiceReady=false;buddy.hearing=false;
            buddy.animation.previewAction=""; buddy.animation.settle();
            buddy.animation.greetings=0;
        }
        function test_live_theme_updates_without_recreating_robot() {
            buddy.reducedMotion=true; wait(100);
            var before=grabImage(buddy);
            Color.accent="#da8fca"; Color.foreground="#d6c5dc"; Color.background="#251e31";
            wait(150);
            verify(!before.equals(grabImage(buddy)),"Changing theme must repaint the existing robot");
            grabImage(buddy).save("/tmp/side-chat-robot-theme.png");
            compare(buddy.characterId,"peek");
        }
        function test_actual_surface_size_and_hidden_clock() {
            buddy.visible=false; surface.visible=true; wait(1000);
            grabImage(surface).save("/tmp/side-chat-robot-surface.png");
            surface.visible=false;
            var phase=buddy.animation.phase; wait(150); compare(buddy.animation.phase,phase);
        }
        function test_render_expressions() {
            for (var action of ["idle","warming","ready","listening","hearing","greet","thinking","acting","speaking","success","needs_input","error","standby","drag"]) {
                buddy.preview(action); wait(action === "standby" ? 750 : 420);
                var shot=grabImage(buddy);
                verify(shot.width>0);
                shot.save("/tmp/side-chat-robot-"+action+".png");
            }
            buddy.visible=false; wait(30); buddy.visible=true; wait(950);
            compare(buddy.animation.arrival,1);
        }
        function test_live_events() {
            buddy.greet(); compare(buddy.currentAction,"greet");
            buddy.mood="error"; compare(buddy.currentAction,"error");
            buddy.mood="needs_input"; compare(buddy.currentAction,"needs_input");
            buddy.mood="idle"; buddy.dragging=true; compare(buddy.currentAction,"drag");
            buddy.dragging=false; compare(buddy.currentAction,"drop");
            buddy.animation.settle(); buddy.engaged=true; compare(buddy.currentAction,"hover");
            buddy.engaged=false; buddy.mood="standby"; wait(750);
            buddy.mood="listening"; compare(buddy.currentAction,"wake");
            buddy.completedAt=Date.now()/1000; compare(buddy.currentAction,"success");
        }
        function test_every_preview() {
            for (var reaction of Expressions.actions) {
                buddy.preview(reaction.id); compare(buddy.currentAction,reaction.id); wait(20);
            }
        }
        function test_warmup_completion_has_one_ready_reaction() {
            buddy.mood="warming"
            buddy.voiceReady=true;buddy.mood="idle"
            compare(buddy.currentAction,"ready")
            wait(180);verify(buddy.animation.readySignal>0)
            var before=buddy.animation.progress
            buddy.mood="listening";buddy.inputLevel=.02
            verify(buddy.animation.progress>=before)
            compare(buddy.currentAction,"ready")
            tryCompare(buddy,"currentAction","listening",1600)
            buddy.voiceReady=true;buddy.inputLevel=.08
            compare(buddy.currentAction,"listening")
        }
        function test_real_speech_interrupts_the_ready_flourish() {
            buddy.mood="warming";buddy.voiceReady=true;buddy.mood="listening"
            compare(buddy.currentAction,"ready")
            buddy.hearing=true
            compare(buddy.currentAction,"hearing");compare(buddy.animation.gesture,"")
            buddy.hearing=false;buddy.mood="thinking"
            compare(buddy.currentAction,"thinking")
            buddy.mood="needs_input";compare(buddy.currentAction,"needs_input")
        }
        function test_state_colors_follow_the_theme_and_stay_distinct() {
            buddy.reducedMotion=true
            var colors=[]
            for(var state of ["listening","thinking","speaking","success","needs_input","error"]) {
                buddy.preview(state)
                colors.push(String(buddy.expressionColor))
            }
            compare(new Set(colors).size,colors.length)
            buddy.preview("thinking")
            var before=String(buddy.expressionColor)
            Color.accent="#da8fca"
            verify(String(buddy.expressionColor)!==before)
        }
        function test_listening_responds_to_audio_and_quiet_input_settles() {
            buddy.mood="listening";buddy.animation.settle();buddy.inputLevel=0
            tryCompare(buddy.animation,"energy",0,300)
            buddy.inputLevel=.035
            tryVerify(()=>buddy.animation.energy>.3,400)
            compare(buddy.currentAction,"listening")
            buddy.inputLevel=0
            tryCompare(buddy.animation,"energy",0,400)
            buddy.reducedMotion=true;buddy.inputLevel=.5
            compare(buddy.animation.energy,0)
        }
        function test_voxtype_mic_uses_one_toggle_request() {
            chat.peek={stage:"idle",ready:true,preview:false,expressiveness:1,listening:false,speaking:false,muted:false,asrModel:"voxtype",handsFree:false,wakeEnabled:false}
            chat.commands=[];surface.visible=true;surface.controlsVisible=true;wait(80)
            var mic=findChild(surface,"companion-mic");verify(mic);mic.clicked()
            compare(chat.commands.length,1);compare(chat.commands[0].action,"peek_listen");compare(chat.commands[0].enabled,true)
            chat.peek=Object.assign({},chat.peek,{listening:true});chat.commands=[];mic.clicked()
            compare(chat.commands.length,1);compare(chat.commands[0].enabled,false)
            surface.visible=false
        }
        function test_reduced_motion_stops_all_animation() {
            buddy.preview("success"); wait(100);
            buddy.reducedMotion=true;
            compare(buddy.animation.animated,false);
            compare(buddy.animation.arrival,1); compare(buddy.animation.blink,1); compare(buddy.animation.joy,0);
            var phase=buddy.animation.phase;
            wait(100); var still=grabImage(buddy); wait(150);
            verify(still.equals(grabImage(buddy)),"Reduced motion must stop facial transitions too");
            buddy.preview("blink"); wait(200);
            compare(buddy.animation.phase,phase); compare(buddy.animation.blink,1);
            buddy.reducedMotion=false; buddy.expressiveness=0;
            buddy.preview("arrive"); buddy.greet();
            compare(buddy.animation.arrival,1); compare(buddy.animation.greeting,0);
        }
        function test_preview_keyboard() {
            buddy.visible=false; appearance.visible=true; wait(50);
            var reaction=findChild(appearance,"companion-reaction"); verify(reaction);
            reaction.forceActiveFocus(); keyClick(Qt.Key_Down);
            var preview=findChild(appearance,"companion-preview"); verify(preview);
            preview.preview("speaking"); compare(preview.currentAction,"speaking");
            wait(1100); grabImage(appearance).save("/tmp/side-chat-robot-settings.png");
            appearance.visible=false;
        }
    }
}
