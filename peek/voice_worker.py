#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""JSONL voice worker. Models stay local; microphone PCM never leaves this process."""
import json
import os
from pathlib import Path
import signal
import sys
import threading
import time
from collections import deque
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from peek.audio import EchoAudio,devices,terminate
from peek.engines import recognizer,final_recognizer,pocket,vad,synthesizer
from peek.settings import DEFAULTS,VOICES,validate
from peek.feedback import ACKNOWLEDGMENT
from peek.speech_queue import SpeechJob,SpeechQueue
from peek.listening import NoiseFloor,pause_seconds
from peek.parakeet import Parakeet
from peek.wake import WakeDetector,ConversationGate


class VoiceWorker:
    def __init__(self):
        self.prefs=validate(DEFAULTS,json.loads(os.environ.get('SIDE_CHAT_VOICE_SETTINGS','{}')),check_files=False)
        self.output_lock=threading.Lock()
        self.lock=threading.RLock()
        self.shutdown=threading.Event()
        self.ready=threading.Event()
        self.queue=SpeechQueue()
        self.speech_cache={}
        self.audio=EchoAudio()
        self.capture=None
        self.player=None
        self.listening=False
        self.speaking=False
        self.armed=False
        self.record_epoch=0
        self.input_generation=0
        self.input_utterance=0;self.input_active=False
        self.speech_paused=threading.Event()
        self.speaker=26
        self.voice=self.prefs['voice']
        self.finish=threading.Event()
        self.restart_after_finish=False
        self.speed=1.07
        self.source=self.prefs['source']
        self.sink=self.prefs['sink']
        self.parakeet=None
        self.wake_detector=None;self.gate=ConversationGate(self.prefs['followupSeconds'])
        self.engaged=False;self.standby=False
        self.capture_thread=None
        self.load_thread=threading.Thread(target=self.load,daemon=True)
        self.speech_thread=threading.Thread(target=self.speech,daemon=True)
        self.load_thread.start();self.speech_thread.start()

    def emit(self,kind,**values):
        with self.output_lock:
            try:print(json.dumps(dict(type=kind,**values)),flush=True)
            except (BrokenPipeError,OSError):
                # A shell reload may close stdout before model threads finish.
                # Cleanup must still join those threads and release audio.
                self.shutdown.set();sys.stdout=open(os.devnull,'w')

    def load(self):
        try:
            start=time.monotonic()
            self.detector=vad(self.prefs)
            # Starting a turn needs sustained speech; continuing an accepted turn
            # must react sooner so a resumed word does not lose to the endpoint.
            self.continuation_detector=vad(dict(self.prefs,minSpeech=.1,noiseRejection='balanced'))
            if self.prefs['wakeEnabled']:self.wake_detector=WakeDetector(self.prefs['wakeThreshold'])
            if self.prefs['asrModel']=='parakeet-unified':self.parakeet=Parakeet(self.prefs)
            else:self.asr=recognizer(self.prefs);self.final_asr=final_recognizer(self.prefs)
            if self.prefs['ttsModel']=='pocket':self.tts,self.voices=pocket(self.prefs)
            else:self.tts=synthesizer(self.prefs)
            # Warm both graphs without recording or playing audio.
            self.speech_cache[(self.voice,ACKNOWLEDGMENT)]=list(self.speech_chunks(ACKNOWLEDGMENT,self.voice))
            if self.parakeet:
                self.parakeet.accept(np.zeros(16000,dtype=np.float32));self.parakeet.finish();self.parakeet.reset()
            else:
                stream=self.asr.create_stream();stream.accept_waveform(16000,np.zeros(16000,dtype=np.float32))
                while self.asr.is_ready(stream):self.asr.decode_stream(stream)
            self.ready.set()
            self.emit('ready',loadSeconds=round(time.monotonic()-start,2),devices=devices())
        except Exception as exc:self.emit('error',text=str(exc))

    def cancel(self,status_only=False,hold=False):
        with self.lock:
            active=self.queue.cancel(status_only)
            if not status_only:
                if hold or self.input_active:self.speech_paused.set()
                else:self.speech_paused.clear()
            if active or not status_only:
                terminate(self.player)
                self.player=None;self.speaking=False
                self.emit('playback',active=False,level=0)

    def pause_speech(self, user=False):
        with self.lock:
            if user:
                self.input_utterance+=1;self.input_active=True
            self.speech_paused.set()
            if self.speaking:
                self.speaking=False
                self.emit('playback',active=False,paused=True,level=0)

    def resume_speech(self, utterance=None):
        with self.lock:
            # The controller may still be handling the previous utterance when
            # capture detects the next one. Its delayed resume must not win.
            if self.input_active or (utterance is not None and utterance!=self.input_utterance):return
            was_paused=self.speech_paused.is_set();self.speech_paused.clear()
            job=self.queue.active
            if (was_paused and self.player and self.player.poll() is None and not self.player.stdin.closed
                    and job and not job.cancelled.is_set()):
                self.speaking=True
                self.emit('playback',active=True,paused=False,resumed=True,level=0,turn=job.turn,status=job.status,voice=job.voice)

    def capture_event(self,epoch,kind,**values):
        with self.lock:
            if epoch!=self.record_epoch or self.shutdown.is_set():return False
            if values.get('generation',self.input_generation)!=self.input_generation:return False
            self.emit(kind,**values)
            return True

    def listen(self, enabled):
        with self.lock:
            # Finish the previous phrase before reusing its recognizer. A quick
            # off/on may reopen capture, but must not discard that phrase.
            if enabled and self.finish.is_set() and self.capture_thread and self.capture_thread.is_alive():
                self.restart_after_finish=True;return
            self.restart_after_finish=False
            if enabled==self.listening and not self.finish.is_set():return
            self.finish.clear()
            self.listening=enabled
            self.record_epoch+=1
            self.input_active=False
            epoch=self.record_epoch
            terminate(self.capture)
            self.capture=None
        if enabled:
            self.finish.clear()
            self.capture_thread=threading.Thread(target=self.record,args=(epoch,),daemon=True)
            self.capture_thread.start()
        else:
            with self.lock:
                self.resume_speech()
                # Capture and playback have independent mute controls. Keep the
                # current output route alive until its sentence has drained.
                if not self.player:self.audio.close()
            if self.capture_thread and self.capture_thread is not threading.current_thread():self.capture_thread.join(timeout=2)
            self.emit('microphone',active=False,level=0,partial='')

    def finish_input(self):
        with self.lock:
            self.restart_after_finish=False
            if self.finish.is_set() or not self.listening:return
            # Stop hardware capture immediately, retaining the accepted audio
            # and generation until the recording thread finalizes it once.
            self.finish.set();self.listening=False
            self.emit('microphone',active=False,level=0,finishing=self.input_active)
            proc=self.capture
        terminate(proc)

    def record(self,epoch):
        proc=None;submitted=False
        try:
            while not self.ready.wait(.1):
                if epoch!=self.record_epoch or self.shutdown.is_set() or self.finish.is_set():return
            with self.lock:
                if epoch!=self.record_epoch or self.finish.is_set():return
                if not self.audio.module:self.audio.start(self.source,self.sink,self.prefs['echoCancellation'])
                proc=self.audio.record();self.capture=proc
                self.emit('microphone',active=True,aec=self.audio.aec)
            stream=None if self.parakeet else self.asr.create_stream()
            if self.parakeet:self.parakeet.reset()
            self.detector.reset()
            self.continuation_detector.reset()
            pending=b'';last_text='';last_level=0;voiced=False;recording=[];preroll=deque(maxlen=max(12,int((max(self.prefs['minSpeech'],.28 if self.prefs['noiseRejection']=='strong' else 0)+.2)/.032)+1))
            generation=self.input_generation;clock=0;endpoint_at=None;total_samples=0
            floor=NoiseFloor();discarding=False;quiet_for=0
            while epoch==self.record_epoch and not self.shutdown.is_set():
                chunk=b'' if self.finish.is_set() else proc.stdout.read(2048)
                # Terminating capture can release one last buffered frame from
                # this read. It belongs to the old microphone session.
                with self.lock:
                    if epoch!=self.record_epoch or self.shutdown.is_set():break
                finishing=self.finish.is_set()
                if not chunk and not finishing:raise RuntimeError('Microphone disconnected. Select a device and turn the microphone on again.')
                continuing=False;ended=False
                if not finishing:
                    pending+=chunk
                    if len(pending)<2048:continue
                    samples=np.frombuffer(pending[:2048],dtype='<f4').copy();pending=pending[2048:]
                    clock+=len(samples)/16000
                    rms=float(np.sqrt(np.mean(samples*samples)))
                    now=time.monotonic()
                    if now-last_level>.085:
                        self.capture_event(epoch,'level',input=min(1,rms*9));last_level=now
                    if self.prefs['wakeEnabled']:
                        if self.engaged or self.speaking or self.speech_paused.is_set():self.gate.wake()
                        standby=not self.gate.active()
                        if standby!=self.standby:
                            self.standby=standby;self.capture_event(epoch,'standby',active=standby)
                        protected=(self.engaged or self.speaking) and not voiced and not self.gate.accepts_interrupt()
                        if standby or protected:
                            if self.wake_detector.accept(samples):
                                with self.lock:
                                    if epoch!=self.record_epoch or self.shutdown.is_set():break
                                    self.gate.address();self.wake_detector.reset();self.emit('wake')
                                    self.queue.put(SpeechJob('__peek_chime__',voice=self.voice,status=True))
                                self.detector.reset();self.continuation_detector.reset();preroll.clear()
                            continue
                    if self.speaking and not self.prefs['bargeIn']:
                        self.detector.reset();preroll.clear();continue
                    self.detector.accept_waveform(samples)
                    self.continuation_detector.accept_waveform(samples)
                    speech_detected=self.detector.is_speech_detected()
                    continuing=self.continuation_detector.is_speech_detected()
                    ended=not (self.continuation_detector if voiced else self.detector).empty()
                    while not self.detector.empty():self.detector.pop()
                    while not self.continuation_detector.empty():self.continuation_detector.pop()
                    if discarding:
                        quiet_for=0 if continuing else quiet_for+len(samples)/16000
                        if quiet_for>=max(.6,self.prefs['endSilence']):discarding=False;self.detector.reset()
                        if not self.finish.is_set():continue
                    if not speech_detected and not voiced:floor.observe(rms)
                    new_speech=speech_detected and not voiced
                    if new_speech:
                        recent=max([rms]+[float(np.sqrt(np.mean(a*a))) for a in preroll])
                        if not floor.accepts(recent,self.prefs['noiseRejection']=='strong'):
                            self.detector.reset();preroll.clear();continue
                        with self.lock:
                            if epoch!=self.record_epoch or self.shutdown.is_set():break
                            if self.finish.is_set():continue
                            voiced=True;submitted=False
                            generation=self.input_generation
                            self.gate.wake()
                            self.input_utterance+=1;self.input_active=True
                            if self.prefs['bargeIn']:self.pause_speech()
                            self.emit('speech_start',generation=generation,utterance=self.input_utterance)
                    if voiced:
                        self.gate.wake()
                        audio=np.concatenate([*preroll,samples]) if new_speech and preroll else samples
                        recording.append(audio)
                        total_samples+=len(audio)
                        if self.parakeet:text=self.parakeet.accept(audio)
                        else:
                            stream.accept_waveform(16000,audio)
                            while self.asr.is_ready(stream):self.asr.decode_stream(stream)
                            text=self.asr.get_result(stream).strip()
                        if text!=last_text:self.capture_event(epoch,'partial',text=text,generation=generation);last_text=text
                    else:preroll.append(samples)
                duration=total_samples/16000
                if continuing:endpoint_at=None
                if ended and voiced:
                    endpoint_at=clock+max(0,pause_seconds(last_text,self.prefs['endSilence'],self.prefs['adaptivePause'])-self.prefs['endSilence'])
                auto_end=(self.prefs['handsFree'] or self.prefs['wakeEnabled']) and endpoint_at is not None and clock>=endpoint_at
                limited=duration>=self.prefs['maxUtterance']
                if auto_end or limited or self.finish.is_set():
                    final=''
                    valid=generation==self.input_generation and epoch==self.record_epoch
                    if limited:
                        discarding=True;quiet_for=0
                        if valid:self.capture_event(epoch,'input_notice',text='That was too long to send as one request. Please try a shorter version.',generation=generation)
                    elif voiced and recording and valid:
                        endpoint=time.monotonic()
                        self.capture_event(epoch,'transcribing',generation=generation,partial=last_text,
                                  utterance=self.input_utterance,
                                  pauseSeconds=pause_seconds(last_text,self.prefs['endSilence'],self.prefs['adaptivePause']))
                        if self.parakeet:final=self.parakeet.finish()
                        else:
                            segments,_=self.final_asr.transcribe(np.concatenate(recording),language='en',beam_size=1,
                                condition_on_previous_text=False,initial_prompt='Omarchy, Hyprland, font size, configuration, Codex, Claude, terminal.')
                            final=''.join(s.text for s in segments if s.no_speech_prob<.65).strip()
                        if final and epoch==self.record_epoch and generation==self.input_generation:
                            self.gate.wake()
                            self.gate.consume_address()
                            submitted=self.capture_event(epoch,'transcript',text=final,generation=generation,utterance=self.input_utterance,utteranceSeconds=round(duration,2),finalizeSeconds=round(time.monotonic()-endpoint,3),model=self.prefs['asrModel'])
                    if epoch!=self.record_epoch or self.shutdown.is_set():break
                    if self.parakeet:self.parakeet.reset()
                    else:self.asr.reset(stream)
                    had_speech=voiced
                    self.detector.reset();preroll.clear();last_text='';recording=[];voiced=False;total_samples=0;endpoint_at=None
                    self.continuation_detector.reset()
                    with self.lock:
                        if epoch!=self.record_epoch or self.shutdown.is_set():break
                        self.input_active=False
                        self.capture_event(epoch,'utterance_end',recognized=bool(final),hadSpeech=had_speech,limited=limited,generation=generation,utterance=self.input_utterance)
                        self.capture_event(epoch,'partial',text='',generation=generation)
                        if self.finish.is_set():
                            self.listening=False
                            if not self.player:self.audio.close()
                            break
        except Exception as exc:
            with self.lock:
                if epoch==self.record_epoch:
                    self.listening=False;self.input_active=False
                    self.resume_speech()
                    self.emit('microphone',active=False,level=0)
                    self.emit('error',text=str(exc))
        finally:
            terminate(proc)
            if proc and proc.stdout:proc.stdout.close()
            with self.lock:
                if epoch==self.record_epoch and self.finish.is_set():
                    self.finish.clear();self.capture=None;self.input_active=False
                    if not submitted:self.resume_speech()
                    restart=self.restart_after_finish and not self.shutdown.is_set()
                    self.restart_after_finish=False
                    # Keep the requested restart atomic with a newer off/stop.
                    if restart:self.listen(True)

    def speech(self):
        while not self.shutdown.is_set():
            job=self.queue.get()
            if job is None:continue
            text,turn=job.text,job.turn
            while not self.ready.wait(.1):
                if self.shutdown.is_set():return
            if job.cancelled.is_set() or (job.status and time.monotonic()-job.queued_at>2):
                self.queue.finish(job);continue
            proc=None
            try:
                started=time.monotonic()
                played=0;play_started=0
                chunks=self.speech_cache.get((job.voice,text))
                for chunk in chunks if chunks is not None else self.speech_chunks(text,job.voice):
                    samples=np.asarray(np.clip(np.asarray(chunk)*self.prefs['volume'],-1,1),dtype='<f4')
                    # Recheck pauses during pacing and atomically before writing:
                    # speech can start while this chunk is waiting to be played.
                    while not job.cancelled.is_set() and not self.shutdown.is_set():
                        paused_at=time.monotonic()
                        while self.speech_paused.is_set() and not job.cancelled.is_set() and not self.shutdown.is_set():time.sleep(.02)
                        if play_started:play_started+=time.monotonic()-paused_at
                        if job.cancelled.is_set() or self.shutdown.is_set():break
                        if proc and time.monotonic()<play_started+played/self.tts.sample_rate-.064:
                            time.sleep(.008);continue
                        with self.lock:
                            if job.cancelled.is_set():break
                            if self.speech_paused.is_set():continue
                            if proc is None:
                                proc=self.audio.play(self.tts.sample_rate,self.sink);self.player=proc;self.speaking=True
                                play_started=time.monotonic()
                                self.emit('playback',active=True,text=text,turn=turn,level=0,status=job.status,voice=job.voice,
                                          firstAudioSeconds=round(play_started-started,3),queuedSeconds=round(play_started-job.queued_at,3))
                            proc.stdin.write(samples.tobytes());proc.stdin.flush()
                            played+=len(samples)
                            self.emit('output_level',level=min(1,float(np.sqrt(np.mean(samples*samples)))*6))
                        break
                    if job.cancelled.is_set() or self.shutdown.is_set():break
                if not job.cancelled.is_set() and proc:
                    proc.stdin.close();proc.wait(timeout=5)
                    if proc.returncode:raise RuntimeError('Audio output disconnected.')
            except Exception as exc:
                if not job.cancelled.is_set():self.emit('error',text=str(exc))
            finally:
                terminate(proc)
                if proc and proc.stdin and not proc.stdin.closed:proc.stdin.close()
                with self.lock:
                    self.queue.finish(job)
                    if not job.cancelled.is_set():
                        self.speaking=False;self.player=None
                        self.emit('playback',active=False,level=0,turn=turn)
                    if not self.listening:self.audio.close()

    def speech_chunks(self,text,voice=None):
        voice=voice or self.voice
        if text=='__peek_chime__':
            rate=self.tts.sample_rate;t=np.arange(int(rate*.12))/rate
            yield (np.sin(2*np.pi*740*t)+.3*np.sin(2*np.pi*1110*t))*np.sin(np.pi*t/.12)**2*.08
            return
        if self.prefs['ttsModel']=='pocket':
            for chunk in self.tts.generate_audio_stream(self.voices[voice],text,copy_state=True):
                yield chunk.detach().cpu().numpy()
        else:
            sid={'af_heart':3,'af_bella':2,'am_michael':16}[voice]
            audio=self.tts.generate(text,sid=sid,speed=self.prefs['speechRate'])
            for start in range(0,len(audio.samples),1536):yield audio.samples[start:start+1536]

    def command(self,c):
        action=c.get('action')
        if action=='listen':
            if c.get('enabled') is not True and c.get('finish') is True:self.finish_input()
            else:self.listen(c.get('enabled') is True)
        elif action=='cancel':self.cancel(hold=c.get('hold') is True)
        elif action=='pause_speech':
            with self.lock:
                # A controller acknowledgement can arrive after a microphone
                # toggle or a newer utterance. Only the owning input may pause.
                if 'generation' in c and (not self.listening or not self.input_active
                        or c['generation']!=self.input_generation or c.get('utterance')!=self.input_utterance):return
                self.pause_speech()
        elif action=='resume_speech':self.resume_speech(c.get('utterance'))
        elif action=='invalidate_input':
            with self.lock:self.input_generation=int(c.get('generation',self.input_generation+1))
        elif action=='clear_status':self.cancel(status_only=True)
        elif action=='engaged':
            self.engaged=c.get('enabled') is True
            self.gate.wake()
        elif action=='wake':self.gate.address();self.emit('wake')
        elif action=='standby':self.gate.standby();self.engaged=False
        elif action=='speak':
            text=str(c.get('text',''))[:1200]
            voice=c.get('voice') or self.voice
            if voice not in VOICES[self.prefs['ttsModel']]:raise ValueError('That voice is not available in the loaded speech model.')
            if text:
                with self.lock:
                    status=c.get('status') is True
                    if not status:self.cancel(status_only=True)
                    self.queue.put(SpeechJob(text,str(c.get('turn','')),voice,status))
        elif action=='settings':
            prefs=validate(self.prefs,{k:v for k,v in c.items() if k in DEFAULTS},check_files=False)
            source=prefs['source'];sink=prefs['sink']
            restart_audio=self.listening and (source!=self.source or sink!=self.sink or prefs['echoCancellation']!=self.prefs['echoCancellation'])
            if restart_audio:self.cancel();self.listen(False)
            self.prefs=prefs
            self.gate.seconds=prefs['followupSeconds']
            self.source=source;self.sink=sink
            if restart_audio:self.listen(True)
            self.voice=self.prefs['voice']
        elif action=='flush':
            self.finish_input()
        elif action=='close':self.close()

    def close(self):
        self.shutdown.set();self.listen(False);self.cancel()
        if self.capture_thread:self.capture_thread.join(timeout=3)
        self.load_thread.join(timeout=8)
        self.speech_thread.join(timeout=8)
        if self.parakeet:self.parakeet.close()
        if self.wake_detector:self.wake_detector.close()
        self.audio.close()


if __name__=='__main__':
    os.umask(0o077)
    worker=VoiceWorker()
    signal.signal(signal.SIGTERM,lambda *_:sys.exit(0))
    try:
        for line in sys.stdin:
            try:worker.command(json.loads(line))
            except Exception as exc:worker.emit('error',text=str(exc))
    finally:worker.close()
