"""Exercise noisy input, pauses, microphone mute and speech recovery with virtual audio."""
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time

import numpy as np
import soundfile as sf
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from peek.settings import DEFAULTS
from peek.engines import pocket


def run(*args):return subprocess.check_output(args,text=True).strip()


def prepare(folder):
    model,voices=pocket()
    rate=model.sample_rate
    def synth(text):
        a=np.concatenate([c.detach().cpu().numpy() for c in model.generate_audio_stream(voices['mary'],text,copy_state=True)])
        active=np.flatnonzero(np.abs(a)>.008)
        return a[max(0,active[0]-rate//20):min(len(a),active[-1]+rate//20)]
    clean=synth('Remember that the fixture color is blue.')
    first=synth('Remember that my favorite color is')
    second=synth('blue.')
    long=synth('This request keeps going for a while because we need to test what happens when it is too long to send as one instruction. Please do not run a command from the middle of a sentence.')
    del model,voices
    rng=np.random.default_rng(47)
    def noise(n):
        t=np.arange(n)/rate
        a=.012*np.sin(2*np.pi*120*t)+rng.normal(0,.006,n)
        for i in range(rate//3,n-400,rate//4):a[i:i+400]+=rng.normal(0,.12,400)*np.exp(-np.arange(400)/65)
        return a
    fixtures={'noise':noise(rate*5),'clean':clean,'mixed':clean+noise(len(clean))*.6,
              'pause':np.concatenate([first,np.zeros(int(rate*.7)),second]),
              'hold':np.concatenate([first,np.zeros(int(rate*1.3)),second]),'long':long}
    for name,a in fixtures.items():sf.write(folder/(name+'.wav'),a,rate)


def main():
    folder=Path(tempfile.mkdtemp(prefix='peek-listening-audit-'))
    if len(sys.argv)>1:
        for source in Path(sys.argv[1]).glob('*.wav'):shutil.copy2(source,folder/source.name)
    else:prepare(folder)
    stem='peek_audit_'+str(os.getpid());input_sink=stem+'_input';output_sink=stem+'_output'
    defaults={k:run('pactl','get-default-'+k) for k in ('source','sink')}
    modules=[];proc=None;events=[];condition=threading.Condition()
    prefs=dict(DEFAULTS,handsFree=True,source=input_sink+'.monitor',sink=output_sink,
               noiseRejection='strong',voice='mary')
    def send(action,**values):proc.stdin.write(json.dumps(dict(action=action,**values))+'\n');proc.stdin.flush()
    def reader():
        for line in proc.stdout:
            e=json.loads(line)
            with condition:events.append((time.monotonic(),e));condition.notify_all()
    def wait(predicate,after=0,timeout=25):
        deadline=time.monotonic()+timeout
        with condition:
            while time.monotonic()<deadline:
                errors=[e for t,e in events if t>=after and e.get('type')=='error']
                if errors:raise RuntimeError(errors)
                found=next(((t,e) for t,e in events if t>=after and predicate(e)),None)
                if found:return found
                condition.wait(.05)
        raise RuntimeError('Timed out: '+repr(events[-6:]))
    def play(name):
        subprocess.run(['pw-play','--target',input_sink,str(folder/(name+'.wav'))],check=True,timeout=30)
        return time.monotonic()
    def idle():send('resume_speech');time.sleep(.15)
    def settings(**changes):prefs.update(changes);send('settings',**prefs)
    try:
        for name in (input_sink,output_sink):
            modules.append(run('pactl','load-module','module-null-sink','sink_name='+name,'sink_properties="priority.session=0"'))
        with (folder/'worker.log').open('w') as log:
            proc=subprocess.Popen([sys.executable,'-B','peek/voice_worker.py'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                stderr=log,text=True,env=dict(os.environ,HF_HUB_OFFLINE='1',SIDE_CHAT_VOICE_SETTINGS=json.dumps(prefs)))
        threading.Thread(target=reader,daemon=True).start()
        wait(lambda e:e.get('type')=='ready',timeout=35)
        send('listen',enabled=True);wait(lambda e:e.get('type')=='microphone' and e.get('active'))
        start=time.monotonic();play('noise');time.sleep(1)
        noise_events=[e for t,e in events if t>=start and e.get('type') in ('speech_start','transcript')]
        assert not noise_events,noise_events
        print('Fan and keyboard fixture: no speech or commands detected',flush=True)
        results={}
        for name in ('clean','mixed','pause'):
            start=time.monotonic();finished=play(name)
            at,event=wait(lambda e:e.get('type')=='transcript',start)
            time.sleep(.8)
            transcripts=[e['text'] for t,e in events if t>=start and e.get('type')=='transcript']
            assert len(transcripts)==1 and 'blue' in transcripts[0].lower(),(name,transcripts)
            results[name]={'text':event['text'],'finalizeSeconds':event['finalizeSeconds'],'afterPlayerEndedMs':round((at-finished)*1000)}
            print(name+': '+json.dumps(results[name]),flush=True);idle()
        settings(handsFree=False)
        start=time.monotonic();play('hold');time.sleep(.6)
        assert not any(t>=start and e.get('type')=='transcript' for t,e in events),'Hold-to-talk sent before release'
        send('flush');_,event=wait(lambda e:e.get('type')=='transcript',start)
        assert 'blue' in event['text'].lower(),event
        wait(lambda e:e.get('type')=='microphone' and not e.get('active'),start);idle()
        print('Hold-to-talk: pause preserved, sent only on release',flush=True)
        settings(handsFree=True);send('listen',enabled=True)
        wait(lambda e:e.get('type')=='microphone' and e.get('active'),start)
        start=time.monotonic();play('clean')
        assert not any(t>=start and e.get('type')=='transcript' for t,e in events),'Fixture ended after automatic submission'
        muted=time.monotonic();send('listen',enabled=False,finish=True)
        off,_=wait(lambda e:e.get('type')=='microphone' and not e.get('active'),muted)
        at,event=wait(lambda e:e.get('type')=='transcript',muted)
        assert 'blue' in event['text'].lower(),event
        assert off<at,'Microphone was not disabled before recognition finished'
        time.sleep(.8)
        assert sum(t>=start and e.get('type')=='transcript' for t,e in events)==1,'Mic-off submitted twice'
        results['micOff']={'text':event['text'],'finalizeSeconds':event['finalizeSeconds'],
                           'afterMicOffMs':round((at-muted)*1000),'micDisabledMs':round((off-muted)*1000)}
        print('Microphone off sends accepted phrase: '+json.dumps(results['micOff']),flush=True);idle()
        # Pausing speech must preserve both the current sentence and queued answer.
        start=time.monotonic();send('speak',text='The settings are ready. You can choose a voice and continue whenever you like.')
        wait(lambda e:e.get('type')=='playback' and e.get('active'),start)
        send('pause_speech');paused,_=wait(lambda e:e.get('type')=='playback' and e.get('paused'),start)
        time.sleep(.4);quiet_since=time.monotonic();time.sleep(.3)
        assert not any(t>=quiet_since and e.get('type')=='output_level' for t,e in events),'Audio continued during pause'
        send('resume_speech');resumed,_=wait(lambda e:e.get('type')=='playback' and e.get('active') and e.get('paused') is False,paused)
        wait(lambda e:e.get('type')=='playback' and not e.get('active') and not e.get('paused'),resumed+.01)
        print('Interrupted reply: paused and resumed without cancelling',flush=True)
        settings(handsFree=True);send('listen',enabled=True)
        wait(lambda e:e.get('type')=='microphone' and e.get('active'),resumed)
        start=time.monotonic();send('speak',text='You can turn off the microphone while I finish speaking this sentence. You can also turn it back on, and I will keep speaking without starting over or losing the rest of my answer.')
        active,_=wait(lambda e:e.get('type')=='playback' and e.get('active'),start)
        send('listen',enabled=False,finish=True);off,_=wait(lambda e:e.get('type')=='microphone' and not e.get('active'),active)
        wait(lambda e:e.get('type')=='output_level' and e.get('level',0)>0,off+.1)
        # Re-enable capture while the same sentence still owns the output route.
        send('listen',enabled=True);on,_=wait(lambda e:e.get('type')=='microphone' and e.get('active'),off)
        wait(lambda e:e.get('type')=='output_level' and e.get('level',0)>0,on+.1)
        send('listen',enabled=False,finish=True);off,_=wait(lambda e:e.get('type')=='microphone' and not e.get('active'),on)
        wait(lambda e:e.get('type')=='output_level' and e.get('level',0)>0,off+.1)
        ended,_=wait(lambda e:e.get('type')=='playback' and not e.get('active'),off+.1)
        assert not any(active<t<ended and e.get('type')=='playback' for t,e in events),'Microphone toggle interrupted or restarted playback'
        print('Microphone off/on/off: same spoken reply continued to completion',flush=True)
        send('listen',enabled=True)
        wait(lambda e:e.get('type')=='microphone' and e.get('active'),off)
        start=time.monotonic()
        send('speak',text='This previous reply should pause when you speak and stay paused until your new request is accepted. It must not start over.')
        wait(lambda e:e.get('type')=='playback' and e.get('active'),start)
        send('speak',text='This old queued reply must never be heard.')
        fixture=subprocess.Popen(['pw-play','--target',input_sink,str(folder/'clean.wav')])
        try:
            heard,event=wait(lambda e:e.get('type')=='speech_start',start)
            utterance=event['utterance']
            send('resume_speech',utterance=utterance-1)
            wait(lambda e:e.get('type')=='utterance_end',heard)
            send('resume_speech',utterance=utterance-1)
            quiet_since=time.monotonic();time.sleep(.25)
            assert not any(t>=quiet_since and e.get('type')=='output_level' for t,e in events),'Stale resume restarted the old reply'
            assert not any(t>heard and e.get('type')=='playback' and e.get('active') for t,e in events),'Old reply resumed during input'
            # A recognized request retires the old queue before accepting output.
            send('cancel',hold=True);send('speak',text='Your new reply.',turn='new-request')
            send('resume_speech',utterance=utterance)
            active,_=wait(lambda e:e.get('type')=='playback' and e.get('active') and e.get('turn')=='new-request',heard)
            wait(lambda e:e.get('type')=='playback' and not e.get('active') and e.get('turn')=='new-request',active)
            assert not any(t>heard and e.get('text')=='This old queued reply must never be heard.' for t,e in events)
        finally:
            if fixture.poll() is None:fixture.terminate()
            fixture.wait(timeout=5)
        print('Next utterance: stale resume rejected; old reply queue retired',flush=True)
        settings(maxUtterance=5)
        start=time.monotonic();play('long')
        wait(lambda e:e.get('type')=='input_notice',start);time.sleep(1)
        assert not any(t>=start and e.get('type')=='transcript' for t,e in events),'Truncated request escaped'
        result={'noiseRejected':True,'samples':results,'holdToTalkPreserved':True,'pausedReplyResumed':True,
                'staleResumeRejected':True,'previousReplyNotReplayed':True,
                'micMutePreservedOutput':True,'micTogglePreservedOutput':True,'micOffSendsUtterance':True,'longRequestNotExecuted':True,
                'defaultDevicesUnchanged':all(run('pactl','get-default-'+k)==v for k,v in defaults.items()),'folder':str(folder)}
        assert result['defaultDevicesUnchanged']
        (folder/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2),flush=True)
    finally:
        (folder/'events.json').write_text(json.dumps(events,indent=2))
        print('Fixture artifacts: '+str(folder),flush=True)
        if proc:
            proc.stdin.close()
            try:proc.wait(timeout=15)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
            proc.stdout.close()
        for module in modules:subprocess.run(['pactl','unload-module',module],capture_output=True)


if __name__=='__main__':main()
