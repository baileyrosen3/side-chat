// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.Commons
import "Theme.js" as Theme
import "RobotExpressions.js" as Catalog

ColumnLayout {
    id: root
    property bool reducedMotion: false
    property real expressiveness: 1
    signal settingChanged(string key, var value)
    spacing: Style.space(8)
    component Label: Text {
        Layout.fillWidth: true; wrapMode: Text.Wrap
        color: Theme.alpha(Color.foreground,.62)
        font.family: Style.font.family; font.pixelSize: Style.font.body
    }
    Label { text: "Meet Peek"; color: Color.foreground; font.bold: true }
    Rectangle {
        Layout.fillWidth: true; implicitHeight: Style.space(165)
        radius: Style.space(5); color: Theme.alpha(Color.foreground,.025)
        clip: true
        Item {
            anchors.centerIn: parent; width: Style.space(125); height: parent.height
            // The same left-edge crop as the live companion.
            clip: true
            Rectangle { x: 0; y: Style.space(15); width: 1; height: parent.height-Style.space(30); color: Theme.alpha(Color.foreground,.16) }
            JarvisBuddy {
                id: preview
                objectName: "companion-preview"
                x: -Style.space(66); y: -Style.space(12); width: Style.space(200); height: width
                reducedMotion: root.reducedMotion; expressiveness: root.expressiveness
                mood: "idle"
            }
        }
        Text {
            anchors.left: parent.left; anchors.bottom: parent.bottom; anchors.margins: Style.space(8)
            text: Catalog.actionName(preview.currentAction)
            color: Theme.alpha(Color.foreground,.55); font.family: Style.font.family; font.pixelSize: Style.font.body
        }
        Text {
            anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: Style.space(8)
            text: "Preview · no mic"
            color: Theme.alpha(Color.foreground,.45); font.family: Style.font.family; font.pixelSize: Style.font.body
        }
    }
    Label { text: "A curious little robot with a warm smile, expressive eyes, and a soft spot for a job well done." }
    RowLayout {
        Layout.fillWidth: true; spacing: Style.space(5)
        ComboBox {
            id: reaction
            objectName: "companion-reaction"
            Layout.fillWidth: true; implicitHeight: Style.space(28)
            model: Catalog.actions; textRole: "name"; valueRole: "id"
            font.family: Style.font.family; font.pixelSize: Style.font.body
            palette.button: Color.background; palette.buttonText: Color.foreground
            palette.text: Color.foreground; palette.base: Color.background; palette.highlight: Color.accent
            Accessible.name: "Preview companion reaction"
            onActivated: preview.preview(Catalog.actions[currentIndex].id)
        }
        ActionButton { text: "Replay"; onClicked: preview.preview(Catalog.actions[reaction.currentIndex].id) }
    }
    Label { text: "19 expressions · try a greeting, a task, or a celebration. Apply to keep your motion settings." }
    RowLayout {
        Layout.fillWidth: true
        Label { text: "Reduce motion" }
        ActionButton {
            text: root.reducedMotion ? "On" : "Off"; selected: root.reducedMotion
            Accessible.name: "Reduce companion motion: "+text
            onClicked: root.settingChanged("reducedMotion",!root.reducedMotion)
        }
    }
    RowLayout {
        Layout.fillWidth: true
        Label { text: "Expression" }
        Slider {
            Layout.fillWidth: true; Layout.maximumWidth: Style.space(145)
            from: 0; to: 1.5; stepSize: .1; value: root.expressiveness
            Accessible.name: "Companion expression"
            onMoved: root.settingChanged("expressiveness",Math.round(value*10)/10)
        }
        Label { Layout.fillWidth: false; text: root.expressiveness.toFixed(1)+"×" }
    }
    Label { visible: root.reducedMotion || root.expressiveness === 0; text: "Motion is paused. Static poses and status captions still show what’s happening." }
}
