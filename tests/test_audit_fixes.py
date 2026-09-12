"""Regressions for the interaction and recovery failures found in the UI audit."""
import json
from contextlib import closing
import queue
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from agent_session import wait_response
from backend import Bridge
from peek.context import capture, requested
from peek.control import Control
from thoughts import ThoughtStore, atomic_write


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = ThoughtStore(self.root / 'state', self.root / 'notes')

    def test_corrupt_drafts_preserve_original_and_allow_one_save(self):
        self.store.state.mkdir(parents=True)
        raw = b'{broken recovery data'
        (self.store.state / 'drafts.json').write_bytes(raw)
        operation = {'key': 'draft-one', 'body': 'Keep exactly once'}
        first = self.store.save(operation)
        second = self.store.save(operation)
        self.assertEqual(first['id'], second['id'])
        snapshot = self.store.snapshot()
        self.assertEqual(len(snapshot['notes']), 1)
        self.assertTrue(snapshot['warnings'])
        self.assertEqual(next(self.store.state.glob('drafts-recovery-*.json')).read_bytes(), raw)

    def test_retry_after_committed_note_and_failed_cleanup_is_idempotent(self):
        operation = {'key': 'draft-one', 'body': 'Keep exactly once'}
        self.store.write_draft(operation)
        def write(path, text):
            if path.name == 'drafts.json':
                raise OSError('Simulated interrupted cleanup')
            atomic_write(path, text)
        with patch('thoughts.atomic_write', side_effect=write), self.assertRaisesRegex(OSError, 'note was saved'):
            self.store.save(operation)
        saved = self.store.save(operation)
        self.assertEqual(len(self.store.snapshot()['notes']), 1)
        self.assertEqual(self.store.read(saved['id'])['body'], operation['body'])
        self.assertEqual(self.store.drafts(), {})


class BridgeAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.events = []
        self.bridge = Bridge(self.root / 'state', self.events.append)
        self.addCleanup(lambda: self.bridge.close())
        self.bridge.thoughts.store.directory = self.root / 'notes'
        self.bridge.settings['cwd'] = str(self.root)

    def test_busy_draft_attachments_survive_switch_and_restart(self):
        self.bridge.new()
        identity = self.bridge.current['id']
        self.bridge.busy = True
        self.bridge.dispatch({'action': 'draft', 'id': identity, 'text': 'Next question', 'attachments': ['/tmp/example file.md']})
        self.bridge.busy = False
        self.bridge.new()
        self.bridge.dispatch({'action': 'open', 'id': identity})
        self.assertEqual(self.bridge.current['draft'], 'Next question')
        self.bridge.close()
        self.bridge = Bridge(self.root / 'state', self.events.append)
        self.assertEqual(self.bridge.current['draftAttachments'], ['/tmp/example file.md'])

    def test_corrupt_conversation_and_preferences_do_not_block_startup(self):
        self.bridge.new(); self.bridge.save(self.bridge.current)
        identity = self.bridge.current['id']
        self.bridge.close()
        with closing(sqlite3.connect(self.root / 'state/chats.sqlite3')) as db:
            with db:
                db.execute('INSERT INTO chats VALUES (?,?,?)', ('broken', 9999999999, '{damaged'))
                db.execute("INSERT OR REPLACE INTO settings VALUES ('preferences',?)", ('[]',))
        self.bridge = Bridge(self.root / 'state', self.events.append)
        self.assertEqual(self.bridge.current['id'], identity)
        originals = self.bridge.db.execute('SELECT data FROM recovery').fetchall()
        self.assertEqual({r[0] for r in originals}, {'{damaged', '[]'})

    def test_original_draft_and_in_progress_edit_both_survive_restart(self):
        self.bridge.new()
        self.bridge.current['messages']=[{'role':'user','text':'Original message'}]
        self.bridge.save(self.bridge.current)
        identity=self.bridge.current['messages'][0]['id']
        self.bridge.dispatch({'action':'draft','text':'Next question','attachments':['/tmp/next.txt'],
            'editDraft':{'index':0,'messageId':identity,'text':'An unfinished edit','attachments':['/tmp/edit.txt']}})
        self.bridge.close()
        self.bridge=Bridge(self.root/'state',self.events.append)
        self.assertEqual(self.bridge.current['draft'],'Next question')
        self.assertEqual(self.bridge.current['draftAttachments'],['/tmp/next.txt'])
        self.assertEqual(self.bridge.current['draftEdit']['text'],'An unfinished edit')
        self.assertEqual(self.bridge.current['draftEdit']['messageId'],identity)

    def test_stop_during_startup_never_delivers_prompt(self):
        self.bridge.new()
        self.bridge.current['messages'] = [{'role': 'user', 'text': 'Do something'}, {'role': 'assistant', 'text': '', 'status': 'streaming'}]
        self.bridge.busy = True
        entered, release = threading.Event(), threading.Event()
        sent = []
        def connect(chat):
            entered.set(); release.wait(2)
            return SimpleNamespace(events=queue.Queue(), send=sent.append)
        with patch.object(self.bridge, 'ensure_rpc', side_effect=connect):
            worker = threading.Thread(target=self.bridge.generate_native, args=(self.bridge.current, 'Do something', []))
            worker.start()
            self.assertTrue(entered.wait(1))
            self.bridge.dispatch({'action': 'stop'})
            release.set(); worker.join(2)
        self.assertFalse(worker.is_alive())
        self.assertEqual(sent, [])
        self.assertEqual(self.bridge.current['messages'][-1]['status'], 'stopped')
        self.assertNotIn('error', self.bridge.current['messages'][-1])

    def test_redirect_acknowledges_only_after_acceptance(self):
        self.bridge.new(); self.bridge.busy=True
        self.bridge.peek.state['enabled']=True
        self.bridge.current['draft']='Use another approach'
        self.bridge.ui_requests=[{'id':'question'}]
        with self.assertRaisesRegex(ValueError,'pending question'):
            self.bridge.dispatch({'action':'peek_redirect','text':'Use another approach'})
        self.assertFalse(any(e['type']=='redirect_accepted' for e in self.events))
        self.assertEqual(self.bridge.current['draft'],'Use another approach')
        self.bridge.ui_requests=[]
        with patch.object(self.bridge.peek,'steer') as steer:
            self.bridge.dispatch({'action':'peek_redirect','text':'Use another approach'})
            steer.assert_called_once_with('Use another approach')
        self.assertEqual(self.events[-1],{'type':'redirect_accepted','text':'Use another approach'})
        self.bridge.busy=False; self.bridge.peek.state['enabled']=False

    def test_search_tracks_edits_deletes_restores_and_message_location(self):
        self.bridge.new()
        chat = self.bridge.current
        chat['messages'] = [{'text': 'Unrelated'}, {'text': 'Deep Café needle in message two'}]
        self.bridge.save(chat)
        result = self.bridge.workspace.search('CAFÉ needle')[0]
        self.assertEqual(result['messageIndex'], 1)
        self.assertEqual(self.bridge.workspace.search('eed')[0]['id'], chat['id'])
        chat['messages'][1]['text'] = 'Replaced with another phrase'
        self.bridge.save(chat)
        self.assertEqual(self.bridge.workspace.search('needle'), [])
        self.bridge.dispatch({'action': 'delete', 'id': chat['id']})
        self.assertEqual(self.bridge.workspace.search('another'), [])
        self.bridge.workspace.restore({'kind': 'chat', 'id': chat['id']})
        self.assertEqual(self.bridge.workspace.search('another')[0]['messageIndex'], 1)

    def test_search_is_not_queued_behind_export(self):
        entered, release, found = threading.Event(), threading.Event(), threading.Event()
        def export(path):
            entered.set(); release.wait(2); return path
        def search(*args):
            found.set(); return []
        with patch.object(self.bridge.workspace, 'export', side_effect=export), patch.object(self.bridge.workspace, 'search', side_effect=search):
            self.bridge.workspace.dispatch({'action': 'workspace_export', 'serial': 1, 'path': '/tmp/example.zip'})
            try:
                self.assertTrue(entered.wait(1))
                self.bridge.workspace.dispatch({'action': 'workspace_search', 'serial': 2})
                self.assertTrue(found.wait(1))
            finally:
                release.set()

    def test_file_links_use_editor_argv_and_reject_other_schemes(self):
        target = self.root / 'A file.md'; target.write_text('Example')
        with patch('backend.subprocess.Popen') as launch:
            self.bridge.open_link(target.as_uri() + '#L12')
            self.assertEqual(launch.call_args.args[0][0], 'omarchy-launch-editor')
            self.assertTrue(any(str(target) in arg for arg in launch.call_args.args[0]))
            with self.assertRaises(ValueError):
                self.bridge.open_link('javascript:alert(1)')
            with self.assertRaises(ValueError):
                self.bridge.open_link('file://remote/tmp/file')
            self.assertEqual(launch.call_count, 1)


class InputAuditTests(unittest.TestCase):
    def test_generic_words_never_capture_desktop(self):
        prefs = {'screenContext': 'on-request'}
        with patch('peek.context.subprocess.check_output') as read:
            for text in ('Fix this error', 'Explain that', 'Look here', 'Implement screenshot export'):
                self.assertEqual(capture(prefs, text), ('', []))
            read.assert_not_called()
        for text in ('Look at my screen', 'Read this window', 'Take a screenshot'):
            self.assertTrue(requested(text))

    def test_startup_wait_is_interruptible(self):
        cancelled = threading.Event()
        timer = threading.Timer(.03, cancelled.set); timer.start()
        try:
            with self.assertRaisesRegex(ValueError, 'Stopped'):
                wait_response(queue.Queue(), 2, cancelled)
        finally:
            timer.join()

    def test_takeover_remains_armed_between_actions_and_capability_is_real(self):
        with patch.object(Control, 'watch_input', lambda _: None):
            control = Control(lambda event: None)
        try:
            self.assertFalse(control.handle({'op': 'capabilities'})['takeover'])
            control.handle({'op': '_configure', 'enabled': True, 'turn': 'one'})
            with patch.object(control, 'execute', return_value={}):
                control.handle({'op': 'screenshot'})
            self.assertFalse(control.active)
            self.assertTrue(control.takeover_armed)
            control.physical_input(moved=True)
            self.assertFalse(control.enabled)
            with self.assertRaisesRegex(RuntimeError, 'stopped'):
                control.handle({'op': 'click'})
        finally:
            control.close()
