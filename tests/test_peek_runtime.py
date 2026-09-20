import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

from backend import Bridge
from peek.audio import release_worker_audio
from peek.controller import PeekController
from peek.store import Store


class PeekRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.events = []
        self.bridge = Bridge(self.temp.name, self.events.append)

    def tearDown(self):
        self.bridge.close()
        self.temp.cleanup()

    def disable(self):
        self.bridge.dispatch({'action': 'peek_runtime', 'enabled': False})
        thread = self.bridge.peek.shutdown_thread
        if thread:
            thread.join(10)
            self.assertFalse(thread.is_alive(), 'Peek shutdown did not finish')
        self.assertFalse(self.bridge.peek.state.get('runtimeStopping'))
        self.assertFalse(self.bridge.peek.state['error'])

    def test_disable_stops_threads_and_database_access_and_preserves_data(self):
        peek = self.bridge.peek
        peek.companion.store.remember('Keep my preferences')
        threads = [peek.input_thread, peek.feedback_thread, peek.companion.thread]
        self.disable()
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertIsNone(peek.companion)
        self.assertIsNone(peek.voice)
        self.assertIsNone(peek.control)
        with patch.object(Store, 'db', side_effect=AssertionError('Disabled Peek opened its database')):
            for action in ('peek_status', 'peek_companion_status', 'peek_devices'):
                self.bridge.dispatch({'action': action})
            for command in ({'action': 'peek', 'enabled': True},
                            {'action': 'peek_toggle_listen'}, {'action': 'peek_standby'},
                            {'action': 'peek_memory_save', 'text': 'No'},
                            {'action': 'peek_say', 'text': 'No'},
                            {'action': 'peek_settings', 'settings': {'volume': .5}}):
                with self.assertRaisesRegex(ValueError, 'disabled'):
                    self.bridge.dispatch(command)
            with self.assertRaisesRegex(ValueError, 'disabled'):
                peek.ensure_control()
            self.assertFalse(peek.try_local('remember this'))
        self.bridge.dispatch({'action': 'peek_runtime', 'enabled': True})
        self.assertEqual(peek.companion.store.items('memory')[0]['text'], 'Keep my preferences')
        self.assertFalse(peek.enabled)
        self.assertIsNone(peek.voice)
        self.assertIsNone(peek.control)

    def test_disabled_restart_never_opens_companion_store_or_starts_threads(self):
        self.disable()
        self.bridge.close()
        with patch('peek.controller.Companion', side_effect=AssertionError('Started companion')):
            self.bridge = Bridge(self.temp.name, self.events.append)
        self.assertFalse(self.bridge.peek.prefs['runtimeEnabled'])
        self.assertIsNone(self.bridge.peek.feedback_thread)
        self.assertIsNone(self.bridge.peek.input_thread)
        self.bridge.new()
        self.assertIsNotNone(self.bridge.current)
        with patch.object(self.bridge.thoughts, 'check_reminders') as reminders:
            self.bridge.dispatch({'action': 'ping'})
            reminders.assert_called_once()

    def test_disable_does_not_cancel_plain_chat_or_close_its_session(self):
        rpc = Mock(peek_enabled=False)
        self.bridge.rpc = rpc
        self.bridge.busy = True
        self.disable()
        self.assertFalse(self.bridge.cancelled.is_set())
        rpc.close.assert_not_called()
        self.bridge.rpc = None
        self.bridge.busy = False

    def test_disable_cancels_peek_task_and_waits_without_holding_bridge_lock(self):
        peek = self.bridge.peek
        peek.state['enabled'] = True
        self.bridge.busy = True
        rpc = Mock(peek_enabled=True, proc=None)
        self.bridge.rpc = rpc
        def task():
            self.bridge.cancelled.wait(5)
            with self.bridge.lock:
                self.bridge.busy = False
        self.bridge.worker = threading.Thread(target=task)
        self.bridge.worker.start()
        self.disable()
        self.assertTrue(self.bridge.cancelled.is_set())
        self.assertFalse(self.bridge.worker.is_alive())
        self.assertIsNone(self.bridge.rpc)
        rpc.close.assert_called_once()

    def test_invalid_toggle_and_failed_persistence_leave_runtime_running(self):
        for value in (None, 'false', 0):
            with self.assertRaises(ValueError):
                self.bridge.dispatch({'action': 'peek_runtime', 'enabled': value})
        db = self.bridge.db
        try:
            self.bridge.db = Mock()
            self.bridge.db.execute.side_effect = sqlite3.OperationalError('read only')
            with self.assertRaises(sqlite3.OperationalError):
                self.bridge.dispatch({'action': 'peek_runtime', 'enabled': False})
        finally:
            self.bridge.db = db
        self.assertTrue(self.bridge.peek.prefs['runtimeEnabled'])
        self.assertTrue(self.bridge.peek.feedback_thread.is_alive())

    def test_hidden_local_task_finishes_before_database_shutdown(self):
        entered, finished = threading.Event(), threading.Event()
        peek = self.bridge.peek
        def task():
            entered.set()
            self.bridge.cancelled.wait(5)
            # A local command already in flight can finish its final write.
            peek.companion.store.activity('Cancelled', 'Stopped')
            finished.set()
        peek.local_worker = threading.Thread(target=task)
        peek.local_worker.start()
        self.assertTrue(entered.wait(2))
        self.disable()
        self.assertTrue(finished.is_set())
        self.assertFalse(peek.local_worker.is_alive())

    def test_reenable_waits_for_worker_cleanup(self):
        entered, release = threading.Event(), threading.Event()
        original = self.bridge.peek.enable
        def slow_stop(enabled):
            entered.set()
            release.wait(5)
            original(enabled)
        with patch.object(self.bridge.peek, 'enable', side_effect=slow_stop):
            self.bridge.dispatch({'action': 'peek_runtime', 'enabled': False})
            self.assertTrue(entered.wait(2))
            try:
                with self.assertRaisesRegex(ValueError, 'still shutting down'):
                    self.bridge.dispatch({'action': 'peek_runtime', 'enabled': True})
            finally:
                release.set()
                self.bridge.peek.shutdown_thread.join(5)
        self.bridge.dispatch({'action': 'peek_runtime', 'enabled': True})
        self.assertTrue(self.bridge.peek.prefs['runtimeEnabled'])

    def test_real_control_server_is_reaped_and_socket_removed(self):
        peek = self.bridge.peek
        peek.python = Path(sys.executable)
        peek.ensure_control()
        proc = peek.control
        self.assertTrue(peek.socket.exists())
        self.disable()
        self.assertIsNotNone(proc.poll())
        self.assertFalse(peek.socket.exists())
        self.assertEqual(peek.reader_threads, [])


