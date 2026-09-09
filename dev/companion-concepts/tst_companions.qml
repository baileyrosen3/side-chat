import QtQuick
import QtTest
import "../.."
import "../../CompanionCatalog.js" as Catalog

Rectangle {
    color: "#12151b"
    width: 420; height: 640
    PeekBuddy { id: buddy; width: 400; height: 400 }
    CompanionPicker { id: picker; width: 320; visible: false; onSettingChanged: (key,value) => { if (key === "companion") companion=value; } }
    TestCase {
        name: "Companions"
        when: windowShown
        function init() {
            buddy.visible=true; buddy.companion="peek";
            buddy.reducedMotion=false; buddy.expressiveness=1;
            buddy.mood="idle"; buddy.dragging=false; buddy.engaged=false;
            buddy.animation.previewAction=""; buddy.animation.settle();
        }
        function test_all_rigs_render_and_switch_in_place() {
            for (var character of Catalog.companions) {
                buddy.companion=character.id;
                compare(buddy.characterId,character.id);
                wait(1000);
                var shot=grabImage(buddy);
                verify(shot.width>0);
                shot.save("/tmp/side-chat-"+character.id+".png");
                buddy.visible=false; wait(30); buddy.visible=true;
            }
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
            for (var character of Catalog.companions) {
                buddy.companion=character.id;
                for (var reaction of Catalog.actions) {
                    buddy.preview(reaction.id);
                    compare(buddy.currentAction,reaction.id);
                    wait(20);
                }
            }
        }
        function test_reduced_motion_stops_all_animation() {
            buddy.preview("success"); wait(100);
            buddy.reducedMotion=true;
            compare(buddy.animation.animated,false);
            compare(buddy.animation.arrival,1);
            compare(buddy.animation.blink,1);
            compare(buddy.animation.joy,0);
            var phase=buddy.animation.phase;
            buddy.preview("blink"); wait(200);
            compare(buddy.animation.phase,phase);
            compare(buddy.animation.blink,1);
            buddy.reducedMotion=false; buddy.expressiveness=0;
            buddy.preview("arrive"); buddy.greet();
            compare(buddy.animation.arrival,1);
            compare(buddy.animation.greeting,0);
        }
        function test_choice_keyboard_and_preview_do_not_save() {
            buddy.visible=false; picker.visible=true;
            wait(50);
            var option=findChild(picker,"companion-choice-orbit");
            verify(option);
            option.forceActiveFocus(); keyClick(Qt.Key_Space);
            compare(picker.companion,"orbit");
            var preview=findChild(picker,"companion-preview");
            verify(preview); compare(preview.characterId,"orbit");
            preview.preview("speaking");
            compare(preview.currentAction,"speaking");
            wait(1100);
            grabImage(picker).save("/tmp/side-chat-picker.png");
            picker.visible=false;
        }
    }
}
