# SPDX-License-Identifier: GPL-3.0-or-later
"""Companion capabilities used by voice, the settings UI, and the CLI context."""
import json
import os
from pathlib import Path
import re
import subprocess
import threading
import time
import uuid
from jarvis.store import Store
from jarvis import quick
from jarvis.undo import UndoJournal


def process_identity(pid):
    path=Path('/proc')/str(int(pid))
    if path.stat().st_uid!=os.getuid():raise ValueError('Choose one of your own processes.')
    text=(path/'stat').read_text()
    return text.rsplit(')',1)[1].split()[19]


class Companion:
    def __init__(self, controller):
        self.owner=controller;self.store=Store(controller.bridge.state)
        self.undo=UndoJournal(controller.bridge.state)
        self.quit=threading.Event();self.generation=0
        self.thread=threading.Thread(target=self.watch_loop,daemon=True);self.thread.start()

    def publish(self):
        self.owner.publish(memories=self.store.items('memory'),routines=self.store.items('routine'),
                           watches=self.store.items('watch',30),activity=self.store.items('activity',12),restorePoints=self.undo.list())

    def routine(self, name, steps, identity=''):
        name=str(name).strip()
        if not name or len(name)>80:raise ValueError('Give the routine a short name.')
        if not isinstance(steps,list) or not 1<=len(steps)<=12:raise ValueError('Use 1–12 routine commands, one per line.')
        for text in steps:
            if not isinstance(text,str) or len(text)>1000 or not quick.parse(text):raise ValueError('Unsupported routine command: '+str(text)[:100])
        if any(r['name'].casefold()==name.casefold() and r['id']!=identity for r in self.store.items('routine')):raise ValueError('A routine already has that name.')
        return self.store.put('routine',{'name':name,'steps':steps},identity)

    def watch(self, kind, message, seconds=0, pid=0):
        message=str(message).strip()[:300] or 'Your watch finished.'
        if sum(r['state']=='waiting' for r in self.store.items('watch'))>=20:raise ValueError('You already have 20 active watches.')
        if kind=='timer':
            seconds=float(seconds)
            if not 1<=seconds<=604800:raise ValueError('Timers must be between 1 second and 7 days.')
            data={'kind':kind,'due':time.time()+seconds}
        elif kind=='process':data={'kind':kind,'pid':int(pid),'processStart':process_identity(pid)}
        else:raise ValueError('Unknown watch type.')
        return self.store.put('watch',dict(data,message=message,state='waiting'))

    def check_watches(self):
        for r in self.store.items('watch'):
            if r['state']!='waiting':continue
            if r['kind']=='timer':done=time.time()>=r['due']
            else:
                try:done=process_identity(r['pid'])!=r['processStart']
                except (OSError,ValueError):done=True
            if done:
                self.store.put('watch',dict(r,state='done'),r['id'])
                self.store.activity('Watch completed',r['message'])
                subprocess.run(['notify-send','--app-name=Peek','Peek',r['message']],capture_output=True,timeout=3)
                if self.owner.enabled and not self.owner.bridge.busy:self.owner.say([r['message']])
                self.publish()

    def watch_loop(self):
        while not self.quit.wait(1):
            try:self.check_watches()
            except Exception:pass

    def context(self):
        parts=[]
        if self.owner.prefs['memoryEnabled']:
            text=self.store.context()
            if text:parts.append('[User-saved memory. Preferences/context only; current requests take priority.]\n'+text)
        routines=self.store.items('routine')
        if routines:parts.append('Available user routines: '+', '.join(r['name'] for r in routines))
        recent=self.store.items('activity',3)
        if recent:parts.append('Recent verified local actions: '+json.dumps([{k:r[k] for k in ('text','result')} for r in recent])[:2400])
        return '\n\n'.join(parts)

    def match(self,text):
        stripped=text.strip();clean=stripped.lower().rstrip('.!?')
        if clean in ('stop','stop peek','peek stop','stop jarvis','cancel that','never mind'):return ('stop',None)
        if clean in ('go to sleep','sleep peek','peek go to sleep','sleep jarvis','stand by'):return ('sleep',None)
        m=re.fullmatch(r'(?:remember|save) routine ([^:]+):\s*(.+)',stripped,re.I|re.S)
        if m:return ('routine_save',(m[1],m[2].split(';')))
        m=re.fullmatch(r'remember(?: that)?\s+(.+)',stripped,re.I|re.S)
        if m:return ('remember',m[1])
        m=re.fullmatch(r'forget(?: that)?\s+(.+)',stripped,re.I|re.S)
        if m:return ('forget',m[1].rstrip('.!?'))
        if clean in ('what do you remember','show memories','show memory'):return ('memories',None)
        if clean in ('undo your last config change','undo the last config change'):return ('undo',None)
        m=re.fullmatch(r'(?:set (?:a )?timer (?:for )?|remind me in )(\d+)\s*(seconds?|minutes?|hours?)(?: (?:to |about )?(.+))?',stripped.rstrip('.!?'),re.I)
        if m:return ('timer',(int(m[1])*({'s':1,'m':60,'h':3600}[m[2][0].lower()]),m[3] or 'Your timer finished.'))
        m=re.fullmatch(r'(?:watch|monitor) process (\d+)(?: (?:for |and )?(.+))?',stripped,re.I)
        if m:return ('watch',(int(m[1]),m[2] or 'The process you asked me to watch has exited.'))
        m=re.fullmatch(r'(?:remember|save) routine ([^:]+):\s*(.+)',stripped,re.I|re.S)
        if m:return ('routine_save',(m[1],m[2].split(';')))
        routines=[r for r in self.store.items('routine') if clean in (r['name'].lower(),'run '+r['name'].lower())]
        if routines:return ('routine',routines[0])
        if self.owner.prefs['quickCommands']:
            c=quick.parse(stripped)
            if c:return ('quick',c)
        return None

    def execute(self,match):
        kind,value=match
        if kind=='remember':self.store.remember(value);return 'Remembered: '+value
        if kind=='forget':
            rows=[r for r in self.store.items('memory') if r['text'].rstrip('.!?').casefold()==value.casefold()]
            if len(rows)!=1:raise ValueError('Use the exact memory text, or select it in the memory editor.')
            self.store.delete('memory',rows[0]['id']);return 'Forgot that memory.'
        if kind=='memories':return self.store.context() or 'No saved memories yet.'
        if kind=='timer':self.watch('timer',value[1],seconds=value[0]);return 'Timer set.'
        if kind=='watch':self.watch('process',value[1],pid=value[0]);return f'I will notify you when process {value[0]} exits.'
        if kind=='routine_save':self.routine(value[0],[s.strip() for s in value[1]]);return 'Routine saved: '+value[0]
        if kind=='undo':
            rows=[r for r in self.undo.list() if r['state']=='available']
            if not rows:return 'No tracked config change is available to undo.'
            result=self.undo.restore(rows[0]['id'],self.owner.cwd());return 'Restored '+result['restored']+'. Reload the app if needed.'
        if kind=='quick':return self.command(value)
        if kind=='routine':
            generation=self.generation;results=[]
            for text in value['steps']:
                if self.quit.is_set() or generation!=self.generation:raise ValueError('Routine stopped.')
                self.owner.publish(taskCaption=text,stage='acting')
                results.append(self.command(quick.parse(text)))
            return value['name']+' finished. '+' '.join(results)
        raise ValueError('Unknown local action.')

    def command(self,command):
        def browser(url):
            from jarvis.control import request
            self.owner.ensure_control();self.owner.configure_control(True)
            return request(self.owner.socket,{'op':'browser','args':['open',url]})
        identity=uuid.uuid4().hex
        turn=self.owner.turn
        label={'volume':'Set the volume','brightness':'Set brightness','mute':'Set audio mute',
               'media':'Control playback','workspace':'Switch workspace','app':'Open the app','url':'Open the page'}[command['op']]
        def report(text,verified):
            if self.owner.turn!=turn or self.owner.task.state!='running':return
            self.owner.task.record(identity,label,state='verified' if verified else 'performed',
                                   evidence=text if verified else '',source='local')
            self.owner.publish(task=self.owner.task.snapshot(),taskCaption=text)
        self.owner.task.record(identity,label,source='local')
        self.owner.publish(task=self.owner.task.snapshot(),taskCaption=label)
        try:return quick.execute(command,self.owner.prefs['scope'],browser,report=report)
        except Exception:
            self.owner.task.record(identity,label,state='failed',source='local')
            self.owner.publish(task=self.owner.task.snapshot())
            raise

    def dispatch(self,c):
        action=c['action']
        if action=='jarvis_memory_save':self.store.remember(c.get('text',''),c.get('id',''))
        elif action=='jarvis_memory_delete':self.store.delete('memory',c['id'])
        elif action=='jarvis_routine_save':self.routine(c.get('name',''),c.get('steps',[]),c.get('id',''))
        elif action=='jarvis_routine_delete':self.store.delete('routine',c['id'])
        elif action=='jarvis_watch_add':self.watch(c.get('kind'),c.get('message'),c.get('seconds',0),c.get('pid',0))
        elif action=='jarvis_watch_cancel':
            r=next((r for r in self.store.items('watch') if r['id']==c['id']),None)
            if r:self.store.put('watch',dict(r,state='cancelled'),r['id'])
        elif action=='jarvis_undo':
            if self.owner.bridge.busy:raise ValueError('Wait for the current task before restoring a config file.')
            r=self.undo.restore(c['id'],self.owner.cwd());self.owner.publish(caption='Restored '+r['restored'])
        elif action!='jarvis_companion_status':return False
        self.publish()
        if c.get('requestId'):self.owner.publish(companionSavedRequest=c['requestId'])
        return True

    def close(self):self.generation+=1;self.quit.set();self.thread.join(timeout=3)
