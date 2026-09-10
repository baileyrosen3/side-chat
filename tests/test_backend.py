import json
import os
from pathlib import Path
import stat
import tempfile
import time
import unittest
from unittest.mock import patch

from backend import Bridge, StreamParser


FAKE_AGENT = r'''#!/usr/bin/env python3
import json, os, pathlib, sys, time
prompt = pathlib.Path(next(a[1:] for a in sys.argv if a.startswith('@'))).read_text()
pathlib.Path(os.environ['TEST_PROMPT']).write_text(prompt)
mode = os.environ.get('TEST_MODE', '')
def emit(event):
    print(json.dumps(event, ensure_ascii=False), flush=True)
emit({'type': 'message_update', 'assistantMessageEvent': {'type': 'text_delta', 'delta': 'Hello '}})
if mode == 'slow':
    time.sleep(30)
if mode == 'error':
    emit({'type': 'message_end', 'message': {'role': 'assistant', 'content': [], 'stopReason': 'error', 'errorMessage': 'Login expired'}})
    sys.exit(1)
# Fill stderr beyond a pipe buffer: the bridge must drain both pipes.
sys.stderr.write('diagnostic\n' * 12000)
sys.stderr.flush()
# Split a non-ASCII character across OS reads.
data = json.dumps({'type': 'message_update', 'assistantMessageEvent': {'type': 'text_delta', 'delta': '🌿 café'}}, ensure_ascii=False).encode() + b'\n'
for byte in data:
    os.write(sys.stdout.fileno(), bytes([byte]))
emit({'type': 'message_end', 'message': {'role': 'assistant', 'model': 'test-model', 'content': [{'type':'text','text':'Hello 🌿 café'}], 'usage': {'input': 12, 'output': 3}}})
'''


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)
        (self.path / 'bin').mkdir()
        (self.path / 'config/omarchy/defaults').mkdir(parents=True)
        (self.path / 'config/omarchy/defaults/agent').write_text('omp\n')
        executable = self.path / 'bin/omp'
        executable.write_text(FAKE_AGENT)
        executable.chmod(0o755)
        self.env = patch.dict(os.environ, {'PATH': str(self.path / 'bin') + os.pathsep + os.environ['PATH'],
            'XDG_CONFIG_HOME': str(self.path / 'config'), 'TEST_PROMPT': str(self.path / 'prompt'), 'TEST_MODE': ''})
        self.env.start()
        # Keep exercising the legacy text adapters alongside the native RPC suite.
        self.legacy = patch('backend.NATIVE_AGENTS', set())
        self.legacy.start()
        self.events = []
        self.bridge = Bridge(self.path / 'state', self.events.append)
        self.bridge.settings['cwd'] = str(self.path)

    def tearDown(self):
        self.bridge.close()
        self.legacy.stop()
        self.env.stop()
        self.temp.cleanup()

    def send(self, text, **kwargs):
        self.bridge.dispatch(dict(action='send', text=text, **kwargs))
        self.bridge.worker.join(5)
        self.assertFalse(self.bridge.busy)
        return self.bridge.current['messages'][-1]

    def test_real_subprocess_streaming_unicode_and_stderr(self):
        reply = self.send('Say hello')
        self.assertEqual(reply['text'], 'Hello 🌿 café')
        self.assertEqual(reply['status'], 'complete')
        self.assertEqual(reply['model'], 'test-model')
        self.assertTrue(any(e['type'] == 'delta' for e in self.events))
        self.assertEqual(stat.S_IMODE(self.bridge.state.stat().st_mode), 0o700)

    def test_followup_and_edit_preserve_correct_context(self):
        self.send('First thought')
        self.send('Follow up')
        prompt = (self.path / 'prompt').read_text()
        self.assertIn('First thought', prompt)
        self.assertIn('ASSISTANT:\nHello 🌿 café', prompt)
        self.send('Replacement thought', edit=0)
        self.assertEqual(len(self.bridge.current['messages']), 2)
        prompt = (self.path / 'prompt').read_text()
        self.assertNotIn('First thought', prompt)
        self.assertNotIn('Follow up', prompt)
        self.assertIn('Replacement thought', prompt)

    def test_attachments_are_snapshots_and_reused_on_edit(self):
        original = self.path / 'notes.txt'
        original.write_text('original reference')
        self.send('Read this', attachments=[original.as_uri()])
        original.write_text('changed reference')
        self.send('Explain it again', edit=0)
        prompt = (self.path / 'prompt').read_text()
        self.assertIn('original reference', prompt)
        self.assertNotIn('changed reference', prompt)

    def test_errors_keep_partial_reply_and_support_retry(self):
        os.environ['TEST_MODE'] = 'error'
        reply = self.send('Hello')
        self.assertEqual(reply['status'], 'error')
        self.assertEqual(reply['error'], 'Login expired')
        self.assertEqual(reply['text'], 'Hello ')
        os.environ['TEST_MODE'] = ''
        reply = self.send('Hello', edit=0)
        self.assertEqual(reply['status'], 'complete')

    def test_stop_and_busy_guards(self):
        os.environ['TEST_MODE'] = 'slow'
        self.bridge.dispatch({'action': 'send', 'text': 'Wait'})
        with self.assertRaisesRegex(ValueError, 'Stop the current reply'):
            self.bridge.dispatch({'action': 'new'})
        deadline = time.monotonic() + 3
        while not any(e.get('type') == 'delta' and e.get('text') for e in self.events) and time.monotonic() < deadline:
            time.sleep(0.02)
        proc = self.bridge.process
        self.bridge.dispatch({'action': 'stop'})
        self.bridge.worker.join(3)
        self.assertFalse(self.bridge.busy)
        self.assertEqual(self.bridge.current['messages'][-1]['status'], 'stopped')
        self.assertIsNotNone(proc.poll())

    def test_restart_restores_draft_and_marks_interrupted_reply(self):
        self.send('Remember me')
        self.bridge.dispatch({'action': 'draft', 'text': 'Unsent thought'})
        self.bridge.current['messages'][-1]['status'] = 'streaming'
        self.bridge.save(self.bridge.current)
        self.bridge.close()
        self.bridge = Bridge(self.path / 'state', self.events.append)
        self.assertEqual(self.bridge.current['draft'], 'Unsent thought')
        self.assertEqual(self.bridge.current['messages'][-1]['status'], 'stopped')

    def test_new_conversation_follows_default_without_switching_existing(self):
        self.send('Hello')
        (self.path / 'config/omarchy/defaults/agent').write_text('claude\n')
        self.assertEqual(self.bridge.metadata()['agent'], 'claude')
        self.assertEqual(self.bridge.current['agent'], 'omp')
        self.bridge.dispatch({'action': 'new'})
        self.assertEqual(self.bridge.current['agent'], 'claude')

    def test_outline_defaults_persists_and_resets_without_changing_session(self):
        self.assertEqual(self.bridge.metadata()['appearance'], {'outline': True, 'expanded': False})
        self.bridge.new()
        original_options = dict(self.bridge.current['options'])
        self.bridge.dispatch({'action': 'appearance', 'settings': {'outline': False}})
        self.assertEqual(self.events[-1]['meta']['appearance'], {'outline': False, 'expanded': False})
        self.assertEqual(self.bridge.current['options'], original_options)
        self.assertNotIn('outline', self.bridge.settings)
        self.bridge.close()
        self.bridge = Bridge(self.path / 'state', self.events.append)
        self.assertFalse(self.bridge.metadata()['appearance']['outline'])
        self.bridge.dispatch({'action': 'settings', 'settings': {'cwd': str(self.path), 'model': 'test-model'}})
        self.assertFalse(self.bridge.appearance['outline'])
        self.bridge.dispatch({'action': 'appearance', 'settings': {'outline': True}})
        self.bridge.close()
        self.bridge = Bridge(self.path / 'state', self.events.append)
        self.assertTrue(self.bridge.appearance['outline'])
        self.assertEqual(self.bridge.settings['model'], 'test-model')

    def test_outline_can_change_during_a_reply_without_interrupting_it(self):
        os.environ['TEST_MODE'] = 'slow'
        self.bridge.dispatch({'action': 'send', 'text': 'Wait'})
        try:
            with patch.object(self.bridge, 'close_rpc') as close_rpc:
                self.bridge.dispatch({'action': 'appearance', 'settings': {'outline': False}})
                close_rpc.assert_not_called()
            self.assertTrue(self.bridge.busy)
            self.assertFalse(self.bridge.cancelled.is_set())
            self.assertFalse(self.bridge.appearance['outline'])
        finally:
            self.bridge.dispatch({'action': 'stop'})
            self.bridge.worker.join(3)

    def test_invalid_outline_values_are_rejected_without_saving(self):
        for options in (None, [], {}, {'outline': 'false'}, {'outline': 0},
                        {'outline': None}, {'outline': False, 'model': 'unexpected'}, {'expanded': 'yes'}):
            with self.subTest(options=options), self.assertRaisesRegex(ValueError, 'Outline'):
                self.bridge.dispatch({'action': 'appearance', 'settings': options})
        self.assertTrue(self.bridge.appearance['outline'])
        self.assertIsNone(self.bridge.db.execute("SELECT value FROM settings WHERE key='appearance'").fetchone())

    def test_expanded_view_persists_beside_outline(self):
        self.bridge.dispatch({'action': 'appearance', 'settings': {'expanded': True}})
        self.assertEqual(self.bridge.appearance, {'outline': True, 'expanded': True})
        self.bridge.dispatch({'action': 'appearance', 'settings': {'outline': False}})
        self.assertEqual(self.bridge.appearance, {'outline': False, 'expanded': True})
        self.bridge.close()
        self.bridge = Bridge(self.path / 'state', self.events.append)
        self.assertEqual(self.bridge.appearance, {'outline': False, 'expanded': True})

    def test_saving_preferences_confirms_to_the_ui(self):
        self.bridge.dispatch({'action': 'settings', 'settings': {'cwd': str(self.path), 'model': 'm'}})
        self.assertEqual(self.events[-1]['type'], 'settings_saved')

    def test_export_delete_and_invalid_attachment(self):
        self.send('Export me')
        export = self.path / 'chat.md'
        self.bridge.dispatch({'action': 'export', 'path': export.as_uri()})
        self.assertIn('Hello 🌿 café', export.read_text())
        self.bridge.dispatch({'action': 'delete', 'id': self.bridge.current['id']})
        self.assertEqual(self.bridge.db.execute('SELECT count(*) FROM chats').fetchone()[0], 0)
        binary = self.path / 'binary.bin'
        binary.write_bytes(b'\x00\xff')
        with self.assertRaisesRegex(ValueError, 'attach a text'):
            self.bridge.attachment(binary)


