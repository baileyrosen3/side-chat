"""Semantic control and conflict-aware config edits on a disposable GTK fixture."""
import json,os,subprocess,sys,tempfile,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from peek.control import Control,hypr
from unittest.mock import patch
folder=Path(tempfile.mkdtemp(prefix='peek-companion-live-'))
before=hypr('activewindow');events=[];c=None;fixture_focus=None
locked=hypr('locked').get('locked',False)
p=subprocess.Popen(['/usr/bin/python3','-B',str(Path(__file__).with_name('control_fixture.py')),str(folder)],env=dict(os.environ,GTK_MODULES='atk-bridge'),stdout=subprocess.DEVNULL,stderr=open(folder/'gtk.log','w'))
try:
 deadline=time.monotonic()+10
 while time.monotonic()<deadline:
  window=next((w for w in hypr('clients') if w['pid']==p.pid),None)
  if window and (folder/'layout.json').exists():break
  time.sleep(.1)
 assert window,'Fixture did not open'
 subprocess.run(['hyprctl','dispatch','hl.dsp.focus({ window = "address:'+window['address']+'" })'],check=True,capture_output=True)
 time.sleep(.5)
 if locked:
  fixture_focus=patch('peek.control.hypr',side_effect=lambda kind:window if kind=='activewindow' else hypr(kind));fixture_focus.start()
 c=Control(events.append);c.handle({'op':'_configure','enabled':True,'scope':'desktop','cwd':str(folder)})
 observed=c.handle({'op':'inspect_app'});(folder/'tree.json').write_text(json.dumps(observed,indent=2))
 entry=next(n for n in observed['nodes'] if n['editable'])
 result=c.handle({'op':'accessible_action','target':entry['target'],'actionName':'set_text','text':'semantic edit verified'})
 assert result['verified'],result
 try:c.handle({'op':'accessible_action','target':entry['target'],'actionName':'set_text','text':'stale'})
 except ValueError:pass
 else:raise AssertionError('Old target accepted')
 observed=c.handle({'op':'inspect_app'});button=next(n for n in observed['nodes'] if n['name']=='Click target')
 c.handle({'op':'accessible_action','target':button['target'],'actionName':button['actions'][0]})
 time.sleep(.25);actual=json.loads((folder/'result.json').read_text())
 assert actual['text']=='semantic edit verified' and actual['clicks']==1,actual
 (folder/'fixture.conf').write_text('font_size = 11\n')
 read=c.handle({'op':'config_read','path':'fixture.conf'})
 write=c.handle({'op':'config_write','path':'fixture.conf','text':'font_size = 12\n','expected':read['sha256']})
 restored=c.handle({'op':'undo_restore','id':write['undoId']})
 assert restored['verified'] and (folder/'fixture.conf').read_text()=='font_size = 11\n'
 print(json.dumps({'folder':str(folder),'compositorFocusVerified':not locked,'semanticText':actual['text'],'clicks':actual['clicks'],'staleTargetRejected':True,'undoVerified':restored['verified'],'targetHighlighted':any(e.get('bounds') for e in events)},indent=2))
finally:
 if c:c.close()
 if fixture_focus:fixture_focus.stop()
 p.terminate();p.wait(timeout=4)
 if before.get('address'):subprocess.run(['hyprctl','dispatch','hl.dsp.focus({ window = "address:'+before['address']+'" })'],capture_output=True)
