import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.Commons
import "Theme.js" as Theme

Item {
    id:root
    required property var model
    property bool reducedMotion:false
    readonly property bool todos:model.kind === "todo"
    property bool active:true
    implicitHeight: content.implicitHeight
    enabled:active
    clip:true
    ChatStyle {id:ui}
    function px(n) {return Style.space(n)}
    function syncList(target,rows) {
        var wanted=rows.map(n=>n.id || n.key)
        for(var i=target.count-1;i>=0;i--) if(wanted.indexOf(target.get(i).identity)<0) target.remove(i)
        for(var j=0;j<rows.length;j++) {
            var id=wanted[j],at=-1
            for(var k=j;k<target.count;k++) if(target.get(k).identity===id) {at=k;break}
            if(at<0) target.insert(j,{identity:id,note:rows[j]})
            else {
                if(at!==j) target.move(at,j,1)
                if(JSON.stringify(target.get(j).note)!==JSON.stringify(rows[j])) target.setProperty(j,"note",rows[j])
            }
        }
    }
    function refresh() {syncList(items,model.rows);syncList(doneItems,model.completed)}
    Component.onCompleted:refresh()
    Connections {
        target:root.model
        function onRowsChanged() {root.refresh()}
        function onCompletedChanged() {root.refresh()}
        function onFocusEditor() {if(root.active && root.visible) input.forceActiveFocus()}
    }
    Shortcut {sequence:"Escape";enabled:root.active && root.visible;onActivated:{if(root.model.recording) root.model.request({action:"thoughts_voice_cancel"});else if(root.model.searching) {root.model.searching=false;root.model.query=""}else root.model.close()} }
    Shortcut {sequence:"Ctrl+Return";enabled:root.active && root.visible;onActivated:root.model.save(false)}
    Shortcut {sequence:"Ctrl+Enter";enabled:root.active && root.visible;onActivated:root.model.save(false)}
    Shortcut {sequence:"Ctrl+S";enabled:root.active && root.visible;onActivated:root.model.save(false)}
    Shortcut {sequence:"Ctrl+N";enabled:root.active && root.visible;onActivated:root.model.newThought()}
    Shortcut {sequence:"Ctrl+F";enabled:root.active && root.visible;onActivated:{root.model.searching=true;search.forceActiveFocus()} }
    ListModel {id:items;dynamicRoles:true}
    ListModel {id:doneItems;dynamicRoles:true}
    ColumnLayout {
        id: content
        anchors.fill:parent;spacing:root.px(12)
        RowLayout {
            Layout.fillWidth:true;spacing:root.px(6)
            Text {
                Layout.fillWidth:true
                text:root.todos ? (root.model.counts.todo ? root.model.counts.todo+" to do" : "A little room to get things done") : (root.model.counts.notes ? root.model.counts.notes+(root.model.counts.notes===1 ? " note" : " notes") : "A place for your next idea")
                color:ui.muted;font.family:ui.family;font.pixelSize:ui.caption;elide:Text.ElideRight
            }
            ActionButton {glyph:"new";subtle:true;hint:root.todos ? "New to-do · Ctrl+N" : "New note · Ctrl+N";enabled:!root.model.recording && !root.model.saving;onClicked:root.model.newThought()}
            ActionButton {glyph:"search";subtle:true;hint:"Search · Ctrl+F";selected:root.model.searching;onClicked:{root.model.searching=!root.model.searching;if(root.model.searching) search.forceActiveFocus();else root.model.query=""}}
        }
        ChatField {
            id:search;objectName:"thoughts-search"
            visible:root.model.searching;Layout.fillWidth:true
            glyph:"search";placeholderText:root.todos ? "Find a to-do…" : "Find a note…"
            Accessible.name:"Search thoughts"
            text:root.model.query;onTextEdited:root.model.query=text
        }
        Rectangle {
            id:composer
            Layout.fillWidth:true
            Layout.preferredHeight:Math.min(root.px(160),Math.max(root.px(root.todos ? 82 : 100),input.implicitHeight+root.px(46)))
            color:ui.field;radius:root.px(10)
            border.width:1;border.color:input.activeFocus ? Theme.mix(ui.surface,ui.accent,.7) : ui.line
            Behavior on border.color {ColorAnimation {duration:root.reducedMotion ? 0 : 180} }
            Behavior on Layout.preferredHeight {NumberAnimation {duration:root.reducedMotion ? 0 : 160;easing.type:Easing.OutCubic} }
            ColumnLayout {
                anchors.fill:parent;anchors.margins:root.px(12);spacing:root.px(7)
                ScrollView {
                    Layout.fillWidth:true;Layout.fillHeight:true
                    clip:true;contentWidth:availableWidth
                    ScrollBar.vertical:ChatScrollBar {}
                    TextArea {
                        id:input;objectName:"thoughts-body"
                        width:parent.width
                        text:root.model.body
                        onTextChanged:if(!root.model.loading && text!==root.model.body) root.model.body=text
                        textFormat:TextEdit.PlainText
                        placeholderText:root.model.voicePhase === "recording" ? "Listening…" : root.model.voicePhase === "transcribing" ? "Writing down your words…" : root.todos ? "What needs doing?" : "What’s on your mind?"
                        placeholderTextColor:ui.muted
                        color:ui.foreground;font.family:ui.family;font.pixelSize:ui.body
                        wrapMode:TextEdit.Wrap;selectByMouse:true
                        padding:0;readOnly:root.model.recording || root.model.saving
                        selectionColor:ui.accent;selectedTextColor:ui.accentInk
                        Accessible.name:root.todos ? "New to-do" : "Note text"
                        background:Item {}
                        Keys.onPressed:event=>{
                            if(!root.active || !root.visible) {event.accepted=false;return}
                            if((event.key===Qt.Key_Return || event.key===Qt.Key_Enter) && ((event.modifiers & Qt.ControlModifier) || (root.todos && !(event.modifiers & Qt.ShiftModifier)))) {
                                root.model.save(false);event.accepted=true
                            }
                        }
                    }
                }
                RowLayout {
                    Layout.fillWidth:true;spacing:root.px(6)
                    Text {
                        Layout.fillWidth:true
                        text:root.model.recording ? root.model.voicePhase === "transcribing" ? "Transcribing…" : root.todos ? "Tap Numpad 3 again to stop" : "Tap Numpad 2 again to stop" : root.model.noteId ? "Editing · changes kept as a draft" : root.todos ? "Return to add" : "Ctrl+Return to save"
                        color:ui.muted;font.family:ui.family;font.pixelSize:ui.caption;elide:Text.ElideRight
                    }
                    ActionButton {visible:!!root.model.noteId;glyph:"new";subtle:true;hint:"Keep draft and write a new note";enabled:!root.model.recording && !root.model.saving;onClicked:root.model.newThought()}
                    ActionButton {
                        visible:root.todos;glyph:"bell";subtle:true;selected:!!root.model.effectiveDue || root.model.reminderEditing
                        hint:"Add a reminder";enabled:!root.model.recording && !root.model.saving
                        onClicked:{root.model.reminderEditing=!root.model.reminderEditing;if(root.model.reminderEditing) reminderField.forceActiveFocus()}
                    }
                    ActionButton {
                        objectName:"thoughts-record";glyph:root.model.recording ? "stop" : "mic";subtle:true
                        hint:root.model.recording ? "Stop recording" : root.todos ? "Dictate a to-do · Numpad 3" : "Dictate a note · Numpad 2"
                        danger:root.model.voicePhase === "recording"
                        enabled:!root.model.saving && root.model.voicePhase !== "transcribing"
                        onClicked:root.model.recording ? root.model.stopCapture() : root.model.startCapture()
                    }
                    ActionButton {
                        objectName:"thoughts-save";glyph:root.todos ? "new" : "send";accent:true
                        text:root.model.saving ? "Saving…" : root.model.noteId ? "Save" : root.todos ? "Add" : "Save"
                        hint:root.todos ? "Add to-do · Enter" : "Save note · Ctrl+Enter"
                        enabled:!!root.model.body.trim() && !root.model.recording && !root.model.saving && root.model.dirty
                        onClicked:root.model.save(false)
                    }
                }
            }
        }
        ColumnLayout {
            visible:root.todos && (root.model.reminderEditing || !!root.model.effectiveDue || !!root.model.dueError)
            Layout.fillWidth:true;spacing:root.px(6)
            ChatField {
                id:reminderField;objectName:"thoughts-reminder"
                visible:root.model.reminderEditing;Layout.fillWidth:true
                glyph:"bell";placeholderText:"Tomorrow at 3pm, in 20 minutes…"
                Accessible.name:"Reminder date and time"
                text:root.model.dueText;onTextEdited:root.model.dueText=text
                enabled:!root.model.saving && !root.model.recording
                onAccepted:root.model.save(false)
            }
            RowLayout {
                visible:!!root.model.effectiveDue || !!root.model.dueError;Layout.fillWidth:true
                Text {
                    objectName:"thoughts-due-preview";Layout.fillWidth:true
                    text:root.model.dueError || root.model.dueLabel
                    textFormat:Text.PlainText;color:root.model.dueError ? ui.danger : ui.accent
                    font.family:ui.family;font.pixelSize:ui.caption;wrapMode:Text.Wrap
                }
                ActionButton {glyph:"close";subtle:true;hint:"Remove reminder";onClicked:root.model.clearReminder()}
            }
        }
        ActionButton {
            visible:!!root.model.source.kind;Layout.fillWidth:true
            glyph:root.model.source.kind === "chat" ? "chat" : "attach"
            text:"From " + (root.model.source.label || "selection");subtle:true
            enabled:!!root.model.source.id;hint:"Open source"
            onClicked:root.model.chat.openSource(root.model.source)
        }
        RowLayout {
            visible:!!root.model.error;Layout.fillWidth:true
            Text {Layout.fillWidth:true;text:root.model.error;textFormat:Text.PlainText;color:ui.danger;font.family:ui.family;font.pixelSize:ui.small;wrapMode:Text.Wrap;maximumLineCount:3;elide:Text.ElideRight}
            ActionButton {visible:root.model.dirty && !!root.model.noteId;text:"Save copy";onClicked:root.model.save(true)}
            ActionButton {glyph:"close";hint:"Dismiss error";subtle:true;onClicked:root.model.error=""}
        }
        ListView {
            id:library;objectName:"thoughts-library"
            Layout.fillWidth:true;Layout.fillHeight:true
            Layout.preferredHeight: root.px(items.count || doneItems.count ? Math.min(260, 100 * Math.max(1, items.count)) : 108)
            Layout.minimumHeight: root.px(70)
            model:items;spacing:root.px(8);clip:true;boundsBehavior:Flickable.StopAtBounds
            ScrollBar.vertical:ChatScrollBar {}
            delegate:ThoughtRow {
                required property string identity
                objectName:"thoughts-row-"+identity
                width:ListView.view.width-root.px(3)
                controller:root.model;reducedMotion:root.reducedMotion
            }
            add:Transition {
                enabled:!root.reducedMotion
                ParallelAnimation {
                    NumberAnimation {property:"opacity";from:0;to:1;duration:180}
                    NumberAnimation {property:"scale";from:.97;to:1;duration:230;easing.type:Easing.OutCubic}
                }
            }
            displaced:Transition {enabled:!root.reducedMotion;NumberAnimation {properties:"x,y";duration:230;easing.type:Easing.OutCubic} }
            footer:Column {
                width:library.width
                topPadding:root.px(8)
                ActionButton {
                    visible:root.todos && doneItems.count>0
                    text:(root.model.showCompleted ? "Hide completed" : "Completed")+" · "+doneItems.count
                    glyph:root.model.showCompleted ? "chevron-up" : "chevron-down";subtle:true
                    onClicked:root.model.showCompleted=!root.model.showCompleted
                }
                Item {
                    id:completedReveal
                    property real progress:root.model.showCompleted ? 1 : 0
                    width:parent.width;height:doneColumn.implicitHeight*progress
                    visible:height>0;clip:true
                    Behavior on progress {NumberAnimation {duration:root.reducedMotion ? 0 : 200;easing.type:Easing.OutCubic} }
                    Column {
                        id:doneColumn
                        width:parent.width;spacing:root.px(8);opacity:completedReveal.progress
                        y:-root.px(6)*(1-completedReveal.progress)
                        Repeater {
                            model:root.model.showCompleted || completedReveal.progress > 0 ? doneItems : null
                            ThoughtRow {
                                required property string identity
                                width:library.width-root.px(3);controller:root.model;reducedMotion:root.reducedMotion
                            }
                        }
                    }
                }
            }
            ColumnLayout {
                visible:items.count===0 && doneItems.count===0
                anchors.centerIn:parent;width:parent.width-root.px(36);spacing:root.px(12)
                Icon {name:root.model.query ? "search" : root.todos ? "check" : "thought";ink:Theme.mix(ui.surface,ui.accent,.65);Layout.preferredWidth:root.px(34);Layout.preferredHeight:root.px(40);Layout.alignment:Qt.AlignHCenter}
                Text {Layout.fillWidth:true;text:root.model.query ? "Nothing found" : root.todos ? "A little less to remember." : "Let it out. Keep it here.";color:ui.foreground;font.family:ui.family;font.pixelSize:ui.body;horizontalAlignment:Text.AlignHCenter;wrapMode:Text.Wrap}
                Text {Layout.fillWidth:true;text:root.model.query ? "Try another word." : root.todos ? "Add a to-do above. One thing at a time." : "A quick note, a stray idea, anything.";color:ui.muted;font.family:ui.family;font.pixelSize:ui.small;horizontalAlignment:Text.AlignHCenter;wrapMode:Text.Wrap}
            }
        }
        RowLayout {
            Layout.fillWidth:true
            Icon {name:"check";ink:ui.accent;visible:!!root.model.notice;Layout.preferredWidth:root.px(12);Layout.preferredHeight:root.px(12)}
            Text {Layout.fillWidth:true;text:root.model.notice || root.model.saveStatus || "Saved on this device";color:ui.muted;font.family:ui.family;font.pixelSize:ui.caption;elide:Text.ElideRight}
            ActionButton {visible:!!root.model.undoId;text:"Undo";subtle:true;onClicked:root.model.undoTrash()}
        }
    }
}
