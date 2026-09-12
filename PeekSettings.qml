// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.Commons
import "Theme.js" as Theme

ColumnLayout {
    id: root
    objectName: "peek-settings"
    ChatStyle { id: ui }
    required property var chat
    signal done()
    property string section: "Speech"
    property var draft: ({})
    property var saved: ({})
    property bool pending: false
    readonly property bool dirty: JSON.stringify(draft) !== JSON.stringify(saved)
    // Memory, routines, watches and undo save on their own; the Apply footer only governs preferences.
    readonly property bool dataTab: section === "Companion" && !!companion.item && companion.item.section !== "Appearance"
    readonly property var defaults: chat.peek.defaults || ({})
    readonly property bool atDefaults: keys.every(key => defaults[key] === undefined || draft[key] === defaults[key])
    readonly property string listeningMode: draft.wakeEnabled ? "wake" : draft.handsFree ? "open" : "hold"
    readonly property color dim: ui.muted
    readonly property var keys: ["asrModel","modelPath","asrThreads","streamingProfile","ttsModel","ttsThreads","voice","volume","speechRate","spokenProgress","adaptivePause","noiseRejection","handsFree","endSilence","minSpeech","vadThreshold","maxUtterance","bargeIn","echoCancellation","source","sink","muted","scope","reducedMotion","wakeEnabled","wakeThreshold","followupSeconds","screenContext","selectionContext","screenImages","memoryEnabled","quickCommands","personality","expressiveness"]
    spacing: Style.space(8)
    onSectionChanged: scroll.contentY = 0
    function reset() {
        var next = {}; for (var key of keys) next[key] = chat.peek[key]
        saved = next; draft = Object.assign({},next)
    }
    function restoreDefaults() {
        var next = Object.assign({}, draft)
        for (var key of keys) if (defaults[key] !== undefined) next[key] = defaults[key]
        draft = next
    }
    function set(key, value) {
        var next=Object.assign({},draft)
        if (key === "listeningMode") { next.wakeEnabled=value === "wake"; next.handsFree=value !== "hold" }
        else next[key]=value
        draft=next
    }
    Component.onCompleted: { reset(); chat.request({action:"peek_devices"}) }
    Connections {
        target: root.chat
        function onPeekChanged() {
            if (root.pending && root.keys.every(key => root.draft[key] === root.chat.peek[key])) { root.pending=false; root.reset() }
            else if (!root.dirty) root.reset()
        }
        function onErrorChanged() { if (root.chat.error) root.pending=false }
    }

    component Note: Text {
        Layout.fillWidth: true
        color: root.dim; font.family: Style.font.family; font.pixelSize: ui.small
        wrapMode: Text.Wrap; lineHeight: 1.05
    }
    component Choice: RowLayout {
        id: choice
        required property string label
        required property string key
        required property var options
        spacing: Style.space(3); Layout.fillWidth: true
        Note { text: choice.label; font.weight: Font.Medium; color: ui.foreground; Layout.fillWidth: false; Layout.preferredWidth: Style.space(100) }
        ChatComboBox {
            id: select
            Layout.minimumWidth: 0
            Layout.fillWidth: true; model: choice.options; textRole: "name"; valueRole: "id"
            currentIndex: Math.max(0,choice.options.findIndex(v => v.id === (choice.key === "listeningMode" ? root.listeningMode : root.draft[choice.key])))
            Accessible.name: choice.label
            onActivated: {
                root.set(choice.key,choice.options[currentIndex].id)
                if (choice.key === "ttsModel") { root.set("voice",root.draft.ttsModel === "pocket" ? "alba" : "af_heart"); root.set("speechRate",1) }
                if (choice.key === "asrModel" && choice.options[currentIndex].id === "voxtype") {
                    // Voxtype owns endpointing and activation; keep Peek's
                    // wake/open modes from leaving its daemon recording forever.
                    root.set("wakeEnabled",false); root.set("handsFree",false)
                }
            }

        }
    }
    component Toggle: RowLayout {
        id: toggle
        required property string label
        required property string key
        property string yes: "On"
        property string no: "Off"
        Layout.fillWidth: true
        Note { text: toggle.label; color: ui.foreground }
        ChatSwitch { onText: toggle.yes; offText: toggle.no; checked: !!root.draft[toggle.key]; onClicked: root.set(toggle.key,!root.draft[toggle.key]); Accessible.name: toggle.label + ": " + text }
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
        Note { text: number.label; color: ui.foreground }
        ChatSpinBox {
            id: spin
            from: number.low; to: number.high; stepSize: number.step
            value: Math.round((root.draft[number.key] || 0)*number.multiplier)
            Layout.minimumWidth: implicitWidth
            textFromValue: (v, locale) => (number.multiplier === 1 ? String(v) : (v/number.multiplier).toFixed(2)) + number.unit
            valueFromText: (text, locale) => Math.round(parseFloat(text)*number.multiplier)
            onValueModified: root.set(number.key,value/number.multiplier)
            Accessible.name: number.label
        }
    }

    Flow {
        Layout.fillWidth: true; spacing: Style.space(3)
        Repeater {
            model: ["Speech","Listening","Control","Companion"]
            ActionButton { required property string modelData; text: modelData; tab: true; selected: root.section === modelData; onClicked: root.section = modelData }
        }
    }
    Flickable {
        id: scroll
        Layout.preferredHeight: Math.min(fields.implicitHeight, Style.space(420))
        visible: root.section !== "Companion"
        Layout.fillWidth: true; Layout.fillHeight: true
        clip: true; contentWidth: width; contentHeight: fields.implicitHeight
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ChatScrollBar { }
        ColumnLayout {
            id: fields
            width: scroll.width - Style.space(8); spacing: Style.space(7)
            ColumnLayout {
                visible: root.section === "Speech"; Layout.fillWidth: true; spacing: Style.space(6)
                ChatSection { text: "Recognition" }
                Choice { label: "Model"; key: "asrModel"; options: [{id:"voxtype",name:"Voxtype · shared daemon"},{id:"parakeet-unified",name:"Parakeet Unified"},{id:"zipformer-whisper",name:"Zipformer + Whisper"}] }
                Note { text: root.draft.asrModel === "voxtype" ? (chat.peek.voxtypeAvailable ? "Uses your existing Voxtype daemon; Peek does not load a second ASR model." : "Install voxtype-bin and start its user daemon before applying this choice.") : "English only. Voxtype is the default; Parakeet and Zipformer + Whisper are optional local downloads." }
                Note { visible: root.draft.asrModel === "parakeet-unified"; text: chat.peek.parakeetAvailable ? "Installed · reuses your local model" : "Choose an installed Parakeet Unified ONNX folder below" }
                ColumnLayout {
                    visible: root.draft.asrModel === "parakeet-unified"; Layout.fillWidth: true; spacing: Style.space(3)
                    Note { text: "Model folder · blank uses Voxtype’s model" }
                    ChatField {
                        Layout.fillWidth: true; text: root.draft.modelPath || ""
                        placeholderText: root.chat.peek.modelResolvedPath || "Automatic"; placeholderTextColor: root.dim
                        selectByMouse: true; Accessible.name: "Parakeet model folder"
                        onTextEdited: root.set("modelPath",text)
                    }
                }
                Choice { visible: root.draft.asrModel === "parakeet-unified"; label: "Streaming profile"; key: "streamingProfile"; options: [{id:"fast",name:"Fast · 320 ms"},{id:"balanced",name:"Balanced · 560 ms"},{id:"accurate",name:"More context · 1,120 ms"}] }
                NumberSetting { visible: root.draft.asrModel !== "voxtype"; label: "Recognition threads"; key: "asrThreads"; low: 1; high: 12 }
                ChatSection { text: "Spoken replies" }
                Choice { label: "Model"; key: "ttsModel"; options: [{id:"pocket",name:"Pocket TTS"},{id:"kokoro",name:"Kokoro"}] }
                Note { text: root.draft.ttsModel === "pocket" ? "Streams speech as it is generated." : "Waits for complete sentences before speaking." }
                Choice { label: "Voice"; key: "voice"; options: root.draft.ttsModel === "pocket" ? [{id:"alba",name:"Alba"},{id:"marius",name:"Marius"},{id:"javert",name:"Javert"},{id:"fantine",name:"Fantine"},{id:"eponine",name:"Éponine"},{id:"azelma",name:"Azelma"},{id:"charles",name:"Charles"},{id:"mary",name:"Mary"},{id:"peter_yearsley",name:"Peter"}] : [{id:"af_heart",name:"Heart"},{id:"af_bella",name:"Bella"},{id:"am_michael",name:"Michael"}] }
                ActionButton {
                    objectName: "voicePreview"
                    text: "Preview voice"; subtle: true
                    enabled: root.chat.peek.ready && root.chat.peek.enabled && !root.chat.busy && root.draft.ttsModel === root.chat.peek.ttsModel
                    onClicked: root.chat.request({action:"peek_voice_preview",voice:root.draft.voice})
                }
                Note { text: !root.chat.peek.enabled ? "Turn on Peek to hear a sample." : root.draft.ttsModel !== root.chat.peek.ttsModel ? "Apply the speech model to preview its voices." : "Preview works while muted. Apply to save your voice." }
                NumberSetting { label: "Speech threads"; key: "ttsThreads"; low: 1; high: 12 }
                NumberSetting { visible: root.draft.ttsModel === "kokoro"; label: "Speaking pace"; key: "speechRate"; low: 70; high: 140; multiplier: 100; step: 5; unit: "×" }
                NumberSetting { label: "Voice volume"; key: "volume"; low: 0; high: 150; multiplier: 100; step: 5; unit: "×" }
                Toggle { label: "Mute spoken replies"; key: "muted" }
                Toggle { label: "Spoken progress updates"; key: "spokenProgress" }
                Note { text: "Speech runs locally; replies use your selected agent." }
            }
            ColumnLayout {
                visible: root.section === "Listening"; Layout.fillWidth: true; spacing: Style.space(6)
                ChatSection { text: "Activation" }
                Choice { label: "Listening"; key: "listeningMode"; options: root.draft.asrModel === "voxtype" ? [{id:"hold",name:"Manual toggle"}] : [{id:"wake",name:"Wake phrase"},{id:"open",name:"Open microphone"},{id:"hold",name:"Hold to talk"}] }
                Note { text: root.draft.asrModel === "voxtype" ? "Voxtype mode uses the microphone toggle as push-to-talk. Peek submits the saved transcript when you toggle it off; wake phrase and automatic silence endpointing are unavailable." : root.listeningMode === "wake" ? "Wake phrase: Hey Jarvis. The bundled upstream detector recognizes this phrase. Wait for the chime, then speak to Peek. Follow up after an answer, or say the phrase again to interrupt." : root.listeningMode === "hold" ? "Hold the microphone while speaking. Release to send." : "Nearby speech can trigger requests. Use wake word or hold-to-talk in shared rooms." }
                ChatSection { text: "Detection" }
                Choice { visible: root.draft.asrModel !== "voxtype"; label: "Noise rejection"; key: "noiseRejection"; options: [{id:"balanced",name:"Balanced"},{id:"strong",name:"Strong"}] }
                Note { visible: root.draft.asrModel !== "voxtype"; text: root.draft.noiseRejection === "strong" ? "Rejects faint sounds and needs at least 280 ms of speech, so quiet speech may be missed." : "Includes softer speech." }
                NumberSetting { visible: root.draft.asrModel !== "voxtype" && root.draft.wakeEnabled; label: "Wake confidence"; key: "wakeThreshold"; low: 50; high: 99; multiplier: 100; step: 1 }
                NumberSetting { visible: root.draft.asrModel !== "voxtype" && root.draft.wakeEnabled; label: "Follow-up window"; key: "followupSeconds"; low: 5; high: 60; unit: " s" }
                Toggle { visible: root.draft.asrModel !== "voxtype"; label: "Wait for unfinished phrases"; key: "adaptivePause" }
                NumberSetting { visible: root.draft.asrModel !== "voxtype"; label: "Pause before sending"; key: "endSilence"; low: 30; high: 200; multiplier: 100; step: 5; unit: " s" }
                NumberSetting { visible: root.draft.asrModel !== "voxtype"; label: "Minimum speech"; key: "minSpeech"; low: 10; high: 70; multiplier: 100; step: 2; unit: " s" }
                NumberSetting { visible: root.draft.asrModel !== "voxtype"; label: "Speech detection threshold"; key: "vadThreshold"; low: 20; high: 90; multiplier: 100; step: 5 }
                NumberSetting { visible: root.draft.asrModel !== "voxtype"; label: "Maximum utterance"; key: "maxUtterance"; low: 5; high: 60; step: 5; unit: " s" }
                Toggle { label: "Interrupt Peek by speaking"; key: "bargeIn" }
                Toggle { visible: root.draft.asrModel !== "voxtype"; label: "Echo cancellation"; key: "echoCancellation" }
                Note { text: root.draft.asrModel === "voxtype" ? "Voxtype owns microphone routing and endpointing. Its device and output settings remain in ~/.config/voxtype/config.toml." : "Recommended with speakers; includes noise suppression." }
                ChatSection { text: "Audio devices" }
                Choice { visible: root.draft.asrModel !== "voxtype"; label: "Microphone"; key: "source"; options: [{id:"",name:"System default"}].concat((root.chat.peek.devices || []).filter(d => d.kind === "Audio/Source")) }
                Choice { visible: root.draft.asrModel !== "voxtype"; label: "Speaker"; key: "sink"; options: [{id:"",name:"System default"}].concat((root.chat.peek.devices || []).filter(d => d.kind === "Audio/Sink")) }
                ActionButton { visible: root.draft.asrModel !== "voxtype"; text: "Refresh devices"; subtle: true; onClicked: root.chat.request({action:"peek_devices"}) }
            }
            ColumnLayout {
                visible: root.section === "Control"; Layout.fillWidth: true; spacing: Style.space(6)
                ChatSection { text: "Access & context" }
                Choice { label: "Computer control"; key: "scope"; options: [{id:"desktop",name:"Desktop"},{id:"browser",name:"Isolated browser"}] }
                Note { text: root.draft.scope === "desktop" ? "Uses your apps and normal browser profile, with screenshots, mouse and keyboard." : "Uses a separate headless Chromium without desktop input." }
                Choice { label: "Screen context"; key: "screenContext"; options: [{id:"off",name:"Off"},{id:"on-request",name:"When I mention my screen"},{id:"always",name:"Every Desktop request"}] }
                Note { visible: root.draft.screenContext === "on-request"; text: "Shares the active window when you explicitly mention “my screen”, “this window”, or a screenshot. Ordinary words like “this” or “error” do not capture it." }
                Toggle { label: "Include screen image"; key: "screenImages" }
                Toggle { label: "Include selected text"; key: "selectionContext" }
                Note { text: "Screen context goes to your agent’s provider. Selected text comes from the focused app." }
                ChatSection { text: "Behavior" }
                Toggle { label: "Use saved memories"; key: "memoryEnabled" }
                Toggle { label: "Fast local commands"; key: "quickCommands" }
                Choice { label: "Spoken personality"; key: "personality"; options: [{id:"concise",name:"Concise"},{id:"balanced",name:"Balanced"},{id:"witty",name:"Lightly witty"}] }
                Note { text: (root.chat.peek.controlCapabilities && root.chat.peek.controlCapabilities.takeover ? "Physical takeover monitors " + root.chat.peek.controlCapabilities.inputDevices + " input devices. " : "Physical takeover is not available yet. Use the Stop button. ") + (root.chat.peek.controlCapabilities && root.chat.peek.controlCapabilities.stopShortcut ? "Ctrl+Alt+Esc stops speech and computer actions. " : "") + "Agent permissions still apply." }
            }
        }
    }
    Loader {
        id: companion
        visible: root.section === "Companion"; active: visible
        Layout.preferredHeight: Math.min(item ? item.contentHeight : 0, Style.space(420))
        Layout.fillWidth: true; Layout.fillHeight: true
        sourceComponent: Component { CompanionSettings { chat: root.chat; draft: root.draft; onSettingChanged: (key,value) => root.set(key,value) } }
    }
    Rectangle { Layout.fillWidth: true; height: 1; color: ui.line }
    RowLayout {
        Layout.fillWidth: true
        ActionButton {
            objectName: "peek-apply"
            visible: !root.dataTab || root.dirty
            text: root.pending ? "Applying…" : "Apply"; accent: true; enabled: root.dirty && !chat.busy && !root.pending
            onClicked: { var changed={}; for (var key of root.keys) if (root.draft[key] !== root.saved[key]) changed[key]=root.draft[key]; root.pending=true; chat.request({action:"peek_settings",settings:changed}) }
        }
        ActionButton { text: root.dirty ? "Discard" : "Back"; subtle: true; onClicked: { if (root.dirty) root.reset(); else root.done() } }
        ActionButton {
            objectName: "peek-defaults"
            visible: !root.dataTab && Object.keys(root.defaults).length > 0
            text: "Defaults"; subtle: true; enabled: !root.atDefaults && !chat.busy
            hint: "Restore the built-in Peek preferences, then Apply"
            onClicked: root.restoreDefaults()
        }
        Note { text: root.dataTab && !root.dirty ? "" : chat.busy ? "Task running" : root.dirty ? "Unsaved changes" : "Saved"; horizontalAlignment: Text.AlignRight }
    }
}
