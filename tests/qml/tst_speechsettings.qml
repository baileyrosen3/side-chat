import QtQuick
import QtTest
import "../.."
import "../../VoiceStatus.js" as Voice

Rectangle {
    width: 360; height: 760; color: "#14171d"
    QtObject {
        id: chat
        property var peek: ({enabled:true,ready:true,ttsModel:"pocket",voice:"marius",spokenProgress:true,
            asrModel:"parakeet-unified",streamingProfile:"fast",asrThreads:4,ttsThreads:4,volume:1,
            speechRate:1,endSilence:.45,minSpeech:.18,vadThreshold:.55,maxUtterance:25,
            handsFree:true,echoCancellation:true,bargeIn:true,source:"",sink:"",devices:[],
            adaptivePause:true,noiseRejection:"strong",wakeEnabled:false,wakeThreshold:.97,followupSeconds:12,modelPath:"",parakeetAvailable:true})
        property bool busy: false
        property string error: ""
        property var commands: []
        function request(command) { commands=commands.concat([command]) }
    }
    PeekSettings { id: settings; anchors.fill: parent; anchors.margins: 12; chat: chat }
    TestCase {
        name: "SpeechSettings"
        when: windowShown
        function init() { failOnWarning(/.?/); chat.busy=false; settings.section="Speech"; settings.reset(); chat.commands=[] }
        function test_preview_uses_draft_without_apply() {
            settings.set("voice","fantine");
            var button=findChild(settings,"voicePreview"); verify(button); verify(button.enabled);
            button.clicked();
            compare(chat.commands.length,1);
            compare(chat.commands[0].action,"peek_voice_preview");
            compare(chat.commands[0].voice,"fantine");
            compare(chat.peek.voice,"marius"); verify(settings.dirty);
            grabImage(settings).save("/tmp/side-chat-voice-settings.png");
        }
        function test_busy_or_unapplied_model_disables_preview() {
            var button=findChild(settings,"voicePreview");
            chat.busy=true; verify(!button.enabled);
            chat.busy=false; settings.set("ttsModel","kokoro"); verify(!button.enabled);
            settings.reset(); verify(button.enabled);
        }
        function test_listening_modes_are_mutually_consistent() {
            settings.set("listeningMode","wake"); compare(settings.draft.wakeEnabled,true); compare(settings.draft.handsFree,true);
            settings.set("listeningMode","hold"); compare(settings.draft.wakeEnabled,false); compare(settings.draft.handsFree,false);
            settings.set("listeningMode","open"); compare(settings.draft.wakeEnabled,false); compare(settings.draft.handsFree,true);
            verify(settings.draft.listeningMode === undefined,"Derived mode must not be saved as an unknown setting");
        }
        function test_hearing_and_transcribing_take_priority_over_busy() {
            compare(Voice.label({ready:true,hearing:true},true),"Listening to you");
            compare(Voice.label({ready:true,transcribing:true},true),"Understanding");
        }
        function test_listening_controls_render() {
            settings.section="Listening"; wait(50);
            grabImage(settings).save("/tmp/side-chat-listening-settings.png");
        }
    }
}
