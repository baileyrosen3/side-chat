import json
import os
import importlib.util
from pathlib import Path
import tempfile
import socket
import struct
import threading
import time
import unittest
from unittest.mock import Mock, patch

from peek.voxtype import VoxtypeBridge, VoxtypeError, compatibility_problem


class VoxtypeBridgeTests(unittest.TestCase):
    def setUp(self):
        runtime=tempfile.TemporaryDirectory()
        self.addCleanup(runtime.cleanup)
        self.runtime=Path(runtime.name)/'voxtype';self.runtime.mkdir()
        environment=patch.dict(os.environ,XDG_RUNTIME_DIR=runtime.name)
        environment.start();self.addCleanup(environment.stop)
        status=patch.object(VoxtypeBridge,'status',side_effect=['idle','recording'])
        # Bridge status checks are independent of the command/file contract.
        self.status=status.start()
        self.addCleanup(status.stop)

    def test_known_broken_daemon_is_rejected_before_recording(self):
        (self.runtime/'version').write_text('1.0.1')
        with tempfile.TemporaryDirectory() as folder, patch('peek.voxtype.shutil.which',return_value='/usr/bin/voxtype'), patch('peek.voxtype.subprocess.run') as run:
            bridge=VoxtypeBridge(folder)
            with self.assertRaisesRegex(VoxtypeError,'unpatched 1.0.1'):bridge.start()
            run.assert_not_called()
            self.assertFalse(bridge.active)

    def test_guard_reads_daemon_version_not_packaged_cli_version(self):
        (self.runtime/'version').write_text('1.0.1-peek-streaming-fix')
        with patch('peek.voxtype.subprocess.run') as run:
            self.assertIsNone(compatibility_problem())
            run.assert_not_called()

    def test_missing_version_is_not_treated_as_verified_incompatibility(self):
        self.assertIsNone(compatibility_problem())

    def test_busy_dictation_is_not_hijacked_or_cancelled(self):
        self.status.side_effect=['recording']
        with tempfile.TemporaryDirectory() as folder, patch('peek.voxtype.shutil.which',return_value='/usr/bin/voxtype'), patch('peek.voxtype.subprocess.run') as run:
            bridge=VoxtypeBridge(folder)
            with self.assertRaisesRegex(VoxtypeError,'Finish regular dictation'):
                bridge.start()
            bridge.cancel()
            run.assert_not_called()
            self.assertFalse(bridge.active)

    def test_failed_start_cleans_up_and_allows_retry(self):
        self.status.side_effect=['idle',VoxtypeError('Daemon unavailable'),'idle','recording']
        with tempfile.TemporaryDirectory() as folder, patch('peek.voxtype.shutil.which',return_value='/usr/bin/voxtype'), patch('peek.voxtype.subprocess.run') as run:
            run.return_value=Mock(returncode=0,stdout='',stderr='')
            bridge=VoxtypeBridge(folder)
            with self.assertRaisesRegex(VoxtypeError,'Daemon unavailable'):bridge.start()
            self.assertFalse(bridge.active)
            self.assertIsNone(bridge.path)
            bridge.start()
            self.assertTrue(bridge.active)
            bridge.cancel()

    def test_meter_handles_split_frames_and_disconnect_without_capturing_audio(self):
        with tempfile.TemporaryDirectory() as folder, patch('peek.voxtype.shutil.which',return_value='/usr/bin/voxtype'):
            bridge=VoxtypeBridge(folder);bridge.active=True
            reader,writer=socket.socketpair()
            reader.setblocking(False);bridge.meter=reader
            try:
                frame=struct.pack('=Ifff',1,-.2,.1,-14)
                writer.sendall(frame[:7]);self.assertEqual(bridge.level(),0)
                writer.sendall(frame[7:]);self.assertAlmostEqual(bridge.level(),.6,places=5)
                self.assertEqual(bridge.level(),0)
                writer.close();self.assertEqual(bridge.level(),0)
                self.assertIsNone(bridge.meter)
            finally:writer.close();bridge.close_meter()

    def test_missing_meter_does_not_fail_recording(self):
        with tempfile.TemporaryDirectory() as folder, patch('peek.voxtype.shutil.which',return_value='/usr/bin/voxtype'):
            bridge=VoxtypeBridge(folder);bridge.active=True;bridge.runtime=Path(folder)
            self.assertEqual(bridge.level(),0)
            self.assertTrue(bridge.active)

    def test_start_uses_private_file_mode_without_typing_into_focused_apps(self):
        self.status.side_effect=['idle','streaming']
        with tempfile.TemporaryDirectory() as folder, patch('peek.voxtype.shutil.which', return_value='/usr/bin/voxtype') as which, patch('peek.voxtype.subprocess.run') as run:
            run.return_value=type('Result',(),{'returncode':0,'stdout':'','stderr':''})()
            bridge=VoxtypeBridge(folder)
            bridge.start()
            self.assertTrue(bridge.active)
            command=run.call_args.args[0]
            self.assertEqual(command[:3], ['/usr/bin/voxtype','record','start'])
            self.assertIn('--no-osd',command)
            self.assertIn('--no-auto-submit',command)
            file_arg=next(value for value in command if value.startswith('--file='))
            self.assertTrue(Path(file_arg.split('=',1)[1]).parent == Path(folder))
            which.assert_called_once_with('voxtype')

    def test_stop_reads_transcript_and_removes_private_file(self):
        with tempfile.TemporaryDirectory() as folder, patch('peek.voxtype.shutil.which', return_value='/usr/bin/voxtype'), patch('peek.voxtype.subprocess.run') as run:
            def invoke(command, **kwargs):
                if command[1:3] == ['record','stop']:
                    path=Path(command[command.index('--wait-file')+1])
                    path.write_text('  Open the terminal.  \n',encoding='utf-8')
                return type('Result',(),{'returncode':0,'stdout':json.dumps({'status':'transcribed'}),'stderr':''})()
            run.side_effect=invoke
            bridge=VoxtypeBridge(folder);bridge.start()
            self.assertEqual(bridge.stop(), 'Open the terminal.')
            self.assertFalse(any(Path(folder).iterdir()))
            self.assertFalse(bridge.active)

    def test_empty_transcript_is_not_reported_as_an_error(self):
        with tempfile.TemporaryDirectory() as folder, patch('peek.voxtype.shutil.which', return_value='/usr/bin/voxtype'), patch('peek.voxtype.subprocess.run') as run:
            run.side_effect=[
                type('Result',(),{'returncode':0,'stdout':'','stderr':''})(),
                type('Result',(),{'returncode':3,'stdout':json.dumps({'status':'nothing_to_transcribe'}),'stderr':''})(),
            ]
            bridge=VoxtypeBridge(folder);bridge.start()
            self.assertEqual(bridge.stop(), '')
            self.assertFalse(bridge.active)

    def test_missing_daemon_is_actionable(self):
        with patch('peek.voxtype.shutil.which', return_value=None):
            with self.assertRaisesRegex(VoxtypeError, 'Voxtype is not installed'):
                VoxtypeBridge(tempfile.mkdtemp())


