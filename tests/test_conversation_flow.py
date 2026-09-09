import tempfile
import threading
import unittest
from unittest.mock import Mock,patch

from backend import Bridge
from jarvis.listening import NoiseFloor,pause_seconds
from jarvis.audio import EchoAudio
from jarvis.wake import ConversationGate


class ListeningPolicyTests(unittest.TestCase):
    def test_task_activity_does_not_authorize_background_interruptions(self):
        gate=ConversationGate(5)
        gate.address(100);self.assertTrue(gate.accepts_interrupt(101))
        gate.consume_address();gate.wake(102)
        self.assertTrue(gate.active(103));self.assertFalse(gate.accepts_interrupt(103))
        gate.address(104);self.assertTrue(gate.accepts_interrupt(105))
        gate.standby();self.assertFalse(gate.accepts_interrupt(105))

    def test_extra_pause_only_for_unfinished_phrases(self):
        for text in ('Open the','I need this because','Change the color and...'):
            self.assertEqual(pause_seconds(text,.45),1)
            self.assertEqual(pause_seconds(text,.45,False),.45)
        for text in ('Stop.','Yes.','Open Firefox.','Set the volume to 25 percent.'):
            self.assertEqual(pause_seconds(text,.45),.45)
        self.assertEqual(pause_seconds('Open the',1.5),1.5)

    def test_noise_floor_rejects_faint_starts_without_chasing_spikes(self):
        floor=NoiseFloor()
        for _ in range(100):floor.observe(.002)
        floor.observe(.2)
        self.assertFalse(floor.accepts(.003,True))
        self.assertTrue(floor.accepts(.02,True))
        self.assertTrue(floor.accepts(.0001,False))

    def test_monitor_routes_explicitly_and_devices_cannot_fall_back(self):
        a=EchoAudio();a.source='fixture.monitor'
        with patch('jarvis.audio.subprocess.Popen') as spawn:a.record()
        args=spawn.call_args.args[0]
        self.assertEqual(args[args.index('--target')+1],'fixture')
        self.assertIn('stream.capture.sink=true',args[args.index('-P')+1])
        self.assertIn('node.dont-fallback=true',args[args.index('-P')+1])


class ConversationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.b=Bridge(self.temp.name,lambda _:None)
        self.b.new();self.b.current['agent']='omp'
        self.b.current['messages']=[{'role':'assistant','text':'First step complete.','tools':[]}]
        self.v=self.b.jarvis;self.v.state.update(enabled=True,ready=True,listening=True)
        self.v.prefs.update(muted=False,screenContext='off')
        self.sent=[];self.v.send_worker=self.sent.append

    def tearDown(self):
        self.b.busy=False;self.b.rpc=None;self.b.close();self.temp.cleanup()

    def test_microphone_shortcut_toggles_requested_state_while_warming(self):
        self.v.state.update(ready=False,listening=False)
        self.v.want_listen=True
        prefs=dict(self.v.prefs)
        self.v.dispatch({'action':'jarvis_toggle_listen'})
        self.assertFalse(self.v.want_listen)
        self.v.dispatch({'action':'jarvis_toggle_listen'})
        self.assertTrue(self.v.want_listen)
        self.v.dispatch({'action':'jarvis_toggle_listen'})
        self.assertFalse(self.v.want_listen)
        self.v.voice_event({'type':'ready'})
        listens=[c['enabled'] for c in self.sent if c['action']=='listen']
        self.assertEqual(listens,[False,True,False,False])
        self.assertEqual(self.v.prefs,prefs)
        self.assertFalse(any(c['action']=='cancel' for c in self.sent))

    def test_microphone_shortcut_starts_jarvis_with_microphone_enabled(self):
        for hands_free in (False,True):
            with self.subTest(hands_free=hands_free):
                self.v.state.update(enabled=False,ready=False,listening=False)
                self.v.prefs['handsFree']=hands_free
                self.v.prefs['wakeEnabled']=False
                prefs=dict(self.v.prefs)
                def enable(enabled):
                    self.v.state['enabled']=enabled
                    self.v.want_listen=self.v.prefs['handsFree']
                with patch.object(self.v,'enable',side_effect=enable) as start:
                    self.v.dispatch({'action':'jarvis_toggle_listen','accent':'#57c2ff'})
                start.assert_called_once_with(True)
                self.assertTrue(self.v.want_listen)
                self.assertEqual(self.sent[-1],{'action':'listen','enabled':True})
                self.assertEqual(self.v.prefs,prefs)
                self.assertEqual(self.v.state['accent'],'#57c2ff')

    def test_microphone_shortcut_finishes_input_without_stopping_answer(self):
        self.b.busy=True;self.v.want_listen=True
        self.v.state['speaking']=True
        self.v.voice_event({'type':'speech_start'})
        generation=self.v.input_generation
        self.v.dispatch({'action':'jarvis_toggle_listen'})
        self.assertEqual(self.v.input_generation,generation)
        self.assertEqual(self.sent[-1],{'action':'listen','enabled':False,'finish':True})
        self.assertFalse(self.v.want_listen)
        self.assertTrue(self.b.busy)
        self.assertTrue(self.v.state['speaking'])
        self.assertFalse(any(c['action']=='cancel' for c in self.sent))

    def test_microphone_off_sends_pending_phrase_to_agent(self):
        self.v.want_listen=True
        generation=self.v.input_generation
        self.v.voice_event({'type':'speech_start','generation':generation,'utterance':1})
        self.v.dispatch({'action':'jarvis_toggle_listen'})
        self.v.voice_event({'type':'microphone','active':False,'finishing':True})
        self.assertFalse(self.v.state['listening'])
        self.assertTrue(self.v.state['transcribing'])
        self.assertFalse(any(c['action']=='resume_speech' for c in self.sent))
        with patch.object(self.b,'send') as send:
            self.v.voice_event({'type':'transcript','text':'Use the blue theme.','generation':generation,'utterance':1})
            self.v.voice_event({'type':'utterance_end','recognized':True,'hadSpeech':True,'generation':generation,'utterance':1})
            self.v.input_queue.join()
            send.assert_called_once_with({'text':'Use the blue theme.','attachments':[]})
        self.assertFalse(self.v.want_listen)
        self.assertFalse(self.v.state['transcribing'])

    def test_microphone_off_without_speech_preserves_answer(self):
        self.v.want_listen=True;self.v.state['speaking']=True
        self.v.dispatch({'action':'jarvis_toggle_listen'})
        with patch.object(self.b,'send') as send:
            self.v.voice_event({'type':'microphone','active':False,'finishing':False})
            send.assert_not_called()
        self.assertTrue(self.v.state['speaking'])
        self.assertFalse(self.v.state['transcribing'])
        self.assertFalse(any(c['action']=='cancel' for c in self.sent))

    def test_noise_pauses_instead_of_discarding_reply(self):
        self.b.busy=True
        with patch.object(self.v,'configure_control') as control:
            self.v.voice_event({'type':'speech_start'})
            self.assertIn({'action':'pause_speech','generation':self.v.input_generation,'utterance':0},self.sent)
            self.assertFalse(any(c['action']=='cancel' for c in self.sent))
            self.v.voice_event({'type':'utterance_end','recognized':False,'hadSpeech':True})
            self.assertIn({'action':'resume_speech','utterance':0},self.sent)
            control.assert_called_once_with(True)

    def test_control_remains_paused_until_correction_is_accepted(self):
        self.b.busy=True;entered=threading.Event();release=threading.Event()
        self.b.rpc=Mock();self.b.rpc.request.side_effect=lambda *a,**k:(entered.set(),release.wait(2))
        try:
            with patch.object(self.v,'configure_control') as control:
                self.v.voice_event({'type':'speech_start'})
                self.v.voice_event({'type':'transcribing'})
                self.v.voice_event({'type':'transcript','text':'Use blue instead.'})
                self.assertTrue(entered.wait(1))
                self.v.voice_event({'type':'utterance_end','recognized':True})
                self.assertTrue(self.v.correction_paused);control.assert_not_called()
                release.set();self.v.input_queue.join()
                self.assertFalse(self.v.correction_paused);control.assert_called_once_with(True)
        finally:release.set()

    def test_resume_belongs_to_latest_observed_utterance(self):
        self.v.voice_event({'type':'speech_start','utterance':4})
        self.v.voice_event({'type':'utterance_end','recognized':False,'utterance':4})
        self.assertEqual(self.sent[-1],{'action':'resume_speech','utterance':4})

    def test_resume_does_not_redisplay_previous_reply(self):
        self.v.state['caption']='Understanding what you said…'
        self.v.voice_event({'type':'playback','active':True,'resumed':True,'text':'The previous reply.'})
        self.assertEqual(self.v.state['caption'],'Understanding what you said…')

    def test_stop_invalidates_input_waiting_behind_another_operation(self):
        with patch.object(self.b,'send') as send:
            with self.b.lock:
                self.v.voice_event({'type':'transcript','text':'Open Firefox.','generation':0})
                self.v.stop()
            self.v.input_queue.join();send.assert_not_called()
        self.v.voice_event({'type':'speech_start','generation':0})
        self.assertFalse(self.v.user_speaking)

    def test_queued_followups_are_kept_in_order(self):
        self.b.busy=True;self.v.prefs['bargeIn']=False
        self.v.submit_voice('Then explain the result.')
        self.v.submit_voice('Also tell me what changed.')
        self.assertEqual(self.v.pending,'Then explain the result.\nAlso tell me what changed.')
        self.assertFalse(any(c['action']=='cancel' for c in self.sent))

    def test_understanding_is_visible_and_empty_speech_is_recoverable(self):
        self.v.voice_event({'type':'speech_start'})
        self.v.voice_event({'type':'transcribing'})
        self.assertTrue(self.v.state['transcribing']);self.assertFalse(self.v.state['hearing'])
        self.assertIn('Understanding',self.v.state['caption'])
        self.v.voice_event({'type':'utterance_end','recognized':False,'hadSpeech':True})
        self.assertFalse(self.v.state['transcribing']);self.assertFalse(self.v.state['error'])
        self.assertIn('try again',self.v.state['inputNotice'])

    def test_agent_failure_is_briefly_spoken_without_reading_technical_error(self):
        self.v.was_busy=True
        self.v.observe({'type':'state','busy':False,'current':{'messages':[{'role':'assistant','status':'error','error':'private traceback detail'}]}})
        spoken=[c['text'] for c in self.sent if c['action']=='speak']
        self.assertEqual(spoken,["I couldn't finish that. The details are in the chat."])


if __name__=='__main__':unittest.main()
