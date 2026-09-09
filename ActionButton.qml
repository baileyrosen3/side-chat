import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "Theme.js" as Theme
import qs.Commons

AbstractButton {
    id: root

    property string glyph: ""
    property string trailingGlyph: ""
    property bool accent: false
    property bool subtle: false
    property bool selected: false
    property bool tab: false
    property bool uppercase: tab || accent
    property int textAlignment: Text.AlignHCenter
    property string hint: ""
    property color ink: accent || selected ? ui.accentInk : subtle && !hovered && !activeFocus ? ui.muted : ui.foreground
    readonly property real lift: accent || tab && selected ? ui.shadow : 0

    implicitWidth: Math.max(ui.controlHeight, content.implicitWidth + leftPadding + rightPadding)
    implicitHeight: ui.controlHeight
    leftPadding: Style.space(text ? 9 : 5)
    rightPadding: leftPadding
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    opacity: enabled ? 1 : 0.4
    Accessible.name: hint || text
    Accessible.role: tab ? Accessible.PageTab : Accessible.Button
    Accessible.checkable: tab || checkable
    Accessible.checked: tab ? selected : checked

    ChatStyle {
        id: ui
    }

    HoverHandler {
        cursorShape: root.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
    }

    ToolTip {
        visible: root.hovered && root.hint !== ""
        text: root.hint
        delay: 450
        timeout: 4500
        width: Math.min(implicitWidth, Style.space(280))

        contentItem: Text {
            text: root.hint
            color: ui.foreground
            font.family: Style.font.family
            font.pixelSize: ui.small
            wrapMode: Text.WordWrap
        }

        background: Rectangle {
            color: ui.surface
            radius: ui.radius
            border.width: ui.stroke
            border.color: ui.line
        }

    }

    Behavior on opacity {
        NumberAnimation {
            duration: 140
        }

    }

    contentItem: RowLayout {
        id: content

        spacing: Style.space(4)
        transform: Translate { x: root.down ? root.lift : 0; y: x }

        Icon {
            visible: root.glyph !== ""
            name: root.glyph
            ink: root.ink
            Layout.preferredWidth: Style.space(13)
            Layout.preferredHeight: Style.space(13)
            Layout.alignment: Qt.AlignVCenter
        }

        Text {
            visible: root.text !== ""
            Layout.fillWidth: true
            text: root.uppercase ? root.text.toUpperCase() : root.text
            color: root.ink
            font.family: Style.font.family
            font.pixelSize: ui.small
            font.weight: root.accent || root.selected || root.tab ? Font.DemiBold : Font.Medium
            font.letterSpacing: root.tab ? 0.35 : 0
            elide: Text.ElideRight
            horizontalAlignment: root.textAlignment
            verticalAlignment: Text.AlignVCenter
        }

        Icon {
            visible: root.trailingGlyph !== ""
            name: root.trailingGlyph
            ink: root.ink
            Layout.preferredWidth: Style.space(10)
            Layout.preferredHeight: Style.space(10)
        }

    }

    background: Item {
        Rectangle {
            x: root.lift
            y: root.lift
            width: parent.width - root.lift
            height: parent.height - root.lift
            color: ui.foreground
            visible: root.lift > 0 && root.enabled
        }

        Rectangle {
            x: root.down ? root.lift : 0
            y: x
            width: parent.width - root.lift
            height: parent.height - root.lift
            color: root.accent || root.selected ? ui.accent : root.hovered || root.activeFocus ? ui.secondary : root.subtle || root.tab ? "transparent" : ui.field
            border.width: root.activeFocus || root.accent ? ui.stroke : root.selected || !root.subtle && !root.tab ? 1 : 0
            border.color: root.activeFocus || root.accent ? ui.foreground : ui.border
        }

    }

}
