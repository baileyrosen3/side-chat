# SPDX-License-Identifier: GPL-3.0-or-later
"""Resident Parakeet Unified streaming adapter; reuse Voxtype's ONNX directory."""
import json
import os
from pathlib import Path
import select
import subprocess
import threading
import time
from jarvis.settings import DATA, model_path


class Parakeet:
    def __init__(self, prefs):
        import onnxruntime
        library=next((Path(onnxruntime.__file__).parent/'capi').glob('libonnxruntime.so.*'))
        chunk={'fast':.32,'balanced':.56,'accurate':1.12}[prefs['streamingProfile']]
        self.lock=threading.Lock()
        self.proc=subprocess.Popen([str(DATA/'bin/jarvis-parakeet'),str(model_path(prefs)),str(prefs['asrThreads']),str(chunk)],
                                   stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=None,text=True,bufsize=1,
                                   env=dict(os.environ,ORT_DYLIB_PATH=str(library)))
        try:
            if not self.read(45).get('ready'):raise RuntimeError('Parakeet did not become ready.')
        except Exception:self.close();raise

    def read(self, timeout=15):
        if not select.select([self.proc.stdout],[],[],timeout)[0]:
            raise RuntimeError('Parakeet recognition timed out. Try fewer CPU threads or the Fast streaming profile.')
        line=self.proc.stdout.readline()
        if not line:raise RuntimeError('Parakeet worker stopped. Check the Peek voice log.')
        result=json.loads(line)
        if result.get('error'):raise RuntimeError(result['error'])
        return result

    def request(self, op, **values):
        with self.lock:
            self.proc.stdin.write(json.dumps(dict(op=op,**values))+'\n');self.proc.stdin.flush()
            return self.read().get('text','').strip()

    def accept(self,samples):return self.request('audio',samples=samples.tolist())
    def finish(self):return self.request('finish')
    def reset(self):self.request('reset')
    def close(self):
        if self.proc.poll() is None:
            self.proc.terminate()
            try:self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:self.proc.kill();self.proc.wait()
        self.proc.stdin.close();self.proc.stdout.close()
