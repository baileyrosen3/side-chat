#!/usr/bin/env python3
"""Disposable GTK surface for visible mouse/keyboard/scroll/drag validation."""
import json,sys
from pathlib import Path
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,Gdk,GLib
root=Path(sys.argv[1]);root.mkdir(exist_ok=True)
window=Gtk.Window(title='Peek control fixture')
window.set_wmclass('jarvis-control-fixture','jarvis-control-fixture');window.set_default_size(540,430)
box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12);box.set_border_width(20);window.add(box)
box.pack_start(Gtk.Label(label='Peek input test · disposable window'),False,False,0)
entry=Gtk.Entry();entry.set_placeholder_text('Typing target');box.pack_start(entry,False,False,0)
button=Gtk.Button(label='Click target');box.pack_start(button,False,False,0)
area=Gtk.DrawingArea();area.set_size_request(400,80);area.add_events(Gdk.EventMask.BUTTON_PRESS_MASK|Gdk.EventMask.BUTTON_RELEASE_MASK|Gdk.EventMask.POINTER_MOTION_MASK);box.pack_start(area,False,False,0)
scroll=Gtk.ScrolledWindow();scroll.set_min_content_height(140);items=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=7)
for i in range(40):items.pack_start(Gtk.Label(label='Scroll target row '+str(i)),False,False,0)
scroll.add(items);box.pack_start(scroll,True,True,0)
state={'clicks':0,'text':'','scroll':0,'drag':False,'keys':[]}
def save():
 state['text']=entry.get_text();state['scroll']=scroll.get_vadjustment().get_value()
 (root/'result.json').write_text(json.dumps(state))
def clicked(*_):state['clicks']+=1;save()
button.connect('clicked',clicked);entry.connect('changed',lambda *_:save());scroll.get_vadjustment().connect('value-changed',lambda *_:save())
area.connect('draw',lambda widget,c:(c.set_source_rgb(.3,.35,.45),c.paint(),False)[-1])
area.connect('button-press-event',lambda *_:state.update(dragStart=True) or False)
area.connect('button-release-event',lambda *_:state.update(drag=state.get('dragStart',False)) or save() or False)
window.connect('destroy',Gtk.main_quit)
def layout():
 out={}
 for name,w in [('entry',entry),('button',button),('drag',area),('scroll',scroll)]:
  x,y=w.translate_coordinates(window,0,0);a=w.get_allocation();out[name]=[x,y,a.width,a.height]
 (root/'layout.json').write_text(json.dumps(out));save();return False
entry.connect('key-press-event',lambda _,e:state['keys'].append({'key':Gdk.keyval_name(e.keyval),'state':int(e.state)}) or save() or False)
window.connect('configure-event',lambda *_:GLib.timeout_add(100,layout) and False)
window.show_all();GLib.timeout_add(400,layout);Gtk.main()
