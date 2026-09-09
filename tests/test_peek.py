import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from backend import Bridge
from peek.controller import SpeechSegments
from peek.control import bounds,point,Control


class SpeechTests(unittest.TestCase):
    def test_streamed_fences_links_and_private_code_are_not_spoken(self):
        reader=SpeechSegments();parts=[]
        text='I checked it.\n```bash\nrm -rf /never-run-this\n```\nThe [documentation](https://example.test/a) confirms it.\n'
        for char in text:parts+=reader.feed(reader.text+char)
        parts+=reader.feed(text,True)
        self.assertEqual(parts,['I checked it.','The documentation confirms it.'])

    def test_final_tail_and_snapshot_replay(self):
        reader=SpeechSegments()
        self.assertEqual(reader.feed('Hello there'),[])
        self.assertEqual(reader.feed('Hello there',True),['Hello there'])
        self.assertEqual(reader.feed('Hello there',True),[])
        self.assertEqual(reader.feed('A replacement snapshot',True),[])

    def test_bounded_clause_latency(self):
        reader=SpeechSegments()
        chunks=reader.feed('a long phrase '*30)
        self.assertTrue(chunks)
        self.assertLessEqual(max(map(len,chunks)),220)


class CoordinateTests(unittest.TestCase):
    def test_fractional_outputs_and_rotated_screens(self):
        m={'x':7670,'y':1350,'width':2880,'height':1800,'scale':2.25,'transform':0}
        f={'bounds':bounds(m),'width':1280,'height':800}
        self.assertEqual(point(f,640,400),(8310,1750))
        m.update(x=7124,y=0,width=3840,height=2160,scale=1.6)
        f={'bounds':bounds(m),'width':1280,'height':720}
        self.assertEqual(point(f,640,360),(8324,675))
        m['transform']=1
        self.assertEqual(bounds(m)[2:],(1350,2400))
        for x,y in [(-1,0),(1280,2),(float('nan'),0),(2,float('inf'))]:
            with self.assertRaises(ValueError):point(f,x,y)

    def test_stop_invalidates_frames_and_future_input(self):
        with patch.object(Control,'watch_input',lambda _:None):c=Control(lambda _:None)
        try:
            c.handle({'op':'_configure','enabled':True});epoch=c.epoch;c.frames['old']={}
            c.stop()
            self.assertFalse(c.frames)
            with self.assertRaises(RuntimeError):c.check(epoch)
            with self.assertRaises(RuntimeError):c.handle({'op':'click'})
        finally:c.close()


class ActivityTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory()
        self.bridge=Bridge(self.folder.name,lambda _:None)
        self.voice=self.bridge.peek
        self.voice.state.update(enabled=True,ready=True,listening=True)
        self.voice.prefs['muted']=True
        self.bridge.current={'messages':[{'role':'assistant','text':'','tools':[]}]}
        self.bridge.busy=True
        self.voice.begin_turn()

    def tearDown(self):
        self.bridge.busy=False;self.bridge.close();self.folder.cleanup()

    def test_microphone_and_playback_end_restore_thinking_during_a_turn(self):
        self.voice.voice_event({'type':'microphone','active':False})
        self.assertEqual(self.voice.state['stage'],'thinking')
        self.assertEqual(self.voice.state['caption'],'Peek is thinking…')
        self.voice.voice_event({'type':'playback','active':True,'text':'I will check.'})
        self.assertEqual(self.voice.state['stage'],'speaking')
        self.voice.voice_event({'type':'playback','active':False})
        self.assertEqual(self.voice.state['stage'],'thinking')
        self.assertEqual(self.voice.state['caption'],'Peek is thinking…')

    def test_completed_tool_returns_to_thinking_until_turn_finishes(self):
        tools=[{'name':'read','status':'running'}]
        self.bridge.current['messages'][-1]['tools']=tools
        self.voice.observe({'type':'delta','text':'','tools':tools})
        self.assertEqual(self.voice.state['stage'],'acting')
        tools[0]['status']='complete'
        self.voice.observe({'type':'delta','text':'','tools':tools})
        self.assertEqual(self.voice.state['stage'],'thinking')
        self.bridge.busy=False
        self.voice.observe({'type':'state','busy':False})
        self.assertEqual(self.voice.state['stage'],'listening')

    def test_pending_approval_and_stop_take_priority_over_thinking(self):
        request={'id':'approval','title':'Allow edit?'}
        self.bridge.ui_requests=[request]
        self.voice.observe({'type':'agent_ui','requests':[request]})
        self.voice.voice_event({'type':'microphone','active':False})
        self.voice.voice_event({'type':'playback','active':False})
        self.assertEqual(self.voice.state['stage'],'needs_input')
        self.bridge.ui_requests=[]
        self.voice.observe({'type':'agent_ui','requests':[]})
        self.assertEqual(self.voice.state['stage'],'thinking')
        self.voice.stop()
        self.voice.voice_event({'type':'playback','active':False})
        self.assertEqual(self.voice.state['stage'],'idle')