@unittest.skipUnless(importlib.util.find_spec('sherpa_onnx'),'requires the local voice runtime')
class VoxtypeWorkerTests(unittest.TestCase):
    def recording_worker(self):
        from peek.voice_worker import VoiceWorker
        from peek.speech_queue import SpeechQueue
        worker=VoiceWorker.__new__(VoiceWorker)
        worker.lock=threading.RLock();worker.queue=SpeechQueue()
        worker.voxtype=Mock(active=True);worker.finish=threading.Event()
        worker.listening=True;worker.input_active=True;worker.record_epoch=2
        worker.input_generation=0;worker.input_utterance=2
        worker.speech_paused=threading.Event();worker.speech_paused.set()
        worker.player=None;worker.speaking=False;worker.emit=Mock()
        return worker

    def test_starting_reply_does_not_cancel_a_newer_recording(self):
        worker=self.recording_worker()
        worker.command({'action':'cancel','hold':True})
        worker.voxtype.cancel.assert_not_called()
        self.assertTrue(worker.listening)
        self.assertTrue(worker.input_active)
        # The old request may finish while the newer recording is still live.
        worker.resume_speech(utterance=1)
        self.assertTrue(worker.speech_paused.is_set())
        worker.input_active=False
        worker.resume_speech(utterance=2)
        self.assertFalse(worker.speech_paused.is_set())

    def test_explicit_stop_releases_daemon_and_speech_pause(self):
        worker=self.recording_worker()
        worker.command({'action':'cancel','input':True})
        worker.voxtype.cancel.assert_called_once()
        self.assertFalse(worker.listening)
        self.assertFalse(worker.input_active)
        self.assertFalse(worker.speech_paused.is_set())
        self.assertEqual(worker.record_epoch,3)

    def test_manual_toggle_emits_one_transcript_through_normal_controller_events(self):
        self.check_manual_recording('Open the terminal.')

    def test_empty_recording_shows_notice_without_submitting_a_request(self):
        self.check_manual_recording('')

    def test_old_recording_thread_cannot_cancel_new_session(self):
        self.check_manual_recording('',supersede=True)

    def check_manual_recording(self,text,supersede=False):
        from peek.voice_worker import VoiceWorker
        from peek.settings import DEFAULTS

        class FakeVoxtype:
            def __init__(self):
                self.active=False;self.started=threading.Event();self.cancelled=False
            def start(self):self.active=True;self.started.set()
            def stop(self):self.active=False;return text
            def level(self):return .4
            def cancel(self):self.active=False;self.cancelled=True

        worker=VoiceWorker.__new__(VoiceWorker)
        worker.lock=threading.RLock();worker.shutdown=threading.Event();worker.ready=threading.Event();worker.ready.set()
        worker.finish=threading.Event();worker.restart_after_finish=False;worker.record_epoch=1;worker.input_generation=0
        worker.input_utterance=0;worker.input_active=False;worker.listening=True;worker.capture=None
        worker.prefs=dict(DEFAULTS,asrModel='voxtype',handsFree=False,wakeEnabled=False,bargeIn=False)
        worker.voxtype=FakeVoxtype();worker.gate=Mock();worker.emit=Mock();worker.resume_speech=Mock()
        thread=threading.Thread(target=worker.record_voxtype,args=(1,),daemon=True);thread.start()
        try:
            self.assertTrue(worker.voxtype.started.wait(1))
            if supersede:
                with worker.lock:worker.record_epoch+=1
            else:worker.finish_input()
            thread.join(2)
            self.assertFalse(thread.is_alive())
            if supersede:
                self.assertFalse(worker.voxtype.cancelled)
                self.assertTrue(worker.voxtype.active)
                return
            events=[call.args[0] for call in worker.emit.call_args_list]
            self.assertIn('transcribing',events)
            microphone=next(call for call in worker.emit.call_args_list
                            if call.args[0]=='microphone' and call.kwargs['active'])
            self.assertEqual(microphone.kwargs['utterance'],worker.input_utterance)
            transcripts=[call for call in worker.emit.call_args_list if call.args[0]=='transcript']
            self.assertEqual(len(transcripts),1 if text else 0)
            if text:self.assertEqual(transcripts[0].kwargs['text'],text)
            else:self.assertIn('input_notice',events)
            self.assertFalse(worker.voxtype.active)
        finally:
            worker.shutdown.set();worker.finish.set();thread.join(1)


if __name__=='__main__':unittest.main()
