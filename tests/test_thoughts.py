import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from thoughts import ThoughtStore, ThoughtsController, notes_directory


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = ThoughtStore(self.root / 'state', self.root / 'notes')

    def save(self, **values):
        return self.store.save(dict(body='A thought about café 🌿', **values))

    def test_reads_original_omathought_without_rewriting(self):
        self.store.folder.mkdir()
        path = self.store.folder / '20260911-120000.md'
        text = '---\ncreated: 2026-09-11T12:00:00-04:00\n---\n\nKeep this.\n'
        path.write_text(text)
        note = self.store.snapshot()['notes'][0]
        self.assertEqual(note['body'], 'Keep this.')
        self.assertEqual(path.read_text(), text)
        self.assertFalse((self.root / 'state').exists())

    def test_save_roundtrip_unicode_metadata_and_private_files(self):
        note = self.save(title='Café', tags='work, #idea, work')
        self.assertEqual(note['tags'], ['work', 'idea'])
        self.assertEqual(note['title'], 'Café')
        self.assertEqual(Path(note['path']).stat().st_mode & 0o777, 0o600)
        self.assertIn('created:', Path(note['path']).read_text())

    def test_edit_preserves_created_unknown_yaml_and_markdown_whitespace(self):
        self.store.folder.mkdir()
        path = self.store.folder / 'handwritten.md'
        path.write_text('---\ncreated: 2020-01-01\ncustom:\n  nested: yes\n---\n\noriginal\n')
        note = self.store.read('handwritten')
        edited = self.store.save(dict(note, body='## Code\n\n    indented\n\n---\n\nMore'))
        self.assertEqual(edited['created'], '2020-01-01')
        self.assertIn('custom:\n  nested: yes', path.read_text())
        self.assertIn('    indented', edited['body'])
        self.assertIn('\n---\n', edited['body'])

    def test_conflict_keeps_external_edit_and_recovery_draft(self):
        note = self.save()
        draft = dict(note, key='draft-conflict', body='My draft')
        self.store.write_draft(draft)
        Path(note['path']).write_text('External update')
        with self.assertRaisesRegex(ValueError, 'another editor'):
            self.store.save(draft)
        self.assertEqual(Path(note['path']).read_text(), 'External update')
        self.assertEqual(self.store.drafts()['draft-conflict']['body'], 'My draft')
        draft['id'] = ''
        self.assertEqual(self.store.save(draft)['body'], 'My draft')
        self.assertNotIn('draft-conflict', self.store.drafts())

    def test_trash_restore_preserves_bytes_and_does_not_overwrite(self):
        note = self.save()
        original = Path(note['path']).read_bytes()
        self.store.modify(note['id'], note['revision'], 'trash')
        self.assertFalse(Path(note['path']).exists())
        trashed = self.store.read(note['id'], True)
        self.assertEqual(Path(trashed['path']).read_bytes(), original)
        Path(note['path']).write_text('New note at old name')
        with self.assertRaisesRegex(ValueError, 'already exists'):
            self.store.modify(note['id'], note['revision'], 'restore')
        self.assertEqual(Path(trashed['path']).read_bytes(), original)
        Path(note['path']).unlink()
        self.store.modify(note['id'], note['revision'], 'restore')
        self.assertEqual(Path(note['path']).read_bytes(), original)

    def test_pin_archive_and_external_conflict(self):
        note = self.save()
        self.store.modify(note['id'], note['revision'], 'pin')
        pinned = self.store.read(note['id'])
        self.assertTrue(pinned['pinned'])
        with self.assertRaisesRegex(ValueError, 'changed outside'):
            self.store.modify(note['id'], note['revision'], 'archive')
        self.store.modify(note['id'], pinned['revision'], 'archive')
        self.assertTrue(self.store.read(note['id'])['archived'])

    def test_todo_completion_persists_and_can_be_unchecked(self):
        note = self.store.save({'body':'Buy groceries', 'kind':'todo'})
        self.store.modify(note['id'], note['revision'], 'complete')
        done = self.store.read(note['id'])
        self.assertTrue(done['done'])
        self.assertEqual(done['kind'], 'todo')
        self.assertEqual(done['body'], 'Buy groceries')
        self.store.modify(done['id'], done['revision'], 'complete')
        self.assertFalse(self.store.read(note['id'])['done'])

    def test_editing_todo_keeps_completed_state(self):
        note = self.store.save({'body':'Buy groceries', 'kind':'todo'})
        self.store.modify(note['id'],note['revision'],'complete')
        done = self.store.read(note['id'])
        edited = self.store.save(dict(done,body='Buy groceries and coffee'))
        self.assertTrue(edited['done'])
        self.assertEqual(edited['kind'],'todo')

    def test_multiple_drafts_survive_new_store_and_save_clears_only_one(self):
        for key in ['draft-a', 'draft-b']:
            self.store.write_draft(dict(key=key,body=key))
        recovered = ThoughtStore(self.root / 'state', self.root / 'notes')
        self.assertEqual(len(recovered.drafts()), 2)
        recovered.save(dict(key='draft-a',body='Finished'))
        self.assertEqual(list(recovered.drafts()), ['draft-b'])

    def test_malformed_frontmatter_is_not_swallowed(self):
        note = self.store.save({'body':'---\nan unfinished separator'})
        self.assertEqual(note['body'], '---\nan unfinished separator')

    def test_traversal_symlink_and_empty_writes_refused(self):
        for identity in ('../outside', '/tmp/a', 'a/b', '..', 'a\\b'):
            with self.assertRaises(ValueError):
                self.store.path(identity)
        self.store.folder.mkdir()
        outside = self.root / 'outside.md'
        outside.write_text('Do not modify')
        (self.store.folder / 'linked.md').symlink_to(outside)
        with self.assertRaises(ValueError):
            self.store.read('linked')
        with self.assertRaises(ValueError):
            self.store.save({'body':' \n\t'})
        self.assertEqual(outside.read_text(), 'Do not modify')

    def test_one_unreadable_note_does_not_hide_library(self):
        self.save()
        (self.store.folder / 'bad.md').write_bytes(b'\xff')
        snapshot = self.store.snapshot()
        self.assertEqual(len(snapshot['notes']), 1)
        self.assertEqual(len(snapshot['warnings']), 1)

    def test_existing_notes_directory_setting(self):
        state = self.root / 'xdg'
        path = state / 'omarchy/settings/omathought.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({'notesDir':str(self.root / 'my notes')}))
        with patch.dict(os.environ, {'XDG_STATE_HOME':str(state), 'SIDE_CHAT_THOUGHTS_DIR':''}):
            self.assertEqual(notes_directory(), self.root / 'my notes')


