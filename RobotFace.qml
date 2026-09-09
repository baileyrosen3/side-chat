// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick3D
import qs.Commons

CustomMaterial {
    id: root
    required property var motion
    readonly property var m: motion
    readonly property string action: m.action
    readonly property bool calm: m.reducedMotion || m.expressiveness === 0
    readonly property real targetHappy: action === "success" ? 1 : action === "greet" || action === "wink" || action === "ready" ? .95 : action === "hover" ? .72 : action === "listening" || action === "hearing" ? .48 : action === "thinking" || action === "warming" ? .08 : action === "error" || action === "needs_input" ? 0 : .36
    property real animatedHappy: targetHappy
    readonly property real happy: calm ? targetHappy : animatedHappy
    readonly property real targetCurious: action === "needs_input" ? 1.2 : action === "thinking" ? .95 : action === "hover" ? .9 : action === "listening" || action === "hearing" ? .65 : 0
    property real animatedCurious: targetCurious
    readonly property real curious: calm ? targetCurious : animatedCurious
    readonly property real targetWorried: action === "error" ? 1 : 0
    property real animatedWorried: targetWorried
    readonly property real worried: calm ? targetWorried : animatedWorried
    readonly property real targetSurprised: action === "drag" ? 1 : action === "wake" ? .8 : action === "ready" ? .85*(1-m.progress) : action === "hearing" ? .22 : 0
    property real animatedSurprised: targetSurprised
    readonly property real surprised: calm ? targetSurprised : animatedSurprised
    readonly property real targetDrowsy: m.asleep ? 1 : 0
    property real animatedDrowsy: targetDrowsy
    readonly property real drowsy: calm ? targetDrowsy : animatedDrowsy
    readonly property real targetTalking: action === "speaking" ? 1 : 0
    property real animatedTalking: targetTalking
    readonly property real talking: calm ? targetTalking : animatedTalking
    readonly property real targetFocused: action === "acting" ? 1 : 0
    property real animatedFocused: targetFocused
    readonly property real focused: calm ? targetFocused : animatedFocused
    readonly property real leftBlink: m.gesture === "wink" ? 1-.98*Math.sin(m.progress*Math.PI) : m.blink
    readonly property real rightBlink: m.blink
    readonly property real gazeHorizontal: m.yaw*.008
    readonly property real gazeVertical: -m.pitch*.009
    readonly property real speech: m.energy
    readonly property real clock: m.cycle
    readonly property real listening: action === "listening" || action === "hearing" ? 1 : 0
    readonly property real hearing: action === "hearing" ? 1 : 0
    readonly property real booting: action === "warming" ? 1 : 0
    readonly property real readyBurst: action === "ready" ? m.readySignal : 0
    readonly property real celebrating: action === "success" || action === "greet" ? 1 : 0
    readonly property real signalPulse: m.animated ? .5+.5*Math.sin(clock*2.5) : .5
    function mixColor(a,b,t) { return Qt.rgba(a.r+(b.r-a.r)*t,a.g+(b.g-a.g)*t,a.b+(b.b-a.b)*t,1) }
    function stateColor() {
        if(action === "error") return mixColor(Color.urgent,Color.foreground,.12)
        if(m.asleep) return mixColor(Color.background,Color.accent,.55)
        // State hues rotate with the live theme accent, including monochrome
        // themes, which use the theme's urgent hue as their reference.
        var hue=Color.accent.hslSaturation>.08 ? Color.accent.hslHue : Color.urgent.hslHue+.5
        var shifts={warming:.45,thinking:.18,acting:.08,speaking:-.14,success:-.28,greet:-.22,wink:.14,hover:.1,needs_input:.50,drag:.35,drop:.12}
        hue=((hue+(shifts[action] || 0))%1+1)%1
        return Qt.hsla(hue,Math.max(.60,Color.accent.hslSaturation),Math.max(.54,Math.min(.68,Color.accent.hslLightness)),1)
    }
    readonly property color targetTint: stateColor()
    property color animatedTint: targetTint
    readonly property color signalTint: calm || !m.animated ? targetTint : animatedTint
    readonly property color eyeColor: mixColor(signalTint,Color.foreground,Math.min(.5,readyBurst*.25+listening*(.08+speech*.18)+talking*speech*.12))
    readonly property color screenColor: mixColor(Color.background,signalTint,m.asleep ? .025 : .09+listening*speech*.035)
    readonly property color detailColor: mixColor(signalTint,Color.foreground,.35)
    Behavior on animatedHappy { NumberAnimation { duration: root.calm ? 0 : 330; easing.type: Easing.OutCubic } }
    Behavior on animatedCurious { NumberAnimation { duration: root.calm ? 0 : 430; easing.type: Easing.OutCubic } }
    Behavior on animatedWorried { NumberAnimation { duration: root.calm ? 0 : 400; easing.type: Easing.OutCubic } }
    Behavior on animatedSurprised { NumberAnimation { duration: root.calm ? 0 : 220; easing.type: Easing.OutBack } }
    Behavior on animatedDrowsy { NumberAnimation { duration: root.calm ? 0 : 600; easing.type: Easing.InOutCubic } }
    Behavior on animatedTalking { NumberAnimation { duration: root.calm ? 0 : 160 } }
    Behavior on animatedFocused { NumberAnimation { duration: root.calm ? 0 : 280 } }
    Behavior on animatedTint { ColorAnimation { duration: root.calm || !root.m.animated ? 0 : 420; easing.type:Easing.InOutCubic } }
    vertexShader: "assets/companion/face.vert"
    fragmentShader: "assets/companion/face.frag"
}
