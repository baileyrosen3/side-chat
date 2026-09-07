import QtQuick
import QtTest
import qs.Commons
import "../.."
import "../../RobotExpressions.js" as Expressions

Rectangle {
    color: "#12151b"
    width: 420; height: 640
    JarvisBuddy { id: buddy; width: 400; height: 400 }
    RobotAppearance { id: appearance; width: 320; visible: false }
    QtObject {
        id: chat
        property var jarvis: ({stage:"idle",ready:false,preview:true,expressiveness:1,listening:false,speaking:false,muted:false})
        property bool busy: false
        property string error: ""
        function request(command) { }
        function openConversation() { }
        function openJarvisSettings() { }
        function setJarvis(enabled,reopen) { }
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
            for (var action of ["idle","greet","thinking","speaking","success","needs_input","error","standby","drag"]) {
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