class FakeVoice:
    def __init__(self, directory):
        self.active = False
        self.cancelled = False
    def start(self):
        time.sleep(.04)
        self.active = True
    def stop(self):
        self.active = False
        return 'Captured without an agent'
    def cancel(self):
        self.cancelled = True
        self.active = False
    def level(self):
        return .5


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.events = []
        self.bridge = SimpleNamespace(state=Path(self.temp.name), peek=SimpleNamespace(want_listen=False,state={},transcribing=False),
                                      emit=lambda **event:self.events.append(event))
        self.controller = ThoughtsController(self.bridge)
        self.addCleanup(self.controller.close)

    @patch('peek.voxtype.VoxtypeBridge', FakeVoice)
    def test_release_before_start_ack_still_stops_and_persists_transcript(self):
        self.controller.start_voice('draft-voice')
        self.controller.dispatch({'action':'thoughts_voice_stop'})
        self.controller.thread.join(2)
        self.assertFalse(self.controller.thread.is_alive())
        self.assertEqual(self.controller.phase, 'idle')
        self.assertEqual(self.controller.store.drafts()['draft-voice']['body'], 'Captured without an agent')
        self.assertTrue(any(e['type']=='thoughts_transcript' for e in self.events))

    @patch('peek.voxtype.VoxtypeBridge', FakeVoice)
    def test_cancel_during_start_discards_audio(self):
        self.controller.start_voice('draft-cancel')
        self.controller.cancel_voice()

        self.controller.thread.join(2)
        self.assertTrue(self.controller.voice.cancelled)
        self.assertFalse(any(e['type']=='thoughts_transcript' for e in self.events))

    def test_peek_microphone_ownership_refused(self):
        self.bridge.peek.want_listen = True
        self.controller.dispatch({'action':'thoughts_voice_start','key':'draft-busy'})
        self.assertEqual(self.controller.phase, 'idle')
        self.assertIn('Pause Peek', self.events[-1]['text'])

    @patch('peek.voxtype.VoxtypeBridge', FakeVoice)
    def test_repeat_does_not_start_another_recording(self):
        self.controller.start_voice('draft-repeat')
        voice = self.controller.voice
        self.controller.start_voice('draft-repeat')
        self.assertIs(voice, self.controller.voice)
        self.controller.cancel_voice()


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        from backend import Bridge
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.events = []
        self.bridge = Bridge(root/'state', self.events.append)
        self.bridge.thoughts.store.directory = root/'notes'
        self.addCleanup(self.bridge.close)

    def test_note_and_todo_work_without_agent_and_while_chat_busy(self):
        self.bridge.busy = True
        with patch.object(self.bridge,'send',side_effect=AssertionError('Started an agent')):
            for kind in ('note','todo'):
                self.bridge.dispatch({'action':'thoughts_save','body':'Local '+kind,'kind':kind})
        self.assertEqual(len(self.bridge.thoughts.store.snapshot()['notes']),2)
        self.assertTrue(self.bridge.busy)
        self.assertIsNone(self.bridge.current)

    def test_peek_save_command_never_becomes_memory_or_agent_context(self):
        self.bridge.peek.state['enabled'] = True
        self.bridge.peek.prefs['muted'] = True
        with patch.object(self.bridge,'send',side_effect=AssertionError('Started an agent')):
            self.bridge.peek.submit_voice('Save this thought: The private garden idea')
            self.bridge.peek.submit_voice('Add a todo: water the garden')
        notes = self.bridge.thoughts.store.snapshot()['notes']
        self.assertEqual(len(notes),2)
        self.assertEqual({n['kind'] for n in notes},{'note','todo'})
        self.assertEqual(self.bridge.peek.companion.store.items('memory'),[])
        self.assertNotIn('garden',self.bridge.peek.companion.context())

    def test_discarded_new_draft_uses_recoverable_trash(self):
        draft={'key':'draft-delete','body':'Still recoverable','kind':'note'}
        self.bridge.thoughts.store.write_draft(draft)
        self.bridge.dispatch(dict(draft,action='thoughts_discard'))
        snapshot=self.bridge.thoughts.store.snapshot()
        self.assertEqual(snapshot['drafts'],{})
        self.assertTrue(snapshot['notes'][0]['trashed'])
        note=snapshot['notes'][0]
        self.bridge.dispatch({'action':'thoughts_modify','id':note['id'],'revision':note['revision'],'operation':'restore'})
        self.assertFalse(self.bridge.thoughts.store.snapshot()['notes'][0]['trashed'])

    def test_peek_opens_the_requested_workspace_tab_without_an_agent(self):
        self.bridge.peek.state['enabled'] = True
        self.bridge.peek.prefs['muted'] = True
        with patch.object(self.bridge, 'send', side_effect=AssertionError('Started an agent')):
            self.bridge.peek.submit_voice('Show my to-dos')
            self.bridge.peek.submit_voice('Open my notes')
            self.bridge.peek.submit_voice('Find my notes about the garden')
        opened = [event for event in self.events if event['type'] == 'thoughts_open']
        self.assertEqual([(event['kind'], event['query']) for event in opened],
                         [('todo', ''), ('note', ''), ('note', 'the garden')])


if __name__ == '__main__':
    unittest.main()
