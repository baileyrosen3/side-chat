# SPDX-License-Identifier: GPL-3.0-or-later
"""Peek mode coordinates one existing CLI session, local speech, and observable input."""
import hashlib
import json
import os
from pathlib import Path
import re
import queue
import subprocess
import threading
import time
import uuid
from peek.control import request as control_request
from peek.settings import DEFAULTS, RELOAD, validate, model_info
from peek.companion import Companion
from peek.feedback import SpokenFeedback
from peek.task import TaskProgress


class SpeechSegments:
    """Incremental public Markdown reader; fences and URLs never become spoken code."""
    def __init__(self):
        self.text='';self.offset=0;self.fenced=False

    @staticmethod
    def clean(text):
        text=re.sub(r'!\[[^\]]*\]\([^)]*\)','',text)
        text=re.sub(r'\[([^\]]+)\]\([^)]*\)',r'\1',text)
        text=re.sub(r'https?://\S+','',text)
        text=re.sub(r'`[^`]*`','',text)
        text=re.sub(r'<[^>]+>','',text)
        text=re.sub(r'^[\s#>*\-]+','',text)
        return re.sub(r'\s+',' ',text.replace('**','').replace('__','')).strip()

    @staticmethod
    def safe_boundary(text):
        # Wait for complete inline Markdown, even if a delta ends inside a URL.
        if text.count('`')%2 or text.count('[')!=text.count(']'):return False
        if re.search(r'\]\([^)]*$',text):return False
        without_links=re.sub(r'\[[^\]]*\]\([^)]*\)','',text)
        if re.search(r'https?://\S*$',without_links):return False
        if re.search(r'\b(?:Mr|Mrs|Ms|Dr|Prof|St|vs|etc|e\.g|i\.e)\.$',text,re.I):return False
        return True

    def feed(self,text,final=False,settled=False):
        if len(text)<len(self.text) and self.text.startswith(text):
            # Delayed/empty snapshots can arrive while a stream is restarting.
            # Keep the consumed prefix so the next full snapshot cannot replay it.
            return []
        if not text.startswith(self.text[:self.offset]):
            # A rewritten snapshot must not replay previously spoken content.
            self.offset=len(text);self.text=text;return []
        self.text=text;out=[]
        while self.offset<len(text):
            tail=text[self.offset:]
            if tail.startswith('```') or tail.startswith('~~~'):
                end=tail.find('\n')
                if end<0 and not final:break
                self.fenced=not self.fenced;self.offset+=end+1 if end>=0 else len(tail);continue
            newline=tail.find('\n')
            if self.fenced:
                if newline<0:
                    if final:self.offset=len(text)
                    break
                self.offset+=newline+1;continue
            pattern=r'[.!?](?=\s)|\n'
            if settled:pattern=r'[.!?](?=\s|$)|\n'
            cut=next((m.end() for m in re.finditer(pattern,tail) if self.safe_boundary(tail[:m.end()])),0)
            if not cut:
                cut=next((m.end() for m in re.finditer(r'[,;:](?=\s)',tail)
                          if m.end()>=80 and self.safe_boundary(tail[:m.end()])),0)
            if not cut and len(tail)>220:
                cut=tail.rfind(' ',70,220)
                if cut>0 and not self.safe_boundary(tail[:cut]):cut=0
            if not cut:
                if not final:break
                cut=len(tail)
            segment=tail[:cut];self.offset+=cut
            cleaned=self.clean(segment)
            if cleaned and not cleaned.startswith(('{','[')):out.append(cleaned)
        return out


