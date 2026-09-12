import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.Commons
import "Theme.js" as Theme

Item {
    id:root
    required property var note
    required property var controller
    property bool reducedMotion:false
    property bool checked:!!note.done
    property bool removing:false
    readonly property bool task:note.kind === "todo"
    implicitHeight:content.implicitHeight+Style.space(24)
    height:implicitHeight
    ChatStyle { id:ui }
    onNoteChanged:if(!removing) checked=!!note.done
    Connections {
        target:root.controller
        function onErrorChanged() {if(root.controller.error) root.checked=!!root.note.done}
    }
    Rectangle {
        anchors.fill:parent
        color:hit.hovered ? ui.secondary : ui.field
        radius:Style.space(7)
        border.width:hit.activeFocus ? 1 : 0
        border.color:ui.accent
        Behavior on color { ColorAnimation {duration:root.reducedMotion ? 0 : 140} }
    }
    AbstractButton {
        id:hit
        anchors.fill:parent
        hoverEnabled:true;focusPolicy:Qt.StrongFocus
        Accessible.name:root.note.body
        onClicked:root.controller.select(root.note)
    }
    RowLayout {
        id:content
        anchors.left:parent.left;anchors.right:parent.right;anchors.top:parent.top
        anchors.margins:Style.space(12)
        spacing:Style.space(10)
        AbstractButton {
            id:check
            objectName:"thoughts-checkbox"
            visible:root.task
            Layout.preferredWidth:ui.controlHeight;Layout.preferredHeight:ui.controlHeight
            Layout.alignment:Qt.AlignTop
            Accessible.name:root.checked ? "Mark to-do incomplete" : "Complete to-do"
            Accessible.role:Accessible.CheckBox;Accessible.checked:root.checked
            enabled:!root.controller.pendingId && !root.note.isDraft && !root.controller.recording && !root.controller.saving
            onClicked:{root.checked=!root.checked;root.controller.modify(root.note,"complete")}
            background:Rectangle {
                anchors.centerIn:parent;width:Style.space(19);height:width;radius:Style.space(5)
                color:root.checked ? ui.accent : "transparent"
                border.color:root.checked || check.activeFocus || check.hovered ? ui.accent : ui.border
                border.width:1
                Behavior on color {ColorAnimation {duration:root.reducedMotion ? 0 : 150} }
            }
            Icon {
                anchors.centerIn:parent;width:Style.space(13);height:width;name:"check";ink:ui.accentInk
                scale:root.checked ? 1 : .3;opacity:root.checked ? 1 : 0
                Behavior on scale {NumberAnimation {duration:root.reducedMotion ? 0 : 220;easing.type:Easing.OutBack} }
                Behavior on opacity {NumberAnimation {duration:root.reducedMotion ? 0 : 120} }
            }
        }
        ColumnLayout {
            Layout.fillWidth:true;spacing:Style.space(7)
            Text {
                id:bodyText
                Layout.fillWidth:true
                text:root.note.body;textFormat:Text.PlainText;wrapMode:Text.Wrap
                maximumLineCount:root.task ? 3 : 4;elide:Text.ElideRight
                color:root.checked ? ui.muted : ui.foreground
                font.family:ui.family;font.pixelSize:ui.body;font.strikeout:root.checked
                lineHeight:1.3
                opacity:root.checked ? .65 : 1
                Behavior on opacity {NumberAnimation {duration:root.reducedMotion ? 0 : 200} }
            }
            Text {
                visible:!root.task || !!root.note.isDraft
                text:root.note.isDraft ? "Draft" : Qt.formatDateTime(new Date(root.note.created),"MMM d · h:mm ap")
                color:ui.muted;font.family:ui.family;font.pixelSize:ui.caption
            }
            Text {
                visible:root.task && !!root.note.due && !root.checked
                text:root.note.due ? Qt.formatDateTime(new Date(root.note.due*1000),"MMM d · h:mm ap") : ""
                color:root.note.due*1000<Date.now() ? ui.danger : ui.accent
                font.family:ui.family;font.pixelSize:ui.caption
            }
        }
        Row {
            Layout.alignment:Qt.AlignTop
            opacity:hit.hovered || rowHover.hovered || chatAction.activeFocus || trashAction.activeFocus || convertAction.activeFocus ? 1 : 0.65
            Behavior on opacity {NumberAnimation {duration:root.reducedMotion ? 0 : 120} }
            HoverHandler { id:rowHover }
            ActionButton {
                id:chatAction;visible:!root.task;glyph:"chat";hint:"Discuss in chat";subtle:true
                implicitWidth:ui.controlHeight;implicitHeight:ui.controlHeight
                onClicked:root.controller.discuss(root.note)
            }
            ActionButton {
                id:convertAction;glyph:root.task ? "edit" : "check";hint:root.task ? "Turn into a note" : "Turn into a to-do";subtle:true
                implicitWidth:ui.controlHeight;implicitHeight:ui.controlHeight
                visible:!root.note.isDraft
                onClicked:root.controller.modify(root.note,"convert")
            }
            ActionButton {
                id:trashAction;glyph:"close";hint:"Delete · can be undone";subtle:true
                implicitWidth:ui.controlHeight;implicitHeight:ui.controlHeight
                enabled:!root.controller.pendingId && !root.controller.recording
                onClicked:root.controller.modify(root.note,"trash")
            }
        }
    }
    ListView.onRemove:{root.removing=true;removeAnimation.start()}
    SequentialAnimation {
        id:removeAnimation
        PropertyAction {target:root;property:"ListView.delayRemove";value:true}
        PauseAnimation {duration:root.reducedMotion ? 0 : 110}
        ParallelAnimation {
            NumberAnimation {target:root;property:"opacity";to:0;duration:root.reducedMotion ? 0 : 150}
            NumberAnimation {target:root;property:"height";to:0;duration:root.reducedMotion ? 0 : 200;easing.type:Easing.InOutCubic}
        }
        PropertyAction {target:root;property:"ListView.delayRemove";value:false}
    }
}
