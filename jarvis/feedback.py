# SPDX-License-Identifier: GPL-3.0-or-later
"""Brief public progress cues, based on observed work rather than model reasoning."""
ACKNOWLEDGMENT = 'Got it.'


class SpokenFeedback:
    def __init__(self):
        self.active=False

    def start(self, now):
        self.active=True;self.started=now;self.last_spoken=now
        self.acknowledged=False;self.activity='';self.used=set();self.updates=0

    def finish(self):
        self.active=False

    def spoken(self, now):
        if self.active:self.acknowledged=True;self.last_spoken=now

    def tools(self, tools):
        running=[str(t.get('name','')).lower() for t in tools if t.get('status')=='running']
        name=running[-1] if running else ''
        if any(word in name for word in ('search','web','browse')):self.activity="I'm looking that up."
        elif any(word in name for word in ('read','list','grep','find')):self.activity="I'm checking the details."
        elif any(word in name for word in ('edit','write','patch')):self.activity="I'm making the changes."
        elif name:self.activity="I'm working on it."
        else:self.activity=''

    def due(self, now, blocked=False):
        if not self.active or blocked:return ''
        if not self.acknowledged:
            if now-self.started<.25:return ''
            self.spoken(now)
            return ACKNOWLEDGMENT if now-self.started<2 else ''
        # Leave room for actual commentary; never repeat a loop of filler.
        if now-self.last_spoken<10 or self.updates>=3:return ''
        text=self.activity
        if not text or text in self.used:
            if now-self.last_spoken<25 or 'waiting' in self.used:return ''
            text="This is taking a little longer. I'm still on it."
            self.used.add('waiting')
        self.used.add(text);self.updates+=1;self.spoken(now)
        return text
