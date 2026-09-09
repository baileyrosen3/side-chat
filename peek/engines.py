# SPDX-License-Identifier: GPL-3.0-or-later
"""Resident CPU speech models. No network calls during inference."""
import os
from pathlib import Path
import sherpa_onnx as sherpa
from peek.settings import VOICES

DATA = Path(os.environ.get('SIDE_CHAT_DATA', Path(os.environ.get('XDG_DATA_HOME', Path.home()/'.local/share'))/'side-chat'))
MODELS = DATA/'models'


def recognizer(prefs=None):
    prefs=prefs or {}
    d=MODELS/'asr'
    return sherpa.OnlineRecognizer.from_transducer(
        tokens=str(d/'tokens.txt'),
        **{part:str(d/f'{part}-epoch-99-avg-1-chunk-16-left-128.int8.onnx') for part in ('encoder','decoder','joiner')},
        num_threads=prefs.get('asrThreads',2), sample_rate=16000, enable_endpoint_detection=True,
        rule1_min_trailing_silence=2.4, rule2_min_trailing_silence=prefs.get('endSilence',.65),
        rule3_min_utterance_length=prefs.get('maxUtterance',25), provider='cpu')


def synthesizer(prefs=None):
    d=MODELS/'kokoro-int8-multi-lang-v1_0'
    config=sherpa.OfflineTtsConfig(model=sherpa.OfflineTtsModelConfig(
        kokoro=sherpa.OfflineTtsKokoroModelConfig(
            model=str(d/'model.int8.onnx'), voices=str(d/'voices.bin'),
            tokens=str(d/'tokens.txt'), data_dir=str(d/'espeak-ng-data'),
            lexicon=str(d/'lexicon-gb-en.txt'), lang='en'),
        num_threads=(prefs or {}).get('ttsThreads',3), provider='cpu'), max_num_sentences=1)
    if not config.validate():
        raise RuntimeError('Speech output model is incomplete. Run peek/setup.py.')
    return sherpa.OfflineTts(config)


def vad(prefs=None):
    prefs=prefs or {}
    config=sherpa.VadModelConfig()
    config.silero_vad.model=str(MODELS/'silero_vad.onnx')
    config.silero_vad.min_silence_duration=prefs.get('endSilence',.65)
    config.silero_vad.min_speech_duration=prefs.get('minSpeech',.18)
    config.silero_vad.threshold=prefs.get('vadThreshold',.55)
    if prefs.get('noiseRejection')=='strong':
        config.silero_vad.threshold=max(.68,config.silero_vad.threshold)
        config.silero_vad.min_speech_duration=max(.28,config.silero_vad.min_speech_duration)
    config.silero_vad.max_speech_duration=prefs.get('maxUtterance',25)
    config.sample_rate=16000
    config.num_threads=1
    return sherpa.VoiceActivityDetector(config, buffer_size_in_seconds=30)


def final_recognizer(prefs=None):
    from faster_whisper import WhisperModel
    return WhisperModel(str(MODELS/'whisper-base.en'),device='cpu',compute_type='int8',cpu_threads=(prefs or {}).get('asrThreads',4),local_files_only=True)


def pocket(prefs=None):
    import torch
    from pocket_tts import TTSModel
    torch.set_num_threads((prefs or {}).get('ttsThreads',4))
    model=TTSModel.load_model(language='english')
    voices={name:model.get_state_for_audio_prompt(name) for name in VOICES['pocket']}
    return model,voices
