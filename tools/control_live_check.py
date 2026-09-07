import json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from jarvis.control import Control,hypr,bounds
c=Control(lambda e: print(json.dumps(e),flush=True))
try:
 target=next(w for w in hypr('clients') if w.get('title')=='Jarvis control fixture')
 monitor=next(m for m in hypr('monitors') if m['id']==target['monitor'])
 c.handle({'op':'_configure','enabled':True})
 c.handle({'op':'focus','window':target['address']})
 layout=json.loads(Path('/tmp/jarvis-control-fixture/layout.json').read_text())
 def action(op,widget,**extra):
  frame=c.handle({'op':'screenshot','screen':monitor['name']})['details']
  target=next(w for w in hypr('clients') if w.get('title')=='Jarvis control fixture')
  x,y,w,h=layout[widget];left,top,lw,lh=frame['bounds']
  px=(target['at'][0]+x+w/2-left)*frame['width']/lw;py=(target['at'][1]+y+h/2-top)*frame['height']/lh
  c.handle(dict(op=op,frame=frame['id'],x=px,y=py,**extra));time.sleep(.15)
 action('click','entry')
 action('type','entry',text='Jarvis ✓ café')
 action('key','entry',key='Ctrl+a')
 action('type','entry',text='Verified Unicode ✓')
 action('click','button')
 action('scroll','scroll',amount=-5)
 frame=c.handle({'op':'screenshot','screen':monitor['name']})['details'];target=next(w for w in hypr('clients') if w.get('title')=='Jarvis control fixture')
 x,y,w,h=layout['drag'];left,top,lw,lh=frame['bounds']
 ax=(target['at'][0]+x+20-left)*frame['width']/lw;ay=(target['at'][1]+y+h/2-top)*frame['height']/lh
 bx=ax+(w-40)*frame['width']/lw
 c.handle({'op':'drag','frame':frame['id'],'x':ax,'y':ay,'toX':bx,'toY':ay})
 time.sleep(.2)
 print('RESULT',Path('/tmp/jarvis-control-fixture/result.json').read_text())
finally:c.close()
