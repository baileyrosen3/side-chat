#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Install private, pinned speech dependencies and verified open model artifacts."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile
import urllib.request
import sys
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from jarvis.settings import DEFAULTS, model_path

ROOT = Path(os.environ.get('SIDE_CHAT_DATA', Path(os.environ.get('XDG_DATA_HOME', Path.home()/'.local/share'))/'side-chat'))
ASR_REPO = 'csukuangfj/sherpa-onnx-streaming-zipformer-en-2023-06-26'
ASR_REV = '672fbf1b30579d6585301139bb363f42a0ad4a24'
TTS_URL = 'https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/kokoro-int8-multi-lang-v1_0.tar.bz2'
TTS_SHA = '75654a84864be26f345f020f4070c2c019e96dd1b7f9bf6e2ffd59efac6aa5a3'
PARAKEET_REPO = 'bobNight/parakeet-unified-en-0.6b-onnx'
PARAKEET_REV = '09e9060322d99c5f070010724786e6ee090fd51d'


def preflight(models_only=False):
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise SystemExit('The pinned Peek binaries currently require Linux x86_64.')
    if os.geteuid() == 0:
        raise SystemExit('Run speech setup as your desktop user, without sudo.')
    if not models_only:
        missing = [name for name in ('uv', 'cargo', 'rustc', 'cc') if not shutil.which(name)]
        if missing:
            raise SystemExit('Missing build tools: '+', '.join(missing)+
                             '. Run python3 setup.py --with-peek from the plugin root.')
        if not Path(__file__).with_name('parakeet').joinpath('Cargo.lock').is_file():
            raise SystemExit('Missing jarvis/parakeet/Cargo.lock. Download the complete plugin source.')


def digest(path):
    with Path(path).open('rb') as file:return hashlib.file_digest(file,'sha256').hexdigest()


def fetch(url, path, expected=None):
    path = Path(path)
    if path.is_file() and (not expected or digest(path) == expected):
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix+'.part')
    print('Downloading '+path.name, flush=True)
    with urllib.request.urlopen(url, timeout=90) as src, temp.open('wb') as dst:
        shutil.copyfileobj(src, dst, 1024*1024)
    actual = digest(temp)
    if expected and actual != expected:
        temp.unlink()
        raise ValueError('Checksum mismatch: '+path.name)
    temp.replace(path)


def models(with_kokoro=False, with_legacy=False):
    target = ROOT/'models'
    target.mkdir(parents=True, exist_ok=True)
    existing=model_path(DEFAULTS)
    names=('encoder.onnx','encoder.onnx.data','decoder_joint.onnx','tokenizer.model')
    if all((existing/name).is_file() for name in names):
        print('Reusing Parakeet: '+str(existing),flush=True)
    else:
        tree=json.load(urllib.request.urlopen(f'https://huggingface.co/api/models/{PARAKEET_REPO}/tree/{PARAKEET_REV}'))
        files={f['path']:f for f in tree}
        for name in names:
            fetch(f'https://huggingface.co/{PARAKEET_REPO}/resolve/{PARAKEET_REV}/{name}',target/'parakeet-unified-en-0.6b'/name,files[name].get('lfs',{}).get('oid'))
    if with_legacy:
        tree = json.load(urllib.request.urlopen(f'https://huggingface.co/api/models/{ASR_REPO}/tree/{ASR_REV}'))
        files = {f['path']: f for f in tree}
        names = [f'{part}-epoch-99-avg-1-chunk-16-left-128.int8.onnx' for part in ('encoder','decoder','joiner')]+['tokens.txt','README.md']
        for name in names:
            fetch(f'https://huggingface.co/{ASR_REPO}/resolve/{ASR_REV}/{name}', target/'asr'/name, files[name].get('lfs',{}).get('oid'))
    archive = target/'kokoro.tar.bz2'
    tts = target/'kokoro-int8-multi-lang-v1_0'
    if with_kokoro and not (tts/'model.int8.onnx').is_file():
        fetch(TTS_URL, archive, TTS_SHA)
        with tarfile.open(archive) as package:
            package.extractall(target, filter='data')
        archive.unlink()
    fetch('https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx', target/'silero_vad.onnx', '9e2449e1087496d8d4caba907f23e0bd3f78d91fa552479bb9c23ac09cbb1fd6')
    print('Models ready: '+str(target), flush=True)


