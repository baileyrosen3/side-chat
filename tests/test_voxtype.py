import json
import importlib.util
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

from peek.voxtype import VoxtypeBridge, VoxtypeError


class VoxtypeBridgeTests(unittest.TestCase):
    def test_start_uses_private_file_mode_without_typing_into_focused_apps(self):
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
    def test_manual_toggle_emits_one_transcript_through_normal_controller_events(self):
        from peek.voice_worker import VoiceWorker
        from peek.settings import DEFAULTS

        class FakeVoxtype:
            def __init__(self):
                self.active=False;self.started=threading.Event();self.cancelled=False
            def start(self):self.active=True;self.started.set()
            def stop(self):self.active=False;return 'Open the terminal.'
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
            worker.finish_input()
            thread.join(2)
            self.assertFalse(thread.is_alive())
            events=[call.args[0] for call in worker.emit.call_args_list]
            self.assertIn('transcribing',events)
            transcripts=[call for call in worker.emit.call_args_list if call.args[0]=='transcript']
            self.assertEqual(len(transcripts),1)
            self.assertEqual(transcripts[0].kwargs['text'],'Open the terminal.')
            self.assertFalse(worker.voxtype.active)
        finally:
            worker.shutdown.set();worker.finish.set();thread.join(1)


if __name__=='__main__':unittest.main()
