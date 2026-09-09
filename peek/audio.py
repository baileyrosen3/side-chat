# SPDX-License-Identifier: GPL-3.0-or-later
"""PipeWire audio endpoints owned only for the lifetime of an armed voice worker."""
import json
import os
import subprocess


def run(*args):
    return subprocess.run(args,capture_output=True,text=True,timeout=6,check=True).stdout.strip()


def devices():
    nodes=json.loads(run('pw-dump'))
    return [{'id':p.get('node.name',''), 'name':p.get('node.description',p.get('node.name','')), 'kind':p['media.class']}
            for obj in nodes if (p:=obj.get('info',{}).get('props',{})).get('media.class') in ('Audio/Source','Audio/Sink')
            and not p.get('node.name','').startswith('side_chat_peek_')]


class EchoAudio:
    def __init__(self):
        self.module=None
        self.source=''
        self.sink=''
        self.aec=False

    def start(self, source='', sink='', echo=True):
        self.close()
        if not echo:
            self.source=source or run('pactl','get-default-source')
            self.sink=sink or run('pactl','get-default-sink')
            return
        suffix=str(os.getpid())
        self.source='side_chat_peek_mic_'+suffix
        self.sink='side_chat_peek_speaker_'+suffix
        args=['pactl','load-module','module-echo-cancel', 'aec_method=webrtc', 'rate=48000', 'channels=1',
              'aec_args="high_pass_filter=1 noise_suppression=1 analog_gain_control=0 digital_gain_control=0"',
              'source_name='+self.source,'sink_name='+self.sink,
              'source_properties=device.description=PeekMicrophone','sink_properties=device.description=PeekSpeaker']
        # Explicit masters avoid selecting a previous echo-cancellation virtual device.
        source=source or run('pactl','get-default-source')
        sink=sink or run('pactl','get-default-sink')
        args+=['source_master='+source,'sink_master='+sink]
        self.module=run(*args)
        self.aec=True

    def record(self):
        # Pulse's .monitor names are not PipeWire node names. Disable fallback:
        # a disconnected selected device must never silently switch to another mic.
        monitor=self.source.endswith('.monitor')
        target=self.source[:-8] if monitor else self.source
        props='node.dont-fallback=true node.dont-reconnect=true'
        if monitor:props+=' stream.capture.sink=true'
        return subprocess.Popen(['pw-record','--raw','--format','f32','--rate','16000','--channels','1',
                                 '--latency','32ms','-P',props,'--target',target,'-'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)

    def play(self, rate, sink=''):
        args=['pw-play','--raw','--format','f32','--rate',str(rate),'--channels','1','--latency','64ms']
        if self.aec:args+=['--target',self.sink]
        elif sink:args+=['--target',sink]
        return subprocess.Popen(args+['-'],stdin=subprocess.PIPE,stderr=subprocess.DEVNULL)

    def close(self):
        if self.module:
            try:run('pactl','unload-module',self.module)
            except (OSError,subprocess.SubprocessError):pass
        self.module=None
        self.aec=False


def terminate(proc):
    if proc and proc.poll() is None:
        proc.terminate()
        try:proc.wait(timeout=.3)
        except subprocess.TimeoutExpired:
            proc.kill();proc.wait(timeout=1)
