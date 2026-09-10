// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.Commons
import "Theme.js" as Theme
import "VoiceStatus.js" as Voice
import "CompanionGaze.js" as Gaze

Item {
    id: root
    ChatStyle { id: ui }
    required property var chat
    property bool present: true
    readonly property bool interactive: transition.interactive
    readonly property alias reveal: transition
    visible: transition.rendered
    onPresentChanged: if (!present) hideControls()
    CompanionTransition {
        id: transition
        present: root.present
        reducedMotion: !!root.voice.reducedMotion || root.voice.expressiveness === 0
    }
    property bool controlsPinned: false
    property bool controlsVisible: false
    readonly property bool controlsHovered: mouse.containsMouse || dockHover.hovered
    onControlsHoveredChanged: {
        if (controlsHovered && interactive) { controlsDismiss.stop();controlsVisible=true }
        else controlsDismiss.restart()
    }
    onVisibleChanged: if (!visible) hideControls()
    property bool dragging: false
    property real pointerX: 0
    property real pointerY: 0
    property real startPointer: 0
    property var desktopPointer: null
    property point desktopOrigin: Qt.point(0, 0)
    property real gazeDistance: Style.space(280)
    readonly property var voice: chat.peek
    readonly property var task: voice.task || ({state:"idle",steps:[],total:0})
    readonly property alias bodyRegion: bodyHit
    readonly property alias panelRegion: dock
    readonly property alias details: taskDetails
    readonly property var attention: Gaze.attention(voice, chat.busy, desktopPointer, targetFresh ? voice.actionTarget : null)
    readonly property string attentionSource: attention.source
    readonly property var gaze: attention.point ? Gaze.direction(attention.point, Qt.point(
        desktopOrigin.x + bodyHit.x + buddy.x + buddy.width / 2 + Style.space(-17 + buddy.animation.lean * 23),
        desktopOrigin.y + bodyHit.y + buddy.y + buddy.height / 2 - Style.space(15)), gazeDistance) : ({x:0,y:0})
    readonly property bool needsAnswer: voice.stage === "needs_input"
    readonly property string stateLabel: chat.error ? "Needs attention" : Voice.label(voice,chat.busy)
    readonly property string headline: chat.error || voice.error ? stateLabel : needsAnswer ? "Your answer is needed" : voice.hearing || voice.transcribing || voice.speaking ? stateLabel
                                      : chat.busy ? (voice.taskCaption || task.label || "Working through your request")
                                      : resultVisible ? task.label || stateLabel : stateLabel
    readonly property string captionText: voice.preview && !voice.previewScenario ? "Design preview. Microphone and agent are disabled."
        : chat.error || voice.error || voice.partial || (noticeVisible ? voice.inputNotice : "")
        || (needsAnswer ? (((chat.agentRequests || [])[0] || {}).title || voice.caption || "Open the conversation to answer.")
            : voice.transcribing ? "Turning your words into a request…" : voice.speaking ? voice.caption || "" : resultVisible ? task.detail || "" : "") || ""
    property bool targetFresh: false
    property real targetStamp: 0
    property bool resultVisible: false
    property string resultKey: ""
    property bool noticeVisible: false
    property real lastNoticeAt: 0
    onVoiceChanged: {
        var target=voice.actionTarget
        if (target && target.at !== targetStamp) { targetStamp=target.at;targetFresh=true;targetExpiry.restart() }
        else if (!target) targetFresh=false
        if (voice.inputNotice && voice.inputNoticeAt > lastNoticeAt) {
            lastNoticeAt=voice.inputNoticeAt;noticeVisible=true;noticeTimer.restart()
        } else if (!voice.inputNotice) noticeVisible=false
    }
    onTaskChanged: {
        var key=(task.turn || "")+":"+task.state
        if (key !== resultKey) {
            resultKey=key
            resultVisible=["verified","review","answered","error","stopped"].indexOf(task.state)>=0
            if(resultVisible) resultExpiry.restart()
            else { resultExpiry.stop();taskDetails.expanded=false }
        }
    }
    Timer { id: targetExpiry; interval: 5000; onTriggered: root.targetFresh=false }
    Timer { id: resultExpiry; interval: 12000; onTriggered: root.resultVisible=false }
    Timer { id: noticeTimer; interval: 5000; onTriggered: root.noticeVisible=false }
    Timer { id: controlsDismiss; interval: 250; onTriggered: root.hideControls() }
    signal dragStarted()
    signal dragMoved(real delta)
    signal dragFinished()
    implicitWidth: Style.space(346)
    implicitHeight: Math.max(Style.space(218),dock.y+dock.height+Style.space(8))
    function showControls() { if(!interactive) return;controlsDismiss.stop();controlsVisible=true;controlsPinned=true;Qt.callLater(()=>mic.forceActiveFocus()) }
    function hideControls() { controlsDismiss.stop();controlsVisible=false;controlsPinned=false;taskDetails.expanded=false }
    function setting(key,value) { var s={};s[key]=value;chat.request({action:"peek_settings",settings:s}) }
    Keys.onEscapePressed: hideControls()

    Item {
        id: bodyHit
        x: 0; y: Style.space(35); width: Style.space(108); height: Style.space(170)
        clip: true
        PeekBuddy {
            id: buddy
            objectName: "companion-body"
            x: -Style.space(66); y: -Style.space(15); width: Style.space(200); height: width
            mood: chat.error || root.voice.error ? "error" : root.voice.stage || "idle"
            inputLevel: root.voice.inputLevel || 0; outputLevel: root.voice.outputLevel || 0
            reducedMotion: root.voice.reducedMotion || false; completedAt: root.voice.completedAt || 0
            revealProgress: transition.progress
            voiceReady: !!root.voice.ready; hearing: !!root.voice.hearing
            expressiveness: root.voice.expressiveness === undefined ? 1 : root.voice.expressiveness
            tracking: root.attention.tracking || (mouse.containsMouse && !chat.busy)
            engaged: root.controlsVisible
            gazeX: root.attention.tracking ? root.gaze.x : mouse.containsMouse && !chat.busy ? root.pointerX : 0
            gazeY: root.attention.tracking ? root.gaze.y : mouse.containsMouse && !chat.busy ? root.pointerY : 0
            dragging: root.dragging
        }
        MouseArea {
            id: mouse; anchors.fill: parent; hoverEnabled: true
            enabled: root.interactive
            cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor
            Accessible.role: Accessible.Button; Accessible.name: "Peek. Show controls or drag along the screen edge."
            Accessible.onPressAction: root.showControls()
            onPressed: event => { root.startPointer=mapToGlobal(event.x,event.y).y;root.dragStarted() }
            onPositionChanged: event => {
                root.pointerX=(event.x/width-.5)*2;root.pointerY=(event.y/height-.5)*2
                if(pressed) { var delta=mapToGlobal(event.x,event.y).y-root.startPointer; if(Math.abs(delta)>Style.space(5)) root.dragging=true; if(root.dragging) root.dragMoved(delta) }
            }
            onReleased: {
                if(root.dragging) root.dragFinished()
                else { root.controlsPinned=!root.controlsPinned;if(root.controlsPinned) root.showControls() }
                root.dragging=false
            }
            onCanceled: { if(root.dragging) root.dragFinished();root.dragging=false }
        }
    }
    Rectangle {
        id: dock
        objectName: "companion-dock"
        visible: root.controlsVisible
        x: Style.space(110); y: Style.space(30)
        width: Style.space(228); height: content.implicitHeight+Style.space(20)
        color: ui.surface; radius: ui.radius
        border.width: 1; border.color: ui.border
        HoverHandler { id: dockHover; enabled: dock.visible }
        Rectangle { x:0;y:Style.space(10);width:Style.space(2);height:Style.space(24);color: chat.error || root.voice.error ? ui.danger : ui.accent }
        ColumnLayout {
            id: content
            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
            anchors.margins: Style.space(10)
            spacing: Style.space(7)
            RowLayout {
                Layout.fillWidth: true
                Text { text:"PEEK";color:ui.muted;font.family:ui.family;font.pixelSize:ui.caption;font.letterSpacing:.8;font.weight:Font.DemiBold }
                Item { Layout.fillWidth:true }
                Text { text:root.voice.scope === "browser" ? "Browser" : "Desktop";color:ui.muted;font.family:ui.family;font.pixelSize:ui.caption }
                Row {
                    spacing:Style.space(2);Layout.preferredWidth:Style.space(10);Layout.preferredHeight:Style.space(12)
                    Repeater {
                        model:3
                        Rectangle {
                            required property int index
                            width:Style.space(2); anchors.verticalCenter:parent.verticalCenter
                            height:Style.space(3+(index === 1 ? 9 : 6)*(root.voice.reducedMotion ? 0 : root.voice.speaking ? root.voice.outputLevel || 0 : root.voice.listening ? root.voice.inputLevel || 0 : 0))
                            color:root.voice.listening || root.voice.speaking ? ui.accent : ui.muted
                            Behavior on height { NumberAnimation { duration:root.voice.reducedMotion ? 0 : 100 } }
                        }
                    }
                }
            }
            Text {
                objectName:"companion-headline"
                Layout.fillWidth:true
                text:root.headline; color:ui.foreground
                font.family:ui.family;font.pixelSize:ui.body;font.weight:Font.DemiBold
                textFormat:Text.PlainText;wrapMode:Text.WordWrap;maximumLineCount:2;elide:Text.ElideRight
                Accessible.role:Accessible.StaticText
            }
            Text {
                objectName:"companion-caption"
                Layout.fillWidth:true
                visible:text.length>0
                text:root.captionText;color:root.voice.partial ? ui.foreground : ui.muted
                font.family:ui.family;font.pixelSize:ui.small
                textFormat:Text.PlainText;wrapMode:Text.WordWrap;maximumLineCount:3;elide:Text.ElideRight
                Accessible.role:Accessible.StaticText
            }
            ActionButton {
                visible:root.needsAnswer;Layout.fillWidth:true
                text:"Open question";glyph:"chat";accent:true
                onClicked:chat.openConversation()
            }
            TaskDetails { id:taskDetails;Layout.fillWidth:true;task:root.task }
            Rectangle { Layout.fillWidth:true;height:1;color:ui.line }
            RowLayout {
                Layout.fillWidth:true;spacing:Style.space(4)
                ActionButton {
                    id:mic;objectName:"companion-mic"
                    glyph:root.voice.listening ? "mic" : "mic-off";accent:!!root.voice.listening
                    enabled:!!root.voice.ready && !root.voice.preview
                    hint:root.voice.preview ? "Preview · microphone disabled" : root.voice.standby ? "Wake Peek" : root.voice.asrModel === "voxtype" ? (root.voice.listening ? "Stop Voxtype recording" : "Start Voxtype recording") : !root.voice.handsFree && !root.voice.wakeEnabled ? "Hold to talk" : root.voice.listening ? "Mute microphone" : "Listen"
                    onClicked: if(root.voice.standby) chat.request({action:"peek_wake"}); else if(root.voice.asrModel === "voxtype" || root.voice.handsFree || root.voice.wakeEnabled) chat.request({action:"peek_listen",enabled:!root.voice.listening})
                    onPressed: if(root.voice.asrModel !== "voxtype" && !root.voice.handsFree && !root.voice.wakeEnabled) chat.request({action:"peek_listen",enabled:true})
                    onReleased: if(root.voice.asrModel !== "voxtype" && !root.voice.handsFree && !root.voice.wakeEnabled) chat.request({action:"peek_finish"})
                    onCanceled: if(root.voice.asrModel !== "voxtype" && !root.voice.handsFree && !root.voice.wakeEnabled) chat.request({action:"peek_listen",enabled:false})
                }
                ActionButton { objectName:"companion-stop";glyph:"stop";hint:"Stop speech and actions · Ctrl+Alt+Esc";enabled:chat.busy || root.voice.speaking || root.voice.stage === "acting";onClicked:chat.request({action:"peek_stop"}) }
                ActionButton { glyph:"chat";hint:"Open conversation";onClicked:chat.openConversation() }
                Item { Layout.fillWidth:true }
                ActionButton { objectName:"companion-more";glyph:root.controlsPinned ? "chevron-up" : "chevron-down";hint:root.controlsPinned ? "Fewer controls" : "More controls";selected:root.controlsPinned;checkable:true;checked:root.controlsPinned;onClicked:root.controlsPinned=!root.controlsPinned }
            }
            RowLayout {
                visible:root.controlsPinned
                Layout.fillWidth:true;spacing:Style.space(4)
                ActionButton { glyph:root.voice.muted ? "muted" : "volume";hint:root.voice.muted ? "Unmute replies" : "Mute spoken replies";accent:!!root.voice.muted;onClicked:root.setting("muted",!root.voice.muted) }
                ActionButton { glyph:root.voice.scope === "browser" ? "globe" : "desktop";hint:root.voice.scope === "browser" ? "Switch to desktop" : "Switch to isolated browser";enabled:!chat.busy;onClicked:root.setting("scope",root.voice.scope === "desktop" ? "browser" : "desktop") }
                ActionButton { glyph:"settings";hint:"Peek settings";onClicked: { root.controlsPinned=false;chat.openPeekSettings() } }
                ActionButton { glyph:"sleep";hint:root.voice.wakeEnabled ? "Stand by for the wake phrase" : "Mute microphone and pause";onClicked: { chat.request({action:"peek_standby"});root.controlsPinned=false } }
                Item { Layout.fillWidth:true }
                ActionButton { glyph:"power";hint:"Turn Peek off";onClicked:chat.setPeek(false,false) }
            }
        }
    }
}
