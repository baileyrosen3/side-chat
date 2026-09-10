#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Standard stdio MCP transport for the same Peek computer broker."""
import json,os,sys,threading
sys.dont_write_bytecode=True  # Plugin file changes trigger a live Omarchy reload.
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from peek.control import request
SCHEMA=json.loads(Path(__file__).with_name('tool-schema.json').read_text())
DESCRIPTION='Control the computer visibly through Peek. Use windows, focus, then screenshot. Input requires the returned fresh frame ID; x/y and toX/toY are screenshot pixels. Re-observe after actions. key accepts Ctrl+l or Return; type supports Unicode. browser args is an array of agent-browser CLI arguments following the selected mode. DESKTOP: open URL launches the visible default Omarchy browser; then use native screenshot/mouse/keyboard. BROWSER: isolated headless Chromium supports open URL, snapshot -i, click @e1, fill @e2 text, press Enter. Never use a separate hidden browser in Desktop mode. Prefer inspect_app for accessible app controls, then accessible_action with returned target and actionName (or text for an editable target). Targets expire; re-inspect after acting. If no accessibility tree is exposed, use screenshots and native input. For small user config edits use config_read(path) then config_write(path,text,expected=sha256 returned by read). This verifies and records an undo point; undo_list and undo_restore(id) restore only when the file has not changed since. Stop and user takeover invalidate pending desktop input. Peek must be enabled.'
lock=threading.Lock()
def emit(message):
 with lock:print(json.dumps(message),flush=True)
def handle(message):
 identity=message.get('id');method=message.get('method');params=message.get('params',{})
 try:
  if method=='initialize':result={'protocolVersion':params.get('protocolVersion','2024-11-05'),'capabilities':{'tools':{}},'serverInfo':{'name':'side-chat-peek','version':'1.4.0'}}
  elif method=='ping':result={}
  elif method=='tools/list':result={'tools':[{'name':'computer','description':DESCRIPTION,'inputSchema':SCHEMA}]}
  elif method=='tools/call':
   if params.get('name')!='computer':raise ValueError('Unknown tool')
   command=dict(params.get('arguments') or {})
   if command.get('op') not in SCHEMA['properties']['op']['enum']:raise ValueError('Unknown computer operation')
   command['callId']=str(identity)
   try:
    data=request(os.environ['SIDE_CHAT_CONTROL_SOCKET'],command)
    result={'content':data['content']} if 'content' in data else {'content':[{'type':'text','text':json.dumps(data)}]}
   except Exception as exc:result={'content':[{'type':'text','text':str(exc)}],'isError':True}
  elif method and method.startswith('notifications/'):
   if method=='notifications/cancelled':
    try:request(os.environ['SIDE_CHAT_CONTROL_SOCKET'],{'op':'_stop'})
    except Exception:pass
   return
  else:
   emit({'jsonrpc':'2.0','id':identity,'error':{'code':-32601,'message':'Unsupported method'}});return
  if identity is not None:emit({'jsonrpc':'2.0','id':identity,'result':result})
 except Exception as exc:
  if identity is not None:emit({'jsonrpc':'2.0','id':identity,'error':{'code':-32602,'message':str(exc)}})
if __name__=='__main__':
 for line in sys.stdin:
  try:
   message=json.loads(line)
   if message.get('method')=='tools/call':threading.Thread(target=handle,args=(message,),daemon=True).start()
   else:handle(message)
  except ValueError:pass
