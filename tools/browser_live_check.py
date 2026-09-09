"""Exercise headless Chromium input and its in-page AI marker on a local page."""
import json,sys,time
from pathlib import Path
from urllib.parse import quote
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from peek.control import Control,run,hypr
c=Control(lambda e:None)
html='''<!doctype html><html><head><title>Peek browser fixture</title></head><body style="font:18px sans-serif;padding:30px"><label>Test text <input id="test" aria-label="Test text"></label><button onclick="document.querySelector('output').textContent=document.querySelector('input').value">Verify</button><output role="status"></output></body></html>'''
try:
 before={w['address'] for w in hypr('clients')}
 c.handle({'op':'_configure','enabled':True,'scope':'browser'})
 def browser(*args):return json.loads(c.handle({'op':'browser','args':list(args)})['result'])
 browser('open','data:text/html,'+quote(html));browser('snapshot','-i')
 browser('fill','#test','Independent mouse ✓')
 marker=browser('get','count','#__side_chat_peek_pointer')['data']
 browser('click','button')
 result=browser('get','text','output')['data']
 assert result['text']=='Independent mouse ✓',result
 assert not [w for w in hypr('clients') if w['address'] not in before and (w.get('class')=='org.omarchy.peek.browser' or 'Peek browser fixture' in w.get('title',''))],'Headless mode opened a desktop window'
 print(json.dumps({'marker':marker,'output':result,'scope':c.scope}))
 Path('/tmp/peek-browser-live.json').write_text(json.dumps({'marker':marker,'output':result,'scope':c.scope}))
finally:
 try:browser('close')
 except Exception:pass
 c.close()
