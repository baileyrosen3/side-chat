// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick

Item {
    id: root
    property bool present: false
    property bool reducedMotion: false
    property real progress: 0
    property bool initialized: false
    readonly property bool rendered: present || progress > 0
    readonly property bool interactive: present && progress >= .98
    readonly property bool moving: travel.running

    function update() {
        if (!initialized) return
        // Starting from the current value also makes a mid-flight reversal
        // continuous. Never reset to the beginning of an entrance or exit.
        travel.stop()
        var target=present ? 1 : 0
        if (reducedMotion || Math.abs(target-progress)<.001) { progress=target;return }
        travel.to=target
        travel.duration=Math.max(90,(present ? 620 : 420)*Math.abs(target-progress))
        travel.easing.type=present ? Easing.OutCubic : Easing.InOutCubic
        travel.start()
    }
    onPresentChanged: update()
    onReducedMotionChanged: update()
    Component.onCompleted: { initialized=true;update() }
    NumberAnimation {
        id: travel
        target: root; property: "progress"
        easing.type: Easing.InOutCubic
    }
}
