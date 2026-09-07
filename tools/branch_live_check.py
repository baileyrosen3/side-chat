"""Resume an authenticated fixture session and verify a native retry excludes a turn."""
import json,sys,time,queue,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from agent_session import RpcSession,NativeTurn
agent=sys.argv[1];record=json.load(open('/tmp/jarvis-'+agent+'-live.json'))
s=RpcSession(agent,tempfile.mkdtemp(prefix='jarvis-branch-check-'),{'cwd':record['folder']},record['native']['sessionFile'])
def turn(text):
 while not s.events.empty():s.events.get_nowait()
 s.send({'type':'prompt','message':text});t=NativeTurn();end=time.monotonic()+60
 while not t.done and time.monotonic()<end:
  try:t.feed(s.events.get(timeout=.1))
  except queue.Empty:pass
 if not t.done or t.error:raise RuntimeError(t.error or 'Timeout')
 return t.text
try:
 turn('For this turn only, reply exactly: disposable branch marker 7421. Do not use tools.')
 before=s.request('get_state');entries=s.request('get_fork_messages')['messages']
 s.request('fork',entryId=entries[-1]['entryId'])
 text=turn('Reply with a short answer: What setting and value did we change in the original config task? Do not use tools.')
 after=s.request('get_state');messages=s.request('get_messages')['messages']
 visible='\n'.join(str(m.get('content','')) for m in messages)
 result={'agent':agent,'text':text,'new_session':before['sessionId']!=after['sessionId'],'removed_turn_absent':'disposable branch marker 7421' not in visible,'original_file_preserved':Path(before['sessionFile']).exists()}
 Path('/tmp/jarvis-'+agent+'-branch.json').write_text(json.dumps(result));print(json.dumps(result),flush=True)
finally:s.close()
