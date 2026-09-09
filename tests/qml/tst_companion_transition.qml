import QtQuick
import QtTest
import "../.."

Item {
    width: 200; height: 200
    CompanionTransition { id: transition }
    TestCase {
        name: "CompanionTransition"
        when: windowShown
        function init() {
            failOnWarning(/.?/)
            transition.reducedMotion=true;transition.present=false
            transition.reducedMotion=false
        }
        function test_departure_finishes_before_hiding_and_disables_input_immediately() {
            compare(transition.rendered,false)
            transition.present=true
            compare(transition.rendered,true);compare(transition.interactive,false)
            wait(180)
            verify(transition.progress>0 && transition.progress<1)
            tryCompare(transition,"progress",1,800)
            compare(transition.interactive,true)
            transition.present=false
            compare(transition.rendered,true);compare(transition.interactive,false)
            wait(100)
            verify(transition.progress>0 && transition.progress<1)
            tryCompare(transition,"rendered",false,600)
            compare(transition.progress,0);compare(transition.moving,false)
        }
        function test_reversal_continues_from_current_position() {
            transition.present=true;wait(220)
            var before=transition.progress
            verify(before>0 && before<1)
            transition.present=false
            compare(transition.progress,before)
            wait(40)
            verify(transition.progress<before)
            before=transition.progress
            transition.present=true
            compare(transition.progress,before)
            tryCompare(transition,"progress",1,800)
            compare(transition.rendered,true)
        }
        function test_rapid_toggles_do_not_leave_a_stale_hide() {
            transition.present=true
            for(var i=0;i<6;i++) { wait(30);transition.present=!transition.present }
            transition.present=true
            tryCompare(transition,"progress",1,850)
            wait(450)
            compare(transition.rendered,true);compare(transition.interactive,true)
        }
        function test_reduced_motion_settles_an_active_transition() {
            transition.present=true;wait(150)
            transition.reducedMotion=true
            compare(transition.progress,1);compare(transition.moving,false)
            transition.present=false
            compare(transition.progress,0);compare(transition.rendered,false)
            transition.present=true
            compare(transition.progress,1);compare(transition.interactive,true)
        }
    }
}
