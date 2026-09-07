import QtQuick
import QtQuick.Controls
import "Theme.js" as Theme
import qs.Commons

AbstractButton {
    id: root

    property string glyph: ""
    property bool accent: false
    property bool subtle: false
    property bool selected: false
    property string hint: ""
    property color ink: accent ? Color.background : hovered || selected ? Color.accent : Color.foreground

    implicitWidth: Math.max(Style.space(26), content.implicitWidth + Style.space(text ? 14 : 10))
    implicitHeight: Style.space(26)
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    opacity: enabled ? 1 : 0.3
    scale: down ? 0.98 : 1
    Accessible.name: hint || text

    HoverHandler {
        cursorShape: root.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
    }

    ToolTip {
        visible: root.hovered && root.hint !== ""
        text: root.hint
        delay: 450
        timeout: 4500

        contentItem: Text {
            text: root.hint
            color: Color.foreground
            font.family: Style.font.family
            font.pixelSize: Style.font.body
        }

        background: Rectangle {
            color: Color.popups.background
            radius: Style.space(3)
            border.width: 1
            border.color: Theme.alpha(Color.foreground, 0.14)
        }

    }

    Behavior on scale {
        NumberAnimation {
            duration: 100
            easing.type: Easing.OutCubic
        }

    }

    Behavior on opacity {
        NumberAnimation {
            duration: 140
        }

    }

    contentItem: Item {
        implicitWidth: content.implicitWidth

        Row {
            id: content

            anchors.centerIn: parent
            spacing: Style.space(5)

            Icon {
                visible: root.glyph !== ""
                name: root.glyph
                ink: root.ink
                width: Style.space(14)
                height: width
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                visible: root.text !== ""
                text: root.text
                color: root.ink
                font.family: Style.font.family
                font.pixelSize: Style.font.body
                font.weight: root.accent || root.selected ? Font.DemiBold : Font.Normal
                anchors.verticalCenter: parent.verticalCenter
            }

        }

    }

    background: Rectangle {
        radius: Style.space(3)
        color: root.accent ? Color.accent : Theme.alpha(Color.foreground, root.down ? 0.1 : root.hovered ? 0.055 : 0)
        border.width: root.activeFocus ? 1 : 0
        border.color: Color.accent

        Rectangle {
            visible: root.selected && !root.accent
            anchors.bottom: parent.bottom
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width - Style.space(14)
            height: 1
            color: Color.accent
        }

        Behavior on color {
            ColorAnimation {
                duration: 130
            }

        }

    }

}