class ParserTests(unittest.TestCase):
    def test_claude_snapshot_does_not_duplicate_deltas(self):
        p = StreamParser('claude')
        p.feed(json.dumps({'type':'stream_event', 'event': {'type':'content_block_delta','delta': {'type':'text_delta','text':'Hello'}}}))
        p.feed(json.dumps({'type':'assistant','message': {'content':[{'type':'text','text':'Hello'}]}}))
        p.feed(json.dumps({'type':'result','result':'Hello'}))
        self.assertEqual(p.text, 'Hello')

    def test_tool_and_reasoning_events_are_not_shown_as_answers(self):
        p = StreamParser('omp')
        p.feed(json.dumps({'type':'message_update','assistantMessageEvent':{'type':'thinking_delta','delta':'private'}}))
        p.feed(json.dumps({'type':'tool_execution_end','result': {'text':'tool output'}}))
        self.assertEqual(p.text, '')

    def test_codex_and_opencode_public_event_shapes(self):
        p = StreamParser('codex')
        p.feed(json.dumps({'type':'item.completed', 'item': {'type':'agent_message','text':'Ready'}}))
        p.feed(json.dumps({'type':'turn.completed', 'usage': {'input_tokens':12}}))
        self.assertEqual(p.text, 'Ready')
        self.assertEqual(p.usage['input_tokens'], 12)
        p = StreamParser('opencode')
        p.feed(json.dumps({'type':'text', 'part': {'text':'A'}}))
        p.feed(json.dumps({'type':'text', 'part': {'text':'B'}}))
        self.assertEqual(p.text, 'AB')


if __name__ == '__main__':
    unittest.main()
