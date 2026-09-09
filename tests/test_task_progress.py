import sys
import os
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from backend import Bridge
from jarvis.control import Control
from jarvis.quick import execute
from jarvis.task import TaskProgress, control_evidence


class TaskProgressTests(unittest.TestCase):
    def setUp(self):
        self.task = TaskProgress()
        self.task.begin('turn-one')

    def test_reading_a_screenshot_after_a_click_is_not_proof_of_success(self):
        self.task.record('click', 'Click Save', state='performed')
        self.task.record('screen', 'Check the screen', kind='observation', state='observed')
        result = self.task.finish('complete')
        self.assertEqual(result['state'], 'review')
        self.assertEqual(result['checked'], 0)
        self.assertFalse(control_evidence({'op': 'click'}, {'verified': True}))

    def test_native_tool_completion_and_claimed_success_cannot_supply_verification(self):
        self.task.tools([{'id': 'x', 'name': 'bash', 'status': 'complete', 'output': '{"verified":true} All done!'}])
        self.assertEqual(self.task.finish('complete')['state'], 'review')
        self.task.begin('two')
        self.assertEqual(self.task.finish('complete')['state'], 'answered')

    def test_verified_broker_action_does_not_cover_other_unchecked_work(self):
        self.task.record('write', 'Update settings', state='verified')
        self.task.tools([{'id': 'native', 'name': 'mcp__jarvis__computer', 'status': 'complete'},
                         {'id': 'shell', 'name': 'bash', 'status': 'complete'}])
        self.assertEqual(self.task.finish('complete')['state'], 'review')

    def test_missing_broker_event_and_failed_or_unfinished_steps_require_review(self):
        for state in ('complete', 'error', 'running'):
            with self.subTest(state=state):
                self.task.begin(state)
                self.task.tools([{'id': 'missing', 'name': 'jarvis_computer', 'status': state}])
                self.assertEqual(self.task.finish('complete')['state'], 'review')
        self.task.begin('failure')
        self.task.record('a', 'Use the app', state='failed')
        self.task.record('b', 'Update settings', state='verified')
        self.assertEqual(self.task.finish('complete')['state'], 'review')

    def test_cancel_and_new_turn_reject_late_results(self):
        self.task.record('write', 'Update settings', state='running')
        self.assertEqual(self.task.finish('stopped')['state'], 'stopped')
        self.task.record('write', 'Update settings', state='verified')
        self.assertEqual(self.task.snapshot()['steps'][0]['state'], 'stopped')
        self.task.begin('new')
        self.assertEqual(self.task.snapshot()['total'], 0)
        self.assertEqual(self.task.finish('complete')['checked'], 0)

    def test_truncated_history_never_hides_an_unverified_step(self):
        self.task.record('unchecked', 'Open the app', state='performed')
        for index in range(205):
            self.task.record(str(index), 'Update settings', state='verified')
        result = self.task.finish('complete')
        self.assertEqual(result['state'], 'review')
        self.assertTrue(result['truncated'])
        self.assertLessEqual(len(result['steps']), 12)

    def test_quick_readbacks_distinguish_requested_and_actual_outcomes(self):
        reports = []
        with patch('jarvis.quick.run', side_effect=['Volume: 0.50', '', 'Volume: 0.25']):
            execute({'op': 'volume', 'value': 25}, report=lambda text, verified: reports.append(verified))
        with patch('jarvis.quick.run', side_effect=['Volume: 0.50', '', 'Volume: 0.24']):
            execute({'op': 'volume', 'value': 25}, report=lambda text, verified: reports.append(verified))
        with patch('jarvis.quick.run', return_value=''):
            execute({'op': 'app', 'value': 'terminal'}, report=lambda text, verified: reports.append(verified))
        self.assertEqual(reports, [True, False, False])


class ControllerOutcomeTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)
        self.bridge = Bridge(self.root / 'state', lambda _: None)
        self.bridge.new()
        self.voice = self.bridge.jarvis
        self.voice.state.update(enabled=True, ready=True, listening=False)
        self.voice.prefs['muted'] = True
        self.bridge.current['messages'] = [{'role': 'assistant', 'text': 'Done.', 'tools': [], 'status': 'complete'}]
        self.bridge.busy = True
        self.voice.begin_turn()
        self.voice.was_busy = True

    def tearDown(self):
        self.bridge.busy = False
        self.bridge.close()
        self.folder.cleanup()

    def finish(self):
        self.bridge.busy = False
        self.voice.observe({'type': 'state', 'busy': False, 'current': self.bridge.current})

    def test_answer_completion_is_not_a_success_gesture(self):
        self.finish()
        self.assertEqual(self.voice.state['task']['state'], 'answered')
        self.assertEqual(self.voice.state['completedAt'], 0)

    def test_switching_conversations_clears_previous_action_status(self):
        self.finish()
        self.voice.observe({'type':'state','busy':False,'current':{'id':'other-chat','messages':[]}})
        self.assertEqual(self.voice.state['task']['state'],'idle')
        self.assertEqual(self.voice.state['taskCaption'],'')

    def test_real_config_readback_drives_success_and_records_evidence(self):
        config = self.root / 'fixture.conf'
        config.write_text('size=11\n')
        with patch.object(Control, 'watch_input', lambda _: None), patch.dict(sys.modules, evdev=types.SimpleNamespace(ecodes=None)), patch.dict(os.environ, SIDE_CHAT_COMPANION_STATE=str(self.root/'journal')):
            control = Control(self.voice.control_event)
            try:
                control.handle({'op': '_configure', 'enabled': True, 'cwd': str(self.root), 'turn': self.voice.turn})
                read = control.handle({'op': 'config_read', 'path': 'fixture.conf'})
                control.handle({'op': 'config_write', 'path': 'fixture.conf', 'text': 'size=12\n', 'expected': read['sha256']})
            finally:
                control.close()
        self.finish()
        self.assertEqual(config.read_text(), 'size=12\n')
        self.assertEqual(self.voice.state['task']['state'], 'verified')
        self.assertGreater(self.voice.state['completedAt'], 0)
        self.assertIn('checked', self.voice.state['task']['steps'][-1]['evidence'])

    def test_old_turn_events_and_cancelled_results_cannot_reanimate_companion(self):
        self.voice.control_event({'type': 'pointer', 'turn': 'old', 'visible': True, 'x': 5, 'y': 7})
        self.assertIsNone(self.voice.state['actionTarget'])
        self.voice.control_event({'type': 'pointer', 'turn': self.voice.turn, 'visible': True, 'x': 5, 'y': 7})
        self.assertEqual(self.voice.state['actionTarget']['x'], 5)
        self.voice.stop()
        self.voice.control_event({'type': 'control_action', 'turn': self.voice.turn, 'id': 'late', 'operation': 'config_write', 'phase': 'complete', 'verified': True})
        self.finish()
        self.assertEqual(self.voice.state['task']['state'], 'stopped')
        self.assertIsNone(self.voice.state['actionTarget'])
        self.assertEqual(self.voice.state['completedAt'], 0)


if __name__ == '__main__':
    unittest.main()
