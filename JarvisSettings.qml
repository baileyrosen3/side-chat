// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.Commons
import "Theme.js" as Theme

ColumnLayout {
    id: root
    required property var chat
    signal done()
    property string section: "Speech"
    property var draft: ({})
    property var saved: ({})
    property bool pending: false
    readonly property bool dirty: JSON.stringify(draft) !== JSON.stringify(saved)
    readonly property string listeningMode: draft.wakeEnabled ? "wake" : draft.handsFree ? "open" : "hold"
    readonly property color dim: Theme.alpha(Color.foreground, 0.55)
    readonly property var keys: ["asrModel","modelPath","asrThreads","streamingProfile","ttsModel","ttsThreads","voice","volume","speechRate","spokenProgress","adaptivePause","noiseRejection","handsFree","endSilence","minSpeech","vadThreshold","maxUtterance","bargeIn","echoCancellation","source","sink","muted","scope","reducedMotion","wakeEnabled","wakeThreshold","followupSeconds","screenContext","selectionContext","screenImages","memoryEnabled","quickCommands","personality","expressiveness"]
    spacing: Style.space(8)
    onSectionChanged: scroll.contentY = 0
    function reset() {
        var next = {}; for (var key of keys) next[key] = chat.jarvis[key]
        saved = next; draft = Object.assign({},next)
    }
    function set(key, value) {
        var next=Object.assign({},draft)
        if (key === "listeningMode") { next.wakeEnabled=value === "wake"; next.handsFree=value !== "hold" }
        else next[key]=value
        draft=next
    }
    Component.onCompleted: { reset(); chat.request({action:"jarvis_devices"}) }
    Connections {
        target: root.chat
        function onJarvisChanged() {
            if (root.pending && root.keys.every(key => root.draft[key] === root.chat.jarvis[key])) { root.pending=false; root.reset() }
            else if (!root.dirty) root.reset()
        }
        function onErrorChanged() { if (root.chat.error) root.pending=false }
    }

    component Note: Text {
        Layout.fillWidth: true
        color: root.dim; font.family: Style.font.family; font.pixelSize: Style.font.body
        wrapMode: Text.Wrap; lineHeight: 1.15
    }
    component Choice: ColumnLayout {
        id: choice
        required property string label
        required property string key
        required property var options
        spacing: Style.space(3); Layout.fillWidth: true
        Note { text: choice.label }
        ComboBox {
            id: select
            implicitHeight: Style.space(27)
            Layout.fillWidth: true; model: choice.options; textRole: "name"; valueRole: "id"
            currentIndex: Math.max(0,choice.options.findIndex(v => v.id === (choice.key === "listeningMode" ? root.listeningMode : root.draft[choice.key])))
            font.family: Style.font.family; font.pixelSize: Style.font.body
            palette.button: Color.background; palette.buttonText: Color.foreground
            palette.text: Color.foreground; palette.base: Color.background
            palette.highlight: Color.accent; palette.highlightedText: Color.background
            Accessible.name: choice.label
            onActivated: {
                root.set(choice.key,choice.options[currentIndex].id)
                if (choice.key === "ttsModel") { root.set("voice",root.draft.ttsModel === "pocket" ? "alba" : "af_heart"); root.set("speechRate",1) }
            }
            background: Rectangle { radius: Style.space(5); color: Theme.alpha(Color.foreground,0.045); border.width: select.activeFocus ? 1 : 0; border.color: Color.accent }
            contentItem: Text { leftPadding: Style.space(8); rightPadding: Style.space(22); text: select.displayText; color: Color.foreground; font: select.font; elide: Text.ElideRight; verticalAlignment: Text.AlignVCenter }
        }
    }
    component Toggle: RowLayout {
        id: toggle
        required property string label
        required property string key
        property string yes: "On"
        property string no: "Off"
        Layout.fillWidth: true
        Note { text: toggle.label }
        ActionButton { text: root.draft[toggle.key] ? toggle.yes : toggle.no; subtle: !root.draft[toggle.key]; onClicked: root.set(toggle.key,!root.draft[toggle.key]); Accessible.name: toggle.label + ": " + text }
    }
    component NumberSetting: RowLayout {
        id: number
        required property string label
        required property string key
        required property int low
        required property int high
        property int multiplier: 1
        property int step: 1
        property string unit: ""
        Layout.fillWidth: true
        Note { text: number.label }
        SpinBox {
            id: spin
            implicitHeight: Style.space(27)
            from: number.low; to: number.high; stepSize: number.step; editable: true
            value: Math.round((root.draft[number.key] || 0)*number.multiplier)
            font.family: Style.font.family; font.pixelSize: Style.font.body
            palette.button: Color.background; palette.buttonText: Color.foreground
            palette.text: Color.foreground; palette.base: Color.background; palette.highlight: Color.accent
            implicitWidth: Style.space(136)
            Layout.minimumWidth: implicitWidth
            textFromValue: (v, locale) => (number.multiplier === 1 ? String(v) : (v/number.multiplier).toFixed(2)) + number.unit
            valueFromText: (text, locale) => Math.round(parseFloat(text)*number.multiplier)
            onValueModified: root.set(number.key,value/number.multiplier)
            Accessible.name: number.label
            background: Rectangle { radius: Style.space(5); color: Theme.alpha(Color.foreground,0.045); border.width: spin.activeFocus ? 1 : 0; border.color: Color.accent }
        }
    }

    RowLayout {
        Layout.fillWidth: true; spacing: Style.space(4)
        Repeater {
            model: ["Speech","Listening","Control","Companion"]
            ActionButton { required property string modelData; text: modelData; selected: root.section === modelData; onClicked: root.section = modelData }
        }
        Item { Layout.fillWidth: true }
    }
    Flickable {
        id: scroll
        visible: root.section !== "Companion"
        Layout.fillWidth: true; Layout.fillHeight: true
        clip: true; contentWidth: width; contentHeight: fields.implicitHeight
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar { }
        ColumnLayout {
            id: fields
            width: scroll.width - Style.space(8); spacing: Style.space(10)
            ColumnLayout {
                visible: root.section === "Speech"; Layout.fillWidth: true; spacing: Style.space(9)
                Choice { label: "Speech recognition"; key: "asrModel"; options: [{id:"parakeet-unified",name:"Parakeet Unified · English"},{id:"zipformer-whisper",name:"Zipformer + Whisper · English"}] }
                Note { visible: root.draft.asrModel === "parakeet-unified"; text: chat.jarvis.parakeetAvailable ? "Installed · reuses your local model" : "Choose an installed Parakeet Unified ONNX folder below" }
                ColumnLayout {
                    visible: root.draft.asrModel === "parakeet-unified"; Layout.fillWidth: true; spacing: Style.space(3)
                    Note { text: "Model folder · blank uses Voxtype’s model" }
                    TextField {
                        Layout.fillWidth: true; text: root.draft.modelPath || ""
                        placeholderText: root.chat.jarvis.modelResolvedPath || "Automatic"; placeholderTextColor: root.dim
                        color: Color.foreground; font.family: Style.font.family; font.pixelSize: Style.font.body
                        selectByMouse: true; Accessible.name: "Parakeet model folder"
                        onTextEdited: root.set("modelPath",text)
                        background: Rectangle { radius: Style.space(5); color: Theme.alpha(Color.foreground,0.045); border.width: parent.activeFocus ? 1 : 0; border.color: Color.accent }
                    }
                }
                Choice { visible: root.draft.asrModel === "parakeet-unified"; label: "Streaming profile"; key: "streamingProfile"; options: [{id:"fast",name:"Fast · 320 ms chunks"},{id:"balanced",name:"Balanced · 560 ms chunks"},{id:"accurate",name:"More context · 1,120 ms chunks"}] }
                NumberSetting { label: "Recognition CPU threads"; key: "asrThreads"; low: 1; high: 12 }
                Rectangle { Layout.fillWidth: true; height: 1; color: Theme.alpha(Color.foreground,0.09) }
                Choice { label: "Speech output model"; key: "ttsModel"; options: [{id:"pocket",name:"Pocket TTS · streaming"},{id:"kokoro",name:"Kokoro · complete sentences"}] }
                Choice { label: "Voice"; key: "voice"; options: root.draft.ttsModel === "pocket" ? [{id:"alba",name:"Alba"},{id:"marius",name:"Marius"},{id:"javert",name:"Javert"},{id:"fantine",name:"Fantine"},{id:"eponine",name:"Éponine"},{id:"azelma",name:"Azelma"},{id:"charles",name:"Charles"},{id:"mary",name:"Mary"},{id:"peter_yearsley",name:"Peter"}] : [{id:"af_heart",name:"Heart"},{id:"af_bella",name:"Bella"},{id:"am_michael",name:"Michael"}] }
                ActionButton {
                    objectName: "voicePreview"
                    text: "Preview voice"; subtle: true
                    enabled: root.chat.jarvis.ready && root.chat.jarvis.enabled && !root.chat.busy && root.draft.ttsModel === root.chat.jarvis.ttsModel
                    onClicked: root.chat.request({action:"jarvis_voice_preview",voice:root.draft.voice})
                }
                Note { text: !root.chat.jarvis.enabled ? "Turn on Jarvis to hear a sample." : root.draft.ttsModel !== root.chat.jarvis.ttsModel ? "Apply the speech model to preview its voices." : "Try a sample, then Apply to use that voice. Preview plays even when replies are muted." }
                NumberSetting { label: "Speech CPU threads"; key: "ttsThreads"; low: 1; high: 12 }
                NumberSetting { visible: root.draft.ttsModel === "kokoro"; label: "Speaking pace"; key: "speechRate"; low: 70; high: 140; multiplier: 100; step: 5; unit: "×" }
                NumberSetting { label: "Voice volume"; key: "volume"; low: 0; high: 150; multiplier: 100; step: 5; unit: "×" }
                Toggle { label: "Mute spoken replies"; key: "muted" }
                Toggle { label: "Quick acknowledgment & progress updates"; key: "spokenProgress" }
                Note { text: "Speech stays local. The conversation uses your selected agent and its model from Chat settings." }
            }
            ColumnLayout {
                visible: root.section === "Listening"; Layout.fillWidth: true; spacing: Style.space(9)
                Choice { label: "When should Jarvis listen?"; key: "listeningMode"; options: [{id:"wake",name:"Hey Jarvis · wake, then follow up"},{id:"open",name:"Open microphone · every voice can trigger"},{id:"hold",name:"Hold to talk · press while speaking"}] }
                Note { text: root.listeningMode === "wake" ? "Say Hey Jarvis to start or interrupt a task. Wait for the chime in standby. After the answer, follow-ups work until the window closes. The Stop button always works." : root.listeningMode === "hold" ? "Hold the microphone button while speaking. Release to send. Pauses while holding keep the request together." : "Open mic treats nearby speech as requests. For shared rooms, choose Hey Jarvis or hold-to-talk." }
                Choice { label: "Background noise rejection"; key: "noiseRejection"; options: [{id:"balanced",name:"Balanced · includes softer speech"},{id:"strong",name:"Strong · reject more faint sounds"}] }
                Note { text: "Strong mode can miss soft voices. Speak near the microphone; use a wake word around TV or other people." }
                NumberSetting { visible: root.draft.wakeEnabled; label: "Wake confidence"; key: "wakeThreshold"; low: 50; high: 99; multiplier: 100; step: 1 }
                NumberSetting { visible: root.draft.wakeEnabled; label: "Follow-up window"; key: "followupSeconds"; low: 5; high: 60; unit: " s" }
                Toggle { label: "Allow pauses in unfinished phrases"; key: "adaptivePause" }
                NumberSetting { label: "Pause before sending"; key: "endSilence"; low: 30; high: 200; multiplier: 100; step: 5; unit: " s" }
                NumberSetting { label: "Minimum speech"; key: "minSpeech"; low: 10; high: 70; multiplier: 100; step: 2; unit: " s" }
                NumberSetting { label: "Speech detection threshold"; key: "vadThreshold"; low: 20; high: 90; multiplier: 100; step: 5 }
                Note { text: "Strong mode uses a higher threshold and at least 280 ms of speech. Adaptive pauses allow extra time after unfinished phrases." }
                NumberSetting { label: "Maximum utterance"; key: "maxUtterance"; low: 5; high: 60; step: 5; unit: " s" }
                Toggle { label: "Interrupt Jarvis by speaking"; key: "bargeIn" }
                Toggle { label: "Echo cancellation"; key: "echoCancellation" }
                Note { text: "Keep this on when using speakers. It also applies local noise suppression." }
                Choice { label: "Microphone"; key: "source"; options: [{id:"",name:"System default"}].concat((root.chat.jarvis.devices || []).filter(d => d.kind === "Audio/Source")) }
                Choice { label: "Speaker"; key: "sink"; options: [{id:"",name:"System default"}].concat((root.chat.jarvis.devices || []).filter(d => d.kind === "Audio/Sink")) }
                ActionButton { text: "Refresh devices"; subtle: true; onClicked: root.chat.request({action:"jarvis_devices"}) }
            }
            ColumnLayout {
                visible: root.section === "Control"; Layout.fillWidth: true; spacing: Style.space(9)
                Choice { label: "Computer control"; key: "scope"; options: [{id:"desktop",name:"Desktop · your apps and default browser"},{id:"browser",name:"Browser · isolated headless Chromium"}] }
                Note { text: root.draft.scope === "desktop" ? "Websites open in your visible default Omarchy browser and normal profile. Jarvis uses screenshots, mouse and keyboard to work there." : "Websites open in a separate headless browser. Desktop mouse and keyboard actions are unavailable in this mode." }
                Choice { label: "Screen context"; key: "screenContext"; options: [{id:"off",name:"Off"},{id:"on-request",name:"When I mention this / that / my screen"},{id:"always",name:"With every Desktop request"}] }
                Toggle { label: "Include screen image"; key: "screenImages" }
                Toggle { label: "Include selected text"; key: "selectionContext" }
                Note { text: "Enabled observations go to your chosen agent and its provider. Selection comes from the focused app’s accessibility interface; clipboard history is never read." }
                Toggle { label: "Use saved memories"; key: "memoryEnabled" }
                Toggle { label: "Fast local commands"; key: "quickCommands" }
                Choice { label: "Spoken personality"; key: "personality"; options: [{id:"concise",name:"Concise"},{id:"balanced",name:"Balanced"},{id:"witty",name:"Lightly witty"}] }
                Note { text: "Move the mouse to take over during desktop input. Ctrl Alt Esc stops speech and computer actions. Your agent keeps its normal file tools and permission policy." }
            }
        }
    }
    Loader {
        visible: root.section === "Companion"; active: visible
        Layout.fillWidth: true; Layout.fillHeight: true
        sourceComponent: Component { CompanionSettings { chat: root.chat; draft: root.draft; onSettingChanged: (key,value) => root.set(key,value) } }
    }
    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.alpha(Color.foreground,0.09) }
    RowLayout {
        Layout.fillWidth: true
        ActionButton {
            text: root.pending ? "Applying…" : "Apply"; accent: true; enabled: root.dirty && !chat.busy && !root.pending
            onClicked: { var changed={}; for (var key of root.keys) if (root.draft[key] !== root.saved[key]) changed[key]=root.draft[key]; root.pending=true; chat.request({action:"jarvis_settings",settings:changed}) }
        }
        ActionButton { text: root.dirty ? "Discard" : "Back"; subtle: true; onClicked: { if (root.dirty) root.reset(); else root.done() } }
        Note { text: chat.busy ? "Task running" : root.dirty ? "Unsaved changes" : "Model changes reload voice"; horizontalAlignment: Text.AlignRight }
    }
}
