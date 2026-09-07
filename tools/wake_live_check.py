"""Synthetic wake and follow-up through PipeWire; never uses the room microphone."""
import json,os,subprocess,sys,tempfile,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend import Bridge
folder=Path(tempfile.mkdtemp(prefix='jarvis-wake-live-'));modules=[];b=None
runtime=Path.home()/'.local/share/side-chat/runtime/bin/python'
def run(*argv):return subprocess.check_output(argv,text=True).strip()
def wait(test,seconds=12):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  if test():return
  if b and b.jarvis.state['error']:raise RuntimeError(b.jarvis.state['error'])
  time.sleep(.1)
 raise AssertionError('Timed out: '+json.dumps(b.jarvis.state if b else {}))
before={k:run('pactl','get-default-'+k) for k in ('source','sink')}
try:
 phrases={'wake':'Hey Jarvis.','ignore':'Remember that this should be ignored.','request':'Remember that the fixture color is blue.','followup':'Remember that the fixture size is small.'}
 prepare="""from jarvis.engines import pocket
import json,numpy as np,soundfile as sf,sys
from pathlib import Path
model,voices=pocket()
for name,text in json.loads(sys.argv[2]).items():
 a=np.concatenate([c.detach().cpu().numpy() for c in model.generate_audio_stream(voices['alba'],text,copy_state=True)])
 sf.write(Path(sys.argv[1])/(name+'.wav'),np.concatenate([np.zeros(model.sample_rate//2),a,np.zeros(model.sample_rate)]),model.sample_rate)
"""
 subprocess.run([str(runtime),'-B','-c',prepare,str(folder),json.dumps(phrases)],check=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
 for name in ('jarvis_fixture_input','jarvis_fixture_output'):modules.append(run('pactl','load-module','module-null-sink','sink_name='+name,'sink_properties="node.description=JarvisFixture priority.session=0"'))
 events=[];b=Bridge(folder/'state',lambda e:events.append(e.copy()))
 voice_events=[];original_voice_event=b.jarvis.voice_event
 def observe_voice(event):voice_events.append(event.copy());original_voice_event(event)
 b.jarvis.voice_event=observe_voice
 b.settings['cwd']=str(folder);b.jarvis.prefs.update(wakeEnabled=True,followupSeconds=5,muted=False,screenContext='off',source='jarvis_fixture_input.monitor',sink='jarvis_fixture_output')
 b.dispatch({'action':'jarvis','enabled':True});wait(lambda:b.jarvis.state['ready'] and b.jarvis.state.get('standby'),25)
 def play(name):subprocess.run(['pw-play','--target','jarvis_fixture_input',str(folder/(name+'.wav'))],check=True,timeout=15)
 def wait_reply():
  turn=b.jarvis.turn
  wait(lambda:not b.busy and not b.jarvis.state['speaking'] and any(e.get('type')=='playback' and not e.get('active') and not e.get('paused') and e.get('turn')==turn for e in voice_events),20)
 play('ignore');time.sleep(1);assert not b.jarvis.companion.store.items('memory'),'Standby transcribed room speech'
 play('wake');wait(lambda:any(e.get('type')=='jarvis_wake' for e in events),4)
 play('request');wait(lambda:len(b.jarvis.companion.store.items('memory'))==1)
 wait_reply()
 play('followup');wait(lambda:len(b.jarvis.companion.store.items('memory'))==2)
 wait_reply()
 b.jarvis.send_worker({'action':'engaged','enabled':True})
 play('ignore');time.sleep(.8)
 assert len(b.jarvis.companion.store.items('memory'))==2,'Background speech interrupted an engaged task without a wake word'
 b.jarvis.send_worker({'action':'engaged','enabled':False})
 wait(lambda:b.jarvis.state.get('standby'),12)
 result={'folder':str(folder),'wakeDetected':True,'ignoredBeforeWake':True,'followupWithoutWake':True,'returnedToStandby':True,'spoke':any(e.get('type')=='jarvis' and e['state'].get('outputLevel',0)>0 for e in events),'memories':[r['text'] for r in b.jarvis.companion.store.items('memory')],'agentStarted':b.rpc is not None}
 assert not result['agentStarted'] and result['spoke'];b.close();b=None
 result['defaultDevicesUnchanged']=all(run('pactl','get-default-'+k)==v for k,v in before.items());assert result['defaultDevicesUnchanged']
 (folder/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
finally:
 if b:b.close()
 for m in modules:subprocess.run(['pactl','unload-module',m],capture_output=True)
