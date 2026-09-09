# SPDX-License-Identifier: GPL-3.0-or-later
"""Local keyword detector and bounded follow-up conversation gate."""
import time
import contextlib
import sys
import numpy as np


class WakeDetector:
    def __init__(self, threshold=.97):
        from pymicro_wakeword import MicroWakeWord,MicroWakeWordFeatures,Model
        # The bundled upstream model is trained for “Hey Jarvis”; Peek is the
        # assistant's product name, but changing the phrase would require a
        # different detector model.
        with contextlib.redirect_stdout(sys.stderr):self.model=MicroWakeWord.from_builtin(Model.HEY_JARVIS)
        self.model.probability_cutoff=threshold
        self.features=MicroWakeWordFeatures();self.pending=b''

    def accept(self, samples):
        self.pending+=np.asarray(np.clip(samples,-1,1)*32767,dtype='<i2').tobytes()
        detected=False
        while len(self.pending)>=320:
            audio,self.pending=self.pending[:320],self.pending[320:]
            for features in self.features.process_streaming(audio):
                if self.model.process_streaming(features):detected=True
        return detected

    def reset(self):self.model.reset();self.features.reset();self.pending=b''
    def close(self):self.model.close()


class ConversationGate:
    def __init__(self, seconds=12):self.seconds=seconds;self.until=0;self.addressed_until=0
    def wake(self,now=None):self.until=(time.monotonic() if now is None else now)+self.seconds
    def address(self,now=None):
        self.wake(now);self.addressed_until=self.until
    def accepts_interrupt(self,now=None):return (time.monotonic() if now is None else now)<self.addressed_until
    def consume_address(self):self.addressed_until=0
    def active(self,now=None):return (time.monotonic() if now is None else now)<self.until
    def standby(self):self.until=0;self.addressed_until=0