def inventory():
    target=ROOT/'models'
    files=[]
    for path in sorted(target.rglob('*')):
        if path.is_file() and path.name!='inventory.json' and '.cache' not in path.parts:
            with path.open('rb') as file:checksum=hashlib.file_digest(file,'sha256').hexdigest()
            files.append({'file':str(path.relative_to(target)),'bytes':path.stat().st_size,'sha256':checksum})
    data={'models':[
        {'name':'Parakeet Unified English 0.6B','repository':PARAKEET_REPO,'revision':PARAKEET_REV,
         'license':'NVIDIA Open Model License','path':str(model_path(DEFAULTS)),
         'files':{name:digest(model_path(DEFAULTS)/name) for name in ('encoder.onnx','encoder.onnx.data','decoder_joint.onnx','tokenizer.model') if (model_path(DEFAULTS)/name).is_file()},
         'runtime':'parakeet-rs 0.3.7 / ONNX Runtime 1.29.0'},
        {'name':'Zipformer English streaming','repository':ASR_REPO,'revision':ASR_REV,'license':'Apache-2.0'},
        {'name':'Whisper base.en','repository':'Systran/faster-whisper-base.en','revision':'3d3d5dee26484f91867d81cb899cfcf72b96be6c','license':'MIT'},
        {'name':'Silero VAD','license':'MIT'},
        {'name':'Pocket TTS English','repository':'kyutai/pocket-tts','revision':'39592ff23c9ef80098bb74895d104c26275fe2c9','license':'CC-BY-4.0','runtime':'pocket-tts==3.1.0','cache':'Hugging Face local cache'},
        {'name':'Pocket preset voices','repository':'kyutai/pocket-tts-without-voice-cloning','revision':'e81d79e8194ad4c7ce879c87a4258ef20cbf2487',
         'voices':{'alba':'CC-BY-4.0 (Alba MacKenna)','marius':'CC0-1.0 (Selfie)','javert':'CC0-1.0 (Butter)',
                   'fantine':'CC-BY-4.0 (VCTK p244)','eponine':'CC-BY-4.0 (VCTK p262)','azelma':'CC-BY-4.0 (VCTK p303)',
                   'charles':'CC-BY-4.0 (VCTK p254)','mary':'CC-BY-4.0 (VCTK p333)','peter_yearsley':'CC0-1.0 (Voice-Zero / Peter Yearsley)'}}],
        'agent_browser':{'version':'0.36.0','license':'Apache-2.0','sha256':'56d15181e51e00213f907fcf39707cfc76bfa804ff20f5a9373661c73f96de5e'},'files':files}
    (target/'inventory.json').write_text(json.dumps(data,indent=2)+'\n')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models-only',action='store_true',help='Only fetch streaming ASR and VAD artifacts')
    parser.add_argument('--with-kokoro',action='store_true',help='Also fetch the optional Kokoro benchmark model')
    parser.add_argument('--with-legacy-asr',action='store_true',help='Also install Zipformer + Whisper as an optional recognition engine')
    args=parser.parse_args()
    preflight(args.models_only)
    if not args.models_only:
        if not (ROOT/'runtime/bin/python').exists():
            subprocess.run(['uv','venv','--python','3.12',str(ROOT/'runtime')],check=True)
        subprocess.run(['uv','pip','install','--python',str(ROOT/'runtime/bin/python'),'--torch-backend','cpu','-r',str(Path(__file__).with_name('requirements.txt'))],check=True)
        if args.with_legacy_asr:
            subprocess.run(['uv','pip','install','--python',str(ROOT/'runtime/bin/python'),
                            '-r',str(Path(__file__).with_name('requirements-legacy.txt'))],check=True)
    models(args.with_kokoro,args.with_legacy_asr)
    if not args.models_only:
        if not shutil.which('cargo'):raise SystemExit('Building the Parakeet adapter requires cargo (Rust). Install Rust, then rerun setup.')
        subprocess.run(['cargo','build','--release','--locked','--manifest-path',str(Path(__file__).with_name('parakeet')/'Cargo.toml')],
                       env=dict(os.environ,CARGO_TARGET_DIR=str(ROOT/'build/parakeet')),check=True)
        (ROOT/'bin').mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/'build/parakeet/release/jarvis-parakeet',ROOT/'bin/jarvis-parakeet.new')
        (ROOT/'bin/jarvis-parakeet.new').replace(ROOT/'bin/jarvis-parakeet')
        if args.with_legacy_asr:subprocess.run([str(ROOT/'runtime/bin/python'), '-c',
            "from huggingface_hub import snapshot_download; snapshot_download('Systran/faster-whisper-base.en',revision='3d3d5dee26484f91867d81cb899cfcf72b96be6c',local_dir="+repr(str(ROOT/'models/whisper-base.en'))+",allow_patterns=['config.json','model.bin','tokenizer.json','vocabulary.*','README.md'])"], check=True)
        subprocess.run([str(ROOT/'runtime/bin/python'), '-c', 'from jarvis.engines import pocket; pocket()'],
                       cwd=Path(__file__).resolve().parent.parent, check=True)
        browser=ROOT/'bin/agent-browser'
        fetch('https://github.com/vercel-labs/agent-browser/releases/download/v0.36.0/agent-browser-linux-x64', browser,
              '56d15181e51e00213f907fcf39707cfc76bfa804ff20f5a9373661c73f96de5e')
        browser.chmod(0o755)

    inventory()
