import QtQuick
import QtQuick.Controls
import qs.Commons

SpinBox {
    id: root
    ChatStyle { id: ui }
    implicitHeight: ui.controlHeight
    implicitWidth: Style.space(118)
    leftPadding: ui.controlHeight
    rightPadding: ui.controlHeight
    editable: true
    validator: RegularExpressionValidator { regularExpression: /[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:\s*[^0-9]*)?/ }
    font.family: ui.family
    font.pixelSize: ui.small
    palette.text: ui.foreground
    palette.base: ui.field
    palette.highlight: ui.accent
    palette.highlightedText: ui.accentInk
    opacity: enabled ? 1 : .45
    contentItem: TextInput {
        text: root.displayText
        font: root.font
        color: ui.foreground
        selectionColor: ui.accent
        selectedTextColor: ui.accentInk
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        readOnly: !root.editable
        validator: root.validator
        inputMethodHints: Qt.ImhFormattedNumbersOnly
    }
    down.indicator: Rectangle {
        x: 1; y: 1
        width: ui.controlHeight - 2; height: root.height - 2
        color: root.down.pressed || root.down.hovered ? ui.secondary : "transparent"
        Rectangle { anchors.centerIn: parent; width: Style.space(7); height: 1; color: root.down.enabled ? ui.foreground : ui.border }
    }
    up.indicator: Rectangle {
        x: root.width - width - 1; y: 1
        width: ui.controlHeight - 2; height: root.height - 2
        color: root.up.pressed || root.up.hovered ? ui.secondary : "transparent"
        Icon { anchors.centerIn: parent; width: Style.space(12); height: width; name: "new"; ink: root.up.enabled ? ui.foreground : ui.border }
    }
    background: Rectangle {
        color: ui.field
        border.width: root.activeFocus ? ui.stroke : 1
        border.color: root.activeFocus ? ui.accent : ui.border
    }
}
