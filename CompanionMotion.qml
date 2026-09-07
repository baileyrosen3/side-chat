// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick

// One animation clock per viewport. Every character interprets these signals
// through its own rig; previews use the same paths as live events.
Item {
    id: root
    property string mood: "idle"
    property real inputLevel: 0
    property real outputLevel: 0
    property bool reducedMotion: false
    property real expressiveness: 1
    property bool tracking: false
    property bool engaged: false
    property bool dragging: false
    property real gazeX: 0
    property real gazeY: 0
    property real completedAt: 0
    property bool ready: false
    property string previewAction: ""
    property string gesture: ""
    property real progress: 0
    property real phase: 0
    property real blink: 1
    property real arrival: 1
    readonly property bool animated: visible && !reducedMotion && expressiveness > 0
    readonly property real amount: animated ? expressiveness : 0
    readonly property string action: previewAction || (mood === "error" || mood === "needs_input" ? mood : dragging ? "drag" : gesture || (((engaged || tracking) && mood === "idle") ? "hover" : mood))
    readonly property bool asleep: action === "standby" || action === "off"
    readonly property real cycle: animated ? phase : 0
    readonly property real pulse: Math.sin(progress * Math.PI) * amount
    readonly property real greeting: gesture === "greet" ? pulse : 0
    readonly property real joy: gesture === "success" ? pulse : 0
    readonly property real waking: gesture === "wake" ? pulse : 0
    readonly property real landing: gesture === "drop" ? Math.sin(progress * Math.PI * 3) * (1-progress) * amount : 0
    readonly property real wave: gesture === "greet" ? Math.sin(progress * Math.PI * 6) * pulse : 0
    readonly property real breathe: Math.sin(cycle) * amount
    readonly property real scan: action === "thinking" ? Math.sin(cycle*2.4) * amount : 0
    readonly property real work: action === "acting" ? Math.sin(cycle*7) * amount : 0
    readonly property real attention: action === "needs_input" ? (.5+.5*Math.sin(cycle*3)) * amount : 0
    readonly property real shake: action === "error" ? Math.sin(cycle*12) * Math.pow(Math.max(0,Math.sin(cycle*2)),6) * amount : 0
    readonly property real warming: action === "warming" ? (.5+.5*Math.sin(cycle*4)) * amount : 0
    readonly property real energy: amount * Math.max(0,Math.min(1,action === "speaking" ? (previewAction ? .45+.35*Math.sin(cycle*11) : outputLevel) : action === "listening" ? (previewAction ? .35+.25*Math.sin(cycle*6) : inputLevel) : 0))
    property real sleep: asleep ? 1 : 0
    property real lift: action === "drag" ? 1 : 0
    property real lean: asleep ? -.45 : action === "hover" || tracking || engaged ? 1 : action === "speaking" ? .8 : action === "listening" ? .6 : .2
    property real yaw: amount * Math.max(-14,Math.min(14,tracking || action === "acting" ? gazeX*14 : action === "hover" ? 10 : scan*9))
    property real pitch: amount * (tracking ? gazeY*9 : action === "listening" ? -5 : 0)

    function trigger(name) {
        if (!animated) return;
        gesture = name;
        gestureAnimation.restart();
    }
    property int greetings: 0
    function greet() { greetings++; trigger(greetings%3 === 0 ? "wink" : "greet"); }
    function enter() { if (animated) entrance.restart(); else arrival=1; }
    function preview(name) {
        previewAction=name;
        gestureAnimation.stop(); gesture=""; progress=0;
        if (name === "arrive") enter();
        else if (name === "blink" && animated) wink.restart();
        else if (["greet","success","wake","drop","wink","nod"].indexOf(name)>=0) trigger(name);
        previewEnd.restart();
    }
    function settle() {
        entrance.stop(); gestureAnimation.stop(); wink.stop();
        arrival=1; gesture=""; progress=0; blink=1;
    }
    Component.onCompleted: { ready=true; enter(); }
    onVisibleChanged: { if (visible) enter(); else settle(); }
    onAnimatedChanged: if (!animated) settle();
    onMoodChanged: {
        if (ready && (mood === "warming" || ((sleep > .1) && mood !== "standby" && mood !== "off"))) trigger("wake");
        if (mood === "error" || mood === "needs_input" || mood === "standby" || mood === "off") { gestureAnimation.stop(); gesture=""; }
    }
    onDraggingChanged: if (ready && !dragging) trigger("drop");
    onCompletedAtChanged: if (ready && completedAt>0 && Math.abs(Date.now()/1000-completedAt)<3) trigger("success");
    Behavior on sleep { NumberAnimation { duration: root.animated ? 700 : 0; easing.type: Easing.InOutCubic } }
    Behavior on lift { NumberAnimation { duration: root.animated ? 260 : 0; easing.type: Easing.OutCubic } }
    Behavior on lean { NumberAnimation { duration: root.animated ? 520 : 0; easing.type: Easing.OutCubic } }
    Behavior on yaw { NumberAnimation { duration: root.animated ? 220 : 0; easing.type: Easing.OutCubic } }
    Behavior on pitch { NumberAnimation { duration: root.animated ? 220 : 0; easing.type: Easing.OutCubic } }
    FrameAnimation {
        running: root.animated
        onTriggered: {
            var dt=Math.min(frameTime,.05);
            root.phase+=dt*Math.PI/4.8;
        }
    }
    NumberAnimation { id: entrance; target: root; property: "arrival"; from: 0; to: 1; duration: 900; easing.type: Easing.OutCubic }
    NumberAnimation {
        id: gestureAnimation; target: root; property: "progress"; from: 0; to: 1
        duration: root.gesture === "greet" ? 1800 : root.gesture === "success" ? 1800 : root.gesture === "wink" ? 1150 : 1000
        onFinished: root.gesture=""
    }
    Timer { id: previewEnd; interval: 3200; onTriggered: root.previewAction="" }
    Timer { interval: 4300; repeat: true; running: root.animated && !root.asleep; onTriggered: wink.restart() }
    SequentialAnimation {
        id: wink; running: false
        NumberAnimation { target: root; property: "blink"; to: .08; duration: root.animated ? 90 : 0 }
        PauseAnimation { duration: root.animated ? 65 : 0 }
        NumberAnimation { target: root; property: "blink"; to: 1; duration: root.animated ? 150 : 0 }
    }
}
