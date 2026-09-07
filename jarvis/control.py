#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Local, observable desktop actions; JSON CLI client and a private Unix-socket broker."""
import argparse
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import re
import selectors
import signal
import socket
import socketserver
import struct
import subprocess
import sys
import threading
import time
import uuid
from urllib.parse import urlsplit
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def run(argv, timeout=12, **kwargs):
    result=subprocess.run(argv,capture_output=True,timeout=timeout,**kwargs)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors='replace')[-1000:] or 'Command failed: '+argv[0])
    return result.stdout


def hypr(kind):
    return json.loads(run(['hyprctl',kind,'-j']))


def topology(monitors):
    return [(m['name'],m['x'],m['y'],m['width'],m['height'],m['scale'],m['transform']) for m in monitors]


def bounds(monitor):
    w,h=monitor['width'],monitor['height']
    if monitor.get('transform',0)%2:w,h=h,w
    return monitor['x'],monitor['y'],w/monitor['scale'],h/monitor['scale']


def point(frame,x,y):
    if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (x,y)):
        raise ValueError('Coordinates must be finite numbers.')
    if not (0<=x<frame['width'] and 0<=y<frame['height']):
        raise ValueError('Target lies outside this screenshot.')
    left,top,width,height=frame['bounds']
    return round(left+x*width/frame['width']),round(top+y*height/frame['height'])


