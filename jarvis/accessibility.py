#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded AT-SPI helper using the system PyGObject installation, via JSON stdin."""
import json
import sys
import time


def inspect(command):
    import gi
    gi.require_version('Atspi','2.0')
    from gi.repository import Atspi
    Atspi.set_timeout(400,1000)
    pid=int(command['pid']);desktop=Atspi.get_desktop(0)
    app=None
    for i in range(desktop.get_child_count()):
        candidate=desktop.get_child_at_index(i)
        if candidate.get_process_id()==pid:app=candidate;break
    if app is None:return {'nodes':[],'selection':'','note':'This app does not expose an AT-SPI tree. Use screenshots and native input.'}
    nodes=[];selection='';deadline=time.monotonic()+3
    queue=[(app,[])];objects={}
    while queue and len(nodes)<180 and time.monotonic()<deadline:
        node,path=queue.pop(0)
        try:
            role=node.get_role_name();name=node.get_name() or ''
            states=node.get_state_set()
            if role=='password text':continue
            showing=states.contains(Atspi.StateType.SHOWING)
            record={'path':path,'name':name[:180],'role':role,'actions':[],'editable':False}
            action=node.get_action_iface()
            if action:record['actions']=[action.get_action_name(i) for i in range(min(8,action.get_n_actions()))]
            record['editable']=bool(node.get_editable_text_iface())
            component=node.get_component_iface()
            if showing and component:
                r=component.get_extents(Atspi.CoordType.WINDOW)
                if r.x>=0 and r.y>=0 and r.width>0 and r.height>0:record['bounds']=[r.x,r.y,r.width,r.height]
            if command.get('selection') and states.contains(Atspi.StateType.FOCUSED):
                text=node.get_text_iface()
                if text and text.get_n_selections():
                    r=text.get_selection(0);selection=Atspi.Text.get_text(text,r.start_offset,min(r.end_offset,r.start_offset+8000))
            if showing and (name or record['actions'] or record['editable']):
                nodes.append(record);objects[tuple(path)]=node
            if len(path)<9:
                for i in range(min(60,node.get_child_count())):queue.append((node.get_child_at_index(i),path+[i]))
        except Exception:continue
    target=command.get('target')
    if target:
        actual=next((n for n in nodes if n['path']==target['path']),None)
        if not actual or any(actual.get(k)!=target.get(k) for k in ('name','role','bounds')):
            raise ValueError('Accessible target changed. Inspect the app again.')
        node=objects[tuple(target['path'])]
        if command.get('action')=='set_text':
            edit=node.get_editable_text_iface()
            if not edit or not edit.set_text_contents(str(command.get('text',''))):raise ValueError('Text field rejected the edit.')
            return {'performed':'set_text','verified':Atspi.Text.get_text(node.get_text_iface(),0,-1)==command.get('text','')}
        action=node.get_action_iface();requested=command.get('action')
        if not action or requested not in actual['actions']:raise ValueError('Choose an action returned by inspect.')
        if not action.do_action(actual['actions'].index(requested)):raise ValueError('The app rejected that action.')
        return {'performed':requested,'next':'Inspect the app or screenshot to verify its result.'}
    return {'nodes':nodes,'selection':selection}


if __name__=='__main__':
    try:print(json.dumps(inspect(json.load(sys.stdin))))
    except Exception as e:print(json.dumps({'error':str(e)}));sys.exit(1)
