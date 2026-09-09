import QtQuick
import QtQuick.Layouts
import qs.Commons

RowLayout {
    id: root
    property string text: ""
    Layout.fillWidth: true
    Layout.topMargin: Style.space(5)
    Layout.bottomMargin: Style.space(3)
    spacing: Style.space(8)
    ChatStyle { id: ui }
    Rectangle {
        Layout.preferredWidth: Style.space(3)
        Layout.preferredHeight: Style.space(10)
        color: ui.accent
    }
    Text {
        text: root.text.toUpperCase()
        color: ui.muted
        font.family: ui.family
        font.pixelSize: ui.caption
        font.weight: Font.DemiBold
        font.letterSpacing: 1
        Accessible.role: Accessible.Heading
    }
    Rectangle {
        Layout.fillWidth: true
        implicitHeight: 1
        color: ui.line
    }
}
