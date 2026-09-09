"""Deliver a real native steering message while a harmless fixture tool is running."""
import json,sys,tempfile,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend import Bridge
folder=Path(tempfile.mkdtemp(prefix='peek-steer-live-'));(folder/'fixture.conf').write_text('size=0\n')
b=Bridge(folder/'state',lambda _:None);b.settings['cwd']=str(folder);b.peek.prefs.update(handsFree=False,muted=True,screenContext='off');b.peek.state['enabled']=True
try:
 text='This is a disposable steering test. First run a shell command that writes first to progress.txt and sleeps for 5 seconds. Only after that command finishes, use peek_computer config_read/config_write to change fixture.conf to size=11 followed by a newline, then verify it. Do not touch any other files or apps. Briefly report the result.'
 b.send({'text':text});deadline=time.monotonic()+60
 while not (folder/'progress.txt').exists() and b.busy and time.monotonic()<deadline:time.sleep(.05)
 assert (folder/'progress.txt').exists() and b.busy,'Did not reach the running tool'
 session=b.current['native']['sessionFile'];b.peek.steer('Change the requested value to size=12 instead of size=11. Keep the existing progress.txt.')
 deadline=time.monotonic()+70
 while time.monotonic()<deadline:
  if not b.busy and not b.peek.pending:break
  time.sleep(.1)
 assert not b.busy
 reply=b.current['messages'][-1]
 result={'folder':str(folder),'status':reply['status'],'text':reply['text'],'corrections':reply.get('steering',[]),'sameSession':b.current['native']['sessionFile']==session,'fixture':(folder/'fixture.conf').read_text(),'progress':(folder/'progress.txt').read_text(),'nativeEntry':b.current['messages'][0].get('nativeEntry')}
 print(json.dumps(result,indent=2));assert 'size=12' in result['fixture'] and result['sameSession'] and result['corrections'] and result['nativeEntry'],result
finally:
 if b.busy:b.cancelled.set();b.worker.join(8)
 b.close()
