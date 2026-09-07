import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from agent_session import NativeTurn, RpcSession, SessionLease, resume_command
from backend import Bridge


FAKE_RPC = r'''#!/usr/bin/env python3
import json,os,pathlib,sys,uuid
args=sys.argv[1:]
folder=pathlib.Path(args[args.index('--session-dir')+1])
resume='--resume' if '--resume' in args else '--session'
file=pathlib.Path(args[args.index(resume)+1]) if resume in args else folder/'native.jsonl'
history=json.loads(file.read_text()) if file.exists() else []
def save():file.write_text(json.dumps(history))
def emit(e):print(json.dumps(e,ensure_ascii=False),flush=True)
def reply(c,data=None,success=True):emit(dict(type='response',id=c.get('id'),command=c['type'],success=success,data=data or {}))
def finish():
 msg={'role':'assistant','content':[{'type':'text','text':'Done 🌿'}],'model':'fixture-model','timestamp':1000}
 history.append(msg);save();emit({'type':'message_end','message':msg});emit({'type':'agent_end'})
save()
if '--mode' not in args:
 history.extend([{'role':'user','content':'From terminal','entryId':'terminal-user','timestamp':2000},
                 {'role':'assistant','content':[{'type':'text','text':'Terminal answer'}],'timestamp':2000}]);save();sys.exit(0)
emit({'type':'ready'})
for line in sys.stdin:
 c=json.loads(line);kind=c['type']
 if kind=='get_state':reply(c,{'sessionFile':str(file),'sessionId':file.stem,'model':{'id':'fixture-model'}})
 elif kind in ('get_branch_messages','get_fork_messages'):reply(c,{'messages':[{'entryId':m['entryId'],'text':m['content']} for m in history if m['role']=='user']})
 elif kind=='get_messages':reply(c,{'messages':history})
 elif kind in ('branch','fork'):
  history=history[:next(i for i,m in enumerate(history) if m.get('entryId')==c['entryId'])]
  file=folder/('branch-'+uuid.uuid4().hex+'.jsonl');save();reply(c,{'cancelled':False})
 elif kind=='prompt':
  with open(os.environ['RPC_LOG'],'a') as log:log.write(json.dumps({'pid':os.getpid(),'args':args,'text':c['message']})+'\n')
  history.append({'role':'user','content':c['message'],'entryId':uuid.uuid4().hex,'timestamp':1000});save()
  reply(c);emit({'type':'agent_start'})
  if 'approve' in c['message']:
   emit({'type':'extension_ui_request','id':'permission-1','method':'confirm','title':'Write fixture?','message':'Change the test fixture.'});continue
  emit({'type':'message_update','assistantMessageEvent':{'type':'text_delta','delta':'Working…'}})
  if 'slow' in c['message']:continue
  emit({'type':'message_end','message':{'role':'assistant','content':[{'type':'text','text':'Working…'}]}})
  emit({'type':'tool_execution_start','toolCallId':'tool-1','toolName':'write','args':{'path':'fixture.txt','content':'updated'}})
  pathlib.Path('fixture.txt').write_text('updated')
  sys.stderr.write('diagnostic\n'*12000);sys.stderr.flush()
  emit({'type':'tool_execution_end','toolCallId':'tool-1','toolName':'write','result':{'content':[{'type':'text','text':'Written'}]}})
  finish()
 elif kind=='extension_ui_response':
  if c.get('confirmed'):pathlib.Path('approved.txt').write_text('allowed')
  finish()
 elif kind=='abort':reply(c);emit({'type':'agent_end'})
 else:reply(c)
'''


class NativeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='side chat test ')
        self.path = Path(self.temp.name)
        (self.path/'bin').mkdir()
        config = self.path/'config/omarchy/defaults'
        config.mkdir(parents=True)
        (config/'agent').write_text('omp')
        for name in ('omp','pi'):
            binary = self.path/'bin'/name
            binary.write_text(FAKE_RPC); binary.chmod(0o755)
        self.env = patch.dict(os.environ, {'PATH':str(self.path/'bin')+os.pathsep+os.environ['PATH'],
                                          'XDG_CONFIG_HOME':str(self.path/'config'),'RPC_LOG':str(self.path/'rpc.log')})
        self.env.start()
        self.events = []
        self.bridge = Bridge(self.path/'state', self.events.append)
        self.bridge.settings['cwd'] = str(self.path)

    def tearDown(self):
        self.bridge.close()
        self.env.stop()
        self.temp.cleanup()

    def wait(self):
        self.bridge.worker.join(7)
        self.assertFalse(self.bridge.busy)
        return self.bridge.current['messages'][-1]

    def send(self,text,**kwargs):
        self.bridge.dispatch(dict(action='send',text=text,**kwargs))
        reply = self.wait()
        self.assertEqual(reply['status'],'complete',reply)
        return reply

    def logs(self):
        return [json.loads(line) for line in (self.path/'rpc.log').read_text().splitlines()]

    def test_persistent_process_tools_and_no_transcript_replay(self):
        first = self.send('First request')
        self.send('Second request')
        logs = self.logs()
        self.assertEqual(logs[0]['pid'],logs[1]['pid'])
        self.assertEqual(logs[1]['text'],'Second request')
        self.assertNotIn('--no-tools',logs[0]['args'])
        self.assertNotIn('--no-skills',logs[0]['args'])
        self.assertNotIn('--auto-approve',logs[0]['args'])
        self.assertEqual((self.path/'fixture.txt').read_text(),'updated')
        self.assertEqual(first['text'],'Working…\n\nDone 🌿')
        self.assertEqual(first['tools'][0]['status'],'complete')
        self.assertTrue(self.bridge.current['messages'][0]['nativeEntry'])

    def test_restart_resumes_native_session(self):
        self.send('Remember this')
        native_file = self.bridge.current['native']['sessionFile']
        self.bridge.close()
        self.bridge = Bridge(self.path/'state', self.events.append)
        self.send('Follow up')
        self.assertEqual(self.bridge.current['native']['sessionFile'],native_file)
        self.assertIn(native_file,self.logs()[-1]['args'])
        self.assertEqual(self.logs()[-1]['text'],'Follow up')

    def test_edit_branches_native_history(self):
        self.send('Original')
        self.send('Later')
        old_file=self.bridge.current['native']['sessionFile']
        self.send('Replacement',edit=0)
        new_file=self.bridge.current['native']['sessionFile']
        self.assertNotEqual(old_file,new_file)
        history=json.loads(Path(new_file).read_text())
        self.assertEqual([m['content'] for m in history if m['role']=='user'],['Replacement'])
        self.assertEqual(len(self.bridge.current['messages']),2)

    def test_stop_keeps_idle_session_available(self):
        self.bridge.dispatch({'action':'send','text':'slow'})
        deadline=time.monotonic()+4
        while not self.bridge.rpc and time.monotonic()<deadline:time.sleep(.02)
        pid=self.bridge.rpc.proc.pid
        self.bridge.dispatch({'action':'stop'})
        self.assertEqual(self.wait()['status'],'stopped')
        self.send('Next')
        self.assertEqual(self.bridge.rpc.proc.pid,pid)

    def test_permission_requires_explicit_response(self):
        self.bridge.dispatch({'action':'send','text':'approve'})
        deadline=time.monotonic()+4
        while not self.bridge.ui_requests and time.monotonic()<deadline:time.sleep(.02)
        self.assertTrue(self.bridge.ui_requests)
        self.assertFalse((self.path/'approved.txt').exists())
        self.bridge.dispatch({'action':'agent_ui_response','id':'permission-1','confirmed':True})
        self.wait()
        self.assertEqual((self.path/'approved.txt').read_text(),'allowed')
        self.assertFalse(self.bridge.ui_requests)

    def test_terminal_handoff_and_sync_preserve_session(self):
        self.send('Panel request')
        chat=self.bridge.current
        native=chat['native']['sessionFile']
        folder=self.bridge.session_folder(chat)
        with self.assertRaisesRegex(ValueError,'open in a terminal'):
            SessionLease(folder)
        with patch('native_bridge.subprocess.Popen') as run:
            # Keep the watcher pending until the simulated terminal has started.
            import threading
            finished=threading.Event()
            run.return_value.wait.side_effect=lambda: finished.wait(5) and 0
            self.bridge.dispatch({'action':'terminal'})
            argv=run.call_args.args[0]
        self.assertIsNone(self.bridge.rpc)
        self.assertTrue(chat['terminalOpen'])
        with self.assertRaisesRegex(ValueError,'terminal'):
            self.bridge.dispatch({'action':'send','text':'Concurrent turn'})
        subprocess.run(argv[4:],check=True,env=os.environ)
        finished.set()
        self.bridge.dispatch({'action':'ping'})
        self.wait()
        self.assertFalse(chat['terminalOpen'])
        self.assertEqual(chat['native']['sessionFile'],native)
        self.assertEqual(chat['messages'][-2]['text'],'From terminal')
        self.assertEqual(chat['messages'][-1]['text'],'Terminal answer')
        self.send('Back in panel')
        self.assertEqual(self.logs()[-1]['text'],'Back in panel')

    def test_pi_uses_its_native_resume_flag(self):
        (self.path/'config/omarchy/defaults/agent').write_text('pi')
        self.send('Pi request')
        native=self.bridge.current['native']['sessionFile']
        self.assertEqual(resume_command('pi',native),['pi','--session',native])

    def test_legacy_chat_migrates_once_and_keeps_visible_history(self):
        self.bridge.new()
        self.bridge.current['messages']=[{'role':'user','text':'Old question','status':'complete','time':1},
                                         {'role':'assistant','text':'I cannot use tools','status':'complete','time':1}]
        self.send('Now edit it')
        self.assertIn('their tool limitations no longer apply',self.logs()[0]['text'])
        self.assertEqual(self.bridge.current['native']['prefixCount'],2)
        self.send('Next task')
        self.assertEqual(self.logs()[-1]['text'],'Next task')


class EventTests(unittest.TestCase):
    def test_terminal_agent_end_and_tool_errors(self):
        turn=NativeTurn()
        turn.feed({'type':'agent_end','isTerminal':False})
        self.assertFalse(turn.done)
        turn.feed({'type':'tool_execution_start','toolCallId':'x','toolName':'bash','args':{'command':'false'}})
        turn.feed({'type':'tool_execution_end','toolCallId':'x','isError':True,'result':{'content':[{'type':'text','text':'exit 1'}]}})
        self.assertEqual(turn.tools[0]['status'],'error')
        self.assertEqual(turn.tools[0]['output'],'exit 1')
        turn.feed({'type':'agent_end'})
        self.assertTrue(turn.done)

    def test_rpc_chunk_validation(self):
        import base64
        rpc=object.__new__(RpcSession);rpc.chunk=None
        data=json.dumps({'type':'test','text':'🌿'},ensure_ascii=False).encode()
        halves=[data[:11],data[11:]]
        for i,part in enumerate(halves):
            result=rpc._frame({'type':'rpc_chunk','chunkId':'a','index':i,'count':2,'byteLength':len(data),'data':base64.b64encode(part).decode()})
        self.assertEqual(result['text'],'🌿')
        with self.assertRaises(ValueError):
            rpc._frame({'type':'rpc_chunk','chunkId':'b','index':1,'count':2,'byteLength':10,'data':'YQ=='})


if __name__=='__main__':unittest.main()
