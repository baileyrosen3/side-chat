import json,time,sys
from pathlib import Path
import torch
from pocket_tts import TTSModel
from faster_whisper import WhisperModel
import numpy as np
import soundfile as sf
torch.set_num_threads(4)
start=time.monotonic();model=TTSModel.load_model();voice=model.get_state_for_audio_prompt('alba');loaded=time.monotonic()-start
asr=WhisperModel(str(Path.home()/'.local/share/side-chat/models/whisper-base.en'),device='cpu',compute_type='int8',cpu_threads=4,local_files_only=True)
rows=[]
for text in ['Hello. I am ready to help.','Open the browser and search for the weather.','Change the font size in the configuration file to twelve.']:
 start=time.monotonic();chunks=[];first=0
 for chunk in model.generate_audio_stream(voice,text,copy_state=True):
  if not chunks:first=time.monotonic()-start
  chunks.append(chunk.detach().cpu().numpy())
 elapsed=time.monotonic()-start
 audio=np.concatenate(chunks)
 samples=np.interp(np.arange(0,len(audio),model.sample_rate/16000),np.arange(len(audio)),audio).astype(np.float32)
 start=time.monotonic();segments,_=asr.transcribe(samples,language='en',beam_size=1,condition_on_previous_text=False,initial_prompt='Omarchy, Hyprland, font size, configuration, Codex, Claude, terminal.')
 recognized=''.join(s.text for s in segments)
 rows.append(dict(text=text,first_chunk_seconds=round(first,3),tts_seconds=round(elapsed,3),audio_seconds=round(len(audio)/model.sample_rate,3),recognized=recognized,asr_seconds=round(time.monotonic()-start,3)))
 sf.write('/tmp/peek-pocket-sample.wav',audio,model.sample_rate)
result=dict(load_seconds=round(loaded,3),rows=rows)
Path('/tmp/peek-pocket-benchmark.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
