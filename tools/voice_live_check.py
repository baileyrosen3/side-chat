"""Full PipeWire -> local STT -> real CLI -> local TTS test using virtual audio only."""
import argparse,json,subprocess,sys,tempfile,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend import Bridge
from peek.settings import validate

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--hands-free',action='store_true')
parser.add_argument('--tts-model',choices=('pocket','kokoro'),default='pocket')
parser.add_argument('--noise-rejection',choices=('balanced','strong'),default='balanced')
args=parser.parse_args()

def run(*args):return subprocess.check_output(args,text=True).strip()
folder=Path(tempfile.mkdtemp(prefix='peek-voice-live-'));modules=[];b=None
before={k:run('pactl','get-default-'+k) for k in ('source','sink')}
try:
 for name in ('peek_fixture_input','peek_fixture_output'):
  modules.append(run('pactl','load-module','module-null-sink','sink_name='+name,'sink_properties="node.description=PeekFixture priority.session=0"'))
 runtime=Path.home()/'.local/share/side-chat/runtime/bin/python'
 prepare="from peek.engines import pocket; import numpy as np,soundfile as sf,sys; model,voices=pocket(); samples=np.concatenate([c.detach().cpu().numpy() for c in model.generate_audio_stream(voices['alba'],'Reply with the words voice link verified.',copy_state=True)]); sf.write(sys.argv[1],samples,model.sample_rate)"
 subprocess.run([str(runtime),'-c',prepare,str(folder/'request.wav')],check=True)
 events=[]
 b=Bridge(folder/'state',lambda event:events.append(event.copy()))
 voice_events=[];voice_event=b.peek.voice_event
 def observe_voice(event):
  voice_events.append(event.copy());voice_event(event)
 b.peek.voice_event=observe_voice
 b.settings['cwd']=str(folder)
 b.peek.prefs.update(handsFree=False,source='peek_fixture_input.monitor',sink='peek_fixture_output',noiseRejection=args.noise_rejection)
 b.peek.prefs=validate(b.peek.prefs,{'ttsModel':args.tts_model})
 b.dispatch({'action':'peek','enabled':True})
 deadline=time.monotonic()+20
 while not b.peek.state['ready'] and time.monotonic()<deadline:time.sleep(.1)
 if not b.peek.state['ready']:raise RuntimeError(b.peek.state)
 if args.hands_free:
  b.dispatch({'action':'peek_settings','settings':{'handsFree':True}})
 b.dispatch({'action':'peek_listen','enabled':True})
 deadline=time.monotonic()+8
 while not b.peek.state['listening'] and time.monotonic()<deadline:time.sleep(.1)
 if not b.peek.state['listening']:raise RuntimeError(b.peek.state)
 subprocess.run(['pw-play','--target','peek_fixture_input',str(folder/'request.wav')],check=True,timeout=10)
 if not args.hands_free:b.dispatch({'action':'peek_finish'})
 deadline=time.monotonic()+50
 while time.monotonic()<deadline:
  wrote_audio=any(e.get('type')=='peek' and e['state'].get('outputLevel',0)>0 for e in events) and any(
   e.get('type')=='playback' and e.get('active') and not e.get('status') and e.get('text')!='__peek_chime__' for e in voice_events)
  if b.peek.state['error']:break
  if b.current and b.current['messages'] and not b.busy and wrote_audio and not b.peek.state['speaking']:break
  time.sleep(.1)
 result={'folder':str(folder),'voice':{k:b.peek.state.get(k) for k in ('ready','listening','speaking','stage','caption','error')},
         'recognition':b.peek.prefs['asrModel'],'tts':args.tts_model,'handsFree':args.hands_free,
         'messages':[{k:m.get(k) for k in ('role','text','status','error')} for m in (b.current or {}).get('messages',[])],
         'spoke':wrote_audio,'playbackFinished':wrote_audio and not b.peek.state['speaking'],
         'transcripts':[e for e in voice_events if e.get('type')=='transcript'],
         'playback':[e for e in voice_events if e.get('type')=='playback' and e.get('active')]}
 (folder/'result.json').write_text(json.dumps(result,indent=2))
 b.close();b=None
 result['default_devices_unchanged']=all(run('pactl','get-default-'+k)==v for k,v in before.items())
 print(json.dumps(result,indent=2))
 assert result['spoke'] and result['playbackFinished'] and not result['voice']['error'] and result['default_devices_unchanged'] and result['messages'][-1]['status']=='complete',result
finally:
 if b:b.close()
 for module in modules:subprocess.run(['pactl','unload-module',module],capture_output=True)
