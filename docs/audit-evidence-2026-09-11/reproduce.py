from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import json, sys, tempfile, threading, queue, time
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from native_bridge import NativeBridge
from thoughts import ThoughtStore
from workspace import WorkspaceController

# Hold startup, cancel, then release it. The RPC double never starts a real agent.
bridge=NativeBridge()
bridge.cancelled=threading.Event(); bridge.lock=threading.RLock(); bridge.ui_requests=[]
bridge.save=Mock();bridge.emit=Mock();bridge.snapshot=Mock();bridge.remember_native=Mock()
bridge.close_rpc=Mock();bridge.busy=True
startup=threading.Event();release=threading.Event();rpc=Mock();rpc.events=queue.Queue()
rpc.events.put({'type':'agent_end'})
rpc.request.return_value={'messages':[]}
sent=[]
def send(value):
    sent.append(value['type'])
    if value['type']=='prompt': rpc.events.put({'type':'agent_end'})
rpc.send.side_effect=send
bridge.rpc=rpc
def ensure(chat):startup.set();release.wait(3);return rpc
bridge.ensure_rpc=ensure
chat={'id':'audit','agent':'codex','messages':[{'role':'user','text':'audit'}, {'role':'assistant','text':''}]}
worker=threading.Thread(target=bridge.generate_native,args=(chat,'audit',[]));worker.start();startup.wait(2)
bridge.cancelled.set();release.set();worker.join(3)
print(json.dumps({'case':'cancel_during_native_startup','sent_after_cancellation':sent,'worker_finished':not worker.is_alive()}))

# A save commits Markdown before attempting to read/remove the recoverable draft.
with tempfile.TemporaryDirectory() as temp:
    store=ThoughtStore(Path(temp)/'state',Path(temp)/'notes')
    store.state.mkdir(parents=True)
    (store.state/'drafts.json').write_text('{invalid')
    try:store.save({'key':'draft-audit','body':'Do not duplicate me'})
    except Exception as error:
        print(json.dumps({'case':'invalid_draft_recovery_file','save_error':type(error).__name__,'markdown_files_committed':len(list(store.folder.glob('*.md')))}))

# Cache warm scanning and ranking at a realistic mature personal-library size.
with tempfile.TemporaryDirectory() as temp:
    import sqlite3
    folder=Path(temp);notes=folder/'notes';notes.mkdir()
    store=ThoughtStore(folder,notes)
    for i in range(2000):
        (notes/f'note-{i:04}.md').write_text('---\ncreated: "2026-09-01T12:00:00-04:00"\n---\n\n'+('Planning a project and collecting ideas. '*25))
    db=sqlite3.connect(folder/'chats.sqlite3');db.execute('CREATE TABLE chats (id TEXT, updated REAL, data TEXT)')
    for i in range(1000):
        data={'id':str(i),'title':'Planning project '+str(i),'messages':[{'text':'Review this project. '*100} for _ in range(20)]}
        db.execute('INSERT INTO chats VALUES (?,?,?)',(str(i),i,json.dumps(data)))
    db.commit();db.close()
    workspace=WorkspaceController(SimpleNamespace(state=folder,thoughts=SimpleNamespace(store=store)))
    samples=[]
    for n in range(4):
        started=time.perf_counter();result=workspace.search('project');samples.append(round((time.perf_counter()-started)*1000,1))
    print(json.dumps({'case':'search_2000_notes_1000_chats','wall_ms':samples,'matches':len(result),'chat_db_mb':round((folder/'chats.sqlite3').stat().st_size/1e6,1)}))
    workspace.close()
