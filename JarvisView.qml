// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.Commons
import "Theme.js" as Theme
import "VoiceStatus.js" as Voice

ColumnLayout {
    id: root
    required property var chat
    required property var host
    property bool preferences: false
    readonly property var voice: chat.jarvis
    readonly property color dim: Theme.alpha(Color.foreground, 0.55)
    spacing: Style.space(8)
    function setting(key,value) { var s={};s[key]=value;chat.request({action:"jarvis_settings",settings:s}) }
    RowLayout {
        Layout.fillWidth: true
        spacing: Style.space(5)
        Rectangle { width: Style.space(4); height: width; radius: width/2; color: voice.listening ? Color.accent : root.dim }
        Text { Layout.fillWidth: true; text: Voice.label(voice,chat.busy); color: root.dim; font.family: Style.font.family; font.pixelSize: Style.font.body; elide: Text.ElideRight }
        ActionButton { glyph: "settings"; subtle: !root.preferences; hint: "Advanced Jarvis settings"; implicitWidth: Style.space(23); implicitHeight: Style.space(23); onClicked: root.preferences = !root.preferences }
    }
    Item {
        visible: !root.preferences
        Layout.fillWidth: true; Layout.fillHeight: true
        Layout.minimumHeight: Style.space(105)
        Loader {
            anchors.fill: parent
            active: root.visible && host.opened && !root.preferences
            source: "JarvisBuddy.qml"
            onLoaded: {
                item.mood = Qt.binding(() => chat.error || root.voice.error ? "error" : root.voice.stage)
                item.inputLevel = Qt.binding(() => root.voice.inputLevel || 0)
                item.outputLevel = Qt.binding(() => root.voice.outputLevel || 0)
                item.reducedMotion = Qt.binding(() => root.voice.reducedMotion || false)
                item.gazeX = Qt.binding(() => root.voice.gazeX || 0)
                item.gazeY = Qt.binding(() => root.voice.gazeY || 0)
                item.expressiveness = Qt.binding(() => root.voice.expressiveness === undefined ? 1 : root.voice.expressiveness)
                item.completedAt = Qt.binding(() => root.voice.completedAt || 0)
            }
        }
        Text { anchors.centerIn: parent; visible: !voice.ready; text: ""; color: root.dim }
    }
    Loader {
        visible: root.preferences; active: root.preferences
        Layout.fillWidth: true; Layout.fillHeight: true
        sourceComponent: Component { JarvisSettings { chat: root.chat; onDone: root.preferences = false } }
    }
    ColumnLayout {
        visible: !root.preferences
        Layout.fillWidth: true
        spacing: Style.space(4)
        Text {
            Layout.fillWidth: true
            text: voice.error || voice.partial || voice.caption || "Ready when you are"
            color: voice.error ? Color.accent : voice.partial ? root.dim : Color.foreground
            font.family: Style.font.family; font.pixelSize: Style.font.body
            wrapMode: Text.WordWrap; maximumLineCount: 4; elide: Text.ElideRight
            Accessible.role: Accessible.StaticText
        }
        Text { visible: chat.busy; Layout.fillWidth: true; text: voice.taskCaption || "Same agent · same session"; elide: Text.ElideRight; color: root.dim; font.family: Style.font.family; font.pixelSize: Style.font.body }
    }
    Repeater {
        model: chat.agentRequests.slice(0,1)
        AgentPrompt { required property var modelData; Layout.fillWidth: true; request: modelData; chat: root.chat; host: root.host }
    }
    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.alpha(Color.foreground,0.09) }
    RowLayout {
        Layout.fillWidth: true
        ActionButton {
            glyph: voice.listening ? "mic" : "mic-off"; accent: voice.listening
            enabled: voice.ready
            hint: voice.standby ? "Wake Jarvis" : voice.handsFree || voice.wakeEnabled ? (voice.listening ? "Mute microphone" : "Listen") : "Hold to talk"
            onClicked: if (voice.standby) chat.request({action:"jarvis_wake"}); else if (voice.handsFree || voice.wakeEnabled) chat.request({action:"jarvis_listen",enabled:!voice.listening})
            onPressed: if (!voice.handsFree && !voice.wakeEnabled) chat.request({action:"jarvis_listen",enabled:true})
            onReleased: if (!voice.handsFree && !voice.wakeEnabled) chat.request({action:"jarvis_finish"})
            onCanceled: if (!voice.handsFree && !voice.wakeEnabled) chat.request({action:"jarvis_listen",enabled:false})
        }
        ActionButton { glyph: "stop"; hint: "Stop speech and actions · Ctrl+Alt+Esc"; enabled: chat.busy || voice.speaking || voice.stage === "acting"; onClicked: chat.request({action:"jarvis_stop"}) }
        Item { Layout.fillWidth: true }
        ActionButton { text: voice.scope === "browser" ? "Browser" : "Desktop"; subtle: true; hint: voice.scope === "browser" ? "Headless browser · click for desktop" : "Desktop and default browser · click for headless browser"; onClicked: root.setting("scope",voice.scope === "desktop" ? "browser" : "desktop") }
        ActionButton { glyph: "chat"; subtle: true; hint: "Return to conversation"; onClicked: chat.setJarvis(false) }
    }
    TextField {
        Layout.fillWidth: true
        placeholderText: chat.busy ? "Correct or redirect…" : "Type instead…"; text: chat.draft
        enabled: !chat.terminalOpen
        font.family: Style.font.family; font.pixelSize: Style.font.body; color: Color.foreground
        placeholderTextColor: root.dim
        leftPadding: Style.space(8); rightPadding: Style.space(8)
        background: Rectangle { color: Theme.alpha(Color.foreground,0.035); radius: Style.space(5); border.width: parent.activeFocus ? 1 : 0; border.color: Color.accent }
        onTextEdited: chat.draft=text
        onAccepted: chat.submit()
    }
}
