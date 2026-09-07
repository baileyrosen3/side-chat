// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Controls
import qs.Commons
import "Theme.js" as Theme
import "VoiceStatus.js" as Voice

Item {
    id: root
    required property var chat
    property bool controlsPinned: false
    property bool controlsVisible: false
    property bool dragging: false
    property real pointerX: 0
    property real pointerY: 0
    property real startPointer: 0
    readonly property var voice: chat.jarvis
    readonly property alias bodyRegion: bodyHit
    readonly property alias controlsRegion: satellites
    readonly property alias captionRegion: caption
    readonly property alias statusRegion: statusStrip
    readonly property string stateLabel: chat.error ? "Needs attention" : Voice.label(voice,chat.busy)
    readonly property bool captionVisible: !!voice.preview || !!chat.error || !!voice.error || !!voice.partial || !!voice.transcribing || noticeVisible || voice.speaking || voice.stage === "needs_input"
    property bool noticeVisible: false
    property real lastNoticeAt: 0
    onVoiceChanged: {
        if (voice.inputNotice && voice.inputNoticeAt > lastNoticeAt) {
            lastNoticeAt=voice.inputNoticeAt; noticeVisible=true; noticeTimer.restart()
        } else if (!voice.inputNotice) noticeVisible=false
    }
    Timer { id: noticeTimer; interval: 5000; onTriggered: root.noticeVisible=false }
    property real reveal: controlsVisible || controlsPinned ? 1 : 0
    signal dragStarted()
    signal dragMoved(real delta)
    signal dragFinished()
    implicitWidth: Style.space(326)
    implicitHeight: Style.space(248)
    function showControls() { controlsPinned=true;controlsVisible=true;Qt.callLater(()=>mic.forceActiveFocus()) }
    function setting(key,value) { var s={};s[key]=value;chat.request({action:"jarvis_settings",settings:s}) }
    Behavior on reveal { NumberAnimation { duration: root.voice.reducedMotion ? 0 : 260; easing.type: Easing.OutCubic } }
    HoverHandler { onHoveredChanged: { if(hovered) { hide.stop();root.controlsVisible=true } else hide.restart() } }
    Timer { id: hide; interval: 420; onTriggered: root.controlsVisible=false }
    Keys.onEscapePressed: { controlsPinned=false;controlsVisible=false }

    Rectangle {
        id: caption
        x: Style.space(112); y: Style.space(4)
        width: Style.space(204); height: captionText.implicitHeight+Style.space(16)
        visible: root.captionVisible; color: Color.popups.background; radius: Style.space(3)
        border.width: 1; border.color: Theme.alpha(Color.foreground,.10)
        Text {
            id: captionText; anchors.fill: parent; anchors.margins: Style.space(8)
            text: root.voice.preview ? "Design preview. Microphone and agent are disabled." : chat.error || root.voice.error || root.voice.partial || (root.noticeVisible ? root.voice.inputNotice : "") || root.voice.caption || "Your input is needed"
            color: root.voice.partial ? Theme.alpha(Color.foreground,.7) : Color.foreground
            font.family: Style.font.family; font.pixelSize: Style.font.body
            textFormat: Text.PlainText; wrapMode: Text.Wrap; maximumLineCount: 3; elide: Text.ElideRight
        }
        MouseArea { anchors.fill: parent; onClicked: chat.openConversation(); cursorShape: Qt.PointingHandCursor }
    }
    Item {
        id: bodyHit
        x: 0; y: Style.space(35); width: Style.space(108); height: Style.space(170)
        clip: true
        // Cropping 66 units aligns the hands with the physical left edge.
        JarvisBuddy {
            id: buddy
            x: -Style.space(66); y: -Style.space(15); width: Style.space(200); height: width
            mood: chat.error || root.voice.error ? "error" : root.voice.stage || "idle"; inputLevel: root.voice.inputLevel || 0; outputLevel: root.voice.outputLevel || 0
            reducedMotion: root.voice.reducedMotion || false; completedAt: root.voice.completedAt || 0
            expressiveness: root.voice.expressiveness === undefined ? 1 : root.voice.expressiveness
            tracking: mouse.containsMouse; engaged: root.controlsPinned || root.controlsVisible
            gazeX: tracking ? root.pointerX : root.voice.gazeX || 0; gazeY: tracking ? root.pointerY : root.voice.gazeY || 0
            dragging: root.dragging
        }
        MouseArea {
            id: mouse; anchors.fill: parent; hoverEnabled: true
            cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor
            Accessible.role: Accessible.Button; Accessible.name: buddy.characterName + ". Show controls or drag along the screen edge."
            Accessible.onPressAction: root.showControls()
            onPressed: event => { root.startPointer=mapToGlobal(event.x,event.y).y;root.dragStarted() }
            onPositionChanged: event => {
                root.pointerX=(event.x/width-.5)*2;root.pointerY=(event.y/height-.5)*2
                if(pressed) { var delta=mapToGlobal(event.x,event.y).y-root.startPointer; if(Math.abs(delta)>Style.space(5)) root.dragging=true; if(root.dragging) root.dragMoved(delta) }
            }
            onReleased: {
                if(root.dragging) root.dragFinished()
                else { buddy.greet();root.controlsPinned=!root.controlsPinned;if(root.controlsPinned) root.showControls() }
                root.dragging=false
            }
            onCanceled: { if(root.dragging) root.dragFinished();root.dragging=false }
        }
    }
    Rectangle {
        id: statusStrip
        x: 0; y: Style.space(211); width: statusRow.implicitWidth+Style.space(18); height: Style.space(25)
        color: Color.popups.background
        Rectangle { width: Style.space(2); height: parent.height; color: chat.error || root.voice.error ? Color.urgent : Color.accent }
        Row {
            id: statusRow; anchors.centerIn: parent; spacing: Style.space(6)
            Row {
                anchors.verticalCenter: parent.verticalCenter; spacing: Style.space(2)
                Repeater {
                    model: 3
                    Rectangle {
                        required property int index
                        width: Style.space(2)
                        height: Style.space(3+(index === 1 ? 8 : 5)*(root.voice.speaking ? root.voice.outputLevel || 0 : root.voice.listening ? root.voice.inputLevel || 0 : 0))
                        anchors.verticalCenter: parent.verticalCenter
                        color: root.voice.listening || root.voice.speaking ? Color.accent : Theme.alpha(Color.foreground,.4)
                        Behavior on height { NumberAnimation { duration: 100 } }
                    }
                }
            }
            Text { text: root.stateLabel; color: Color.foreground; font.family: Style.font.family; font.pixelSize: Style.font.body }
        }
        MouseArea { anchors.fill: parent; onClicked: chat.openConversation(); cursorShape: Qt.PointingHandCursor }
    }
    Item {
        id: satellites
        x: Style.space(112); y: Math.max(Style.space(76),caption.visible ? caption.y+caption.height+Style.space(10) : 0)
        width: Style.space(64); height: Style.space(130)
        visible: root.reveal > .01
        component Satellite: ActionButton {
            required property int slot
            implicitWidth: Style.space(28); implicitHeight: Style.space(28)
            readonly property real progress: Math.max(0,Math.min(1,root.reveal*1.6-slot*.075))
            x: Style.space((slot%2)*34)-(1-progress)*Style.space(7)
            y: Math.floor(slot/2)*Style.space(34)
            opacity: progress*(enabled ? 1 : .3); scale: down ? .97 : 1
            enabled: root.reveal > .8
            background: Rectangle {
                radius: Style.space(3); color: Color.popups.background
                border.width: 1; border.color: parent.hovered || parent.activeFocus ? Color.accent : Theme.alpha(Color.foreground,.13)
            }
            ink: accent || hovered || activeFocus ? Color.accent : Color.foreground
        }
        Satellite {
            id: mic; slot: 0; glyph: root.voice.listening ? "mic" : "mic-off"; accent: root.voice.listening
            hint: root.voice.preview ? "Preview · microphone disabled" : root.voice.standby ? "Wake Jarvis" : !root.voice.handsFree && !root.voice.wakeEnabled ? "Hold to talk" : root.voice.listening ? "Mute microphone" : "Listen"
            enabled: root.reveal > .8 && root.voice.ready && !root.voice.preview
            onClicked: if(root.voice.standby) chat.request({action:"jarvis_wake"}); else if(root.voice.handsFree || root.voice.wakeEnabled) chat.request({action:"jarvis_listen",enabled:!root.voice.listening})
            onPressed: if(!root.voice.handsFree && !root.voice.wakeEnabled) chat.request({action:"jarvis_listen",enabled:true})
            onReleased: if(!root.voice.handsFree && !root.voice.wakeEnabled) chat.request({action:"jarvis_finish"})
            onCanceled: if(!root.voice.handsFree && !root.voice.wakeEnabled) chat.request({action:"jarvis_listen",enabled:false})
        }
        Satellite { slot: 1; glyph: "stop"; hint: "Stop speech and actions"; enabled: root.reveal > .8 && (chat.busy || root.voice.speaking); onClicked: chat.request({action:"jarvis_stop"}) }
        Satellite { slot: 2; glyph: "chat"; hint: "Open conversation"; onClicked: { root.controlsPinned=false;chat.openConversation() } }
        Satellite { slot: 3; glyph: root.voice.muted ? "muted" : "volume"; hint: root.voice.muted ? "Unmute replies" : "Mute spoken replies"; accent: root.voice.muted; onClicked: root.setting("muted",!root.voice.muted) }
        Satellite { slot: 4; glyph: root.voice.scope === "browser" ? "globe" : "desktop"; hint: root.voice.scope === "browser" ? "Browser mode · switch to desktop" : "Desktop mode · switch to browser"; enabled: root.reveal > .8 && !chat.busy; onClicked: root.setting("scope",root.voice.scope === "desktop" ? "browser" : "desktop") }
        Satellite { slot: 5; glyph: "settings"; hint: "Jarvis settings"; onClicked: { root.controlsPinned=false;chat.openJarvisSettings() } }
        Satellite { slot: 6; glyph: "sleep"; hint: root.voice.wakeEnabled ? "Stand by for Hey Jarvis" : "Mute microphone and pause"; onClicked: { chat.request({action:"jarvis_standby"});root.controlsPinned=false } }
        Satellite { slot: 7; glyph: "power"; hint: "Turn Jarvis off"; onClicked: chat.setJarvis(false,false) }
    }
}