class WorkerGroupTests(unittest.TestCase):
    def test_forced_cleanup_only_unloads_the_workers_own_echo_module(self):
        modules = '[{"index":1,"name":"module-echo-cancel","argument":"source_name=side_chat_peek_mic_123 sink_name=side_chat_peek_speaker_123"},' \
                  '{"index":2,"name":"module-echo-cancel","argument":"source_name=side_chat_peek_mic_1234 sink_name=side_chat_peek_speaker_1234"},' \
                  '{"index":3,"name":"module-echo-cancel","argument":"source_name=other sink_name=other"}]'
        with patch('peek.audio.run', side_effect=[modules, '']) as run:
            release_worker_audio(123)
        self.assertEqual(run.call_count, 2)
        run.assert_called_with('pactl', 'unload-module', '1')

    def test_child_is_killed_even_if_parent_exits_first(self):
        child_code = 'import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(60)'
        code = ('import subprocess,sys; child=subprocess.Popen([sys.executable,"-c",'
                + repr(child_code) + ']); print(child.pid,flush=True); sys.stdin.read()')
        proc = subprocess.Popen([sys.executable, '-c', code], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, text=True, start_new_session=True)
        try:
            child = int(proc.stdout.readline())
            PeekController.reap_worker(proc, grace=1)
            self.assertIsNotNone(proc.poll())
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                stat = Path(f'/proc/{child}/stat')
                if not stat.exists() or stat.read_text().rsplit(')', 1)[1].split()[0] == 'Z':
                    break
                time.sleep(.02)
            else:
                self.fail('Worker child was left running')
        finally:
            try:os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:pass
            proc.wait(timeout=3)
            proc.stdout.close()


if __name__ == '__main__':
    unittest.main()
