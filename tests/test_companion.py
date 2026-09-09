import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch,Mock
from backend import Bridge
from peek.quick import parse,execute
from peek.undo import UndoJournal
from peek.store import Store
from peek.wake import ConversationGate

class CompanionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.b=Bridge(self.root/'state',lambda _:None);self.b.settings['cwd']=str(self.root)
        self.b.peek.state.update(enabled=True,ready=True);self.b.peek.prefs.update(muted=True,screenContext='off')
        self.c=self.b.peek.companion
    def tearDown(self):self.b.close();self.temp.cleanup()
    def test_peek_stop_and_sleep_commands_stay_local(self):
        for text in ('Stop Peek.','Peek stop!','Stop Peek.'):
            self.assertEqual(self.c.match(text),('stop',None))
        for text in ('Sleep Peek.','Peek go to sleep.','Sleep Peek.'):
            self.assertEqual(self.c.match(text),('sleep',None))
        self.assertIsNone(self.c.match('Explain how Peek works.'))
    def test_local_commands_persist_without_starting_agent(self):
        with patch.object(self.b,'ensure_rpc',side_effect=AssertionError('Local action started an agent')):
            self.b.send({'text':'remember that I prefer compact windows'});self.b.worker.join(3)
            self.assertFalse(self.b.busy)
            self.assertEqual(self.b.current['messages'][-1]['status'],'complete')
            self.assertIn('compact windows',self.c.context())
            store=Store(self.root/'state');identity=store.items('memory')[0]['id']
            store.remember('Use large text',identity)
            self.assertEqual(store.items('memory')[0]['text'],'Use large text')
            self.c.execute(self.c.match('forget Use large text'))
            self.assertEqual(store.items('memory'),[])
            self.assertEqual(store.items('activity'),[])
            self.assertNotIn('compact windows',self.c.context())
    def test_routine_order_and_stop(self):
        match=self.c.match('remember routine work: open terminal; set volume to 30')
        self.assertEqual(match[0],'routine_save');self.c.execute(match)
        routine=self.c.match('run work');calls=[]
        with patch.object(self.c,'command',side_effect=lambda c:calls.append(c) or 'OK'):
            self.c.execute(routine)
        self.assertEqual([c['op'] for c in calls],['app','volume'])
        with self.assertRaises(ValueError):self.c.routine('unsafe',['open terminal; rm -rf test'])
        def stop(command):self.c.generation+=1;return 'Done'
        with patch.object(self.c,'command',side_effect=stop) as call:
            with self.assertRaisesRegex(ValueError,'stopped'):self.c.execute(routine)
            self.assertEqual(call.call_count,1)
    def test_timer_restart_and_process_reuse_only_notify_once(self):
        self.c.watch('timer','Done',seconds=1)
        self.c.watch('process','Exited',pid=os.getpid())
        with patch('peek.companion.time.time',return_value=time.time()+2),patch('peek.companion.process_identity',return_value='different-start'),patch('peek.companion.subprocess.run') as notify:
            self.c.check_watches();self.c.check_watches()
            self.assertEqual(notify.call_count,2)
        self.assertTrue(all(r['state']=='done' for r in Store(self.root/'state').items('watch')))
    def test_steering_keeps_session_and_completed_work(self):
        self.b.new();self.b.current['messages']=[{'role':'assistant','text':'Finished first step','tools':[{'name':'read','status':'complete'}]}]
        self.b.current['agent']='omp'
        self.b.busy=True;self.b.rpc=Mock();self.b.rpc.proc=None
        rpc=self.b.rpc
        with patch.object(self.b.peek,'configure_control'):
            self.b.peek.steer('Use 12 instead')
        rpc.request.assert_called_once_with('steer',message='User correction to the running task. Preserve completed work and adjust the remaining steps: Use 12 instead',timeout=5)
        self.assertFalse(self.b.cancelled.is_set());self.assertIs(self.b.rpc,rpc)
        self.assertEqual(self.b.current['messages'][-1]['tools'][0]['status'],'complete')
        self.b.busy=False;self.b.rpc=None
    def test_unsupported_steering_queues_correction_in_same_chat(self):
        self.b.new();self.b.current['agent']='claude';self.b.busy=True
        identity=self.b.current['id'];self.b.peek.steer('Use the other file')
        self.assertTrue(self.b.cancelled.is_set());self.assertIn('other file',self.b.peek.pending)
        self.assertEqual(self.b.current['id'],identity);self.b.busy=False

class QuickTests(unittest.TestCase):
    def test_parser_preserves_url_case_and_rejects_shell_commands(self):
        self.assertEqual(parse('open https://example.org/Case?Token=AbC')['value'],'https://example.org/Case?Token=AbC')
        self.assertIsNone(parse('set volume to 20 && shutdown now'))
        with self.assertRaises(ValueError):parse('set volume to 200')
        with self.assertRaises(ValueError):execute(parse('open terminal'),'browser')
    def test_volume_reports_readback(self):
        with patch('peek.quick.run',side_effect=['Volume: 0.50','','Volume: 0.24']) as run:
            self.assertEqual(execute(parse('set volume to 25')),'Volume 24 percent.')
            self.assertEqual(run.call_args_list[1].args[0][-1],'25%')

class UndoTests(unittest.TestCase):
    def test_conflicts_modes_symlinks_and_persistence(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);p=root/'fixture.conf';p.write_text('size=11\n');p.chmod(0o640)
            j=UndoJournal(root/'state');before=j.read(p,root)
            result=j.write(p,root,'size=12\n',before['sha256'])
            self.assertEqual(p.stat().st_mode&0o777,0o640)
            with self.assertRaisesRegex(ValueError,'changed'):j.write(p,root,'size=13\n',before['sha256'])
            p.write_text('manual=edit\n')
            with self.assertRaisesRegex(ValueError,'newer edits'):j.restore(result['undoId'],root)
            self.assertEqual(p.read_text(),'manual=edit\n')
            p.write_text('size=12\n');j=UndoJournal(root/'state')
            self.assertTrue(j.restore(result['undoId'],root)['verified']);self.assertEqual(p.read_text(),'size=11\n')
            link=root/'link';link.symlink_to(p)
            with self.assertRaises(ValueError):j.read(link,root)

class GateTests(unittest.TestCase):
    def test_wake_followup_expiry_and_sleep(self):
        gate=ConversationGate(12)
        with patch('peek.wake.time.monotonic',return_value=100):
            self.assertFalse(gate.active());gate.wake();self.assertTrue(gate.active())
        with patch('peek.wake.time.monotonic',return_value=111):self.assertTrue(gate.active())
        with patch('peek.wake.time.monotonic',return_value=113):
            self.assertFalse(gate.active());gate.wake();gate.standby();self.assertFalse(gate.active())

if __name__=='__main__':unittest.main()
