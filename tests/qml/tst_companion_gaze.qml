import QtQuick
import QtTest
import "../.."
import "../../CompanionGaze.js" as Gaze

Item {
    width: 200; height: 200
    CompanionMotion { id: motion }
    SignalSpy { id: frames; target: motion; signalName: "phaseChanged" }
    TestCase {
        name: "CompanionGaze"
        when: windowShown
        function init() {
            failOnWarning(/.?/);
            motion.visible = true; motion.reducedMotion = false; motion.expressiveness = 1;
            motion.tracking = false; motion.engaged = false; motion.mood = "idle";
            motion.gazeX = 0; motion.gazeY = 0; motion.settle();
        }
        function test_desktop_direction_and_monitor_offsets() {
            var face = {x: 7700, y: 1900};
            var center = Gaze.direction(face, face, 280);
            compare(center.x, 0); compare(center.y, 0);
            var upperLeft = Gaze.direction({x: 7100, y: 700}, face, 280);
            verify(upperLeft.x < 0 && upperLeft.y < 0);
            var lowerRight = Gaze.direction({x: 9500, y: 2100}, face, 280);
            verify(lowerRight.x > 0 && lowerRight.y > 0);
            var relative = Gaze.direction({x: -600, y: -1200}, {x: 0, y: 0}, 280);
            compare(upperLeft.x, relative.x); compare(upperLeft.y, relative.y);
            var scaled = Gaze.direction({x: -1200, y: -2400}, {x: 0, y: 0}, 560);
            compare(relative.x, scaled.x); compare(relative.y, scaled.y);
            var distant = Gaze.direction({x: 1e9, y: -1e9}, face, 0);
            verify(distant.x <= 1 && distant.y >= -1);
        }
        function test_tracking_does_not_open_hover_pose() {
            motion.tracking = true; motion.gazeX = .8; motion.gazeY = -.6;
            wait(950);
            compare(motion.action, "idle"); fuzzyCompare(motion.lean, .2, .001);
            fuzzyCompare(motion.yaw, 11.2, .001); fuzzyCompare(motion.pitch, -5.4, .001);
            motion.engaged = true; compare(motion.action, "hover");
            motion.engaged = false; compare(motion.action, "idle");
            motion.mood = "speaking"; compare(motion.action, "speaking");
        }
        function test_hidden_and_reduced_motion_stop_tracking_animation() {
            motion.tracking = true; motion.gazeX = 1;
            motion.reducedMotion = true;
            compare(motion.animated, false); compare(motion.yaw, 0);
            var phase = motion.phase;
            motion.gazeX = -1; wait(120);
            compare(motion.yaw, 0); compare(motion.phase, phase);
            motion.reducedMotion = false; motion.visible = false;
            phase = motion.phase; wait(120);
            compare(motion.animated, false); compare(motion.phase, phase);
        }
        function test_mouse_burst_is_coalesced_at_bounded_cadence() {
            motion.tracking = true;
            var previous = motion.yaw;
            for (var i = 0; i < 1000; ++i) motion.gazeX = i % 2 ? 1 : -1;
            compare(motion.yaw, previous, "Input events must not update the rig before its next tick");
            frames.clear(); wait(250);
            verify(frames.count > 0 && frames.count <= 17, "Gaze clock must stay bounded near 60 Hz");
            verify(motion.yaw > 0 && motion.yaw <= 14);
        }
        function test_spring_is_smooth_and_independent_of_frame_rate() {
            var fast = {value: 0, velocity: 0}, slow = {value: 0, velocity: 0};
            for (var i = 0; i < 60; ++i) {
                var next = Gaze.spring(fast.value, fast.velocity, 14, 1 / 60);
                verify(next.value >= fast.value && next.value <= 14);
                verify(next.value - fast.value < 1.3, "A turn must ease in without a large first step");
                fast = next;
            }
            for (var j = 0; j < 30; ++j) slow = Gaze.spring(slow.value, slow.velocity, 14, 1 / 30);
            fuzzyCompare(fast.value, slow.value, .005);
            fuzzyCompare(fast.value, 14, .005);
            var reversal = Gaze.spring(fast.value, fast.velocity, -14, 1 / 60);
            verify(Math.abs(reversal.value - fast.value) < 1.3, "Reversing the mouse must not snap the head");
        }
    }
}
