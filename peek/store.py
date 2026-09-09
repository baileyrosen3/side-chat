# SPDX-License-Identifier: GPL-3.0-or-later
"""Private, explicit companion memory, routines, watches and activity."""
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import time
import uuid


class Store:
    def __init__(self, folder):
        Path(folder).mkdir(parents=True,exist_ok=True,mode=0o700)
        self.path=Path(folder)/'companion.sqlite3'
        with self.db() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('CREATE TABLE IF NOT EXISTS items (id TEXT PRIMARY KEY, kind TEXT, updated REAL, data TEXT)')

    @contextmanager
    def db(self):
        db=sqlite3.connect(self.path,timeout=5)
        try:
            yield db;db.commit()
        finally:db.close()

    def items(self, kind, limit=200):
        with self.db() as db:
            return [dict(json.loads(row[2]),id=row[0],updated=row[1]) for row in db.execute('SELECT id,updated,data FROM items WHERE kind=? ORDER BY updated DESC LIMIT ?', (kind,limit))]

    def put(self, kind, data, identity=''):
        if not isinstance(data,dict):raise ValueError('Expected an object.')
        with self.db() as db:
            if identity:
                row=db.execute('SELECT kind FROM items WHERE id=?',(identity,)).fetchone()
                if not row or row[0]!=kind:raise ValueError('That item no longer exists.')
            else:identity=uuid.uuid4().hex
            db.execute('INSERT OR REPLACE INTO items VALUES (?,?,?,?)',(identity,kind,time.time(),json.dumps(data)))
        return identity

    def delete(self, kind, identity):
        with self.db() as db:db.execute('DELETE FROM items WHERE kind=? AND id=?',(kind,identity))

    def remember(self, text, identity=''):
        text=str(text).strip()
        if not text or len(text)>2000:raise ValueError('A memory must contain 1–2,000 characters.')
        if not identity and len(self.items('memory'))>=200:raise ValueError('Memory is full. Remove a memory first.')
        return self.put('memory',{'text':text},identity)

    def context(self):
        records=self.items('memory')
        return '\n'.join('- '+r['text'] for r in records)[:10000]

    def activity(self, text, result):
        self.put('activity',{'text':text,'result':result})
        with self.db() as db:db.execute("DELETE FROM items WHERE kind='activity' AND id NOT IN (SELECT id FROM items WHERE kind='activity' ORDER BY updated DESC LIMIT 80)")
