// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.Commons
import "Theme.js" as Theme
import "RobotExpressions.js" as Catalog

ColumnLayout {
    id: root
    ChatStyle { id: ui }
    property bool reducedMotion: false
    property real expressiveness: 1
    signal settingChanged(string key, var value)
    spacing: Style.space(6)
    component Label: Text {
        Layout.fillWidth: true; wrapMode: Text.Wrap
        color: ui.muted
        font.family: Style.font.family; font.pixelSize: ui.small
    }
    ChatSection { text: "Meet Peek" }
    Rectangle {
        Layout.fillWidth: true; implicitHeight: Style.space(100)
        radius: 0; color: ui.secondary
        border.width: 1; border.color: ui.border
        clip: true
        JarvisBuddy {
            id: preview
            objectName: "companion-preview"
            anchors.centerIn: parent
            width: Style.space(132); height: width
            reducedMotion: root.reducedMotion; expressiveness: root.expressiveness
            mood: "idle"
        }
        Text {
            anchors.left: parent.left; anchors.bottom: parent.bottom; anchors.margins: Style.space(8)
            text: Catalog.actionName(preview.currentAction)
            color: ui.foreground; font.family: Style.font.family; font.pixelSize: ui.small
        }
        Text {
            anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: Style.space(8)
            text: "Preview · no mic"
            color: ui.muted; font.family: Style.font.family; font.pixelSize: ui.small
        }
    }
    RowLayout {
        Layout.fillWidth: true; spacing: Style.space(5)
        ChatComboBox {
            id: reaction
            objectName: "companion-reaction"
            Layout.fillWidth: true
            model: Catalog.actions; textRole: "name"; valueRole: "id"
            Accessible.name: "Preview companion reaction"
            onActivated: preview.preview(Catalog.actions[currentIndex].id)
        }
        ActionButton { text: "Replay"; onClicked: preview.preview(Catalog.actions[reaction.currentIndex].id) }
    }
    Label { text: "Follows the task while working and turns back when you speak. Click for more controls." }
    RowLayout {
        Layout.fillWidth: true
        Label { text: "Reduce motion" }
        ChatSwitch {
            checked: root.reducedMotion
            Accessible.name: "Reduce companion motion: "+text
            onClicked: root.settingChanged("reducedMotion",!root.reducedMotion)
        }
    }
    RowLayout {
        Layout.fillWidth: true
        Label { text: "Expression" }
        Slider {
            id: expressionSlider
            implicitWidth: Style.space(145)
            implicitHeight: ui.controlHeight
            Layout.fillWidth: true; Layout.maximumWidth: Style.space(145)
            from: 0; to: 1.5; stepSize: .1; value: root.expressiveness
            background: Rectangle {
                x: expressionSlider.leftPadding
                y: expressionSlider.topPadding + expressionSlider.availableHeight / 2 - height / 2
                width: expressionSlider.availableWidth
                height: Style.space(6)
                color: ui.field
                border.width: 1; border.color: ui.foreground
                Rectangle { width: expressionSlider.visualPosition * parent.width; height: parent.height; color: ui.accent }
            }
            handle: Rectangle {
                x: expressionSlider.leftPadding + expressionSlider.visualPosition * (expressionSlider.availableWidth - width)
                y: expressionSlider.topPadding + expressionSlider.availableHeight / 2 - height / 2
                width: Style.space(12); height: Style.space(16)
                color: expressionSlider.pressed || expressionSlider.activeFocus ? ui.accent : ui.surface
                border.width: 1; border.color: ui.border
            }
            Accessible.name: "Companion expression"
            onMoved: root.settingChanged("expressiveness",Math.round(value*10)/10)
        }
        Label { Layout.fillWidth: false; text: root.expressiveness.toFixed(1)+"×" }
    }
    Label { visible: root.reducedMotion || root.expressiveness === 0; text: "Motion paused; expressions and status remain visible." }
}