class PeekController:
    def __init__(self,bridge):
        self.bridge=bridge
        self.guard=threading.RLock()
        self.write_lock=threading.Lock()
        self.voice=None;self.control=None
        self.closed=False;self.was_busy=False
        self.speech=SpeechSegments();self.turn='';self.pending=''
        self.want_listen=False;self.spoken=False
        self.data=Path(os.environ.get('SIDE_CHAT_DATA',Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))/'side-chat'))
        self.python=self.data/'runtime/bin/python'
        digest=hashlib.sha256(str(bridge.state).encode()).hexdigest()[:12]
        self.folder=Path(os.environ.get('XDG_RUNTIME_DIR','/tmp'))/('side-chat-'+str(os.getuid())+'-'+digest)
        self.socket=self.folder/'control.sock'
        row=bridge.db.execute("SELECT value FROM settings WHERE key='peek'").fetchone()
        if not row:
            # Preserve voice preferences saved by releases before the Peek
            # rename. New writes use the canonical Peek key below.
            row=bridge.db.execute("SELECT value FROM settings WHERE key='jarvis'").fetchone()
        self.prefs=dict(DEFAULTS)
        if row:
            saved=json.loads(row[0])
            try:self.prefs=validate(self.prefs,{k:v for k,v in saved.items() if k in DEFAULTS},check_files=False)
            except ValueError:pass
        self.state=dict(self.prefs,enabled=False,ready=False,listening=False,speaking=False,stage='off',caption='',partial='',inputLevel=0,outputLevel=0,error='',devices=[])
        self.state.update(model_info(self.prefs))
        self.correction_paused=False
        self.user_speaking=False;self.last_delta=0
        self.transcribing=False;self.input_generation=0;self.input_utterance=0;self.input_pending=set()
        self.input_queue=queue.Queue(maxsize=32)
        self.feedback=SpokenFeedback()
        self.task=TaskProgress()
        self.task_chat=''
        self.feedback_stop=threading.Event()
        self.companion=Companion(self)
        self.feedback_thread=threading.Thread(target=self.feedback_loop,daemon=True)
        self.feedback_thread.start()
        self.input_thread=threading.Thread(target=self.input_loop,daemon=True)
        self.input_thread.start()

    def invalidate_input(self):
        with self.guard:
            self.input_generation+=1;self.input_pending.clear()
            self.user_speaking=False;self.transcribing=False
        self.send_worker({'action':'invalidate_input','generation':self.input_generation})
        self.publish(hearing=False,transcribing=False)

    def input_loop(self):
        while not self.feedback_stop.is_set():
            try:text,generation,token=self.input_queue.get(timeout=.1)
            except queue.Empty:continue
            try:self.submit_voice(text,generation=generation)
            except Exception as exc:self.publish(error=str(exc),stage='error')
            finally:
                with self.guard:self.input_pending.discard(token)
                try:
                    if generation==self.input_generation:self.resume_input()
                finally:self.input_queue.task_done()

    def resume_input(self):
        with self.guard:
            if self.user_speaking or self.transcribing or self.input_pending or not self.enabled:return
            self.send_worker({'action':'resume_speech','utterance':self.input_utterance})
            if self.correction_paused:
                self.correction_paused=False
                if self.bridge.busy and not self.bridge.cancelled.is_set():
                    try:self.configure_control(True)
                    except (OSError,RuntimeError) as exc:self.publish(error=str(exc),stage='error')
        self.refresh_activity()

    def cwd(self):
        return (self.bridge.current or {}).get('options',{}).get('cwd') or self.bridge.settings.get('cwd') or str(Path.home())

    @property
    def enabled(self):return self.state['enabled']

    def publish(self,**values):
        with self.guard:self.state.update(values);state=dict(self.state)
        for key in ('memories','routines','watches','activity','restorePoints'):
            if key not in values:state.pop(key,None)
        self.bridge.emit(type='peek',state=state)

    def send_worker(self,command):
        with self.write_lock:
            if self.voice and self.voice.poll() is None:
                try:self.voice.stdin.write(json.dumps(command)+'\n');self.voice.stdin.flush()
                except (BrokenPipeError,OSError):pass

    def read_process(self,proc,callback,label):
        try:
            for line in proc.stdout:
                try:
                    if (label=='voice' and self.voice is proc) or (label=='control' and self.control is proc):callback(json.loads(line))
                except Exception as exc:self.publish(error=str(exc),stage='error')
        finally:
            if not self.closed and ((label=='voice' and self.voice is proc) or (label=='control' and self.control is proc)):
                self.publish(ready=False,listening=False,speaking=False,stage='error',error=label.capitalize()+' worker stopped. Turn Peek off and on again to reconnect.')

    def ensure_control(self):
        if self.control and self.control.poll() is None:return
        if not self.python.is_file():raise ValueError('Run python3 peek/setup.py to install local speech and input support.')
        self.folder.mkdir(parents=True,exist_ok=True,mode=0o700)
        os.chmod(self.folder,0o700);self.socket.unlink(missing_ok=True)
        log=open(self.bridge.state/'peek-control.log','a')
        self.control=subprocess.Popen([str(self.python),'-B',str(Path(__file__).with_name('control.py')),'--serve',str(self.socket)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True,start_new_session=True,env=dict(os.environ,SIDE_CHAT_CONTROL_LIFELINE='1',SIDE_CHAT_COMPANION_STATE=str(self.bridge.state),PYTHONDONTWRITEBYTECODE='1'))
        log.close()
        threading.Thread(target=self.read_process,args=(self.control,self.control_event,'control'),daemon=True).start()
        deadline=time.monotonic()+4
        while not self.socket.exists():
            if self.control.poll() is not None or time.monotonic()>deadline:raise ValueError('Desktop control could not start. Check peek-control.log.')
            time.sleep(.025)

    def configure_control(self,enabled):
        if self.control and self.control.poll() is None:
            control_request(self.socket,{'op':'_configure','enabled':enabled,'scope':self.prefs['scope'],'turn':self.turn,'accent':self.state.get('accent',''),'cwd':self.cwd()})

    def extension_options(self):
        if not self.enabled:return {}
        self.ensure_control()
        return {'_peek_extension':str(Path(__file__).with_name('agent_extension.ts')),
                '_peek_socket':str(self.socket),'_peek_client':str(Path(__file__).with_name('control.py'))}

    def enable(self,enabled):
        if enabled and self.enabled and self.voice and self.voice.poll() is None:
            self.publish();return
        if enabled:
            agent=self.bridge.current['agent'] if self.bridge.current and self.bridge.current['messages'] else self.bridge.default_agent()
            from agent_session import NATIVE_AGENTS
            if agent not in NATIVE_AGENTS:raise ValueError('Peek needs a native tool session. This agent adapter is not yet available: '+agent)
            if self.bridge.terminal_state(self.bridge.current):raise ValueError('Exit the agent terminal before turning on Peek.')
            self.ensure_control()
            self.publish(enabled=True,ready=False,stage='warming',error='',caption='Warming local voice…')
            self.want_listen=self.prefs['handsFree'] or self.prefs['wakeEnabled']
            if not self.voice or self.voice.poll() is not None:
                log=open(self.bridge.state/'peek-voice.log','a')
                self.voice=subprocess.Popen([str(self.python),'-B',str(Path(__file__).with_name('voice_worker.py'))],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True,start_new_session=True,env=dict(os.environ,HF_HUB_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1',SIDE_CHAT_VOICE_SETTINGS=json.dumps(self.prefs),SIDE_CHAT_VOXTYPE_DIR=str(self.folder/'voxtype')))
                log.close()
                threading.Thread(target=self.read_process,args=(self.voice,self.voice_event,'voice'),daemon=True).start()
            self.configure_control(False)
        else:
            self.invalidate_input()
            with self.guard:self.feedback.finish()
            self.want_listen=False;self.pending=''
            self.send_worker({'action':'listen','enabled':False});self.send_worker({'action':'cancel'})
            self.configure_control(False)
            self.bridge.emit(type='peek_pointer',pointer={'visible':False})
            proc,self.voice=self.voice,None
            if proc:
                try:proc.stdin.close()
                except OSError:pass
                def reap():
                    try:proc.wait(timeout=12)
                    except subprocess.TimeoutExpired:
                        proc.terminate()
                        try:proc.wait(timeout=3)
                        except subprocess.TimeoutExpired:proc.kill()
                threading.Thread(target=reap,daemon=True).start()
            self.publish(enabled=False,ready=False,listening=False,speaking=False,stage='off',inputLevel=0,outputLevel=0,partial='')

    def dispatch(self,c):
        action=c.get('action')
        if self.companion.dispatch(c):return
        if action=='peek':
            self.state['accent']=str(c.get('accent',''))
            self.enable(c.get('enabled') is True)
        elif action=='peek_status':self.companion.publish()
        elif action=='peek_say':self.submit_voice(str(c.get('text','')))
        elif action=='peek_voice_preview':
            if not self.enabled or not self.state['ready']:raise ValueError('Turn on Peek and wait for the voice to be ready before previewing.')
            if self.bridge.busy or self.bridge.ui_requests:raise ValueError('Finish or stop the task before previewing a voice.')
            voice=validate(self.prefs,{'voice':c.get('voice')},check_files=False)['voice']
            self.send_worker({'action':'cancel'})
            self.send_worker({'action':'speak','voice':voice,'text':"Hey, I'm Peek. What are we working on today? Take your time. I'm here when you need me."})
        elif action=='peek_wake':self.send_worker({'action':'wake'})
        elif action=='peek_standby':
            self.stop()
            if self.prefs['wakeEnabled']:
                self.want_listen=True;self.send_worker({'action':'listen','enabled':True})
                self.send_worker({'action':'standby'});self.publish(standby=True,caption='Say the wake phrase',stage='standby')
            else:
                self.want_listen=False;self.send_worker({'action':'listen','enabled':False});self.publish(standby=False,caption='Microphone paused',stage='idle')
        elif action=='peek_stop':self.stop()
        elif action in ('peek_listen','peek_toggle_listen'):
            # Use the requested state: worker acknowledgements can lag behind
            # shortcuts, especially while the speech models are warming up.
            listening=not (self.enabled and self.want_listen) if action=='peek_toggle_listen' else c.get('enabled') is True
            if action=='peek_toggle_listen' and not self.enabled:
                self.state['accent']=str(c.get('accent',''))
                self.enable(True)
            self.want_listen=listening
            self.send_worker({'action':'listen','enabled':True} if listening else {'action':'listen','enabled':False,'finish':True})
        elif action=='peek_finish':
            self.want_listen=False;self.send_worker({'action':'flush'})
        elif action=='peek_settings':
            values=c.get('settings',{})
            prefs=validate(self.prefs,values)
            changed={k for k in prefs if prefs[k]!=self.prefs[k]}
            reload=bool(changed & RELOAD) and self.enabled
            if self.bridge.busy and (reload or 'scope' in changed):
                raise ValueError('Finish or stop the current task before changing the model or control mode.')
            listening=self.want_listen
            if reload:self.enable(False)
            if 'scope' in changed:self.stop()
            self.prefs=prefs
            if 'scope' in changed:self.configure_control(False)
            self.bridge.db.execute("INSERT OR REPLACE INTO settings VALUES ('peek',?)",(json.dumps(self.prefs),));self.bridge.db.commit()
            self.send_worker(dict(self.prefs,action='settings'))
            if self.prefs['muted']:self.send_worker({'action':'cancel'})
            elif not self.prefs['spokenProgress']:self.send_worker({'action':'clear_status'})
            if {'handsFree','wakeEnabled'} & values.keys():
                self.want_listen=self.prefs['handsFree'] or self.prefs['wakeEnabled'];self.send_worker({'action':'listen','enabled':self.want_listen})
            self.publish(**self.prefs,**model_info(self.prefs))
            if reload:
                self.enable(True)
                if not {'handsFree','wakeEnabled'} & changed:self.want_listen=listening
        elif action=='peek_devices':
            from peek.audio import devices
            self.publish(devices=devices(),**model_info(self.prefs))

    def begin_turn(self):
        if not self.enabled:return
        with self.guard:
            self.turn=uuid.uuid4().hex;self.speech=SpeechSegments();self.last_delta=0
            self.bridge.cancelled.clear()
            self.feedback.start(time.monotonic())
            self.task.begin(self.turn)
            self.task_chat=(self.bridge.current or {}).get('id','')
        self.send_worker({'action':'cancel','hold':bool(self.user_speaking or self.input_pending)})
        self.send_worker({'action':'engaged','enabled':True})
        self.correction_paused=False
        self.configure_control(True)
        self.publish(stage='thinking',caption='Peek is thinking…',partial='',error='',
                     task=self.task.snapshot(),taskCaption='Working through your request',
                     completedAt=0,actionTarget=None)

    def abort_turn(self):
        with self.guard:self.feedback.finish()
        self.send_worker({'action':'cancel'})
        self.send_worker({'action':'engaged','enabled':False})
        try:self.configure_control(False)
        except (OSError,RuntimeError):pass
        self.publish(task=self.task.finish('error'),actionTarget=None)
        self.refresh_activity()

    def feedback_loop(self):
        while not self.feedback_stop.wait(.1):
            self.feedback_tick(time.monotonic())

    def feedback_tick(self,now):
        with self.guard:
            if not self.enabled or not self.feedback.active:return
            if self.bridge.cancelled.is_set():return
            blocked=(not self.state['ready'] or self.prefs['muted'] or self.user_speaking
                     or self.transcribing or self.input_pending or self.correction_paused or bool(self.bridge.ui_requests) or bool(self.state['error']))
            if not blocked and self.last_delta and now-self.last_delta>=.2:
                self.say(self.speech.feed(self.speech.text,settled=True))
            text=self.feedback.due(now,blocked=blocked or self.state['speaking'] or not self.prefs['spokenProgress'])
            if text:self.send_worker({'action':'speak','text':text,'turn':self.turn,'status':True})

    def refresh_activity(self):
        """Microphone/playback events must not hide an unfinished agent turn."""
        if not self.enabled:return
        if self.state['error']:stage='error'
        elif self.bridge.ui_requests:stage='needs_input'
        elif self.user_speaking:stage='listening'
        elif self.transcribing:stage='thinking'
        elif self.state['speaking']:stage='speaking'
        elif self.bridge.busy and not self.bridge.cancelled.is_set():
            messages=(self.bridge.current or {}).get('messages',[])
            tools=messages[-1].get('tools',[]) if messages else []
            stage='acting' if any(t.get('status')=='running' for t in tools) else 'thinking'
        elif not self.state['ready'] and self.state['stage']=='warming':stage='warming'
        elif self.state.get('standby') and self.state['listening']:stage='standby'
        else:stage='listening' if self.state['listening'] else 'idle'
        if stage!=self.state['stage']:
            values={'stage':stage}
            if stage=='thinking':values['caption']='Understanding what you said…' if self.transcribing else 'Peek is thinking…'
            self.publish(**values)

    def stop(self):
        self.invalidate_input()
        with self.guard:self.feedback.finish()
        self.companion.generation+=1;self.correction_paused=False
        if self.prefs['asrModel']=='voxtype':self.want_listen=False
        self.pending='';self.bridge.cancelled.set();self.send_worker({'action':'cancel','input':True})
        self.send_worker({'action':'engaged','enabled':False})
        if self.control and self.control.poll() is None:
            try:control_request(self.socket,{'op':'_stop'})
            except (OSError,RuntimeError):pass
        if self.enabled:self.publish(stage='listening' if self.state['listening'] else 'idle',caption='Stopped',speaking=False,outputLevel=0,
                                     task=self.task.finish('stopped'),taskCaption='Stopped',actionTarget=None,completedAt=0)

    def say(self,segments):
        if not self.enabled or self.prefs['muted']:return
        with self.guard:
            for text in segments:
                self.feedback.spoken(time.monotonic())
                self.send_worker({'action':'speak','text':text,'turn':self.turn})

    def observe(self,event):
        if not self.enabled:return
        kind=event.get('type')
        if kind=='delta':
            with self.guard:
                if event.get('text','')!=self.speech.text:self.last_delta=time.monotonic()
                if not self.bridge.cancelled.is_set():
                    self.say(self.speech.feed(event.get('text','')))
                else:
                    # Keep the Markdown cursor current after stopping.
                    self.speech.feed(event.get('text',''))
            tools=event.get('tools',[])
            self.task.tools(tools)
            self.publish(task=self.task.snapshot(),taskCaption=self.task.snapshot()['label'])
            with self.guard:self.feedback.tools(tools)
            if any(t.get('status')=='running' for t in tools) and not self.state['speaking'] and not self.bridge.ui_requests:
                tool=next(t for t in reversed(tools) if t.get('status')=='running')
                self.publish(stage='acting',caption='Using '+tool.get('name','a tool')+'…')
            else:self.refresh_activity()
        elif kind=='agent_ui':
            if event.get('requests'):
                request=event['requests'][0]
                self.send_worker({'action':'cancel'})
                self.publish(stage='needs_input',caption=request.get('title') or request.get('message','Your input is needed'))
                if not self.bridge.cancelled.is_set():self.say([request.get('title','Your input is needed.')])
            else:self.refresh_activity()
        elif kind=='state':
            busy=event.get('busy',False)
            current_id=(event.get('current') or {}).get('id','')
            if not busy and not self.was_busy and current_id!=self.task_chat:
                self.task_chat=current_id;self.task.begin('')
                self.publish(task=self.task.snapshot(),taskCaption='',completedAt=0,actionTarget=None)
            if self.was_busy and not busy:
                with self.guard:self.feedback.finish()
                self.send_worker({'action':'clear_status'})
                self.send_worker({'action':'engaged','enabled':False})
                try:self.configure_control(False)
                except (OSError,RuntimeError):pass
                self.bridge.emit(type='peek_pointer',pointer={'visible':False})
                self.companion.publish()
                current=event.get('current') or {};messages=current.get('messages',[])
                reply=messages[-1] if messages else {}
                self.task.tools(reply.get('tools',[]))
                outcome=self.task.finish('stopped' if self.bridge.cancelled.is_set() else reply.get('status','complete'))
                self.publish(task=outcome,taskCaption=outcome['label'],actionTarget=None,
                             completedAt=time.time() if outcome['state']=='verified' else 0)
                if reply.get('status')=='complete':
                    with self.guard:
                        if not self.bridge.cancelled.is_set():self.say(self.speech.feed(reply.get('text',''),final=True))
                    self.publish(gazeX=0,gazeY=0)
                elif reply.get('status')=='error':
                    self.send_worker({'action':'cancel'})
                    self.publish(error=reply.get('error','The agent could not finish.'),stage='error')
                    if not self.bridge.cancelled.is_set():self.say(["I couldn't finish that. The details are in the chat."])
                if self.pending:
                    pending,self.pending=self.pending,''
                    threading.Thread(target=self.submit_voice,args=(pending,),daemon=True).start()
            self.was_busy=busy
            self.refresh_activity()

    def submit_voice(self,text,generation=None):
        if not self.enabled or not text.strip():return
        try:
            with self.bridge.lock:
                if not self.enabled or (generation is not None and generation!=self.input_generation):return
                local=self.companion.match(text)
                if local and local[0] in ('stop','sleep'):
                    if local[0]=='sleep':
                        self.dispatch({'action':'peek_standby'})
                        self.bridge.emit(type='peek_hide')
                    else:self.stop()
                    return
                if self.prefs['bargeIn'] or not self.bridge.busy:
                    self.send_worker({'action':'cancel','hold':bool(self.user_speaking or self.input_pending)})
                    with self.guard:self.speech.feed(self.speech.text,final=True)
                requests=self.bridge.ui_requests
                if requests:
                    r=requests[0];answer=text.strip().lower().strip('.!?')
                    if r['method']=='confirm' and answer in ('yes','approve','confirm','no','deny','cancel'):
                        self.bridge.answer_ui({'id':r['id'],'confirmed':answer in ('yes','approve','confirm')});return
                    if r['method']=='select':
                        matches=[v for v in r.get('options',[]) if v.lower()==answer]
                        if len(matches)==1:self.bridge.answer_ui({'id':r['id'],'value':matches[0]});return
                    self.publish(caption='Please answer the pending question using its controls.',stage='needs_input');return
                if self.bridge.busy:
                    if self.prefs['bargeIn']:self.steer(text)
                    else:self.pending=(self.pending+'\n'+text).strip();self.publish(caption='I’ll take that next.',taskCaption='Follow-up queued')
                    return
                self.bridge.send({'text':text,'attachments':[]})
        except Exception as exc:
            self.abort_turn();self.publish(error=str(exc),stage='error')

    def steer(self,text):
        """Queue a correction in the native turn, retaining completed tool work."""
        self.send_worker({'action':'cancel','hold':bool(self.user_speaking or self.input_pending)})
        rpc=self.bridge.rpc
        agent=(self.bridge.current or {}).get('agent')
        prompt='User correction to the running task. Preserve completed work and adjust the remaining steps: '+text
        try:
            if not rpc or agent not in ('omp','pi','codex'):raise ValueError('Adapter requires a follow-up turn')
            rpc.request('steer',message=prompt,timeout=5)
            reply=self.bridge.current['messages'][-1]
            reply.setdefault('steering',[]).append({'text':text,'time':time.time()})
            self.bridge.save(self.bridge.current)
            self.bridge.snapshot()
            if self.input_pending:
                self.send_worker({'action':'cancel','hold':True})
                with self.guard:self.speech.feed(self.speech.text,final=True)
            self.resume_input()
            self.publish(caption='Adjusting: '+text,taskCaption=text,stage='thinking')
        except Exception:
            # Unsupported adapters interrupt and continue the same native session.
            self.pending=prompt;self.bridge.cancelled.set()
            self.publish(caption='Continuing this session with your correction…')

    def try_local(self,text):
        if not self.enabled:return False
        match=self.companion.match(text)
        if not match:return False
        if match[0] in ('stop','sleep'):
            self.submit_voice(text);return True
        chat=self.bridge.current
        self.begin_turn()
        now=time.time()
        if not chat['messages']:chat['title']=' '.join(text.split())[:64]
        chat['draft']=''
        chat['messages'] += [{'role':'user','text':text,'attachments':[],'status':'complete','time':now,'local':True},
                             {'role':'assistant','text':'','status':'streaming','time':now+.001,'local':True,'model':'Local command'}]
        reply=chat['messages'][-1]
        self.bridge.busy=True;self.bridge.cancelled.clear();self.bridge.save(chat);self.bridge.snapshot()
        def execute():
            try:
                result=self.companion.execute(match)
                reply.update(text=result,status='complete')
                if match[0] not in ('remember','forget','memories'):
                    self.companion.store.activity(text,result)
            except Exception as exc:reply.update(text='',error=str(exc),status='error')
            finally:
                with self.bridge.lock:
                    if self.bridge.cancelled.is_set():reply['status']='stopped'
                    try:self.configure_control(False)
                    except (OSError,RuntimeError):pass
                    chat['updated']=time.time();self.bridge.busy=False;self.bridge.save(chat);self.bridge.snapshot()
        self.bridge.worker=threading.Thread(target=execute,daemon=True);self.bridge.worker.start()
        return True

    def voice_event(self,e):
        if not self.enabled:return
        kind=e.get('type')
        if 'generation' in e and e['generation']!=self.input_generation:return
        if 'utterance' in e:self.input_utterance=max(self.input_utterance,e['utterance'])
        if kind=='ready':
            self.input_utterance=0
            self.publish(ready=True,stage='idle',caption='Ready when you are',devices=e.get('devices',[]))
            self.send_worker(dict(self.prefs,action='settings'))
            self.send_worker({'action':'invalidate_input','generation':self.input_generation})
            self.send_worker({'action':'listen','enabled':self.want_listen})
            self.refresh_activity()
        elif kind=='microphone':
            if e.get('failed'):self.want_listen=False
            finalizing=not e['active'] and e.get('finishing') is True
            if not e['active']:
                self.user_speaking=False;self.transcribing=finalizing
                if not finalizing:self.resume_input()
            values={'hearing':False,'transcribing':finalizing} if not e['active'] else {}
            if finalizing:values['caption']='Understanding what you said…'
            elif e['active'] and self.prefs['asrModel']=='voxtype':
                values.update(caption='Listening · toggle the microphone again to send',error='',inputNotice='',partial='')
            elif not e['active']:values['partial']=''
            self.publish(listening=e['active'],inputLevel=0,**values)
            self.refresh_activity()
        elif kind=='partial':
            self.publish(partial=e.get('text',''));self.refresh_activity()
        elif kind=='transcript':
            token=uuid.uuid4().hex
            with self.guard:self.input_pending.add(token)
            self.publish(partial='',caption=e['text'],lastHeard=e['text'],transcribing=False)
            # One consumer preserves ordering and rejects queued input after Stop.
            try:self.input_queue.put_nowait((e['text'],self.input_generation,token))
            except queue.Full:
                with self.guard:self.input_pending.discard(token)
                self.publish(inputNotice='Too many requests are waiting. Please let me catch up.',inputNoticeAt=time.time())
        elif kind=='transcribing':
            self.user_speaking=False;self.transcribing=True
            self.publish(hearing=False,transcribing=True,caption='Understanding what you said…')
            self.refresh_activity()
        elif kind=='input_notice':
            self.publish(inputNotice=e['text'],inputNoticeAt=time.time(),caption=e['text'])
        elif kind=='speech_start':
            if not self.prefs['bargeIn'] and (self.state['speaking'] or self.bridge.busy):return
            self.user_speaking=True
            self.transcribing=False
            self.send_worker({'action':'pause_speech','generation':e.get('generation',self.input_generation),'utterance':e.get('utterance',self.input_utterance)})
            if self.bridge.busy and not self.bridge.ui_requests:
                self.correction_paused=True
                if self.control:control_request(self.socket,{'op':'_pause'})
            self.publish(stage='listening',hearing=True,transcribing=False,inputNotice='')
        elif kind=='utterance_end':
            self.user_speaking=False;self.transcribing=False
            self.publish(hearing=False,transcribing=False)
            if e.get('hadSpeech') and not e.get('recognized') and not e.get('limited') and not self.bridge.busy:
                self.publish(inputNotice='I didn’t catch that. Please try again.',inputNoticeAt=time.time())
            self.resume_input()
        elif kind=='standby':self.publish(standby=e['active']);self.refresh_activity()
        elif kind=='wake':
            self.publish(standby=False,caption='I’m listening',stage='listening')
            self.bridge.emit(type='peek_wake')
        elif kind=='level':self.publish(inputLevel=e['input'])
        elif kind=='output_level':self.publish(outputLevel=e['level'])
        elif kind=='playback':
            if e.get('turn') and e['turn']!=self.turn:return
            if e.get('turn')==self.turn and self.turn:
                with self.guard:self.feedback.spoken(time.monotonic())
            values={'speaking':e['active'],'outputLevel':0}
            if e['active'] and not e.get('resumed') and e.get('text')!='__peek_chime__':values['caption']=e.get('text','')
            self.publish(**values)
            self.refresh_activity()
        elif kind=='error':self.publish(error=e['text'],stage='error')

    def control_event(self,e):
        if not self.enabled or (e.get('turn') and e['turn']!=self.turn):return
        kind=e.get('type')
        if kind in ('pointer','control_action') and self.task.state!='running':return
        if kind=='pointer':
            self.bridge.emit(type='peek_pointer',pointer=e)
            if e.get('visible'):
                self.publish(actionTarget={'x':e['x'],'y':e['y'],'at':time.time()} if 'x' in e and 'y' in e else None,
                             gazeX=max(-1,min(1,e.get('gazeX',.6))),gazeY=max(-1,min(1,e.get('gazeY',-.15))),
                             **({'taskCaption':e['targetName']} if e.get('targetName') else {}))
        elif kind=='control_action':
            if self.enabled:
                step_state='running' if e['phase']=='start' else 'failed' if e['phase']=='error' else 'verified' if e.get('verified') else 'observed' if e.get('kind')=='observation' else 'performed'
                self.task.record(e['id'],e.get('label',e['operation'].replace('_',' ').capitalize()),
                                 kind=e.get('kind','action'),state=step_state,evidence=e.get('evidence',''))
                self.publish(task=self.task.snapshot(),taskCaption=self.task.snapshot()['label'])
                if e['phase']=='start' and not self.state['speaking'] and not self.bridge.ui_requests:
                    self.publish(stage='acting',caption=e.get('label',e['operation'].replace('_',' ').capitalize())+'…')
                else:self.refresh_activity()
        elif kind=='emergency_stop':self.stop()
        elif kind=='control_stopped':
            self.bridge.emit(type='peek_pointer',pointer={'visible':False})
            if self.enabled:self.publish(caption=e.get('reason','Stopped'),actionTarget=None)

    def close(self):
        self.feedback_stop.set();self.feedback_thread.join(timeout=1)
        self.invalidate_input();self.input_thread.join(timeout=6)
        self.companion.close()
        self.closed=True;self.enable(False)
        proc,self.control=self.control,None
        if proc:
            proc.terminate()
            try:proc.wait(timeout=2)
            except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=1)
        self.socket.unlink(missing_ok=True)
