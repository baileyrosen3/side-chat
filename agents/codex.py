# SPDX-License-Identifier: GPL-3.0-or-later
"""Native Codex app-server sessions, with normal config and client-handled approvals."""
import json
import os
from pathlib import Path
import queue
import signal
import subprocess
import threading
import time
import uuid
from agent_session import SessionLease,text_content,cli_binary,wait_response
from permission_modes import codex_permissions


def session_id(path):
    with open(path) as file:
        for line in file:
            obj=json.loads(line)
            if obj.get('type')=='session_meta':return obj['payload']['id']
    raise ValueError('This is not a saved Codex session.')


class CodexSession:
    def __init__(self,agent,folder,options,session_file=None,ui_callback=None):
        self.agent=agent;self.options=options;self.lease=SessionLease(folder)
        self.events=queue.Queue();self.pending={};self.ui_pending={};self.guard=threading.Lock();self.write_lock=threading.Lock()
        self.ui_callback=ui_callback;self.stderr='';self.closed=False;self.thread={};self.turn='';self.model='';self.tools={};self.failure=''
        self.peek_enabled=bool(options.get('_peek_extension'))
        env=dict(os.environ);env.pop('CLAUDECODE',None)
        self.proc=None;self.reader=None;self.err_reader=None
        try:
            self.proc=subprocess.Popen([cli_binary('codex'),'app-server','--listen','stdio://'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                       cwd=options['cwd'],env=env,start_new_session=True)
            self.reader=threading.Thread(target=self.read,daemon=True);self.err_reader=threading.Thread(target=self.read_err,daemon=True)
            self.reader.start();self.err_reader.start()
            self.call('initialize',{'clientInfo':{'name':'side_chat','title':'Omarchy Side Chat','version':'1.2.0'},'capabilities':{'experimentalApi':True}})
            self.write({'method':'initialized'})
            params={'cwd':options['cwd']}
            params.update(codex_permissions(options.get('_permission_mode','default')))
            if options.get('model'):params['model']=options['model']
            if self.peek_enabled:
                params['config']={'mcp_servers.peek':{'command':'python3','args':[str(Path(options['_peek_client']).with_name('mcp_server.py'))],
                                  'env':{'SIDE_CHAT_CONTROL_SOCKET':options['_peek_socket']},'startup_timeout_sec':10}}
                params['developerInstructions']='This session also has a local voice interface. Keep public progress and final replies concise and natural to speak. Use the Peek computer MCP tool for visible browser and desktop actions, and normal file/shell tools for config edits. Verify results before reporting success.'
            if session_file:
                if options.get('_permission_mode','default')=='default':
                    # Resume can inherit the old approval policy even when the
                    # caller omits it. Resolve the CLI's actual defaults without
                    # a model turn or a persisted scratch conversation.
                    baseline=self.call('thread/start',{'cwd':options['cwd'],'ephemeral':True},timeout=40)
                    self.default_approvals={k:baseline[k] for k in ('approvalPolicy','approvalsReviewer') if k in baseline}
                    self.call('thread/unsubscribe',{'threadId':baseline['thread']['id']})
                    params.update(self.default_approvals)
                params['threadId']=session_id(session_file)
                result=self.call('thread/resume',params,timeout=40)
            else:result=self.call('thread/start',params,timeout=40)
            self.thread=result['thread'];self.model=result.get('model','')
            if options.get('_permission_mode','default')=='default':
                self.default_approvals={k:result[k] for k in ('approvalPolicy','approvalsReviewer') if k in result}
        except Exception:self.close();raise

    def write(self,value):
        with self.write_lock:
            if self.closed:raise RuntimeError('Codex session closed.')
            self.proc.stdin.write(json.dumps(value).encode()+b'\n');self.proc.stdin.flush()

    def call(self,method,params=None,timeout=30):
        identity=uuid.uuid4().hex;waiter=queue.Queue()
        with self.guard:self.pending[identity]=waiter
        try:
            self.write({'id':identity,'method':method,'params':params or {}})
            try:response=wait_response(waiter,timeout,self.options.get('_cancel_event'))
            except queue.Empty:raise RuntimeError('Codex did not answer '+method+'. '+self.stderr[-500:])
            if response.get('error'):raise RuntimeError(str(response['error'].get('message',response['error'])))
            return response.get('result',{})
        finally:
            with self.guard:self.pending.pop(identity,None)

    def read_err(self):
        for line in self.proc.stderr:self.stderr=(self.stderr+line.decode(errors='replace'))[-12000:]

    def read(self):
        try:
            for line in self.proc.stdout:
                e=json.loads(line)
                if 'method' not in e and 'id' in e:
                    with self.guard:
                        waiter=self.pending.get(e['id'])
                        if waiter:waiter.put(e)
                elif 'id' in e:self.server_request(e)
                else:self.notification(e.get('method',''),e.get('params') or {})
        except Exception as exc:
            self.failure=str(exc)
        finally:
            with self.guard:
                for waiter in self.pending.values():waiter.put({'error':{'message':self.failure or 'Codex app-server closed.'}})
            self.events.put({'type':'session_exit','error':self.failure or 'Codex app-server closed.'})

    def server_request(self,e):
        method=e['method'];p=e.get('params') or {};identity=str(e['id'])
        if method in ('item/commandExecution/requestApproval','item/fileChange/requestApproval','execCommandApproval','applyPatchApproval'):
            self.ui_pending[identity]={'raw':e,'kind':'approval'}
            network=p.get('networkApprovalContext') is not None
            command=method in ('item/commandExecution/requestApproval','execCommandApproval')
            if self.ui_callback:self.ui_callback({'type':'extension_ui_request','id':identity,'method':'confirm',
                'approvalKind':'network' if network else 'bash' if command else 'file',
                'title':'Allow network access?' if network else 'Allow command?' if command else 'Allow file changes?',
                'message':(p.get('reason') or '')+'\n'+json.dumps({k:p[k] for k in ('command','cwd','fileChanges','changes','grantRoot','networkApprovalContext') if p.get(k) is not None},ensure_ascii=False)})
            return
        if method=='item/permissions/requestApproval':
            self.ui_pending[identity]={'raw':e,'kind':'permissions'}
            if self.ui_callback:self.ui_callback({'type':'extension_ui_request','id':identity,'method':'confirm',
                'title':'Allow access for this turn?','message':(p.get('reason') or '')+'\n'+json.dumps(p.get('permissions',{}),ensure_ascii=False)})
            return
        if method=='mcpServer/elicitation/request':
            schema=p.get('requestedSchema') or {}
            if p.get('mode') in ('form','openai/form','openaiForm') and not schema.get('properties'):
                self.ui_pending[identity]={'raw':e,'kind':'elicitation'}
                meta=p.get('_meta') or {}
                if self.ui_callback:self.ui_callback({'type':'extension_ui_request','id':identity,'method':'confirm',
                    'title':p.get('message','Allow MCP tool?'),'message':json.dumps(meta.get('tool_params',{}),ensure_ascii=False)})
            else:
                self.write({'id':e['id'],'result':{'action':'cancel'}})
                if self.ui_callback:self.ui_callback({'method':'notify','message':'This MCP server needs a form or browser login. Continue this session in the terminal to answer it.'})
            return
        if method=='item/tool/requestUserInput':
            group={'raw':e,'kind':'questions','answers':{},'remaining':len(p.get('questions',[]))}
            for q in p.get('questions',[]):
                key=identity+':'+q['id'];self.ui_pending[key]=dict(group=group,question=q)
                choices=[o['label'] for o in q.get('options') or []]
                if self.ui_callback:self.ui_callback({'type':'extension_ui_request','id':key,'method':'select' if choices else 'input',
                    'title':q.get('header','Your input'),'message':q.get('question',''),'options':choices})
            return
        self.write({'id':e['id'],'error':{'code':-32601,'message':'This Side Chat client does not handle '+method}})

    def notification(self,method,p):
        item=p.get('item') or {};kind=item.get('type');identity=item.get('id','')
        if method=='turn/started':self.turn=p['turn']['id'];self.events.put({'type':'agent_start'})
        elif method=='item/started':
            if kind=='agentMessage':self.events.put({'type':'message_start','message':{'role':'assistant'}})
            elif kind in ('commandExecution','fileChange','mcpToolCall','dynamicToolCall','webSearch'):
                name={'commandExecution':'shell','fileChange':'edit','webSearch':'web_search'}.get(kind,item.get('tool','tool'))
                args=item.get('arguments') or {'command':item.get('command'),'changes':item.get('changes')}
                self.tools[identity]=name
                self.events.put({'type':'tool_execution_start','toolCallId':identity,'toolName':name,'args':args})
        elif method=='item/agentMessage/delta':self.events.put({'type':'message_update','assistantMessageEvent':{'type':'text_delta','delta':p.get('delta','')}})
        elif method=='item/commandExecution/outputDelta':self.events.put({'type':'tool_execution_update','toolCallId':p.get('itemId',''),'toolName':'shell',
                'partialResult':{'content':[{'type':'text','text':p.get('delta','')}]}})
        elif method=='item/completed':
            if kind=='agentMessage':self.events.put({'type':'message_end','message':{'role':'assistant','content':[{'type':'text','text':item.get('text','')}],'model':self.model}})
            elif identity in self.tools:
                result=item.get('result') or {'content':[{'type':'text','text':str(item.get('error') or item.get('aggregatedOutput') or item.get('changes') or item.get('contentItems') or '')}]}
                self.events.put({'type':'tool_execution_end','toolCallId':identity,'toolName':self.tools[identity],'result':result,
                                 'isError':item.get('status') in ('failed','declined') or bool(item.get('error')) or item.get('exitCode',0) not in (None,0)})
        elif method=='turn/completed':
            turn=p.get('turn',{});error=turn.get('error')
            if error:self.events.put({'type':'message_end','message':{'role':'assistant','stopReason':'error','errorMessage':error.get('message',str(error))}})
            self.events.put({'type':'agent_end'});self.turn=''
        elif method=='serverRequest/resolved':
            key=str(p.get('requestId'))
            if key in self.ui_pending:
                self.ui_pending.pop(key,None)
                if self.ui_callback:self.ui_callback({'method':'cancel','id':key})

    def turns(self):
        try:
            result=self.call('thread/read',{'threadId':self.thread['id'],'includeTurns':True})
            self.thread=result['thread']
            return self.thread.get('turns',[])
        except RuntimeError as exc:
            if 'list_turns is not supported' not in str(exc):raise
        # Some installed app-server builds expose thread/read but not list_turns.
        # Read only the public completed-item events from their native rollout.
        turns={}
        path=Path(self.thread['path'])
        if not path.exists():return []
        for line in path.read_text().splitlines():
            try:e=json.loads(line)
            except ValueError:continue
            p=e.get('payload',{})
            if e.get('type')!='event_msg' or p.get('type')!='item_completed':continue
            item=dict(p.get('item') or {});kind=item.get('type','')
            item['type']=kind[:1].lower()+kind[1:]
            if kind=='AgentMessage':item['text']=''.join(v.get('text','') for v in item.get('content',[]) if v.get('type') in ('text','Text'))
            identity=p['turn_id']
            turns.setdefault(identity,{'id':identity,'items':[]})['items'].append(item)
        return list(turns.values())

    def history(self):
        messages=[];entries=[]
        for turn in self.turns():
            for item in turn.get('items',[]):
                kind=item.get('type')
                if kind=='userMessage':
                    text=''.join(i.get('text','') for i in item.get('content',[]) if i.get('type')=='text')
                    messages.append({'role':'user','content':text,'timestamp':time.time()*1000})
                    entries.append({'entryId':turn['id'],'text':text})
                elif kind=='agentMessage':messages.append({'role':'assistant','content':[{'type':'text','text':item.get('text','')}],'model':self.model})
                elif kind in ('commandExecution','fileChange','mcpToolCall','dynamicToolCall'):
                    name={'commandExecution':'shell','fileChange':'edit'}.get(kind,item.get('tool','tool'))
                    args=item.get('arguments') or {'command':item.get('command'),'changes':item.get('changes')}
                    messages.append({'role':'assistant','content':[{'type':'toolCall','id':item['id'],'name':name,'arguments':args}]})
                    output=item.get('result') or {'content':[{'type':'text','text':str(item.get('aggregatedOutput') or item.get('changes') or '')}]}
                    messages.append({'role':'toolResult','toolName':name,'toolCallId':item['id'],'content':output.get('content',[]),'isError':bool(item.get('error'))})
        return messages,entries

    def request(self,kind,timeout=30,**values):
        if kind=='steer':
            if not self.turn:raise ValueError('No active Codex turn to steer.')
            return self.call('turn/steer',{'threadId':self.thread['id'],'expectedTurnId':self.turn,
                                         'input':[{'type':'text','text':values['message'],'text_elements':[]}]},timeout=timeout)
        if kind=='get_state':return {'sessionFile':self.thread['path'],'sessionId':self.thread['id'],'model':self.model}
        if kind=='get_messages':return {'messages':self.history()[0]}
        if kind in ('get_branch_messages','get_fork_messages'):return {'messages':self.history()[1]}
        if kind in ('branch','fork'):
            result=self.call('thread/fork',dict(codex_permissions(self.options.get('_permission_mode','default')),
                                              threadId=self.thread['id'],beforeTurnId=values['entryId']))
            self.thread=result['thread'];return {'cancelled':False}
        raise ValueError('Unsupported Codex session command: '+kind)

    def send(self,c):
        kind=c.get('type')
        if kind=='prompt':
            inputs=[{'type':'text','text':c['message'],'text_elements':[]}]
            for image in c.get('images',[]):inputs.append({'type':'image','url':'data:'+image.get('mimeType','image/png')+';base64,'+image['data']})
            params={'threadId':self.thread['id'],'input':inputs}
            if self.options.get('thinking','default')!='default':params['effort']=self.options['thinking']
            result=self.call('turn/start',params,timeout=40);self.turn=result['turn']['id']
        elif kind=='abort':
            if self.turn:self.call('turn/interrupt',{'threadId':self.thread['id'],'turnId':self.turn},timeout=6)
        elif kind=='extension_ui_response':
            pending=self.ui_pending.pop(c['id'],None)
            if not pending:raise ValueError('This Codex prompt expired.')
            if pending.get('kind') in ('elicitation','permissions'):
                raw=pending['raw'];approved=c.get('confirmed') is True and not c.get('cancelled')
                if pending['kind']=='elicitation':result={'action':'accept' if approved else 'decline','content':{} if approved else None}
                else:result={'permissions':raw['params']['permissions'] if approved else {},'scope':'turn'}
                self.write({'id':raw['id'],'result':result})
            elif pending.get('kind')=='approval':
                raw=pending['raw'];approved=c.get('confirmed') is True and not c.get('cancelled')
                legacy=raw['method'] in ('execCommandApproval','applyPatchApproval')
                decision=('approved' if approved else 'denied') if legacy else ('accept' if approved else 'decline')
                self.write({'id':raw['id'],'result':{'decision':decision}})
            else:
                group=pending['group'];qid=pending['question']['id']
                group['answers'][qid]={'answers':[] if c.get('cancelled') else [str(c.get('value',''))]};group['remaining']-=1
                if not group['remaining']:self.write({'id':group['raw']['id'],'result':{'answers':group['answers']}})

    def close(self):
        if self.closed:return
        self.closed=True
        if self.proc is None:self.lease.close();return
        try:
            self.proc.stdin.close();self.proc.wait(timeout=3)
        except (OSError,subprocess.TimeoutExpired):
            try:os.killpg(self.proc.pid,signal.SIGTERM);self.proc.wait(timeout=2)
            except (ProcessLookupError,subprocess.TimeoutExpired):
                if self.proc.poll() is None:self.proc.kill();self.proc.wait(timeout=3)
        for thread in (self.reader,self.err_reader):
            if thread is not threading.current_thread():thread.join(timeout=1)
        for pipe in (self.proc.stdout,self.proc.stderr):pipe.close()
        self.lease.close()
