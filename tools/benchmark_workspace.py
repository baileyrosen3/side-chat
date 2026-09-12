"""Synthetic mature-library search benchmark; creates no user data."""
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from thoughts import ThoughtStore
from workspace import WorkspaceController, initialize_search, index_chat

with tempfile.TemporaryDirectory(prefix='side-chat-search-benchmark-') as directory:
    folder = Path(directory)
    notes = folder / 'notes'; notes.mkdir()
    store = ThoughtStore(folder, notes)
    for i in range(2000):
        (notes / f'note-{i:04}.md').write_text('---\ncreated: "2026-09-01T12:00:00-04:00"\n---\n\n' + 'Planning a project and collecting ideas. ' * 25)
    db = sqlite3.connect(folder / 'chats.sqlite3')
    db.execute('CREATE TABLE chats (id TEXT PRIMARY KEY, updated REAL, data TEXT)')
    initialize_search(db)
    for i in range(1000):
        chat = {'id': str(i), 'title': 'Planning project ' + str(i), 'agent': 'codex', 'updated': i,
                'messages': [{'text': 'Review this project. ' * 100} for _ in range(20)]}
        db.execute('INSERT INTO chats VALUES (?,?,?)', (str(i), i, json.dumps(chat)))
        index_chat(db, chat)
    db.commit(); db.close()
    workspace = WorkspaceController(SimpleNamespace(state=folder, thoughts=SimpleNamespace(store=store)))
    try:
        samples = []
        for _ in range(4):
            started = time.perf_counter()
            result = workspace.search('project')
            samples.append(round((time.perf_counter() - started) * 1000, 1))
        print(json.dumps({'notes': 2000, 'chats': 1000, 'query': 'project', 'milliseconds': samples, 'matches': len(result)}))
    finally:
        workspace.close()