class RecoveryTests(unittest.TestCase):
    def test_sleep_button_and_voice_respect_wake_setting(self):
        with tempfile.TemporaryDirectory() as temp:
            b=Bridge(temp,lambda _:None)
            try:
                v=b.peek
                v.state.update(enabled=True,ready=True)
                for wake in (False,True):
                    for spoken in (False,True):
                        with self.subTest(wake=wake,spoken=spoken), patch.object(v,'send_worker') as send, patch.object(v,'stop'):
                            v.prefs['wakeEnabled']=wake;v.want_listen=True
                            if spoken:v.submit_voice('go to sleep')
                            else:v.dispatch({'action':'peek_standby'})
                            self.assertEqual(v.state['stage'],'standby' if wake else 'idle')
                            self.assertEqual(v.state['standby'],wake)
                            send.assert_called_with({'action':'standby'} if wake else {'action':'listen','enabled':False})
                            self.assertEqual(v.want_listen,wake)
            finally:b.close()

    def test_only_unwritten_initial_sessions_can_be_recreated(self):
        with tempfile.TemporaryDirectory() as temp:
            b=Bridge(Path(temp)/'state',lambda _:None)
            try:
                b.current={'id':'fixture','agent':'omp','messages':[{'role':'user','text':'Hello','status':'complete'},{'role':'assistant','text':'','status':'stopped'}],
                           'native':{'sessionFile':str(Path(temp)/'not-yet-created.jsonl')},'updated':0,'options':b.settings}
                b.recover_pending_native(b.current)
                self.assertNotIn('native',b.current)
                self.assertEqual(len(b.current['messages']),2)
                b.current['native']={'sessionFile':str(Path(temp)/'lost.jsonl'),'materialized':True}
                b.recover_pending_native(b.current)
                self.assertIn('native',b.current)
                b.current['native'].pop('materialized');b.current['messages'][0]['nativeEntry']='persisted-turn'
                b.recover_pending_native(b.current)
                self.assertIn('native',b.current)
            finally:b.close()

    def test_singleton_does_not_open_a_second_bridge(self):
        with tempfile.TemporaryDirectory() as temp:
            b=Bridge(temp,lambda _:None,exclusive=True)
            try:
                with self.assertRaises(RuntimeError):Bridge(temp,lambda _:None,exclusive=True)
            finally:b.close()


class WorkerLifecycleTests(unittest.TestCase):
    def test_control_sigterm_with_open_lifeline_does_not_crash(self):
        with tempfile.TemporaryDirectory() as folder:
            p=subprocess.Popen([sys.executable,'-B','peek/control.py','--serve',str(Path(folder)/'control.sock')],
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=dict(os.environ,SIDE_CHAT_CONTROL_LIFELINE='1'))
            try:
                self.assertEqual(json.loads(p.stdout.readline())['type'],'control_ready')
                p.terminate();p.wait(timeout=3)
                self.assertEqual(p.returncode,0)
                self.assertNotIn('Fatal Python error',p.stderr.read().decode())
            finally:
                if p.poll() is None:p.kill();p.wait()
                p.stdin.close();p.stdout.close();p.stderr.close()

    def test_control_stops_when_parent_pipe_closes(self):
        with tempfile.TemporaryDirectory() as folder:
            socket=Path(folder)/'control.sock'
            p=subprocess.Popen([sys.executable,'-B','peek/control.py','--serve',str(socket)],
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                env=dict(os.environ,SIDE_CHAT_CONTROL_LIFELINE='1'))
            try:
                self.assertEqual(json.loads(p.stdout.readline())['type'],'control_ready')
                p.stdin.close();p.wait(timeout=3)
                self.assertEqual(p.returncode,0);self.assertFalse(socket.exists())
            finally:
                if p.poll() is None:p.kill();p.wait()
                p.stdout.close();p.stderr.close()


if __name__=='__main__':unittest.main()
