#!/usr/bin/env python3
"""Measure local TTS and streaming ASR using generated, non-microphone speech."""
import json
from pathlib import Path
import sys,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import soundfile as sf
from jarvis.engines import recognizer,synthesizer
start=time.monotonic(); tts=synthesizer(); tts_load=time.monotonic()-start
start=time.monotonic(); asr=recognizer(); asr_load=time.monotonic()-start
rows=[]
for text in ['Hello. I am ready to help.','Open the browser and search for the weather.','Change the font size in the configuration file to twelve.']:
    start=time.monotonic(); first=[]
    def callback(samples, progress):
        if not first:first.append(time.monotonic()-start)
        return 1
    audio=tts.generate(text,sid=26,speed=1.07,callback=callback)
    elapsed=time.monotonic()-start
    # Deterministic resampling for the benchmark; PipeWire handles live capture.
    samples=np.interp(np.arange(0,len(audio.samples),audio.sample_rate/16000),np.arange(len(audio.samples)),audio.samples).astype(np.float32)
    samples=np.concatenate([samples,np.zeros(16000,dtype=np.float32)])
    stream=asr.create_stream(); start=time.monotonic(); partial=[]
    for i in range(0,len(samples),1600):
        stream.accept_waveform(16000,samples[i:i+1600])
        while asr.is_ready(stream):asr.decode_stream(stream)
        if not partial and asr.get_result(stream):partial=[i/16000,time.monotonic()-start]
    stream.input_finished()
    while asr.is_ready(stream):asr.decode_stream(stream)
    rows.append(dict(text=text,recognized=asr.get_result(stream),tts_seconds=round(elapsed,3),first_chunk_seconds=round(first[0],3),audio_seconds=round(len(audio.samples)/audio.sample_rate,3),asr_compute_seconds=round(time.monotonic()-start,3),first_partial=partial))
    sf.write('/tmp/jarvis-benchmark.wav',audio.samples,audio.sample_rate)
result=dict(tts_load_seconds=round(tts_load,3),asr_load_seconds=round(asr_load,3),rows=rows)
Path('/tmp/jarvis-voice-benchmark.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
