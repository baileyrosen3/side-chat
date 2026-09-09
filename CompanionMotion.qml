// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import "CompanionGaze.js" as Gaze

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
    property bool voiceReady: false
    property bool hearing: false
    property real gazeX: 0
    property real gazeY: 0
    property real completedAt: 0
    property bool ready: false
    property string previousMood: "idle"
    property string previewAction: ""
    property string gesture: ""
    property real progress: 0
    property real phase: 0
    property real blink: 1
    property real arrival: 1
    property real revealProgress: -1
    readonly property real reveal: Math.max(0,Math.min(1,revealProgress >= 0 ? revealProgress : arrival))
    readonly property bool animated: visible && !reducedMotion && expressiveness > 0
    readonly property real amount: animated ? Math.min(1.5,Math.max(0,expressiveness)) : 0
    readonly property string action: previewAction || (mood === "error" || mood === "needs_input" || mood === "off" || mood === "standby" ? mood : dragging ? "drag" : hearing ? "hearing" : gesture || ((engaged && mood === "idle") ? "hover" : mood))
    readonly property bool asleep: action === "standby" || action === "off"
    readonly property real cycle: animated ? phase : 0
    readonly property real pulse: Math.sin(progress * Math.PI) * amount
    readonly property real greeting: gesture === "greet" ? pulse : 0
    readonly property real joy: gesture === "success" ? pulse*.9 : 0
    readonly property real waking: gesture === "wake" ? pulse : 0
    readonly property real readySignal: gesture === "ready" ? pulse : 0
    readonly property real readyNod: gesture === "ready" ? Math.sin(progress*Math.PI*3)*pulse : 0
    readonly property real landing: gesture === "drop" ? Math.sin(progress * Math.PI * 3) * (1-progress) * amount : 0
    readonly property real wave: gesture === "greet" ? Math.sin(progress * Math.PI * 6) * pulse : 0
    readonly property real breathe: Math.sin(cycle) * amount
    readonly property real scan: action === "thinking" ? Math.sin(cycle*2.4) * amount : 0
    readonly property real work: action === "acting" ? Math.sin(cycle*7) * amount : 0
    readonly property real attention: action === "needs_input" ? .7 * amount : 0
    readonly property real shake: action === "error" ? Math.sin(cycle*9) * Math.pow(Math.max(0,Math.sin(cycle*1.7)),6) * amount*.65 : 0
    readonly property real warming: action === "warming" ? (.5+.5*Math.sin(cycle*4)) * amount : 0
    readonly property real energyTarget: Math.max(0,Math.min(1,action === "speaking" ? (previewAction ? .5+.35*Math.sin(cycle*8) : outputLevel) : action === "listening" || action === "hearing" ? (previewAction ? .45+.3*Math.sin(cycle*5) : Math.sqrt(Math.max(0,inputLevel)*8)) : 0))
    property real smoothEnergy: energyTarget
    readonly property real energy: amount*smoothEnergy
    readonly property real attentive: action === "listening" || action === "hearing" ? amount : 0
    readonly property real listenRock: attentive*Math.sin(cycle*2.2)*(.3+energy*.45)
    readonly property real talkNod: action === "speaking" ? Math.sin(cycle*5)*energy : 0
    readonly property real hearingNod: action === "hearing" ? Math.sin(cycle*3.6)*amount*(.35+energy*.5) : 0
    readonly property real celebration: gesture === "success" ? Math.sin(progress*Math.PI*3)*pulse : 0
    readonly property real targetTilt: action === "hearing" ? -5 : action === "thinking" ? 8 : action === "needs_input" ? 7 : action === "warming" ? 5 : action === "drag" ? 12 : action === "ready" || action === "success" ? -6 : 0
    property real animatedTilt: targetTilt
    readonly property real poseTilt: animated ? animatedTilt : targetTilt
    property real sleep: asleep ? 1 : 0
    property real lift: action === "drag" ? 1 : 0
    property real lean: asleep ? -.65 : action === "hearing" || action === "ready" ? 1.1 : action === "hover" || engaged ? 1 : action === "speaking" ? .9 : action === "listening" ? .92 : action === "thinking" ? .45 : action === "acting" ? .75 : .2
    readonly property real targetYaw: amount * Math.max(-14,Math.min(14,tracking || action === "acting" ? gazeX*14 : action === "hover" ? 10 : scan*3))
    readonly property real targetPitch: amount * (tracking ? gazeY*9 : action === "listening" ? -5 : 0)
    property real yaw: 0
    property real pitch: 0
    property real yawVelocity: 0
    property real pitchVelocity: 0
    readonly property bool gazeMoving: Math.abs(targetYaw - yaw) > .005 || Math.abs(targetPitch - pitch) > .005
                                       || Math.abs(yawVelocity) > .05 || Math.abs(pitchVelocity) > .05
    onTargetYawChanged: if (!animated) { yaw = targetYaw; yawVelocity = 0 }
    onTargetPitchChanged: if (!animated) { pitch = targetPitch; pitchVelocity = 0 }

    function trigger(name) {
        if (!animated) return;
        gesture = name;
        gestureAnimation.restart();
    }
    property int greetings: 0
    function greet() { greetings++; trigger(greetings%3 === 0 ? "wink" : "greet"); }
    function enter() { if (animated && revealProgress < 0) entrance.restart(); else arrival=1; }
    function preview(name) {
        previewAction=name;
        gestureAnimation.stop(); gesture=""; progress=0;
        if (name === "arrive") enter();
        else if (name === "blink" && animated) wink.restart();
        else if (["greet","success","wake","ready","drop","wink","nod"].indexOf(name)>=0) trigger(name);
        previewEnd.restart();
    }
    function settle() {
        entrance.stop(); gestureAnimation.stop(); wink.stop();
        arrival=1; gesture=""; progress=0; blink=1;
    }
    Component.onCompleted: { ready=true; enter(); }
    onVisibleChanged: { if (visible) enter(); else settle(); }
    onAnimatedChanged: if (!animated) settle();
    onVoiceReadyChanged: if (ready && voiceReady && !hearing && ["warming","idle","listening"].indexOf(mood)>=0) trigger("ready")
    onHearingChanged: if (hearing) { gestureAnimation.stop();gesture=""; }
    onMoodChanged: {
        if (ready && !hearing) {
            if(previousMood === "warming" && voiceReady && (mood === "idle" || mood === "listening") && gesture !== "ready") trigger("ready")
            else if (mood === "warming" || ((previousMood === "standby" || previousMood === "off") && mood === "listening")) trigger("wake")
        }
        if (["error","needs_input","standby","off","thinking","acting","speaking"].indexOf(mood)>=0) { gestureAnimation.stop(); gesture=""; }
        previousMood=mood
    }
    onDraggingChanged: if (ready && !dragging) trigger("drop");
    onCompletedAtChanged: if (ready && completedAt>0 && Math.abs(Date.now()/1000-completedAt)<3) trigger("success");
    Behavior on sleep { NumberAnimation { duration: root.animated ? 700 : 0; easing.type: Easing.InOutCubic } }
    Behavior on lift { NumberAnimation { duration: root.animated ? 260 : 0; easing.type: Easing.OutCubic } }
    Behavior on lean { NumberAnimation { duration: root.animated ? 520 : 0; easing.type: Easing.OutCubic } }
    Behavior on smoothEnergy { NumberAnimation { duration: root.animated ? 100 : 0; easing.type: Easing.OutCubic } }
    Behavior on animatedTilt { NumberAnimation { duration: root.animated ? 380 : 0; easing.type: Easing.InOutCubic } }
    // Keep turns fluid at up to 60 Hz; idle motion needs only 30 Hz. This
    // remains bounded on high-refresh displays and coalesces input bursts.
    Timer {
        property real lastTick: 0
        interval: root.gazeMoving ? 16 : 33
        repeat: true
        running: root.animated
        onRunningChanged: lastTick = Date.now()
        onTriggered: {
            var now = Date.now();
            var dt = Math.min(.1, Math.max(0, (now - lastTick) / 1000));
            lastTick = now;
            root.phase+=dt*Math.PI/4.8;
            var horizontal = Gaze.spring(root.yaw, root.yawVelocity, root.targetYaw, dt);
            var vertical = Gaze.spring(root.pitch, root.pitchVelocity, root.targetPitch, dt);
            root.yaw = horizontal.value; root.yawVelocity = horizontal.velocity;
            root.pitch = vertical.value; root.pitchVelocity = vertical.velocity;
        }
    }
    NumberAnimation { id: entrance; target: root; property: "arrival"; from: 0; to: 1; duration: 620; easing.type: Easing.OutCubic }
    NumberAnimation {
        id: gestureAnimation; target: root; property: "progress"; from: 0; to: 1
        duration: root.gesture === "greet" ? 1600 : root.gesture === "success" ? 1500 : root.gesture === "ready" ? 1250 : root.gesture === "wake" ? 1100 : root.gesture === "wink" ? 950 : 800
        onFinished: root.gesture=""
    }
    Timer { id: previewEnd; interval: 3200; onTriggered: root.previewAction="" }
    Timer { interval: 3500 + Math.random()*3000; repeat: true; running: root.animated && !root.asleep; onTriggered: { wink.restart();interval=3500+Math.random()*3000 } }
    SequentialAnimation {
        id: wink; running: false
        NumberAnimation { target: root; property: "blink"; to: .08; duration: root.animated ? 90 : 0 }
        PauseAnimation { duration: root.animated ? 65 : 0 }
        NumberAnimation { target: root; property: "blink"; to: 1; duration: root.animated ? 150 : 0 }
    }
}
