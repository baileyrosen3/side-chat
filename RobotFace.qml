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
    readonly property real targetHappy: action === "success" ? 1 : action === "greet" || action === "wink" ? .85 : action === "hover" ? .6 : action === "error" || action === "needs_input" ? 0 : .32
    property real animatedHappy: targetHappy
    readonly property real happy: calm ? targetHappy : animatedHappy
    readonly property real targetCurious: action === "needs_input" ? 1 : action === "thinking" ? .65 : action === "hover" || action === "listening" ? .5 : 0
    property real animatedCurious: targetCurious
    readonly property real curious: calm ? targetCurious : animatedCurious
    readonly property real targetWorried: action === "error" ? 1 : 0
    property real animatedWorried: targetWorried
    readonly property real worried: calm ? targetWorried : animatedWorried
    readonly property real targetSurprised: action === "drag" ? 1 : action === "wake" ? .55 : 0
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
    property color eyeColor: action === "error" ? Color.urgent : Color.accent
    property color screenColor: Color.background
    property color detailColor: Color.accent
    Behavior on animatedHappy { NumberAnimation { duration: root.calm ? 0 : 330; easing.type: Easing.OutCubic } }
    Behavior on animatedCurious { NumberAnimation { duration: root.calm ? 0 : 430; easing.type: Easing.OutCubic } }
    Behavior on animatedWorried { NumberAnimation { duration: root.calm ? 0 : 400; easing.type: Easing.OutCubic } }
    Behavior on animatedSurprised { NumberAnimation { duration: root.calm ? 0 : 220; easing.type: Easing.OutBack } }
    Behavior on animatedDrowsy { NumberAnimation { duration: root.calm ? 0 : 600; easing.type: Easing.InOutCubic } }
    Behavior on animatedTalking { NumberAnimation { duration: root.calm ? 0 : 160 } }
    Behavior on animatedFocused { NumberAnimation { duration: root.calm ? 0 : 280 } }
    Behavior on eyeColor { ColorAnimation { duration: root.calm ? 0 : 350 } }
    vertexShader: "assets/companion/face.vert"
    fragmentShader: "assets/companion/face.frag"
}