class Control:
    def __init__(self, emit=print):
        self.emit=emit
        self.enabled=False
        self.epoch=0
        self.guard=threading.Lock()
        self.action_lock=threading.Lock()
        self.frames={}
        self.device=None
        self.active=False
        self.scope='desktop'
        self.turn=''
        self.accent='#a0a0b8'
        self.quit=threading.Event()
        self.browser_session='jarvis-'+uuid.uuid4().hex[:12]
        self.browser_started=False
        self.cwd=str(Path.home());self.accessible_frames={};self.journal=None
        self.data=Path(os.environ.get('SIDE_CHAT_DATA',Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))/'side-chat'))
        self.process=None
        self.watcher=threading.Thread(target=self.watch_input,daemon=True)
        self.watcher.start()

    def event(self,kind,**values):
        self.emit(dict(type=kind,turn=self.turn,**values))

    def stop(self,reason='Stopped'):
        with self.guard:
            self.enabled=False;self.epoch+=1;self.frames.clear()
            if self.process and self.process.poll() is None:self.process.terminate()
            if self.device:
                import evdev
                for code in (evdev.ecodes.BTN_LEFT,evdev.ecodes.BTN_RIGHT,evdev.ecodes.BTN_MIDDLE):
                    try:self.device.write(evdev.ecodes.EV_KEY,code,0)
                    except OSError:pass
                self.device.syn()
        self.event('control_stopped',reason=reason)

    def check(self,epoch):
        if not self.enabled or self.epoch!=epoch:raise RuntimeError('Desktop control stopped. Wait for a new user request.')

    def watch_input(self):
        # Read key state only for takeover/Stop; never store or emit keystrokes.
        try:import evdev
        except ImportError:return
        selector=selectors.DefaultSelector();last_scan=0;pressed=set()
        try:
            while not self.quit.is_set():
                if time.monotonic()-last_scan>3:
                    known={key.fileobj.path for key in selector.get_map().values()}
                    for path in evdev.list_devices():
                        if path in known:continue
                        try:
                            device=evdev.InputDevice(path)
                            if device.name.startswith('Side Chat Jarvis'):
                                device.close();continue
                            selector.register(device,selectors.EVENT_READ)
                        except OSError:pass
                    last_scan=time.monotonic()
                for key,_ in selector.select(.05):
                    device=key.fileobj
                    try:
                        for event in device.read():
                            if event.type==evdev.ecodes.EV_KEY:
                                identity=(device.path,event.code)
                                if event.value:pressed.add(identity)
                                else:pressed.discard(identity)
                                codes={code for _,code in pressed}
                                if event.code==evdev.ecodes.KEY_ESC and event.value==1 and codes & {29,97} and codes & {56,100}:
                                    self.stop('Emergency stop · Ctrl+Alt+Esc');self.event('emergency_stop')
                                elif self.active and event.value==1:
                                    self.stop('You took control')
                            elif self.active and event.type in (evdev.ecodes.EV_REL,evdev.ecodes.EV_ABS) and event.code in (0,1):
                                self.stop('You moved the mouse')
                    except (OSError,BlockingIOError):
                        selector.unregister(device);device.close()
        finally:
            for key in list(selector.get_map().values()):key.fileobj.close()
            selector.close()

    def mouse(self):
        if not self.device:
            import evdev
            e=evdev.ecodes
            self.device=evdev.UInput({e.EV_KEY:[e.BTN_LEFT,e.BTN_RIGHT,e.BTN_MIDDLE],e.EV_REL:[e.REL_X,e.REL_Y,e.REL_WHEEL,e.REL_HWHEEL]},name='Side Chat Jarvis pointer')
            time.sleep(.15)
        return self.device

    def move(self,x,y,epoch):
        self.check(epoch)
        run(['hyprctl','dispatch',f'hl.dsp.cursor.move({{ x = {int(x)}, y = {int(y)} }})'])
        self.event('pointer',x=x,y=y,phase='move',visible=True)

    def frame(self,identity,epoch,focus=False):
        self.check(epoch)
        frame=self.frames.get(identity)
        if not frame or time.monotonic()-frame['time']>30:
            raise ValueError('Screenshot expired. Take a fresh screenshot before acting.')
        if topology(hypr('monitors'))!=frame['topology']:
            raise ValueError('Displays changed. Take a fresh screenshot.')
        active=hypr('activewindow')
        if active.get('address')!=frame['window'].get('address') or active.get('at')!=frame['window'].get('at') or active.get('size')!=frame['window'].get('size'):
            raise ValueError('Window focus or geometry changed. Take a fresh screenshot.')
        return frame

    def screenshot(self,c):
        monitors=hypr('monitors');name=c.get('screen')
        monitor=next((m for m in monitors if m['name']==name),None) if name else next((m for m in monitors if m.get('focused')),monitors[0])
        if not monitor:raise ValueError('Unknown monitor. Call windows to list displays.')
        self.event('pointer',visible=False,phase='capture')
        time.sleep(.075)
        scale=min(1,1280/max(bounds(monitor)[2:]))
        png=run(['grim','-o',monitor['name'],'-s',str(scale),'-'])
        width,height=struct.unpack('>II',png[16:24])
        identity=uuid.uuid4().hex
        frame={'id':identity,'screen':monitor['name'],'width':width,'height':height,'bounds':bounds(monitor),
               'topology':topology(monitors),'window':hypr('activewindow'),'time':time.monotonic()}
        self.frames={k:v for k,v in self.frames.items() if time.monotonic()-v['time']<30}
        self.frames[identity]=frame
        details={k:frame[k] for k in ('id','screen','width','height','bounds')}
        details['window']=frame['window'].get('address','')
        return {'content':[{'type':'text','text':json.dumps(details)+'\nUse these screenshot pixel coordinates and frame ID for actions.'},
                           {'type':'image','mimeType':'image/png','data':base64.b64encode(png).decode()}], 'details':details}

    def browser(self,c,epoch):
        args=c.get('args',[])
        allowed={'open','snapshot','click','dblclick','fill','type','press','keydown','keyup','scroll','scrollintoview','get','back','forward','reload','tab','select','check','uncheck','hover','wait','find','download','upload','screenshot','close'}
        if not isinstance(args,list) or not args or args[0] not in allowed or not all(isinstance(x,str) for x in args):
            raise ValueError('Supply a supported agent-browser command as an argument array.')
        if self.scope=='desktop':
            if args[0]!='open' or len(args)!=2:
                raise ValueError('Desktop mode uses your visible default Omarchy browser. Use browser args=["open", "https://…"] to launch it; use windows, focus, screenshot and native input for everything else. Headless DOM commands require Browser mode.')
            url=args[1]
            if urlsplit(url).scheme not in ('http','https') or not urlsplit(url).netloc or any(ord(ch)<32 for ch in url):
                raise ValueError('Supply a complete http:// or https:// URL.')
            env=dict(os.environ);env.pop('BROWSER',None)
            default=run(['xdg-settings','get','default-web-browser'],env=env).decode().strip()
            self.check(epoch)
            run(['omarchy','launch','browser',url],timeout=15)
            self.check(epoch)
            return {'scope':'desktop','requestedUrl':url,'defaultBrowser':default,'launched':True,
                    'activeWindow':hypr('activewindow'),
                    'next':'The URL was sent to the visible default browser. Use windows and screenshot to verify the page; launch success alone does not confirm it loaded. Continue with native mouse/keyboard input.'}
        reserved={'--headed','--headless','--session','--profile','--executable-path','--cdp','--auto-connect','--args','--config','--provider','-p','--extension','--extensions','--namespace','--engine','--state','--restore','--session-name','--init-script','--enable','--device'}
        if any(arg.split('=',1)[0] in reserved for arg in args):
            raise ValueError('Browser mode owns its headless session and launch options. Supply only the page command and its arguments.')
        binary=self.data/'bin/agent-browser'
        env={k:v for k,v in os.environ.items() if not k.startswith('AGENT_BROWSER_')}
        env.update(AGENT_BROWSER_EXECUTABLE_PATH='/usr/bin/chromium',AGENT_BROWSER_SESSION=self.browser_session,
                 AGENT_BROWSER_HEADED='false',AGENT_BROWSER_CONTENT_BOUNDARIES='true',
                 AGENT_BROWSER_ARGS='--class=org.omarchy.jarvis.browser')
        # An explicit empty config prevents a user's global --headed/CDP settings leaking in.
        config=self.data/'browser-headless.json'
        if not config.exists():config.write_text('{"headed":false}')
        base=[str(binary),'--config',str(config),'--session',self.browser_session,'--executable-path','/usr/bin/chromium','--json']
        if args[0] in ('click','dblclick','fill','type','hover','check','uncheck','select') and len(args)>1:
            try:
                box=json.loads(run(base+['get','box',args[1]],env=env,timeout=8))['data']
                x=float(box['x'])+float(box['width'])/2;y=float(box['y'])+float(box['height'])/2
                if math.isfinite(x) and math.isfinite(y):
                    # DOM coordinates stay accurate even with browser zoom or emulated viewports.
                    script="(()=>{document.getElementById('__side_chat_jarvis_pointer')?.remove();const p=document.createElement('div');p.id='__side_chat_jarvis_pointer';p.setAttribute('aria-hidden','true');p.textContent='AI';p.style.cssText="+json.dumps(f'position:fixed;left:{x}px;top:{y}px;z-index:2147483647;pointer-events:none;border:2px solid {self.accent};border-radius:50%;width:24px;height:24px;transform:translate(-50%,-50%);color:{self.accent};background:#202025cc;font:600 9px monospace;display:grid;place-items:center;box-shadow:0 0 0 6px {self.accent}33;')+";document.documentElement.appendChild(p);setTimeout(()=>p.remove(),3000);return true})()"
                    run(base+['eval',script],env=env,timeout=8)
            except (OSError,ValueError,KeyError,RuntimeError,subprocess.SubprocessError):pass
        if args[0]=='screenshot':
            try:run(base+['eval',"document.getElementById('__side_chat_jarvis_pointer')?.remove()"],env=env,timeout=5)
            except (OSError,RuntimeError,subprocess.SubprocessError):pass
        self.check(epoch)
        # Only Browser mode reaches this isolated headless session.
        proc=subprocess.Popen(base+args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
        self.browser_started=args[0]!='close'
        self.process=proc
        try:
            out,err=proc.communicate(timeout=35)
            self.check(epoch)
            if proc.returncode:raise RuntimeError(err.decode(errors='replace')[-1200:] or out.decode(errors='replace')[-1200:])
            result=json.loads(out)
            if result.get('success') is False:raise RuntimeError(str(result.get('error','Browser action failed.')))
            if args[0]=='screenshot':
                path=result.get('data',{}).get('path')
                if path and Path(path).is_file():
                    content=Path(path).read_bytes()
                    if len(content)<5_000_000:return {'content':[{'type':'image','mimeType':'image/png','data':base64.b64encode(content).decode()}]}
            return {'result':out.decode(errors='replace')[-80000:]}
        finally:
            if proc.poll() is None:proc.kill();proc.wait()
            self.process=None

    def handle(self,c):
        op=c.get('op')
        if op=='_configure':
            new_scope=c.get('scope','desktop')
            if new_scope not in ('desktop','browser'):raise ValueError('Unknown computer control mode.')
            if new_scope!=self.scope:self.close_browser()
            with self.guard:
                self.enabled=c.get('enabled') is True
                self.scope=new_scope;self.turn=c.get('turn','')
                self.cwd=str(c.get('cwd') or self.cwd)
                if re.fullmatch(r'#[0-9a-fA-F]{6}',c.get('accent','')):self.accent=c['accent']
                if not self.enabled:self.epoch+=1;self.frames.clear()
            return {'enabled':self.enabled,'scope':self.scope}
        if op=='_stop':self.stop();return {'stopped':True}
        if op=='_pause':self.stop('Listening for your correction');return {'paused':True}
        if op=='capabilities':return {'enabled':self.enabled,'scope':self.scope,'desktop':os.access('/dev/uinput',os.W_OK),'browser':(self.data/'bin/agent-browser').is_file(),'takeover':True,'stopShortcut':'Ctrl+Alt+Esc'}
        with self.action_lock:
            epoch=self.epoch;self.check(epoch)
            if self.scope=='browser' and op not in ('browser','windows'):
                raise ValueError('This task is scoped to the independent browser. Select Current desktop to operate host apps.')
            identity=c.get('callId') or uuid.uuid4().hex
            self.event('control_action',id=identity,operation=op,phase='start')
            self.active=op in ('move','click','drag','scroll','type','key','accessible_action')
            try:
                result=self.execute(c,epoch)
                self.event('control_action',id=identity,operation=op,phase='complete')
                return result
            except Exception as exc:
                self.event('control_action',id=identity,operation=op,phase='error',error=str(exc));raise
            finally:self.active=False

    def execute(self,c,epoch):
        import evdev
        e=evdev.ecodes;op=c.get('op')
        if op=='windows':return {'windows':[{k:w.get(k) for k in ('address','title','class','at','size','monitor','workspace')} for w in hypr('clients')], 'monitors':topology(hypr('monitors'))}
        if op=='screenshot':return self.screenshot(c)
        if op=='browser':return self.browser(c,epoch)
        if op in ('inspect_app','accessible_action'):return self.accessibility(c,epoch)
        if op in ('config_read','config_write','undo_list','undo_restore'):
            from jarvis.undo import UndoJournal
            if self.journal is None:
                folder=Path(os.environ.get('SIDE_CHAT_COMPANION_STATE',self.data/'control-state'))
                folder.mkdir(parents=True,exist_ok=True,mode=0o700);self.journal=UndoJournal(folder)
            self.check(epoch)
            if op=='config_read':return self.journal.read(c.get('path',''),self.cwd)
            if op=='config_write':return self.journal.write(c.get('path',''),self.cwd,c.get('text',''),c.get('expected',''))
            if op=='undo_list':return {'restorePoints':self.journal.list()}
            return self.journal.restore(c.get('id',''),self.cwd)
        if op=='focus':
            address=c.get('window','')
            if not re.fullmatch(r'0x[0-9a-fA-F]+',address):raise ValueError('Use the exact window address returned by windows.')
            if address not in {w['address'] for w in hypr('clients')}:raise ValueError('Window no longer exists.')
            self.check(epoch)
            run(['hyprctl','dispatch','hl.dsp.focus({ window = "address:'+address+'" })'])
            return {'focused':hypr('activewindow').get('address'),'next':'Take a screenshot before input.'}
        frame=self.frame(c.get('frame'),epoch)
        if op in ('move','click','drag','scroll'):
            x,y=point(frame,c.get('x'),c.get('y'))
            self.move(x,y,epoch)
            device=self.mouse();self.check(epoch)
            button={'left':e.BTN_LEFT,'right':e.BTN_RIGHT,'middle':e.BTN_MIDDLE}.get(c.get('button','left'))
            if button is None:raise ValueError('Unknown mouse button.')
            if op=='click':
                for _ in range(min(2,max(1,int(c.get('count',1))))):
                    self.check(epoch);device.write(e.EV_KEY,button,1);device.syn()
                    try:time.sleep(.05)
                    finally:device.write(e.EV_KEY,button,0);device.syn()
                    time.sleep(.075)
                self.event('pointer',x=x,y=y,visible=True,phase='click')
            elif op=='drag':
                endx,endy=point(frame,c.get('toX'),c.get('toY'))
                device.write(e.EV_KEY,button,1);device.syn()
                try:
                    for n in range(1,19):
                        self.move(round(x+(endx-x)*n/18),round(y+(endy-y)*n/18),epoch);time.sleep(.018)
                finally:device.write(e.EV_KEY,button,0);device.syn()
            elif op=='scroll':
                amount=max(-12,min(12,int(c.get('amount',-3))))
                device.write(e.EV_REL,e.REL_HWHEEL if c.get('horizontal') else e.REL_WHEEL,amount);device.syn()
            return {'performed':op,'x':x,'y':y,'next':'Observe again before another action.'}
        if op in ('type','key'):
            args=['wtype']
            if op=='type':args+=['--',str(c.get('text',''))[:10000]]
            else:
                keys=str(c.get('key','')).split('+');mods=keys[:-1];key=keys[-1]
                mapping={'ctrl':'ctrl','alt':'alt','shift':'shift','super':'logo','meta':'logo'}
                if any(m.lower() not in mapping for m in mods) or not re.fullmatch(r'[A-Za-z0-9_]+',key):raise ValueError('Use a shortcut such as Ctrl+l or Return.')
                for m in mods:args+=['-M',mapping[m.lower()]]
                args+=['-k',key]
                for m in reversed(mods):args+=['-m',mapping[m.lower()]]
            self.check(epoch)
            self.process=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            try:
                out,err=self.process.communicate(timeout=8);self.check(epoch)
                if self.process.returncode:raise RuntimeError(err.decode(errors='replace'))
            finally:
                if self.process.poll() is None:self.process.kill();self.process.wait()
                self.process=None
            return {'performed':op,'next':'Observe again before another action.'}
        raise ValueError('Unknown desktop operation.')

    def accessibility(self,c,epoch):
        window=hypr('activewindow')
        if not window.get('pid'):raise ValueError('Focus an app first.')
        query={'pid':window['pid']}
        if c['op']=='accessible_action':
            saved=self.accessible_frames.get(c.get('target'))
            if not saved or time.monotonic()-saved['time']>20 or saved['epoch']!=epoch or saved['window']!=window['address']:
                raise ValueError('Accessible target expired or focus changed. Inspect the app again.')
            query.update(target=saved['node'],action=c.get('actionName'),text=c.get('text',''))
            b=saved['node'].get('bounds')
            if b:
                x=window['at'][0]+b[0]+b[2]/2;y=window['at'][1]+b[1]+b[3]/2
                self.event('pointer',x=x,y=y,visible=True,phase='click',targetName=saved['node']['name'],bounds={'x':x-b[2]/2,'y':y-b[3]/2,'width':b[2],'height':b[3]},gazeX=2*(b[0]+b[2]/2)/max(1,window['size'][0])-1,gazeY=2*(b[1]+b[3]/2)/max(1,window['size'][1])-1)
        self.check(epoch)
        helper=subprocess.run(['/usr/bin/python3','-B',str(Path(__file__).with_name('accessibility.py'))],input=json.dumps(query),capture_output=True,text=True,timeout=6)
        try:result=json.loads(helper.stdout)
        except ValueError:raise ValueError('App accessibility is unavailable. Use a screenshot and native input.')
        self.check(epoch)
        if result.get('error'):raise ValueError(result['error'])
        if c['op']=='inspect_app':
            self.accessible_frames={}
            for node in result['nodes']:
                identity=uuid.uuid4().hex
                self.accessible_frames[identity]={'node':dict(node),'window':window['address'],'epoch':epoch,'time':time.monotonic()}
                node['target']=identity
            result['window']=window['address']
        else:self.accessible_frames.clear()
        return result

    def close_browser(self):
        if self.browser_started:
            try:run([str(self.data/'bin/agent-browser'),'--session',self.browser_session,'close'],timeout=5)
            except (OSError,RuntimeError,subprocess.SubprocessError):pass
            self.browser_started=False

    def close(self):
        self.quit.set();self.stop()
        self.close_browser()
        if self.device:self.device.close()
        self.watcher.join(timeout=.5)


def request(path,command):
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
        client.settimeout(45);client.connect(str(path));client.sendall(json.dumps(command).encode()+b'\n')
        line=client.makefile('rb').readline(8_000_000)
        if not line:raise RuntimeError('Desktop service disconnected.')
        result=json.loads(line)
        if result.get('error'):raise RuntimeError(result['error'])
        return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--serve');parser.add_argument('--socket',default=os.environ.get('SIDE_CHAT_CONTROL_SOCKET'))
    parser.add_argument('command',nargs='?');args=parser.parse_args()
    os.umask(0o077)
    if not args.serve:
        try:print(json.dumps(request(args.socket,json.loads(args.command))))
        except Exception as exc:print(json.dumps({'error':str(exc)}));return 1
        return 0
    path=Path(args.serve);path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    output=threading.Lock()
    def emit(event):
        with output:
            try:print(json.dumps(event),flush=True)
            except (BrokenPipeError,OSError):sys.stdout=open(os.devnull,'w')
    control=Control(emit)
    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            try:
                _,uid,_=struct.unpack('3i',self.request.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
                if uid!=os.getuid():raise PermissionError('Different user.')
                data=self.rfile.readline(8_000_000)
                result=control.handle(json.loads(data))
            except Exception as exc:result={'error':str(exc)}
            try:self.wfile.write(json.dumps(result).encode()+b'\n')
            except BrokenPipeError:pass
    class Server(socketserver.ThreadingUnixStreamServer):daemon_threads=True
    server=Server(str(path),Handler)
    try:
        signal.signal(signal.SIGTERM,lambda *_:sys.exit(0))
        if os.environ.get('SIDE_CHAT_CONTROL_LIFELINE')=='1':
            def lifeline():
                try:
                    while os.read(sys.stdin.fileno(),1):pass
                finally:os.kill(os.getpid(),signal.SIGTERM)
            threading.Thread(target=lifeline,daemon=True).start()
        # A parent can close its pipe as soon as it sees readiness. Establish
        # cleanup before publishing it so SIGTERM cannot leave a stale socket.
        emit({'type':'control_ready'})
        server.serve_forever(poll_interval=.1)
    finally:control.close();server.server_close();path.unlink(missing_ok=True)


if __name__=='__main__':sys.exit(main())
