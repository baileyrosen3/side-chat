import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.Commons

Item {
    id:root
    required property var model
    property bool active:true
    property bool reducedMotion:false
    readonly property bool capture:model.mode==="capture"
    readonly property bool trash:model.mode==="trash"
    enabled:active
    property real reveal:0
    opacity:reveal
    transform:Translate {y:Style.space(6)*(1-root.reveal)}
    Behavior on reveal {NumberAnimation {duration:root.reducedMotion ? 0 : 160;easing.type:Easing.OutCubic}}
    ChatStyle {id:ui}
    function focusEditor() {if(active) {if(capture) passage.forceActiveFocus();else search.forceActiveFocus()}}
    Component.onCompleted:{reveal=1;Qt.callLater(root.focusEditor)}
    Connections {target:root.model;function onFocusInput() {root.focusEditor()}}
    Shortcut {sequence:"Escape";enabled:root.active && root.visible;onActivated:root.model.dismiss()}
    ColumnLayout {
        anchors.fill:parent;spacing:Style.space(10)
        RowLayout {
            Layout.fillWidth:true
            ActionButton {glyph:"back";hint:"Back · Esc";subtle:true;onClicked:root.model.dismiss()}
            Text {
                Layout.fillWidth:true;text:root.capture ? "Capture" : root.trash ? "Recently deleted" : "Search everything"
                color:ui.foreground;font.family:ui.family;font.pixelSize:ui.body;font.weight:Font.DemiBold
            }
            Text {visible:!root.capture;text:root.model.busy ? "Searching…" : "";color:ui.muted;font.family:ui.family;font.pixelSize:ui.caption}
        }
        ChatField {
            id:search;objectName:"workspace-search-input";Layout.fillWidth:true
            visible:!root.capture;glyph:"search"
            placeholderText:root.trash ? "Find something to restore…" : "Notes, to-dos, conversations…"
            Accessible.name:"Search workspace"
            text:root.model.query;onTextEdited:root.model.query=text
            Keys.onDownPressed:event=>{if(results.count) results.currentIndex=Math.min(results.count-1,results.currentIndex+1);event.accepted=true}
            Keys.onUpPressed:event=>{if(results.count) results.currentIndex=Math.max(0,results.currentIndex-1);event.accepted=true}
            onAccepted:if(results.currentIndex>=0 && results.currentIndex<root.model.results.length) root.model.activate(root.model.results[results.currentIndex])
        }
        Text {
            visible:root.capture && !!root.model.captureSource.label
            Layout.fillWidth:true;text:"From " + (root.model.captureSource.label || "selection")
            textFormat:Text.PlainText;color:ui.muted;font.family:ui.family;font.pixelSize:ui.caption;elide:Text.ElideRight
        }
        Rectangle {
            visible:root.capture;Layout.fillWidth:true;Layout.fillHeight:true
            color:ui.field;radius:Style.space(10);border.width:1;border.color:passage.activeFocus ? ui.accent : ui.border
            ScrollView {
                anchors.fill:parent;anchors.margins:Style.space(12)
                clip:true;contentWidth:availableWidth;ScrollBar.vertical:ChatScrollBar {}
                TextArea {
                    id:passage;objectName:"workspace-capture-input"
                    width:parent.width;padding:0
                    text:root.model.captureBody;onTextChanged:if(text!==root.model.captureBody) root.model.captureBody=text
                    placeholderText:"Copy a passage, then choose Use clipboard."
                    placeholderTextColor:ui.muted;textFormat:TextEdit.PlainText
                    color:ui.foreground;wrapMode:TextEdit.Wrap;selectByMouse:true
                    font.family:ui.family;font.pixelSize:ui.body
                    selectionColor:ui.accent;selectedTextColor:ui.accentInk
                    Accessible.name:"Captured text";background:Item {}
                }
            }
        }
        RowLayout {
            visible:root.capture;Layout.fillWidth:true;spacing:Style.space(5)
            ActionButton {text:"Note";glyph:"edit";hint:"Keep as a note draft";Layout.fillWidth:true;enabled:!!root.model.captureBody.trim();onClicked:root.model.useCapture("note")}
            ActionButton {text:"To-do";glyph:"check";hint:"Make a to-do draft";Layout.fillWidth:true;enabled:!!root.model.captureBody.trim();onClicked:root.model.useCapture("todo")}
            ActionButton {text:"Ask Peek";glyph:"orb";hint:"Add to chat and review before sending";Layout.fillWidth:true;enabled:!!root.model.captureBody.trim();onClicked:root.model.useCapture("chat")}
        }
        ListView {
            id:results;objectName:"workspace-search-results"
            visible:!root.capture;Layout.fillWidth:true;Layout.fillHeight:true
            clip:true;spacing:Style.space(6);boundsBehavior:Flickable.StopAtBounds
            model:root.model.results;currentIndex:count ? 0 : -1
            onCurrentIndexChanged:if(currentIndex>=0) positionViewAtIndex(currentIndex,ListView.Contain)
            ScrollBar.vertical:ChatScrollBar {}
            delegate:AbstractButton {
                id:result
                required property var modelData
                required property int index
                width:ListView.view.width-Style.space(3);implicitHeight:resultContent.implicitHeight+Style.space(20)
                hoverEnabled:true;focusPolicy:Qt.StrongFocus
                Accessible.name:(root.trash ? "Restore " : "Open ")+modelData.title
                enabled:modelData.kind!=="warning" && !root.model.busy
                onClicked:root.model.activate(modelData)
                background:Rectangle {
                    radius:Style.space(8);color:result.hovered || result.activeFocus || results.currentIndex===result.index ? ui.secondary : ui.field
                    border.width:results.currentIndex===result.index || result.activeFocus ? 1 : 0;border.color:ui.accent
                    Behavior on color {ColorAnimation {duration:root.reducedMotion ? 0 : 120}}
                }
                contentItem:ColumnLayout {
                    id:resultContent
                    anchors.left:parent.left;anchors.right:parent.right;anchors.verticalCenter:parent.verticalCenter
                    anchors.margins:Style.space(10);spacing:Style.space(4)
                    RowLayout {
                        Layout.fillWidth:true
                        Text {Layout.fillWidth:true;text:result.modelData.title;textFormat:Text.PlainText;color:ui.foreground;font.family:ui.family;font.pixelSize:ui.small;font.weight:Font.DemiBold;elide:Text.ElideRight}
                        Text {text:root.trash ? "Restore" : result.modelData.kind==="chat" ? "Chat" : result.modelData.kind==="todo" ? "To-do" : result.modelData.kind==="note" ? "Note" : "";color:ui.accent;font.family:ui.family;font.pixelSize:ui.caption}
                    }
                    Text {Layout.fillWidth:true;text:result.modelData.snippet;textFormat:Text.PlainText;color:ui.muted;font.family:ui.family;font.pixelSize:ui.caption;wrapMode:Text.Wrap;maximumLineCount:2;elide:Text.ElideRight}
                }
            }
            Text {
                anchors.centerIn:parent;width:parent.width-Style.space(24)
                visible:!results.count && !root.model.busy
                text:root.trash ? "Nothing here. Deleted notes, tasks, and chats can be restored here." : root.model.query ? "No matches. Try another word." : "Your saved notes, tasks, and conversations will appear here."
                color:ui.muted;font.family:ui.family;font.pixelSize:ui.small;wrapMode:Text.Wrap;horizontalAlignment:Text.AlignHCenter
            }
        }
        Text {visible:!!root.model.error;Layout.fillWidth:true;text:root.model.error;textFormat:Text.PlainText;color:ui.danger;font.family:ui.family;font.pixelSize:ui.small;wrapMode:Text.Wrap}
        RowLayout {
            Layout.fillWidth:true
            Text {Layout.fillWidth:true;text:root.capture ? "Review it before saving or sending." : root.trash ? "Kept until you restore them." : "↑ ↓ to choose · Return to open";color:ui.muted;font.family:ui.family;font.pixelSize:ui.caption;wrapMode:Text.Wrap}
            ActionButton {
                visible:!root.trash;glyph:"clipboard";text:root.capture ? "Use clipboard" : "Clipboard"
                subtle:true;enabled:!root.model.capturing
                hint:"Read copied text from the clipboard";onClicked:root.model.capture(true)
            }
        }
    }
}
