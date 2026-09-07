"""Measure the real speech worker through a silent PipeWire sink; never arm a mic or agent."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time

import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend import Bridge
from jarvis.settings import DEFAULTS,VOICES


def run(*args):return subprocess.check_output(args,text=True).strip()


def main():
    sink='jarvis_latency_'+str(os.getpid())
    defaults={k:run('pactl','get-default-'+k) for k in ('source','sink')}
    module=run('pactl','load-module','module-null-sink','sink_name='+sink,
               'sink_properties="node.description=JarvisLatencyTest priority.session=0"')
    recorder=None;worker=None;b=None
    folder=Path(tempfile.mkdtemp(prefix='jarvis-speech-check-'))
    events=[];audio=[];condition=threading.Condition()

    def wait_event(predicate,after=0,timeout=20):
        deadline=time.monotonic()+timeout
        with condition:
            while time.monotonic()<deadline:
                errors=[e for t,e in events if t>=after and e.get('type')=='error']
                if errors:raise RuntimeError(errors)
                match=next(((t,e) for t,e in events if t>=after and predicate(e)),None)
                if match:return match
                condition.wait(.05)
        raise RuntimeError('Speech event timed out: '+repr(events[-4:]))

    def send(**c):b.jarvis.send_worker(c)

    def read_events():
        for line in worker.stdout:
            e=json.loads(line)
            with condition:events.append((time.monotonic(),e));condition.notify_all()
            b.jarvis.voice_event(e)

    def read_audio():
        while True:
            data=recorder.stdout.read(3072)
            if not data:return
            if np.max(np.abs(np.frombuffer(data,dtype='<f4')))>0.003:
                with condition:audio.append(time.monotonic());condition.notify_all()

    try:
        prefs=dict(DEFAULTS,voice='marius',handsFree=False,sink=sink,echoCancellation=False)
        b=Bridge(folder/'state',lambda _:None)
        b.jarvis.prefs=prefs;b.jarvis.state.update(prefs,enabled=True)
        log=(folder/'worker.log').open('w')
        worker=subprocess.Popen([str(Path.home()/'.local/share/side-chat/runtime/bin/python'),'-B','jarvis/voice_worker.py'],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True,
            env=dict(os.environ,HF_HUB_OFFLINE='1',SIDE_CHAT_VOICE_SETTINGS=json.dumps(prefs)))
        log.close();b.jarvis.voice=worker
        threading.Thread(target=read_events,daemon=True).start()
        wait_event(lambda e:e.get('type')=='ready',timeout=35)
        # Pulse monitor names differ from PipeWire node names. parec fails closed
        # on an unknown device, instead of allowing WirePlumber to auto-route it.
        recorder=subprocess.Popen(['parec','--raw','--format=float32le','--rate=24000','--channels=1',
                                   '--latency-msec=32','--device='+sink+'.monitor'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
        threading.Thread(target=read_audio,daemon=True).start()
        b.busy=True;b.current={'messages':[{'role':'assistant','text':'','tools':[]}]}
        started=time.monotonic();b.jarvis.begin_turn()
        ack_at,ack=wait_event(lambda e:e.get('type')=='playback' and e.get('active') and e.get('status'),started)
        with condition:
            condition.wait_for(lambda:any(t>=started for t in audio),timeout=5)
        first_sample=next(t for t in audio if t>=started)
        assert first_sample>=ack_at, 'Audio arrived before speech started: check the monitor routing.'
        answer_start=time.monotonic()
        b.jarvis.observe({'type':'delta','text':"Here's your answer.",'tools':[]})
        answer_at,answer=wait_event(lambda e:e.get('type')=='playback' and e.get('active') and e.get('text')=="Here's your answer.",answer_start)
        wait_event(lambda e:e.get('type')=='playback' and not e.get('active'),answer_at+.01)
        b.jarvis.feedback.finish();b.busy=False
        samples={}
        for voice in VOICES['pocket']:
            start=time.monotonic()
            send(action='speak',voice=voice,text="Hey, I'm Jarvis. How's your day going?")
            at,event=wait_event(lambda e:e.get('type')=='playback' and e.get('active') and e.get('voice')==voice,start)
            wait_event(lambda e:e.get('type')=='playback' and not e.get('active'),at+.01)
            assert any(t>=at for t in audio),voice+' produced no audio'
            samples[voice]=event['firstAudioSeconds']
            print(voice+': first chunk '+str(event['firstAudioSeconds'])+' s',flush=True)
        # Stop must cancel an active sentence and its queued follow-up.
        start=time.monotonic();send(action='speak',text='This is a long sentence to test stopping playback before it reaches the end.')
        wait_event(lambda e:e.get('type')=='playback' and e.get('active'),start)
        send(action='speak',text='This queued sentence must never play.')
        send(action='cancel');send(action='speak',text='The new turn works.')
        at,_=wait_event(lambda e:e.get('type')=='playback' and e.get('active') and e.get('text')=='The new turn works.',start)
        wait_event(lambda e:e.get('type')=='playback' and not e.get('active'),at+.01)
        assert not any(e.get('active') and e.get('text')=='This queued sentence must never play.' for _,e in events)
        assert not any(e.get('type')=='microphone' and e.get('active') for _,e in events)
        result={'ackPlaybackMs':round((ack_at-started)*1000),'ackAudibleInVirtualSinkMs':round((first_sample-started)*1000),
                'sentencePlaybackMs':round((answer_at-answer_start)*1000),'firstChunkSeconds':samples,
                'cancelledQueueDidNotReplay':True,'microphoneNeverArmed':True,
                'defaultsUnchanged':all(run('pactl','get-default-'+k)==v for k,v in defaults.items()),'folder':str(folder)}
        assert result['defaultsUnchanged']
        (folder/'result.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(result,indent=2),flush=True)
    finally:
        if b:b.busy=False;b.close()
        if worker:
            try:worker.wait(timeout=15)
            except subprocess.TimeoutExpired:worker.kill();worker.wait()
            worker.stdout.close()
        if recorder:recorder.terminate();recorder.wait();recorder.stdout.close()
        subprocess.run(['pactl','unload-module',module],capture_output=True)


if __name__=='__main__':main()
