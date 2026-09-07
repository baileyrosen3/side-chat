"""Worker regressions run with the installed voice runtime; no model or mic needed."""
import importlib.util
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from jarvis.speech_queue import SpeechJob,SpeechQueue


@unittest.skipUnless(importlib.util.find_spec('sherpa_onnx'),'requires the local voice runtime')
class SpeechInterruptionTests(unittest.TestCase):
    def setUp(self):
        from jarvis.voice_worker import VoiceWorker
        self.w=VoiceWorker.__new__(VoiceWorker)
        self.w.lock=threading.RLock();self.w.queue=SpeechQueue()
        self.w.speech_paused=threading.Event();self.w.shutdown=threading.Event()
        self.w.input_active=False;self.w.input_utterance=0
        self.w.speaking=True;self.w.listening=True
        self.w.player=Mock();self.w.player.poll.return_value=None;self.w.player.stdin.closed=False
        self.w.emit=Mock();self.w.audio=Mock()
        self.job=SpeechJob('The previous reply.','turn')
        self.w.queue.put(self.job);self.w.queue.get()

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


if __name__=='__main__':unittest.main()
