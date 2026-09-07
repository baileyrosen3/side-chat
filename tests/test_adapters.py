import json
from pathlib import Path
import queue
import tempfile
import threading
import unittest
from unittest.mock import patch
from agent_session import NativeTurn,SessionLease,resume_command
from agents.codex import CodexSession
from agents.claude import ClaudeSession


def codex():
    s=object.__new__(CodexSession);s.ui_pending={};s.events=queue.Queue();s.tools={};s.model='fixture';s.turn=''
    s.sent=[];s.prompts=[];s.write=s.sent.append;s.ui_callback=s.prompts.append
    return s


def claude():
    s=object.__new__(ClaudeSession);s.prompts={};s.events=queue.Queue();s.tools={};s.blocks={};s.model='fixture';s.identity='session';s.active=True
    s.sent=[];s.ui=[];s.write=s.sent.append;s.ui_callback=s.ui.append
    return s


class CodexTests(unittest.TestCase):
    def test_mcp_approval_requires_explicit_answer_without_persistence(self):
        s=codex();request={'id':12,'method':'mcpServer/elicitation/request','params':{'mode':'form','message':'Allow computer?',
            'requestedSchema':{'properties':{}},'_meta':{'tool_params':{'op':'click','x':12},'persist':['always']}}}
        s.server_request(request)
        self.assertFalse(s.sent);self.assertIn('click',s.prompts[0]['message'])
        s.send({'type':'extension_ui_response','id':'12','confirmed':True})
        self.assertEqual(s.sent,[{'id':12,'result':{'action':'accept','content':{}}}])
        s.server_request(request);s.send({'type':'extension_ui_response','id':'12','cancelled':True})
        self.assertEqual(s.sent[-1]['result']['action'],'decline')

    def test_command_prompt_includes_actual_command_and_directory(self):
        s=codex();s.server_request({'id':'a','method':'item/commandExecution/requestApproval','params':{'reason':'Needs access','command':'touch fixture','cwd':'/tmp/fixture'}})
        self.assertIn('touch fixture',s.prompts[0]['message']);self.assertIn('/tmp/fixture',s.prompts[0]['message'])
        s.send({'type':'extension_ui_response','id':'a','confirmed':False})
        self.assertEqual(s.sent[-1]['result'],{'decision':'decline'})

    def test_permission_grant_is_limited_to_requested_profile_and_turn(self):
        s=codex();profile={'fileSystem':{'write':['/tmp/fixture']}}
        s.server_request({'id':3,'method':'item/permissions/requestApproval','params':{'permissions':profile}})
        self.assertFalse(s.sent)
        s.send({'type':'extension_ui_response','id':'3','confirmed':True})
        self.assertEqual(s.sent[-1]['result'],{'permissions':profile,'scope':'turn'})

    def test_public_reply_and_failed_tool_error_survive_stream(self):
        s=codex();t=NativeTurn()
        s.notification('item/started',{'item':{'type':'agentMessage','id':'a'}})
        s.notification('item/reasoning/summaryTextDelta',{'delta':'private'})
        s.notification('item/agentMessage/delta',{'delta':'Checking.'})
        s.notification('item/completed',{'item':{'type':'agentMessage','id':'a','text':'Checking.'}})
        s.notification('item/started',{'item':{'type':'mcpToolCall','id':'t','tool':'computer','arguments':{'op':'windows'}}})
        s.notification('item/completed',{'item':{'type':'mcpToolCall','id':'t','error':{'message':'disconnected'},'status':'failed'}})
        s.notification('turn/completed',{'turn':{}})
        while not s.events.empty():t.feed(s.events.get())
        self.assertTrue(t.done);self.assertEqual(t.text,'Checking.');self.assertEqual(t.tools[0]['status'],'error');self.assertIn('disconnected',t.tools[0]['output'])

    def test_native_fallback_ignores_injected_context_and_preserves_turn_ids(self):
        with tempfile.TemporaryDirectory() as temp:
            s=codex();path=Path(temp)/'rollout.jsonl';s.thread={'id':'thread','path':str(path)}
            rows=[{'type':'response_item','payload':{'type':'message','role':'user','content':[{'type':'input_text','text':'Internal instructions'}]}},
                  {'type':'event_msg','payload':{'type':'item_completed','turn_id':'turn-1','item':{'type':'UserMessage','id':'u','content':[{'type':'text','text':'Hello'}]}}},
                  {'type':'event_msg','payload':{'type':'item_completed','turn_id':'turn-1','item':{'type':'AgentMessage','id':'a','content':[{'type':'Text','text':'Hi'}]}}}]
            path.write_text('\n'.join(map(json.dumps,rows)))
            def unsupported(*_):raise RuntimeError('list_turns is not supported yet')
            s.call=unsupported
            messages,entries=s.history()
            self.assertEqual(entries,[{'entryId':'turn-1','text':'Hello'}]);self.assertEqual(len(messages),2)

    def test_failed_spawn_releases_session_ownership(self):
        with tempfile.TemporaryDirectory() as temp,patch('agents.codex.cli_binary',return_value='/missing/codex'):
            with self.assertRaises(FileNotFoundError):CodexSession('codex',temp,{'cwd':temp})
            SessionLease(temp).close()


class ClaudeTests(unittest.TestCase):
    def test_permission_answer_preserves_input_and_does_not_change_policy(self):
        s=claude();data={'file_path':'/tmp/fixture','new_string':'12'}
        s.prompt({'type':'control_request','request_id':'r','request':{'subtype':'can_use_tool','tool_name':'Edit','input':data}})
        self.assertFalse(s.sent)
        s.send({'type':'extension_ui_response','id':'r','confirmed':True})
        self.assertEqual(s.sent[-1]['response']['response'],{'behavior':'allow','updatedInput':data})

    def test_declined_tool_is_not_approved_on_cancel(self):
        s=claude();s.prompt({'request_id':'r','request':{'subtype':'can_use_tool','tool_name':'Bash','input':{'command':'echo test'}}})
        s.send({'type':'extension_ui_response','id':'r','cancelled':True,'confirmed':True})
        self.assertEqual(s.sent[-1]['response']['response']['behavior'],'deny')

    def test_tool_stream_filters_private_thinking_and_retains_output(self):
        s=claude();t=NativeTurn()
        for e in [{'type':'stream_event','event':{'type':'message_start'}},
                  {'type':'stream_event','event':{'type':'content_block_delta','delta':{'type':'thinking_delta','thinking':'private'}}},
                  {'type':'stream_event','event':{'type':'content_block_delta','delta':{'type':'text_delta','text':'Checking.'}}},
                  {'type':'assistant','message':{'role':'assistant','content':[{'type':'text','text':'Checking.'},{'type':'tool_use','id':'t','name':'Read','input':{'file_path':'fixture'}}]}},
                  {'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':'t','content':'font_size = 12'}]}},
                  {'type':'result','is_error':False}]:s.event(e)
        while not s.events.empty():t.feed(s.events.get())
        self.assertTrue(t.done);self.assertEqual(t.text,'Checking.');self.assertEqual(t.tools[0]['output'],'font_size = 12')
        self.assertEqual(t.tools[0]['status'],'complete')

    def test_native_terminal_argv_uses_cli_session_id(self):
        self.assertEqual(resume_command('claude','/a/session-id.jsonl'),['claude','--resume','session-id'])
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'rollout.jsonl';path.write_text(json.dumps({'type':'session_meta','payload':{'id':'native-id'}}))
            self.assertEqual(resume_command('codex',path),['codex','resume','native-id'])


if __name__=='__main__':unittest.main()
