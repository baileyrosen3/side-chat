import json
import tempfile
import unittest
from unittest.mock import patch

from backend import Bridge


class DefaultAgentTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory()
        self.events=[]
        self.bridge=Bridge(self.folder.name,self.events.append)
        self.default=patch.object(self.bridge,'default_agent',return_value='omp')
        self.agent=self.default.start()
        self.bridge.new()

    def tearDown(self):
        self.bridge.close();self.default.stop();self.folder.cleanup()

    def test_default_change_updates_empty_header_and_permission_provider_before_send(self):
        chat=self.bridge.current
        chat.update(draft='Keep this thought',permissionMode='yolo',bashApproval='always')
        identity=chat['id'];cwd=chat['options']['cwd']
        self.agent.return_value='claude'
        self.bridge.dispatch({'action':'ping'})
        current=self.bridge.current
        self.assertEqual(current['id'],identity)
        self.assertEqual(current['agent'],'claude')
        self.assertEqual(current['draft'],'Keep this thought')
        self.assertEqual(current['options']['cwd'],cwd)
        self.assertNotIn('permissionMode',current);self.assertNotIn('bashApproval',current)
        state=next(e for e in reversed(self.events) if e['type']=='state')
        self.assertEqual(state['current']['agent'],state['meta']['agent'])
        self.assertEqual(state['meta']['agentName'],'Claude')
        self.assertEqual(self.bridge.db.execute('SELECT COUNT(*) FROM chats').fetchone()[0],0)

    def test_saved_draft_is_updated_and_existing_conversations_keep_their_agent(self):
        self.bridge.current['draft']='Draft'
        self.bridge.save(self.bridge.current)
        self.agent.return_value='claude'
        self.bridge.dispatch({'action':'refresh'})
        saved=json.loads(self.bridge.db.execute('SELECT data FROM chats').fetchone()[0])
        self.assertEqual(saved['agent'],'claude');self.assertEqual(saved['draft'],'Draft')
        self.bridge.current['messages']=[{'role':'user','text':'Started with Claude'}]
        self.agent.return_value='omp'
        self.bridge.dispatch({'action':'ping'})
        self.assertEqual(self.bridge.current['agent'],'claude')
        self.assertEqual(self.events[-1]['meta']['agent'],'omp')

    def test_busy_or_native_or_terminal_sessions_are_not_reassigned(self):
        self.agent.return_value='claude'
        for field,value in [('native',{'id':'session'}),('terminalOpen',True)]:
            self.bridge.current[field]=value
            self.assertFalse(self.bridge.sync_default_agent())
            self.assertEqual(self.bridge.current['agent'],'omp')
            self.bridge.current.pop(field)
        self.bridge.busy=True
        self.assertFalse(self.bridge.sync_default_agent())
        self.bridge.busy=False


if __name__=='__main__':unittest.main()
