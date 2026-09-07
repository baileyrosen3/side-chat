import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.Commons
import "Theme.js" as Theme

Column {
    id: root
    required property var tools
    required property var host
    property bool expanded: false
    readonly property int runningCount: tools.filter(t => t.status === "running").length
    readonly property int failedCount: tools.filter(t => t.status === "error").length
    width: parent.width
    spacing: host.px(4)
    ActionButton {
        width: parent.width
        glyph: root.runningCount ? "terminal" : root.failedCount ? "close" : "check"
        text: root.runningCount ? "Using " + root.tools.filter(t => t.status === "running").map(t => t.name).join(", ") + "…"
                               : root.tools.length + (root.tools.length === 1 ? " action" : " actions") + (root.failedCount ? " · " + root.failedCount + " failed" : " completed")
        hint: root.expanded ? "Hide tool activity" : "Show commands, files, and results"
        subtle: true
        onClicked: root.expanded = !root.expanded
    }
    Column {
        visible: root.expanded
        width: parent.width
        spacing: root.host.px(5)
        Repeater {
            model: root.tools
            Rectangle {
                id: toolRow
                required property var modelData
                property bool detailsOpen: false
                width: parent.width
                height: details.implicitHeight + root.host.px(14)
                radius: root.host.px(3)
                color: Theme.alpha(root.host.fg, 0.035)
                Column {
                    id: details
                    x: root.host.px(7); y: root.host.px(7)
                    width: parent.width - root.host.px(14)
                    spacing: root.host.px(5)
                    AbstractButton {
                        width: parent.width
                        implicitHeight: root.host.px(22)
                        Accessible.name: toolRow.modelData.name + " " + toolRow.modelData.status
                        onClicked: toolRow.detailsOpen = !toolRow.detailsOpen
                        contentItem: RowLayout {
                            spacing: root.host.px(5)
                            Text { text: toolRow.modelData.status === "running" ? "·" : toolRow.modelData.status === "complete" ? "✓" : "×"; color: toolRow.modelData.status === "error" ? Color.urgent : Color.accent; font.family: root.host.family; font.pixelSize: root.host.textSize }
                            Text { text: toolRow.modelData.name; color: root.host.fg; font.family: root.host.family; font.pixelSize: root.host.textSize; font.weight: Font.DemiBold }
                            Text {
                                Layout.fillWidth: true
                                text: String(toolRow.modelData.args.command || toolRow.modelData.args.path || toolRow.modelData.args.pattern || "")
                                elide: Text.ElideMiddle; color: root.host.dim; font.family: root.host.family; font.pixelSize: root.host.textSize
                            }
                        }
                    }
                    TextEdit {
                        visible: toolRow.detailsOpen
                        width: parent.width
                        text: JSON.stringify(toolRow.modelData.args, null, 2) + (toolRow.modelData.output ? "\n\n" + toolRow.modelData.output : "")
                        textFormat: TextEdit.PlainText; readOnly: true; selectByMouse: true; wrapMode: TextEdit.WrapAnywhere
                        color: root.host.dim; font.family: root.host.family; font.pixelSize: root.host.textSize
                        selectionColor: Theme.alpha(Color.accent, 0.35)
                    }
                }
            }
        }
    }
}
