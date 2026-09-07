import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from backend import Bridge
from jarvis.controller import JarvisController,SpeechSegments
from jarvis.feedback import ACKNOWLEDGMENT,SpokenFeedback
from jarvis.settings import DEFAULTS,VOICES,validate
from jarvis.speech_queue import SpeechJob,SpeechQueue


class FeedbackTests(unittest.TestCase):
    def test_quick_reply_suppresses_ack_and_updates_are_bounded(self):
        f=SpokenFeedback();f.start(100)
        self.assertFalse(f.due(100.1))
        f.spoken(100.2)
        self.assertFalse(f.due(100.4))
        f.tools([{'name':'web_search','status':'running'}])
        self.assertIn('looking',f.due(111))
        self.assertFalse(f.due(115))
        self.assertFalse(f.due(122))
        self.assertIn('longer',f.due(137))
        self.assertFalse(f.due(200))
        f.finish();self.assertFalse(f.due(300))

    def test_ack_waits_for_user_and_expired_ack_is_not_replayed(self):
        f=SpokenFeedback();f.start(100)
        self.assertFalse(f.due(100.4,blocked=True))
        self.assertEqual(f.due(100.5),ACKNOWLEDGMENT)
        f.start(200);self.assertFalse(f.due(210))
        self.assertFalse(f.due(211))

    def test_completed_tools_do_not_claim_to_be_running(self):
        f=SpokenFeedback();f.start(100);f.due(100.3)
        f.tools([{'name':'write','status':'running'}])
        f.tools([{'name':'write','status':'complete'}])
        self.assertFalse(f.due(111))


class SpeechQueueTests(unittest.TestCase):
    def test_answer_replaces_status_but_retains_other_answer_segments(self):
        q=SpeechQueue();status=SpeechJob('Checking.',status=True)
        q.put(status);self.assertIs(q.get(),status)
        self.assertTrue(q.cancel(status_only=True));self.assertTrue(status.cancelled.is_set())
        first=SpeechJob('First answer.');second=SpeechJob('Second answer.')
        q.put(first);q.cancel(status_only=True);q.put(second)
        q.finish(status);self.assertIs(q.get(),first)
        self.assertFalse(q.put(SpeechJob('Still working.',status=True)))
        self.assertFalse(q.cancel(status_only=True))
        q.finish(first);self.assertIs(q.get(),second)
        self.assertFalse(first.cancelled.is_set());self.assertFalse(second.cancelled.is_set())

    def test_cancel_invalidates_synthesis_and_pending_audio_and_expiry(self):
        q=SpeechQueue();first=SpeechJob('One.');second=SpeechJob('Two.')
        q.put(first);q.get();q.put(second);q.cancel()
        self.assertTrue(first.cancelled.is_set());self.assertTrue(second.cancelled.is_set())
        q.finish(first)
        q.put(SpeechJob('Old cue.',status=True,queued_at=time.monotonic()-3))
        self.assertIsNone(q.get())


class StreamingTests(unittest.TestCase):
    def test_shorter_snapshots_cannot_rewind_spoken_reply(self):
        r=SpeechSegments();text='Here is the last reply. Another detail.'
        self.assertEqual(r.feed(text,final=True),['Here is the last reply.','Another detail.'])
        for stale in ('','Here is the last reply.','Here is the last reply. Another'):
            self.assertEqual(r.feed(stale,final=True),[])
            self.assertEqual(r.feed(text,final=True),[])
        self.assertEqual(r.feed(text+' A new detail.',final=True),['A new detail.'])

    def test_unspoken_tail_survives_stale_snapshot(self):
        r=SpeechSegments()
        self.assertEqual(r.feed('Already spoken. Still arriving'),['Already spoken.'])
        self.assertEqual(r.feed('Already spoken.'),[])
        self.assertEqual(r.feed('Already spoken. Still arriving.',final=True),['Still arriving.'])

    def test_settled_sentence_speaks_without_waiting_for_next_delta(self):
        r=SpeechSegments()
        self.assertEqual(r.feed('Here is the answer.'),[])
        self.assertEqual(r.feed(r.text,settled=True),['Here is the answer.'])
        self.assertEqual(r.feed(r.text,final=True),[])

    def test_natural_clause_can_start_a_long_sentence(self):
        r=SpeechSegments()
        clause='I can help you work through the available choices and find one that fits your routine,'
        self.assertEqual(r.feed(clause+' starting with'),[clause])
        self.assertEqual(r.feed(r.text+' your mornings.',final=True),['starting with your mornings.'])

    def test_partial_markup_numbers_and_abbreviations_are_not_split(self):
        r=SpeechSegments()
        for text in ('Ask Dr.','Ask Dr. Smith about 2.5 and the [guide](https://example.',
                     'Ask Dr. Smith about 2.5 and the [guide](https://example.test/a).'):
            parts=r.feed(text,settled=True)
        self.assertEqual(parts,['Ask Dr. Smith about 2.5 and the guide.'])
        r=SpeechSegments()
        self.assertEqual(r.feed('Check `a long inline code expression. ',settled=True),[])
        self.assertEqual(r.feed(r.text+'Never read it aloud.` It is ready.',settled=True),['Check It is ready.'])


class ControllerFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        with patch.object(JarvisController,'feedback_loop'):
            self.b=Bridge(self.temp.name,lambda _:None)
        self.v=self.b.jarvis;self.v.state.update(enabled=True,ready=True)
        self.b.current={'messages':[{'role':'assistant','text':'','tools':[]}]}
        self.b.busy=True
        self.sent=[];self.v.send_worker=self.sent.append
        self.v.begin_turn();self.sent.clear()

    def tearDown(self):
        self.b.busy=False;self.b.close();self.temp.cleanup()

    def test_cancel_playback_event_does_not_swallow_ack(self):
        self.v.voice_event({'type':'playback','active':False})
        self.v.feedback_tick(self.v.feedback.started+.4)
        self.assertEqual(self.sent[-1]['text'],ACKNOWLEDGMENT)
        self.v.stop();self.sent.clear()
        self.v.feedback_tick(time.monotonic()+100)
        self.v.observe({'type':'delta','text':'Do not speak after stopping. '})
        self.assertFalse(any(c['action']=='speak' for c in self.sent))

    def test_mute_approval_and_speaking_user_suppress_progress(self):
        for kind in ('muted','approval','user','disabled'):
            self.v.begin_turn();self.sent.clear()
            self.v.prefs['muted']=kind=='muted';self.v.prefs['spokenProgress']=kind!='disabled'
            self.b.ui_requests=[{'id':'yes','title':'Approve?'}] if kind=='approval' else []
            self.v.user_speaking=kind=='user'
            self.v.feedback_tick(self.v.feedback.started+1)
            self.assertFalse(self.sent,kind)

    def test_preview_is_explicit_and_does_not_save_or_arm_microphone(self):
        self.b.busy=False;before=dict(self.v.prefs)
        self.v.dispatch({'action':'jarvis_voice_preview','voice':'fantine'})
        self.assertEqual(self.sent[-1]['voice'],'fantine')
        self.assertEqual(self.v.prefs,before)
        self.assertFalse(any(c['action']=='listen' for c in self.sent))
        self.b.busy=True
        with self.assertRaises(ValueError):self.v.dispatch({'action':'jarvis_voice_preview','voice':'marius'})
        for voice in VOICES['pocket']:self.assertEqual(validate(DEFAULTS,{'voice':voice},False)['voice'],voice)

    def test_slow_prompt_does_not_block_audio_event_reader(self):
        started=threading.Event();release=threading.Event();done=threading.Event()
        def slow(_,**kwargs):started.set();release.wait(2);done.set()
        try:
            with patch.object(self.v,'submit_voice',side_effect=slow):
                self.v.voice_event({'type':'transcript','text':'Check this.'})
                self.assertTrue(started.wait(1));self.assertFalse(done.is_set())
                self.v.voice_event({'type':'playback','active':True,'text':'Got it.'})
                self.assertTrue(self.v.state['speaking'])
        finally:release.set();done.wait(1)


if __name__=='__main__':unittest.main()
