// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.Commons

ColumnLayout {
    id: root
    required property var task
    property bool expanded: false
    ChatStyle { id: ui }
    spacing: Style.space(5)
    visible: (task.total || 0) > 0
    function stateLabel(state) {
        return ({running:"Working",verified:"Verified",observed:"Observed",performed:"Performed",
                 failed:"Failed",stopped:"Stopped",unconfirmed:"Not confirmed"})[state] || state
    }
    ActionButton {
        objectName: "task-details-toggle"
        Layout.fillWidth: true
        subtle: true
        textAlignment: Text.AlignLeft
        text: root.task.total + (root.task.total === 1 ? " step" : " steps") + (root.task.checked ? " · " + root.task.checked + " verified" : "")
        trailingGlyph: root.expanded ? "chevron-up" : "chevron-down"
        hint: root.expanded ? "Hide action details" : "Show performed actions and checks"
        checkable: true; checked: root.expanded
        onClicked: root.expanded = !root.expanded
    }
    ColumnLayout {
        visible: root.expanded
        Layout.fillWidth: true
        spacing: Style.space(5)
        Repeater {
            model: (root.task.steps || []).slice(-4)
            RowLayout {
                required property var modelData
                Layout.fillWidth: true
                spacing: Style.space(6)
                Icon {
                    name: modelData.state === "verified" ? "check" : modelData.state === "failed" ? "close" : "chevron-right"
                    ink: modelData.state === "failed" ? ui.danger : modelData.state === "verified" ? ui.accent : ui.muted
                    Layout.preferredWidth: Style.space(11); Layout.preferredHeight: Style.space(11)
                }
                Text {
                    Layout.fillWidth: true
                    text: modelData.label
                    color: ui.foreground; font.family: ui.family; font.pixelSize: ui.small
                    textFormat: Text.PlainText; elide: Text.ElideRight
                    Accessible.name: modelData.label + ". " + root.stateLabel(modelData.state) + (modelData.evidence ? ". " + modelData.evidence : "")
                    HoverHandler { id: hover }
                    ToolTip.visible: hover.hovered
                    ToolTip.text: modelData.evidence || modelData.label
                    ToolTip.delay: 500
                }
                Text {
                    text: root.stateLabel(modelData.state)
                    color: modelData.state === "failed" ? ui.danger : ui.muted
                    font.family: ui.family; font.pixelSize: ui.caption
                }
            }
        }
        Text {
            visible: root.task.total > 4
            Layout.fillWidth: true
            text: "Latest 4 of " + root.task.total + " · full details in chat"
            color: ui.muted; font.family: ui.family; font.pixelSize: ui.caption
            wrapMode: Text.WordWrap
        }
    }
}
