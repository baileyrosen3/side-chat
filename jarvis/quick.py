# SPDX-License-Identifier: GPL-3.0-or-later
"""Exact everyday commands. No generated shell strings or implicit compound actions."""
import re
import json
import subprocess


def parse(text):
    original=re.sub(r'^please\s+','',text.strip(),flags=re.I)
    url=re.fullmatch(r'open (https?://\S+)',original,re.I)
    if url:return {'op':'url','value':url[1]}
    text=re.sub(r'^please\s+','',text.strip().lower()).rstrip('.!?')
    m=re.fullmatch(r'(?:set |turn )?(?:the )?(volume|brightness)(?: to)? (\d{1,3})(?:\s*%| percent)?',text)
    if m:
        n=int(m[2]);maximum=100
        if not 0<=n<=maximum:raise ValueError('Use a percentage from 0 to 100.')
        return {'op':m[1],'value':n}
    m=re.fullmatch(r'(?:turn )?(?:the )?(volume|brightness) (up|down)',text)
    if m:return {'op':m[1],'delta':5 if m[2]=='up' else -5}
    if text in ('mute','mute audio','unmute','unmute audio'):return {'op':'mute','value':not text.startswith('unmute')}
    media={'pause music':'pause','pause media':'pause','resume music':'play','play music':'play','next song':'next','next track':'next','previous track':'previous','previous song':'previous'}
    if text in media:return {'op':'media','value':media[text]}
    m=re.fullmatch(r'(?:switch|go)(?: to)?(?: workspace)? (\d{1,2})',text)
    if m and 1<=int(m[1])<=20:return {'op':'workspace','value':int(m[1])}
    apps={'open terminal':'terminal','open the terminal':'terminal','open browser':'browser','open my browser':'browser','open files':'nautilus','open file manager':'nautilus'}
    if text in apps:return {'op':'app','value':apps[text]}
    if text in ('open google','open google in my browser','open google in the browser'):return {'op':'url','value':'https://www.google.com'}
    m=re.fullmatch(r'open (https?://\S+)',text)
    if m:return {'op':'url','value':m[1]}
    return None


def run(argv):
    result=subprocess.run(argv,capture_output=True,text=True,timeout=8)
    if result.returncode:raise ValueError(result.stderr.strip()[-700:] or 'Command failed: '+argv[0])
    return result.stdout.strip()


def execute(command, scope='desktop', browser=None, report=None):
    def done(text, verified=False):
        if report:report(text,verified)
        return text
    op=command['op']
    if op=='url':
        if not browser:raise ValueError('Browser controller is unavailable.')
        browser(command['value'])
        return done(('Sent to your default browser: ' if scope=='desktop' else 'Opened in the isolated browser: ')+command['value'])
    if scope!='desktop':raise ValueError('Switch to Desktop mode to control apps, media, or system settings.')
    if op=='volume':
        current=run(['wpctl','get-volume','@DEFAULT_AUDIO_SINK@'])
        match=re.search(r'Volume:\s*([\d.]+)',current)
        if not match:raise ValueError('Could not read the speaker volume.')
        target=command.get('value',max(0,min(100,round(float(match[1])*100)+command.get('delta',0))))
        run(['wpctl','set-volume','@DEFAULT_AUDIO_SINK@',str(target)+'%'])
        actual=run(['wpctl','get-volume','@DEFAULT_AUDIO_SINK@'])
        actual=round(float(re.search(r'Volume:\s*([\d.]+)',actual)[1])*100)
        return done('Volume '+str(actual)+' percent.',actual==target)
    if op=='mute':
        run(['wpctl','set-mute','@DEFAULT_AUDIO_SINK@','1' if command['value'] else '0'])
        actual=run(['wpctl','get-volume','@DEFAULT_AUDIO_SINK@'])
        muted='[MUTED]' in actual
        return done('Audio muted.' if muted else 'Audio unmuted.',muted==command['value'])
    if op=='brightness':
        maximum=int(run(['brightnessctl','max']));current=int(run(['brightnessctl','get']))
        target=command.get('value',max(1,min(100,round(current/maximum*100)+command.get('delta',0))))
        run(['brightnessctl','set',str(max(1,target))+'%'])
        actual=int(run(['brightnessctl','get']))
        return done(f'Brightness {round(actual/maximum*100)} percent.',abs(actual-maximum*max(1,target)/100)<=1)
    if op=='media':
        run(['playerctl',command['value']]);actual=run(['playerctl','status']).lower()
        return done('Media '+actual+'.',{'pause':'paused','play':'playing'}.get(command['value'])==actual)
    if op=='workspace':
        run(['hyprctl','dispatch',f'hl.dsp.focus({{ workspace = "{command["value"]}" }})'])
        if json.loads(run(['hyprctl','activeworkspace','-j'])).get('id')!=command['value']:
            raise ValueError('The workspace did not change. Check whether the desktop is locked.')
        return done(f'Workspace {command["value"]}.',True)
    if op=='app':
        run(['omarchy','launch',command['value']]);return done('Launched '+('Files' if command['value']=='nautilus' else command['value'])+'.')
    raise ValueError('Unsupported quick command.')
