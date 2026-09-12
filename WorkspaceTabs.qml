import QtQuick
import QtQuick.Controls
import qs.Commons

Item {
    id: root
    property string section: "chat"
    property bool reducedMotion: false
    property bool notesLocked: false
    property bool compact: false
    readonly property int selectedIndex: section === "notes" ? 1 : section === "todos" ? 2 : 0
    signal chosen(string section)
    implicitHeight: Style.space(compact ? 32 : 36)
    ChatStyle { id: ui }

    Rectangle { anchors.fill: parent; color: ui.field; radius: Style.space(7) }
    Rectangle {
        objectName: "workspace-tab-highlight"
        x: root.selectedIndex * root.width / 3 + Style.space(3)
        y: Style.space(3)
        width: root.width / 3 - Style.space(6)
        height: root.height - Style.space(6)
        color: ui.secondary; radius: Style.space(5)
        border.width: 1; border.color: ui.line
        Behavior on x { NumberAnimation { duration: root.reducedMotion ? 0 : 220; easing.type: Easing.OutCubic } }
    }
    Row {
        anchors.fill: parent
        Repeater {
            model: [{section:"chat",text:"Chat",icon:"chat"}, {section:"notes",text:"Notes",icon:"edit"}, {section:"todos",text:"To-dos",icon:"check"}]
            AbstractButton {
                required property var modelData
                objectName: "workspace-tab-" + modelData.section
                width: root.width / 3; height: root.height
                enabled: !root.notesLocked || modelData.section === "chat"
                Accessible.name: modelData.text
                Accessible.role: Accessible.PageTab
                Accessible.checked: root.section === modelData.section
                onClicked: root.chosen(modelData.section)
                background: Rectangle { color:"transparent"; radius:Style.space(5); border.width:parent.activeFocus ? 1 : 0; border.color:ui.accent }
                contentItem: Item {
                    Row {
                        anchors.centerIn: parent; spacing: Style.space(5)
                        Icon {
                            visible: !root.compact
                            name: modelData.icon; ink: root.section === modelData.section ? ui.foreground : ui.muted
                            width: Style.space(12); height: width; anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            text: modelData.text; color: root.section === modelData.section ? ui.foreground : ui.muted
                            font.family: ui.family; font.pixelSize: ui.small; font.weight: Font.Medium
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                }
            }
        }
    }
}
