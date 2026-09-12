from datetime import datetime
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile
from zoneinfo import ZoneInfo

from reminders import parse
from thoughts import ThoughtStore, ThoughtsController
from workspace import WorkspaceController, read_capture


class ReminderParserTests(unittest.TestCase):
    now = datetime(2026, 9, 11, 12, tzinfo=ZoneInfo('America/New_York'))

    def parse(self, text, **kwargs):
        return parse(text, now=self.now, **kwargs)

    def test_date_suffix_is_removed_only_in_preview(self):
        preview = self.parse('Call Alex tomorrow at 3pm')
        self.assertEqual(preview['body'], 'Call Alex')
        self.assertEqual(datetime.fromtimestamp(preview['due'], self.now.tzinfo).isoformat(), '2026-09-12T15:00:00-04:00')
        self.assertIn('3:00 PM EDT', preview['label'])

    def test_relative_and_bare_afternoon_have_explicit_preview(self):
        self.assertEqual(self.parse('Laundry in 20 minutes')['due'], self.now.timestamp()+1200)
        self.assertEqual(self.parse('tomorrow 3', separate=True)['due'], self.parse('tomorrow at 3pm')['due'])

    def test_plain_task_and_non_suffix_are_unchanged(self):
        for text in ('Buy milk', 'Talk about tomorrow with Alex', 'Discuss timeline at work'):
            self.assertEqual(self.parse(text)['body'], text)
            self.assertEqual(self.parse(text)['due'], 0)

    def test_weekday_rollover_and_date_default(self):
        friday = datetime.fromtimestamp(self.parse('Friday at 9am')['due'], self.now.tzinfo)
        self.assertEqual(friday.day, 18)
        self.assertEqual(datetime.fromtimestamp(self.parse('tomorrow')['due'], self.now.tzinfo).hour, 9)

    def test_invalid_dates_and_past_times_are_not_scheduled(self):
        for text in ('today at 9am', 'tomorrow at 25:99', '2026-02-30', 'in 0 minutes', 'in 999 days'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.parse(text)
        with self.assertRaises(ValueError):
            self.parse('next whenever', separate=True)

    def test_local_dst_gap_is_rejected(self):
        now = datetime(2027, 3, 13, 12, tzinfo=self.now.tzinfo)
        with self.assertRaisesRegex(ValueError, 'daylight saving'):
            parse('Tomorrow at 2:30am', now=now)


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        from backend import Bridge
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.events = []
        self.bridge = Bridge(self.root/'state', self.events.append)
        self.addCleanup(self.bridge.close)
        self.bridge.thoughts.store.directory = self.root/'notes'
        self.bridge.peek.companion.quit.set()
        self.bridge.peek.companion.thread.join(timeout=3)
        self.store = self.bridge.thoughts.store
        self.workspace = self.bridge.workspace

    def task(self, **values):
        return self.store.save(dict(body='Call Alex', kind='todo', due=100, **values))

    def test_source_and_reminder_survive_edit_draft_and_conversion(self):
        note = self.task(source={'kind':'chat', 'id':'conversation', 'label':'Plans'})
        self.store.write_draft(dict(note, key='draft-1', dueText='tomorrow at 3pm'))
        self.assertEqual(self.store.drafts()['draft-1']['dueText'], 'tomorrow at 3pm')
        edited = self.store.save(dict(note, body='Call Alex about plans'))
        self.assertEqual(edited['due'], 100)
        self.assertEqual(edited['source']['id'], 'conversation')
        self.store.modify(edited['id'], edited['revision'], 'convert')
        converted = self.store.read(edited['id'])
        self.assertEqual((converted['kind'],converted['due'],converted['done']), ('note',0,False))
        self.assertEqual(converted['source'], note['source'])

    def test_delivery_is_persistent_deduplicated_and_does_not_change_note_revision(self):
        task = self.task()
        controller = self.bridge.thoughts
        with patch.object(controller,'notify_reminder') as notify:
            controller.check_reminders(now=200)
            controller.check_reminders(now=210)
            notify.assert_called_once()
        self.assertEqual(self.store.read(task['id'])['revision'], task['revision'])
        restarted = ThoughtsController(self.bridge)
        restarted.store = self.store
        with patch.object(restarted,'notify_reminder') as notify:
            restarted.check_reminders(now=300)
            notify.assert_not_called()

    def test_failed_delivery_retries_and_completed_or_trashed_tasks_stay_quiet(self):
        task = self.task()
        with patch.object(self.bridge.thoughts, 'notify_reminder', side_effect=ValueError('Offline')):
            with self.assertRaises(ValueError):
                self.bridge.thoughts.check_reminders(now=200)
        self.assertFalse((self.store.state/'reminders.json').exists())
        self.store.modify(task['id'],task['revision'],'complete')
        with patch.object(self.bridge.thoughts, 'notify_reminder') as notify:
            self.bridge.thoughts.check_reminders(now=210)
            notify.assert_not_called()
        task = self.task()
        self.store.modify(task['id'],task['revision'],'trash')
        with patch.object(self.bridge.thoughts, 'notify_reminder') as notify:
            self.bridge.thoughts.check_reminders(now=220)
            notify.assert_not_called()

    def test_snooze_and_done_reject_stale_notification_actions(self):
        task = self.task()
        with patch('thoughts.time.time',return_value=200):
            self.bridge.thoughts.reminder_action(task['id'],'snooze',100)
        self.assertEqual(self.store.read(task['id'])['due'],800)
        with self.assertRaisesRegex(ValueError,'changed'):
            self.bridge.thoughts.reminder_action(task['id'],'done',100)
        self.bridge.thoughts.reminder_action(task['id'],'done',800)
        self.assertTrue(self.store.read(task['id'])['done'])

    def test_search_finds_full_message_body_unicode_and_all_item_kinds(self):
        self.store.save({'body':'Café release plan'})
        self.task(title='Café release')
        self.bridge.new()
        chat = self.bridge.current
        chat['title']='Conversation'
        chat['messages']=[{'role':'assistant','text':'Café release details deep inside the conversation'}]
        self.bridge.save(chat)
        results=self.workspace.search('CAFÉ release')
        self.assertEqual({row['kind'] for row in results},{'note','todo','chat'})
        self.assertEqual(self.workspace.search('%'),[])
        self.assertEqual(self.workspace.search('absent café'),[])

    def test_deleted_chat_and_note_restore_and_collisions_are_preserved(self):
        self.bridge.new()
        identity=self.bridge.current['id']
        self.bridge.current['title']='Recovery café'
        self.bridge.save(self.bridge.current)
        self.bridge.dispatch({'action':'delete','id':identity})
        self.assertFalse(self.workspace.search('Recovery café'))
        result=self.workspace.search('Recovery café',trash=True)[0]
        self.workspace.restore(result)
        self.assertEqual(self.workspace.search('Recovery café')[0]['id'],identity)
        self.assertFalse(self.workspace.search('Recovery café',trash=True))
        note=self.store.save({'body':'Deleted note'})
        self.store.modify(note['id'],note['revision'],'trash')
        result=self.workspace.search('Deleted note',trash=True)[0]
        Path(note['path']).write_text('External file')
        with self.assertRaises(ValueError):
            self.workspace.restore(result)
        self.assertEqual(Path(note['path']).read_text(),'External file')

    def test_export_contains_consistent_database_and_recovery_without_overwriting(self):
        self.bridge.new()
        self.bridge.dispatch({'action':'draft','text':'Unsent message','source':{'kind':'note','id':'abc','label':'Source'}})
        task=self.task()
        self.store.write_draft({'key':'draft-export','body':'Unfinished note'})
        self.store.modify(task['id'],task['revision'],'trash')
        attachments=self.bridge.state/'attachments'
        attachments.mkdir();(attachments/'fixture.txt').write_text('Attachment')
        (self.bridge.state/'credentials.json').write_text('Do not export')
        destination=self.root/'backup.zip'
        self.workspace.export(destination)
        self.assertEqual(destination.stat().st_mode & 0o777,0o600)
        with zipfile.ZipFile(destination) as archive:
            names=archive.namelist()
            self.assertIn('state/thoughts/drafts.json',names)
            self.assertIn('state/attachments/fixture.txt',names)
            self.assertIn('notes/.thoughts/trash/'+task['id']+'.md',names)
            self.assertNotIn('state/credentials.json',names)
            archive.extract('state/chats.sqlite3',self.root/'exported')
        with closing(sqlite3.connect(self.root/'exported/state/chats.sqlite3')) as db:
            chat=json.loads(db.execute('SELECT data FROM chats').fetchone()[0])
            self.assertEqual(chat['draft'],'Unsent message')
            self.assertEqual(chat['draftSource']['id'],'abc')
        original=destination.read_bytes()
        with self.assertRaisesRegex(ValueError,'already exists'):
            self.workspace.export(destination)
        self.assertEqual(destination.read_bytes(),original)

    def test_superseded_search_does_not_emit_stale_results(self):
        self.workspace.latest['workspace_search']=2
        self.workspace.run({'action':'workspace_search','serial':1,'query':'old'})
        self.assertFalse(any(e['type']=='workspace_results' for e in self.events))


class CaptureTests(unittest.TestCase):
    def test_selection_reads_primary_without_writing_or_using_regular_clipboard(self):
        with patch('workspace.subprocess.check_output',return_value=b'{}'), patch('workspace.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout=b'Selected text')) as run:
            self.assertEqual(read_capture()['text'],'Selected text')
            self.assertEqual(run.call_args.args[0],['wl-paste','--no-newline','--type','text','--primary'])

    def test_empty_selection_requires_explicit_clipboard_choice(self):
        with patch('workspace.subprocess.check_output',return_value=b'{}'), patch('workspace.subprocess.run',return_value=SimpleNamespace(returncode=1,stdout=b'')) as run:
            with self.assertRaisesRegex(ValueError,'Use clipboard'):
                read_capture()
            self.assertEqual(run.call_count,1)
        with patch('workspace.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout=b'Copied text')) as run:
            self.assertEqual(read_capture(True)['source']['kind'],'clipboard')
            self.assertNotIn('--primary',run.call_args.args[0])

    def test_accessibility_selection_keeps_source_label(self):
        with patch('workspace.subprocess.check_output',return_value=b'{"pid":42,"class":"editor"}'), patch('workspace.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout='{"selection":"Editor passage"}')):
            result=read_capture()
            self.assertEqual(result['text'],'Editor passage')
            self.assertEqual(result['source']['label'],'editor')


if __name__ == '__main__':
    unittest.main()
