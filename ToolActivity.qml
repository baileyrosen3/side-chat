import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.Commons
import "Theme.js" as Theme

Column {
    id: root
    ChatStyle { id: ui }
    required property var tools
    required property var host
    property bool expanded: false
    readonly property int runningCount: tools.filter(t => t.status === "running").length
    readonly property int failedCount: tools.filter(t => t.status === "error").length
    readonly property int stoppedCount: tools.filter(t => t.status === "stopped").length
    readonly property int completedCount: tools.filter(t => t.status === "complete").length
    width: parent.width
    spacing: host.px(4)
    ActionButton {
        width: parent.width
        textAlignment: Text.AlignLeft
        glyph: root.runningCount ? "terminal" : root.failedCount ? "close" : root.stoppedCount ? "stop" : "check"
        trailingGlyph: root.expanded ? "chevron-up" : "chevron-down"
        text: root.runningCount ? "Using " + root.tools.filter(t => t.status === "running").map(t => Theme.toolName(t.name)).join(", ") + "…"
                               : [root.completedCount ? root.completedCount + " completed" : "", root.failedCount ? root.failedCount + " failed" : "", root.stoppedCount ? root.stoppedCount + " stopped" : ""].filter(Boolean).join(" · ") || "Tool activity"
        hint: root.expanded ? "Hide tool activity" : "Show commands, files, and results"
        subtle: false
        onClicked: root.expanded = !root.expanded
    }
    Column {
        visible: root.expanded
        width: parent.width
        spacing: root.host.px(5)
        Repeater {
            model: root.expanded ? root.tools : []
            Rectangle {
                id: toolRow
                required property var modelData
                property bool detailsOpen: false
                width: parent.width
                height: details.implicitHeight + root.host.px(12)
                radius: ui.radius
                color: ui.field
                border.width: 1; border.color: ui.line
                Column {
                    id: details
                    x: root.host.px(6); y: root.host.px(6)
                    width: parent.width - root.host.px(12)
                    spacing: root.host.px(5)
                    AbstractButton {
                        width: parent.width
                        implicitHeight: ui.controlHeight
                        background: Rectangle { color: "transparent"; radius: ui.radius; border.width: parent.activeFocus ? 1 : 0; border.color: ui.accent }
                        Accessible.name: Theme.toolName(toolRow.modelData.name) + " " + toolRow.modelData.status
                        hoverEnabled: true
                        focusPolicy: Qt.StrongFocus
                        onClicked: toolRow.detailsOpen = !toolRow.detailsOpen
                        contentItem: RowLayout {
                            spacing: root.host.px(5)
                            Icon { name: toolRow.modelData.status === "running" ? "chevron-right" : toolRow.modelData.status === "complete" ? "check" : "close"; ink: toolRow.modelData.status === "error" ? ui.danger : toolRow.modelData.status === "running" ? ui.muted : ui.emphasis; Layout.preferredWidth: root.host.px(11); Layout.preferredHeight: root.host.px(11) }
                            Text { Layout.maximumWidth: parent.width * 0.45; elide: Text.ElideRight; text: Theme.toolName(toolRow.modelData.name); color: root.host.fg; font.family: root.host.family; font.pixelSize: ui.small; font.weight: Font.Bold }
                            Text {
                                Layout.fillWidth: true
                                text: String(toolRow.modelData.args.command || toolRow.modelData.args.path || toolRow.modelData.args.pattern || "")
                                elide: Text.ElideMiddle; color: root.host.dim; font.family: root.host.family; font.pixelSize: ui.small
                            }
                            Icon { name: toolRow.detailsOpen ? "chevron-up" : "chevron-down"; ink: ui.muted; Layout.preferredWidth: root.host.px(10); Layout.preferredHeight: root.host.px(10) }
                        }
                    }
                    TextEdit {
                        visible: toolRow.detailsOpen
                        width: parent.width
                        text: JSON.stringify(toolRow.modelData.args, null, 2) + (toolRow.modelData.output ? "\n\n" + toolRow.modelData.output : "")
                        textFormat: TextEdit.PlainText; readOnly: true; selectByMouse: true; wrapMode: TextEdit.WrapAnywhere
                        color: root.host.dim; font.family: root.host.family; font.pixelSize: ui.small
                        selectionColor: Theme.alpha(ui.emphasis, 0.35)
                    }
                }
            }
        }
    }
}
