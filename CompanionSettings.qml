// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.Commons
import "Theme.js" as Theme

Flickable {
    id: root
    objectName: "companion-settings"
    ChatStyle { id: ui }
    required property var chat
    property string section: "Appearance"
    property var draft: chat.jarvis
    signal settingChanged(string key, var value)
    property string memoryId: ""
    property string routineId: ""
    property string pending: ""
    property string pendingKind: ""
    function save(command, kind) {
        pending=String(Date.now())+String(Math.random()); pendingKind=kind
        command.requestId=pending; chat.request(command)
    }
    Connections {
        target: root.chat
        function onJarvisChanged() {
            if (!root.pending || root.chat.jarvis.companionSavedRequest !== root.pending) return
            if (root.pendingKind === "memory") { memory.text=""; root.memoryId="" }
            if (root.pendingKind === "routine") { routineName.text=""; steps.text=""; root.routineId="" }
            root.pending=""
        }
        function onErrorChanged() { if (root.chat.error) root.pending="" }
    }
    contentWidth: width; contentHeight: body.implicitHeight
    clip: true; boundsBehavior: Flickable.StopAtBounds
    ScrollBar.vertical: ChatScrollBar {}
    Component.onCompleted: chat.request({action:"jarvis_companion_status"})
    component Label: Text {
        textFormat: Text.PlainText
        Layout.fillWidth: true; wrapMode: Text.Wrap
        color: ui.muted
        font.family: Style.font.family; font.pixelSize: ui.small
    }
    component Field: ChatField {
        Layout.fillWidth: true
    }
    component Area: TextArea {
        Layout.fillWidth: true; wrapMode: TextEdit.Wrap
        font.family: Style.font.family; font.pixelSize: ui.small
        color: ui.foreground; selectByMouse: true
        padding: Style.space(7)
        selectionColor: Theme.alpha(ui.accent, 0.35)
        selectedTextColor: ui.foreground
        placeholderTextColor: ui.muted
        background: Rectangle { radius: ui.radius; color: ui.field; border.width: 1; border.color: ui.border }
    }
    ColumnLayout {
        id: body
        width: root.width-Style.space(8); spacing: Style.space(7)
        Flow {
            Layout.fillWidth: true; spacing: Style.space(3)
            Repeater {
                model: ["Appearance","Memory","Routines","Watches","Undo"]
                ActionButton { required property string modelData; text: modelData; tab: true; selected: root.section === modelData; onClicked: { root.section=modelData; root.contentY=0 } }
            }
        }
        Label { visible: !!chat.error; text: chat.error; color: ui.emphasis }
        RobotAppearance {
            visible: root.section === "Appearance"
            Layout.fillWidth: true
            reducedMotion: root.draft.reducedMotion || false
            expressiveness: root.draft.expressiveness === undefined ? 1 : root.draft.expressiveness
            onSettingChanged: (key,value) => root.settingChanged(key,value)
        }
        ColumnLayout {
            visible: root.section === "Memory"; Layout.fillWidth: true; spacing: Style.space(6)
            ChatSection { text: "Memory" }
            Label { text: "Say “remember that…” or save a fact here. Forget removes the memory, keeping chat history." }
            Area { id: memory; placeholderText: "A preference or fact to remember…"; Accessible.name: "Memory text"; Layout.minimumHeight: Style.space(44) }
            RowLayout {
                ActionButton { text: root.memoryId ? "Update memory" : "Remember"; enabled: !!memory.text.trim() && !root.pending; onClicked: root.save({action:"jarvis_memory_save",id:root.memoryId,text:memory.text},"memory") }
                ActionButton { visible: !!root.memoryId; text: "Cancel"; subtle: true; onClicked: { root.memoryId=""; memory.text="" } }
            }
            Label { visible: !(chat.jarvis.memories || []).length; text: "No memories saved." }
            Repeater {
                model: chat.jarvis.memories || []
                ColumnLayout {
                    required property var modelData
                    Layout.fillWidth: true; spacing: Style.space(2)
                    Label { text: modelData.text; color: ui.foreground }
                    RowLayout {
                        ActionButton { text: "Edit"; subtle: true; onClicked: { root.memoryId=modelData.id; memory.text=modelData.text; root.contentY=0 } }
                        ActionButton { text: "Forget"; subtle: true; onClicked: chat.request({action:"jarvis_memory_delete",id:modelData.id}) }
                    }
                }
            }
        }
        ColumnLayout {
            visible: root.section === "Routines"; Layout.fillWidth: true; spacing: Style.space(6)
            ChatSection { text: "Routines" }
            Label { text: "Add one local command per line, then say the routine’s name to run it." }
            Field { id: routineName; placeholderText: "Routine name"; Accessible.name: "Routine name" }
            Area { id: steps; placeholderText: "open terminal\nset volume to 30"; Accessible.name: "Routine commands"; Layout.minimumHeight: Style.space(60) }
            RowLayout {
                ActionButton { text: root.routineId ? "Update routine" : "Save routine"; enabled: !!routineName.text.trim() && !!steps.text.trim() && !root.pending; onClicked: root.save({action:"jarvis_routine_save",id:root.routineId,name:routineName.text,steps:steps.text.split("\n").map(s=>s.trim()).filter(s=>s.length)},"routine") }
                ActionButton { visible: !!root.routineId; text: "Cancel"; subtle: true; onClicked: { root.routineId=""; routineName.text=""; steps.text="" } }
            }
            Repeater {
                model: chat.jarvis.routines || []
                ColumnLayout {
                    required property var modelData
                    Layout.fillWidth: true; spacing: Style.space(2)
                    Label { text: modelData.name; color: ui.foreground; font.bold: true }
                    Label { text: modelData.steps.join(" · ") }
                    RowLayout {
                        ActionButton { text: "Run"; enabled: !chat.busy && chat.jarvis.enabled; onClicked: chat.request({action:"jarvis_say",text:"run "+modelData.name}) }
                        ActionButton { text: "Edit"; subtle: true; onClicked: { root.routineId=modelData.id; routineName.text=modelData.name; steps.text=modelData.steps.join("\n"); root.contentY=0 } }
                        ActionButton { text: "Delete"; subtle: true; onClicked: chat.request({action:"jarvis_routine_delete",id:modelData.id}) }
                    }
                }
            }
        }
        ColumnLayout {
            visible: root.section === "Watches"; Layout.fillWidth: true; spacing: Style.space(6)
            ChatSection { text: "Watches" }
            Label { text: "Set a reminder or watch a process. Notifications work with the panel hidden while the shell is running." }
            Field { id: watchText; placeholderText: "Reminder text"; Accessible.name: "Reminder text" }
            RowLayout {
                Field { id: minutes; placeholderText: "Minutes"; inputMethodHints: Qt.ImhDigitsOnly; validator: IntValidator { bottom: 1; top: 10080 } Accessible.name: "Timer minutes" }
                ActionButton { text: "Set timer"; enabled: minutes.acceptableInput; onClicked: { chat.request({action:"jarvis_watch_add",kind:"timer",seconds:Number(minutes.text)*60,message:watchText.text || "Your timer finished."}); minutes.text="" } }
            }
            RowLayout {
                Field { id: pid; placeholderText: "Process ID"; inputMethodHints: Qt.ImhDigitsOnly; validator: IntValidator { bottom: 1 } Accessible.name: "Process ID to watch" }
                ActionButton { text: "Watch exit"; enabled: pid.acceptableInput; onClicked: { chat.request({action:"jarvis_watch_add",kind:"process",pid:Number(pid.text),message:watchText.text || "Your watched process exited."}); pid.text="" } }
            }
            Repeater {
                model: chat.jarvis.watches || []
                RowLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    Label { text: modelData.message+" · "+modelData.state+(modelData.kind === "process" ? " · PID "+modelData.pid : " · "+new Date(modelData.due*1000).toLocaleTimeString()) }
                    ActionButton { text: "Cancel"; subtle: true; visible: modelData.state === "waiting"; onClicked: chat.request({action:"jarvis_watch_cancel",id:modelData.id}) }
                }
            }
        }
        ColumnLayout {
            visible: root.section === "Undo"; Layout.fillWidth: true; spacing: Style.space(6)
            ChatSection { text: "Undo" }
            Label { text: "Restore tracked Peek config edits if the file hasn’t changed since. Other CLI edits and app actions aren’t covered." }
            Label { visible: !(chat.jarvis.restorePoints || []).length; text: "No tracked config changes yet." }
            Repeater {
                model: chat.jarvis.restorePoints || []
                ColumnLayout {
                    required property var modelData
                    Layout.fillWidth: true; spacing: Style.space(2)
                    Label { text: modelData.path; color: ui.foreground; wrapMode: Text.WrapAnywhere }
                    RowLayout {
                        Label { text: modelData.state+" · "+new Date(modelData.updated*1000).toLocaleString() }
                        ActionButton { text: "Restore"; enabled: modelData.state === "available" && !chat.busy; onClicked: chat.request({action:"jarvis_undo",id:modelData.id}) }
                    }
                }
            }
        }
    }
}
