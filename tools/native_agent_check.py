"""Opt-in authenticated adapter check, confined to a disposable test file."""
import json,sys,tempfile,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend import Bridge
agent=sys.argv[1];folder=Path(tempfile.mkdtemp(prefix='peek-'+agent+'-live-'))
fixture=folder/'fixture.conf';fixture.write_text('font_size = 11\n')
b=Bridge(folder/'state',lambda e:None);b.default_agent=lambda:agent;b.settings['cwd']=str(folder)
b.peek.prefs.update(handsFree=False,muted=True)
def wait():
 deadline=time.monotonic()+110
 while b.busy and time.monotonic()<deadline:
  for prompt in list(b.ui_requests):
   # This harness authorizes only the fixture edit named in its own test prompt.
   message=prompt.get('message','');title=prompt.get('title','')
   allow=False
   if 'Edit' in title or 'Write' in title:
    try:allow=json.loads(message[message.index('{'):]).get('file_path')==str(fixture)
    except (ValueError,KeyError):pass
   if 'peek' in title.lower() and 'computer' in title.lower():
    try:allow=json.loads(message)=={'op':'windows'}
    except ValueError:pass
   if title=='Allow command?':
    try:
     details=json.loads(message[message.index('{'):]);command=details.get('command','')
     allow=details.get('cwd')==str(folder) and 'fixture.conf' in command and 'font_size = 12' in command and all(x not in command for x in ('rm ', 'curl ', 'wget ', '/home/', 'http'))
    except ValueError:pass
   print(json.dumps({'prompt':title,'allowed_fixture_edit':allow,'message':message[:300]}),flush=True)
   b.dispatch({'action':'agent_ui_response','id':prompt['id'],'confirmed':allow})
  time.sleep(.1)
 if b.busy:b.dispatch({'action':'stop'});b.worker.join(8)
try:
 b.peek.ensure_control();b.peek.state['enabled']=True
 b.dispatch({'action':'send','text':'In this disposable test folder, use your file tools to change fixture.conf from font_size = 11 to font_size = 12, then read it back. Also call the Peek computer MCP tool with op windows once. Do not focus, click, type, or change any other files. Briefly report the result.'})
 wait();reply=b.current['messages'][-1]
 result={'folder':str(folder),'agent':agent,'status':reply['status'],'text':reply['text'],'error':reply.get('error'),'tools':reply.get('tools',[]),'fixture':fixture.read_text(),'native':b.current.get('native')}
 if reply['status']=='complete':
  b.close_rpc();b.sync_native_history(b.current)
  result['synced_messages']=len(b.current['messages']);result['synced_last']=b.current['messages'][-1]['text']
 Path('/tmp/peek-'+agent+'-live.json').write_text(json.dumps(result,indent=2))
 print(json.dumps({k:v for k,v in result.items() if k!='tools'},indent=2),flush=True)
finally:b.close()
