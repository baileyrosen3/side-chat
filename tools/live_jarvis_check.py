"""Exercise the real selected OMP extension only in a disposable folder."""
import json,sys,tempfile,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend import Bridge
folder=Path(tempfile.mkdtemp(prefix='jarvis-live-'))
(folder/'fixture.conf').write_text('font_size = 11\n')
events=[]
b=Bridge(folder/'state',lambda e:events.append(e) if e.get('type') in ('delta','error') else None)
b.settings['cwd']=str(folder)
b.jarvis.prefs.update(handsFree=False,muted=True,screenContext='off')
try:
 b.jarvis.ensure_control();b.jarvis.state['enabled']=True
 b.dispatch({'action':'send','text':'In this disposable test folder, change fixture.conf from font_size = 11 to font_size = 12 using jarvis_computer config_read and config_write with expected sha256, then read it back. Also call jarvis_computer with op windows once to verify the desktop tool is available. Do not focus, click, type, or change any other files. Briefly report the result.'})
 deadline=time.monotonic()+90
 while b.busy and time.monotonic()<deadline:time.sleep(.2)
 if b.busy:b.dispatch({'action':'stop'});b.worker.join(8)
 reply=b.current['messages'][-1]
 print(json.dumps({'folder':str(folder),'status':reply['status'],'text':reply['text'],'error':reply.get('error'),'tools':[(t['name'],t['status']) for t in reply.get('tools',[])],'fixture':(folder/'fixture.conf').read_text(),'native':b.current.get('native')},indent=2))
finally:b.close()
