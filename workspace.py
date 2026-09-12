# SPDX-License-Identifier: GPL-3.0-or-later
"""Local search, explicit text capture, recovery, and workspace exports."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import zipfile

def initialize_search(db):
    db.executescript('''
        CREATE TABLE IF NOT EXISTS chat_search (id TEXT PRIMARY KEY, title TEXT, agent TEXT, updated REAL, body TEXT, folded TEXT, anchors TEXT);
        CREATE VIRTUAL TABLE IF NOT EXISTS chat_search_fts USING fts5(folded, content='chat_search', content_rowid='rowid', tokenize='trigram');
        CREATE TRIGGER IF NOT EXISTS chat_search_insert AFTER INSERT ON chat_search BEGIN
            INSERT INTO chat_search_fts(rowid,folded) VALUES (new.rowid,new.folded);
        END;
        CREATE TRIGGER IF NOT EXISTS chat_search_delete AFTER DELETE ON chat_search BEGIN
            INSERT INTO chat_search_fts(chat_search_fts,rowid,folded) VALUES ('delete',old.rowid,old.folded);
        END;
        CREATE TRIGGER IF NOT EXISTS chat_search_update AFTER UPDATE OF folded ON chat_search BEGIN
            INSERT INTO chat_search_fts(chat_search_fts,rowid,folded) VALUES ('delete',old.rowid,old.folded);
            INSERT INTO chat_search_fts(rowid,folded) VALUES (new.rowid,new.folded);
        END;
        CREATE TRIGGER IF NOT EXISTS chat_deleted_search AFTER DELETE ON chats BEGIN
            DELETE FROM chat_search WHERE id=old.id;
        END;
    ''')


def index_chat(db, chat):
    messages = chat.get('messages', [])
    body = '\n'.join(str(m.get('text', '')) for m in messages)
    anchors, offset = [], 0
    for i, message in enumerate(messages):
        anchors.append([offset, i])
        offset += len(str(message.get('text', '')).casefold()) + 1
    title = chat.get('title') or 'Conversation'
    folded = (title + '\n' + body).casefold()
    db.execute('''INSERT INTO chat_search VALUES (?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
        title=excluded.title,agent=excluded.agent,updated=excluded.updated,body=excluded.body,folded=excluded.folded,anchors=excluded.anchors
        WHERE chat_search.folded != excluded.folded OR chat_search.updated != excluded.updated OR chat_search.agent != excluded.agent OR chat_search.anchors != excluded.anchors''',
        (chat['id'], title, chat['agent'], chat['updated'], body, folded, json.dumps(anchors)))


def match_index(body, anchors, terms):
    positions = [body.casefold().find(term) for term in terms]
    position = min((p for p in positions if p >= 0), default=-1)
    return next((index for start, index in reversed(anchors) if start <= position), -1)


def excerpt(text, query, limit=180):
    text = ' '.join(str(text).split())
    terms = query.casefold().split()
    position = text.casefold().find(terms[0]) if terms else 0
    start = max(0, position - 45)
    return ('…' if start else '') + text[start:start + limit] + ('…' if len(text) > start + limit else '')


def read_capture(clipboard=False):
    """Read before opening the drawer; never synthesize Copy or change the clipboard."""
    if not clipboard:
        try:
            window = json.loads(subprocess.check_output(['hyprctl', 'activewindow', '-j'], timeout=1))
            if window.get('pid'):
                result = subprocess.run(['/usr/bin/python3', '-B', str(Path(__file__).parent / 'peek/accessibility.py')],
                                        input=json.dumps({'pid': window['pid'], 'selection': True}),
                                        capture_output=True, text=True, timeout=4)
                text = json.loads(result.stdout).get('selection', '') if result.returncode == 0 else ''
                if text.strip():
                    return {'text': text[:100_000], 'source': {'kind': 'selection', 'id': '', 'label': str(window.get('class') or 'Selection')[:100]}}
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    command = ['wl-paste', '--no-newline', '--type', 'text']
    if not clipboard:
        command.append('--primary')
    try:
        result = subprocess.run(command, capture_output=True, timeout=2)
        text = result.stdout.decode('utf-8') if result.returncode == 0 else ''
    except (OSError, UnicodeError, subprocess.SubprocessError):
        text = ''
    if not text.strip() or '\x00' in text:
        raise ValueError('No text on the clipboard.' if clipboard else 'No selected text was available. Copy it, then choose Use clipboard.')
    if len(text) > 100_000:
        raise ValueError('Select a shorter passage, under 100,000 characters.')
    return {'text': text, 'source': {'kind': 'clipboard' if clipboard else 'selection', 'id': '',
                                   'label': 'Clipboard' if clipboard else 'Selected text'}}


class WorkspaceController:
    def __init__(self, bridge):
        self.bridge = bridge
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='workspace')
        self.export_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='workspace-export')
        self.latest = {}
        self.closed = False

    def dispatch(self, command):
        self.latest[command.get('action')] = command.get('serial', 0)
        pool = self.export_pool if command.get('action') == 'workspace_export' else self.pool
        pool.submit(self.run, dict(command))

    def run(self, command):
        action, serial = command.get('action'), command.get('serial', 0)
        if self.closed or self.latest.get(action) != serial:
            return
        try:
            if action == 'workspace_search':
                result = {'type': 'workspace_results', 'results': self.search(command.get('query', ''), bool(command.get('trash')))}
            elif action == 'workspace_capture':
                result = {'type': 'workspace_capture', **read_capture(bool(command.get('clipboard')))}
            elif action == 'workspace_restore':
                self.restore(command)
                result = {'type': 'workspace_restored', 'id': command['id']}
            elif action == 'workspace_export':
                result = {'type': 'workspace_exported', 'path': self.export(command.get('path', ''))}
            else:
                raise ValueError('Unknown workspace action.')
            if not self.closed and self.latest.get(action) == serial:
                self.bridge.emit(**result, serial=serial)
        except Exception as exc:
            if not self.closed and self.latest.get(action) == serial:
                self.bridge.emit(type='workspace_error', action=action, serial=serial, text=str(exc))

    def database(self):
        return sqlite3.connect((self.bridge.state / 'chats.sqlite3').as_uri() + '?mode=ro', uri=True)

    def search(self, query, trash=False):
        query = str(query).strip()[:300]
        terms, results, warnings = query.casefold().split(), [], []

        def append(kind, identity, title, body, updated, **extra):
            content = (title + '\n' + body).casefold()
            if all(term in content for term in terms):
                results.append(dict(kind=kind, id=identity, title=title[:100], snippet=excerpt(body, query),
                                    updated=updated, score=2 if query and query.casefold() in title.casefold() else 1, **extra))

        try:
            snapshot = self.bridge.thoughts.store.snapshot()
            warnings.extend(snapshot['warnings'])
            for note in snapshot['notes']:
                if note['trashed'] != trash:
                    continue
                try:
                    updated = datetime.fromisoformat(note['updated']).timestamp()
                except ValueError:
                    updated = 0
                append(note['kind'], note['id'], note['title'] or note['body'].split('\n')[0], note['body'], updated,
                       done=note['done'], due=note['due'], revision=note['revision'])
        except (OSError, ValueError) as exc:
            warnings.append(str(exc))
        with closing(self.database()) as db:
            if trash:
                for data, updated in db.execute('SELECT data,updated FROM chat_trash ORDER BY updated DESC'):
                    try:
                        chat = json.loads(data)
                        body = '\n'.join(str(message.get('text', '')) for message in chat.get('messages', []))
                        append('chat', chat['id'], chat.get('title') or 'Conversation', body, updated)
                    except (ValueError, TypeError, KeyError):
                        warnings.append('A damaged deleted conversation was preserved in the local database.')
            else:
                # Trigrams narrow substring searches; short terms keep the same matching semantics.
                indexed = [term for term in terms if len(term) >= 3]
                sql = 'SELECT id,title,body,updated,anchors FROM chat_search'
                parameters = []
                if indexed:
                    sql += ' WHERE rowid IN (SELECT rowid FROM chat_search_fts WHERE chat_search_fts MATCH ?)'
                    parameters = [' AND '.join('"' + t.replace('"', '""') + '"' for t in indexed)]
                else:
                    sql += ' WHERE 1'
                for term in terms:
                    sql += ' AND instr(folded,?) > 0'
                    parameters.append(term)
                # Rank before loading message bodies into Python; only the best 40 chats
                # can survive the combined Notes/Chat result limit.
                sql += " ORDER BY CASE WHEN ? != '' AND instr(substr(folded,1,instr(folded,char(10))-1),?) > 0 THEN 2 ELSE 1 END DESC, updated DESC LIMIT 40"
                parameters.extend([query.casefold(), query.casefold()])
                for identity, title, body, updated, anchors in db.execute(sql, parameters):
                    if self.closed:
                        break
                    append('chat', identity, title, body, updated, messageIndex=match_index(body, json.loads(anchors), terms))
        results.sort(key=lambda row: (row['score'], row['updated']), reverse=True)
        results = results[:40]
        if warnings:
            results.append({'kind': 'warning', 'id': '', 'title': 'Some notes could not be searched', 'snippet': warnings[0]})
        return results

    def restore(self, command):
        identity = str(command.get('id', ''))
        if command.get('kind') == 'chat':
            with self.bridge.lock:
                db = self.bridge.db
                row = db.execute('SELECT data FROM chat_trash WHERE id=?', (identity,)).fetchone()
                if not row:
                    raise ValueError('This conversation is no longer in Recently deleted.')
                if db.execute('SELECT 1 FROM chats WHERE id=?', (identity,)).fetchone():
                    raise ValueError('A conversation with that identity already exists.')
                chat = json.loads(row[0])
                db.execute('INSERT INTO chats VALUES (?,?,?)', (identity, chat['updated'], row[0]))
                index_chat(db, chat)
                db.execute('DELETE FROM chat_trash WHERE id=?', (identity,))
                db.commit()
                self.bridge.snapshot()
        else:
            self.bridge.thoughts.store.modify(identity, command.get('revision'), 'restore')
            self.bridge.thoughts.publish(modified=identity, operation='restore')

    def export(self, destination):
        path = Path(str(destination)).expanduser()
        if not path.is_absolute() or path.suffix.lower() != '.zip' or not path.parent.is_dir():
            raise ValueError('Choose a .zip file in an existing folder.')
        if path.exists() or path.is_symlink():
            raise ValueError('That file already exists. Choose a new filename.')
        state = self.bridge.state
        fd, temporary = tempfile.mkstemp(prefix='.side-chat-export-', dir=path.parent)
        try:
            with os.fdopen(fd, 'wb') as output, zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
                archive.writestr('README.txt', 'Side Chat workspace backup\n\nstate/: chats, preferences, drafts, and attachment snapshots.\nnotes/: Markdown notes, to-dos, and Recently deleted notes.\nAgent credentials, speech models, and external agent session files are not included.\nClose Side Chat before restoring state files; back up your originals first.\n')
                with tempfile.TemporaryDirectory(prefix='side-chat-db-backup-') as directory:
                    for name in ('chats.sqlite3', 'companion.sqlite3'):
                        source = state / name
                        if not source.exists():
                            continue
                        copy = Path(directory) / name
                        with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as original, closing(sqlite3.connect(copy)) as target:
                            original.backup(target)
                        archive.write(copy, 'state/' + name)
                with self.bridge.thoughts.store.locked():
                    folder = self.bridge.thoughts.store.folder
                    for location, prefix in ((folder, 'notes'), (folder / '.thoughts/trash', 'notes/.thoughts/trash')):
                        for file in location.glob('*.md'):
                            if file.is_file() and not file.is_symlink():
                                archive.write(file, prefix + '/' + file.name)
                    for name in ['drafts.json', 'reminders.json'] + [p.name for p in (state / 'thoughts').glob('drafts-recovery-*.json')]:
                        file = state / 'thoughts' / name
                        if file.is_file() and not file.is_symlink():
                            archive.write(file, 'state/thoughts/' + name)
                attachments = state / 'attachments'
                if not attachments.is_symlink():
                    for file in attachments.rglob('*'):
                        if file.is_file() and not file.is_symlink():
                            archive.write(file, 'state/attachments/' + str(file.relative_to(attachments)))
            os.link(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return str(path)

    def close(self):
        self.closed = True
        self.pool.shutdown(wait=True, cancel_futures=True)
        self.export_pool.shutdown(wait=True, cancel_futures=True)
