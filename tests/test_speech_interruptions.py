"""Worker regressions run with the installed voice runtime; no model or mic needed."""
import importlib.util
import threading
import time
import unittest
from types import SimpleNamespace
from contextlib import contextmanager
from unittest.mock import Mock,patch

from jarvis.speech_queue import SpeechJob,SpeechQueue


@unittest.skipUnless(importlib.util.find_spec('sherpa_onnx'),'requires the local voice runtime')
class SpeechInterruptionTests(unittest.TestCase):
    def setUp(self):
        from jarvis.voice_worker import VoiceWorker
        self.w=VoiceWorker.__new__(VoiceWorker)
        self.w.lock=threading.RLock();self.w.queue=SpeechQueue()
        self.w.speech_paused=threading.Event();self.w.shutdown=threading.Event()
        self.w.finish=threading.Event();self.w.restart_after_finish=False
        self.w.record_epoch=1;self.w.capture=None;self.w.capture_thread=None
        self.w.input_active=False;self.w.input_utterance=0;self.w.input_generation=0
        self.w.speaking=True;self.w.listening=True
        self.w.player=Mock();self.w.player.poll.return_value=None;self.w.player.stdin.closed=False
        self.w.emit=Mock();self.w.audio=Mock()
        self.job=SpeechJob('The previous reply.','turn')
        self.w.queue.put(self.job);self.w.queue.get()

    @contextmanager
    def capturing(self,voiced=True,block_finalize=False):
        """One accepted frame, then blocked capture with no silence endpoint."""
        import numpy as np
        from jarvis.settings import DEFAULTS
        w=self.w;reading=threading.Event();release=threading.Event()
        finalizing=threading.Event();finish_release=threading.Event()
        if not block_finalize:finish_release.set()
        w.ready=threading.Event();w.ready.set()
        w.prefs=dict(DEFAULTS,endSilence=2,adaptivePause=True,noiseRejection='balanced')
        w.source='';w.sink='';w.parakeet=Mock();w.gate=Mock()
        w.parakeet.accept.return_value='Use blue'
        def finalize():
            finalizing.set();finish_release.wait(3);return 'Use blue.'
        w.parakeet.finish.side_effect=finalize
        w.detector=Mock();w.continuation_detector=Mock()
        for detector in (w.detector,w.continuation_detector):
            detector.empty.return_value=True;detector.is_speech_detected.return_value=voiced
        frame=np.full(512,.1,dtype='<f4').tobytes();frames=iter([frame])
        def read(_):
            first=next(frames,None)
            if first is not None:return first
            reading.set();release.wait(3);return b''
        capture=Mock();capture.stdout.read.side_effect=read
        w.audio.record.return_value=capture
        thread=threading.Thread(target=w.record,args=(w.record_epoch,),daemon=True)
        w.capture_thread=thread
        with patch('jarvis.voice_worker.terminate',side_effect=lambda p:release.set() if p is capture else None):
            thread.start()
            try:
                self.assertTrue(reading.wait(1))
                yield SimpleNamespace(thread=thread,finalizing=finalizing,release=finish_release)
            finally:
                w.shutdown.set();release.set();finish_release.set();thread.join(2)

    def test_microphone_off_finalizes_without_waiting_for_silence(self):
        w=self.w
        with self.capturing() as capture:
            w.parakeet.finish.assert_not_called()
            prefs=dict(w.prefs)
            w.command({'action':'listen','enabled':False,'finish':True})
            capture.thread.join(1)
            self.assertFalse(capture.thread.is_alive())
            self.assertEqual(w.prefs,prefs)
            w.parakeet.finish.assert_called_once()
            events=w.emit.call_args_list
            off=next(i for i,c in enumerate(events) if c.args[0]=='microphone' and not c.kwargs['active'])
            transcripts=[(i,c) for i,c in enumerate(events) if c.args[0]=='transcript']
            self.assertEqual(len(transcripts),1)
            self.assertGreater(transcripts[0][0],off)
            self.assertEqual(transcripts[0][1].kwargs['text'],'Use blue.')
            self.assertEqual(transcripts[0][1].kwargs['generation'],0)
            self.assertFalse(w.listening)
            self.assertFalse(self.job.cancelled.is_set())

    def test_quick_off_on_keeps_phrase_and_reopens_after_finalization(self):
        w=self.w
        with self.capturing(block_finalize=True) as capture:
            w.finish_input();self.assertTrue(capture.finalizing.wait(1))
            with patch.object(w,'record') as reopen:
                w.listen(True)
                reopen.assert_not_called()
                capture.release.set();capture.thread.join(1)
                w.capture_thread.join(1)
                reopen.assert_called_once_with(2)
            self.assertTrue(w.listening)
            w.parakeet.finish.assert_called_once()
            self.assertEqual(sum(c.args[0]=='transcript' for c in w.emit.call_args_list),1)

    def test_second_off_during_finalization_cancels_reopen_without_duplicate_send(self):
        w=self.w
        with self.capturing(block_finalize=True) as capture:
            w.finish_input();self.assertTrue(capture.finalizing.wait(1))
            with patch.object(w,'record') as reopen:
                w.listen(True);w.finish_input();w.finish_input()
                capture.release.set();capture.thread.join(1)
                reopen.assert_not_called()
            self.assertFalse(w.listening)
            self.assertEqual(sum(c.args[0]=='transcript' for c in w.emit.call_args_list),1)

    def test_stop_discards_phrase_already_being_finalized(self):
        w=self.w
        with self.capturing(block_finalize=True) as capture:
            w.finish_input();self.assertTrue(capture.finalizing.wait(1))
            w.command({'action':'invalidate_input','generation':1})
            capture.release.set();capture.thread.join(1)
            self.assertFalse(any(c.args[0]=='transcript' for c in w.emit.call_args_list))

    def test_empty_microphone_off_keeps_current_speech_playing(self):
        w=self.w
        with self.capturing(voiced=False) as capture:
            w.finish_input();capture.thread.join(1)
            w.parakeet.finish.assert_not_called()
            self.assertFalse(any(c.args[0]=='transcript' for c in w.emit.call_args_list))
            self.assertTrue(w.speaking)
            self.assertFalse(w.speech_paused.is_set())
            self.assertFalse(self.job.cancelled.is_set())
            w.audio.close.assert_not_called()

    def test_delayed_resume_cannot_restart_reply_during_next_utterance(self):
        w=self.w
        w.pause_speech(user=True);w.input_active=False
        w.pause_speech(user=True)
        w.resume_speech(1)
        self.assertTrue(w.speech_paused.is_set());self.assertFalse(w.speaking)
        w.resume_speech(2)
        self.assertTrue(w.speech_paused.is_set())
        w.input_active=False;w.resume_speech(1)
        self.assertTrue(w.speech_paused.is_set())
        w.resume_speech(2)
        self.assertFalse(w.speech_paused.is_set());self.assertTrue(w.speaking)
        self.assertTrue(w.emit.call_args.kwargs['resumed'])
        self.assertNotIn('text',w.emit.call_args.kwargs)
        self.assertIs(w.queue.active,self.job)

    def test_completed_or_draining_player_cannot_announce_previous_reply(self):
        for exited in (False,True):
            self.w.player.poll.return_value=0 if exited else None
            self.w.player.stdin.closed=not exited
            self.w.pause_speech();self.w.emit.reset_mock()
            self.w.resume_speech(0)
            self.w.emit.assert_not_called()

    def test_cancel_keeps_new_speech_held_while_user_is_talking(self):
        self.w.pause_speech(user=True)
        self.w.player.poll.return_value=0
        self.w.cancel()
        self.assertTrue(self.job.cancelled.is_set())
        self.assertTrue(self.w.speech_paused.is_set())

    def test_muting_discards_a_buffered_capture_frame_before_it_can_pause_speech(self):
        import numpy as np
        from jarvis.settings import DEFAULTS
        w=self.w;reading=threading.Event();release=threading.Event()
        w.ready=threading.Event();w.ready.set();w.finish=threading.Event()
        w.record_epoch=1;w.input_generation=0;w.capture=None
        w.prefs=dict(DEFAULTS,noiseRejection='balanced');w.source='';w.sink=''
        w.parakeet=None;w.asr=Mock();w.asr.is_ready.return_value=False
        w.asr.get_result.return_value='Buffered old speech'
        w.detector=Mock();w.continuation_detector=Mock();w.gate=Mock()
        for detector in (w.detector,w.continuation_detector):
            detector.empty.return_value=True;detector.is_speech_detected.return_value=True
        frame=np.full(512,.1,dtype='<f4').tobytes()
        def read(_):reading.set();release.wait(2);return frame
        capture=Mock();capture.stdout.read.side_effect=read
        w.audio.record.return_value=capture
        w.capture_thread=threading.Thread(target=w.record,args=(1,),daemon=True)
        with patch('jarvis.voice_worker.terminate',side_effect=lambda _:release.set()):
            w.capture_thread.start()
            try:
                self.assertTrue(reading.wait(1))
                w.listen(False)
                self.assertFalse(w.speech_paused.is_set())
                self.assertTrue(w.speaking)
                self.assertFalse(w.input_active)
                self.assertFalse(any(c.args[0]=='speech_start' for c in w.emit.call_args_list))
                self.assertFalse(self.job.cancelled.is_set())
                w.audio.close.assert_not_called()
            finally:release.set();w.shutdown.set();w.capture_thread.join(2)

    def test_pause_during_pcm_pacing_resumes_without_duplicate_samples(self):
        import numpy as np
        w=self.w;first=threading.Event();next_chunk=threading.Event();done=threading.Event()
        pcm=[]
        chunks=[np.full(4800,value,dtype='<f4') for value in (.1,.2,.3)]
        def generate(*_):
            yield chunks[0]
            next_chunk.set()
            yield from chunks[1:]
        def write(data):pcm.append(data);first.set()
        proc=Mock();proc.poll.return_value=None;proc.stdin.closed=False
        proc.stdin.write.side_effect=write
        def finish(**_):proc.returncode=0;proc.poll.return_value=0;done.set()
        proc.wait.side_effect=finish
        w.ready=threading.Event();w.ready.set();w.player=None
        w.speech_cache={};w.speech_chunks=generate;w.tts=SimpleNamespace(sample_rate=24000)
        w.prefs={'volume':1};w.sink='';w.audio.play.return_value=proc
        w.queue.finish(self.job);w.queue.put(self.job)
        thread=threading.Thread(target=w.speech,daemon=True);thread.start()
        try:
            self.assertTrue(first.wait(1));self.assertTrue(next_chunk.wait(1))
            w.pause_speech(user=True);count=len(pcm)
            time.sleep(.25)
            self.assertEqual(len(pcm),count)
            w.resume_speech(0);time.sleep(.05)
            self.assertEqual(len(pcm),count)
            w.input_active=False;w.resume_speech(1)
            self.assertTrue(done.wait(2))
            self.assertEqual(b''.join(pcm),b''.join(c.tobytes() for c in chunks))
            w.audio.play.assert_called_once()
        finally:w.shutdown.set();thread.join(2)

    def test_delayed_pause_cannot_mute_a_new_or_disabled_microphone_session(self):
        w=self.w;w.input_generation=2;w.input_utterance=3
        w.listening=False
        w.command({'action':'pause_speech','generation':1,'utterance':2})
        self.assertFalse(w.speech_paused.is_set());self.assertTrue(w.speaking)
        w.listening=True
        w.command({'action':'pause_speech','generation':2,'utterance':3})
        self.assertFalse(w.speech_paused.is_set())
        w.input_active=True
        w.command({'action':'pause_speech','generation':1,'utterance':2})
        self.assertFalse(w.speech_paused.is_set())
        w.command({'action':'pause_speech','generation':2,'utterance':3})
        self.assertTrue(w.speech_paused.is_set())
        self.assertFalse(self.job.cancelled.is_set())

    def test_capture_events_from_a_muted_session_are_discarded(self):
        w=self.w;w.record_epoch=4;w.input_generation=2
        self.assertFalse(w.capture_event(3,'transcript',text='old',generation=2))
        self.assertFalse(w.capture_event(4,'transcript',text='old',generation=1))
        w.emit.assert_not_called()
        self.assertTrue(w.capture_event(4,'partial',text='current',generation=2))
        w.emit.assert_called_once_with('partial',text='current',generation=2)


if __name__=='__main__':unittest.main()
