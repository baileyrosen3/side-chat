# SPDX-License-Identifier: GPL-3.0-or-later
"""Validated preferences shared by the UI controller and resident voice worker."""
import math
import os
from pathlib import Path

DATA_HOME = Path(os.environ.get('XDG_DATA_HOME', Path.home()/'.local/share'))
DATA = Path(os.environ.get('SIDE_CHAT_DATA', DATA_HOME/'side-chat'))
DEFAULTS = dict(scope='desktop', source='', sink='', voice='alba', handsFree=True,
                muted=False, reducedMotion=False, bargeIn=True, echoCancellation=True, spokenProgress=True,
                adaptivePause=True, noiseRejection='balanced',
                asrModel='parakeet-unified', modelPath='', asrThreads=4,
                streamingProfile='fast', endSilence=.45, minSpeech=.18,
                vadThreshold=.55, maxUtterance=25, ttsModel='pocket', ttsThreads=4,
                volume=1.0, speechRate=1.0, wakeEnabled=False, wakeThreshold=.97,
                followupSeconds=12, screenContext='on-request', selectionContext=False,
                screenImages=True, memoryEnabled=True, quickCommands=True,
                personality='balanced', expressiveness=1.0, companionPosition=.16)
ENUMS = dict(scope=('desktop','browser'), asrModel=('parakeet-unified','zipformer-whisper'),
             streamingProfile=('fast','balanced','accurate'), ttsModel=('pocket','kokoro'),
             voice=('alba','marius','javert','fantine','eponine','azelma','charles','mary','peter_yearsley','af_heart','af_bella','am_michael'),
             screenContext=('off','on-request','always'),personality=('concise','balanced','witty'),noiseRejection=('balanced','strong'))
RANGES = dict(asrThreads=(1,12), ttsThreads=(1,12), endSilence=(.3,2),
              minSpeech=(.1,.7), vadThreshold=(.2,.9), maxUtterance=(5,60),
              volume=(0,1.5), speechRate=(.7,1.4),wakeThreshold=(.5,.99),followupSeconds=(5,60),expressiveness=(0,1.5),companionPosition=(0,1))
RELOAD = {'asrModel','modelPath','asrThreads','streamingProfile','endSilence','minSpeech',
          'vadThreshold','maxUtterance','ttsModel','ttsThreads','wakeEnabled','wakeThreshold','noiseRejection'}
VOICES = {'pocket':('alba','marius','javert','fantine','eponine','azelma','charles','mary','peter_yearsley'),
          'kokoro':('af_heart','af_bella','am_michael')}


def model_path(prefs):
    if prefs.get('modelPath'):return Path(prefs['modelPath']).expanduser()
    shared=DATA_HOME/'voxtype/models/parakeet-unified-en-0.6b'
    complete=all((shared/name).is_file() for name in
                 ('encoder.onnx','encoder.onnx.data','decoder_joint.onnx','tokenizer.model'))
    return shared if complete else DATA/'models/parakeet-unified-en-0.6b'


def validate(current, values, check_files=True):
    result=dict(current)
    if not isinstance(values,dict):raise ValueError('Peek settings must be an object.')
    for key,value in values.items():
        if key not in DEFAULTS:raise ValueError('Unknown Peek setting: '+key)
        if key in ENUMS:
            if value not in ENUMS[key]:raise ValueError('Unsupported '+key+'.')
        elif key in RANGES:
            lo,hi=RANGES[key]
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not lo<=value<=hi:
                raise ValueError(f'{key} must be between {lo} and {hi}.')
            if key in ('asrThreads','ttsThreads','maxUtterance'):
                if int(value)!=value:raise ValueError(key+' must be a whole number.')
                value=int(value)
        elif isinstance(DEFAULTS[key],bool):
            if not isinstance(value,bool):raise ValueError(key+' must be on or off.')
        elif not isinstance(value,str) or len(value)>4096 or '\x00' in value:
            raise ValueError('Invalid '+key+'.')
        result[key]=value
    if result['voice'] not in VOICES[result['ttsModel']]:
        if 'voice' in values and 'ttsModel' not in values:raise ValueError('That voice belongs to a different speech model.')
        result['voice']=VOICES[result['ttsModel']][0]
    if result['ttsModel']=='pocket' and 'speechRate' in values and result['speechRate']!=1:
        raise ValueError('Pocket TTS uses its natural voice pace. Speech rate is available with Kokoro.')
    if check_files and {'asrModel','modelPath'} & values.keys():
        if result['asrModel']=='parakeet-unified':
            missing=[name for name in ('encoder.onnx','encoder.onnx.data','decoder_joint.onnx','tokenizer.model') if not (model_path(result)/name).is_file()]
            if missing:raise ValueError('Parakeet model is incomplete: '+', '.join(missing))
        elif not (DATA/'models/whisper-base.en/model.bin').is_file():
            raise ValueError('The legacy Whisper model is not installed.')
    if check_files and values.get('ttsModel')=='kokoro' and not (DATA/'models/kokoro-int8-multi-lang-v1_0/model.int8.onnx').is_file():
        raise ValueError('Install optional Kokoro with python3 jarvis/setup.py --with-kokoro.')
    return result


def model_info(prefs):
    path=model_path(prefs)
    return {'modelResolvedPath':str(path), 'parakeetAvailable':all((path/n).is_file() for n in ('encoder.onnx','encoder.onnx.data','decoder_joint.onnx','tokenizer.model')),
            'kokoroAvailable':(DATA/'models/kokoro-int8-multi-lang-v1_0/model.int8.onnx').is_file()}


def scope_instruction(scope):
    if scope=='desktop':
        return ('Peek control mode for THIS turn: DESKTOP. Browser requests mean the user’s visible default Omarchy browser. '
                'Use the Peek computer tool with op="browser", args=["open", "https://www.google.com"] (substitute the requested URL); '
                'this launches the configured browser and normal profile on the desktop. Then use windows, focus, screenshot, and native mouse/keyboard operations. '
                'Do not use your built-in browser tool, Playwright, headless Chromium, or a separate browser context in Desktop mode. '
                'A hidden page does not fulfill a request to open a website. Verify visible results before saying it opened. ')
    return ('Peek control mode for THIS turn: BROWSER. Use the Peek computer tool op="browser" for an isolated headless Chromium session. '
            'Do not launch or control host desktop apps in Browser mode. Explain that pages open in the isolated browser when relevant. ')
