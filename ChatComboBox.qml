import QtQuick
import QtQuick.Controls
import qs.Commons
import "Theme.js" as Theme

ComboBox {
    id: root

    implicitHeight: ui.controlHeight
    implicitWidth: Style.space(132)
    font.family: ui.family
    font.pixelSize: ui.small
    opacity: enabled ? 1 : 0.45
    palette.button: ui.surface
    palette.buttonText: ui.foreground
    palette.text: ui.foreground
    palette.base: ui.surface
    palette.highlight: ui.accent
    palette.highlightedText: ui.accentInk

    ChatStyle {
        id: ui
    }

    contentItem: Text {
        leftPadding: Style.space(8)
        rightPadding: Style.space(24)
        text: root.displayText
        font: root.font
        color: ui.foreground
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    indicator: Icon {
        x: root.width - width - Style.space(8)
        anchors.verticalCenter: parent.verticalCenter
        name: "chevron-down"
        ink: ui.muted
        width: Style.space(12)
        height: width
    }

    background: Rectangle {
        radius: ui.radius
        color: root.hovered ? ui.secondary : ui.field
        border.width: root.activeFocus ? ui.stroke : 1
        border.color: root.activeFocus ? ui.accent : ui.border
    }

    delegate: ItemDelegate {
        required property int index

        width: root.width
        implicitHeight: ui.controlHeight
        highlighted: root.highlightedIndex === index

        contentItem: Text {
            text: root.textAt(index)
            color: parent.highlighted ? ui.accentInk : ui.foreground
            font: root.font
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
        }

        background: Rectangle {
            radius: ui.radius
            color: parent.highlighted ? ui.accent : "transparent"
        }

    }

    popup: Popup {
        y: root.height + Style.space(3)
        width: root.width
        padding: Style.space(3)
        implicitHeight: Math.min(contentItem.implicitHeight + padding * 2, Style.space(240))

        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: root.popup.visible ? root.delegateModel : null
            currentIndex: root.highlightedIndex

            ScrollBar.vertical: ChatScrollBar {
            }

        }

        background: Rectangle {
            color: ui.surface
            radius: ui.radius
            border.width: ui.stroke
            border.color: ui.border
        }

    }

}
