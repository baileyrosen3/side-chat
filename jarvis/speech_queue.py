# SPDX-License-Identifier: GPL-3.0-or-later
"""Cancelable speech with disposable progress cues that never delay an answer."""
from collections import deque
from dataclasses import dataclass, field
import threading
import time


@dataclass
class SpeechJob:
    text: str
    turn: str = ''
    voice: str = ''
    status: bool = False
    queued_at: float = field(default_factory=time.monotonic)
    cancelled: threading.Event = field(default_factory=threading.Event)


class SpeechQueue:
    def __init__(self):
        self.condition=threading.Condition()
        self.pending=deque();self.active=None

    def cancel(self, status_only=False):
        with self.condition:
            for job in list(self.pending):
                if not status_only or job.status:
                    job.cancelled.set();self.pending.remove(job)
            active=self.active
            if active and (not status_only or active.status):
                active.cancelled.set();return True
            return False

    def put(self, job):
        with self.condition:
            if job.status and (self.pending or (self.active and not self.active.cancelled.is_set())):return False
            if len(self.pending)>=48:raise ValueError('Speech queue is full. Stop speech to clear it.')
            self.pending.append(job);self.condition.notify();return True

    def get(self):
        with self.condition:
            if not self.pending:self.condition.wait(.1)
            while self.pending:
                job=self.pending.popleft()
                if job.cancelled.is_set() or (job.status and time.monotonic()-job.queued_at>2):continue
                self.active=job;return job
            return None

    def finish(self, job):
        with self.condition:
            if self.active is job:self.active=None
