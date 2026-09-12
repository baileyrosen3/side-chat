# SPDX-License-Identifier: GPL-3.0-or-later
"""Markdown thoughts, recoverable drafts, and capture independent of agent sessions."""
from contextlib import contextmanager
from datetime import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import select
import tempfile
import threading
import time
import uuid
from reminders import parse as parse_reminder, valid_due

MAX_TEXT = 100_000


def item_source(value):
    if not isinstance(value, dict) or value.get('kind') not in ('chat', 'note', 'selection', 'clipboard'):
        return {}
    return {key: str(value.get(key, ''))[:200] for key in ('kind', 'id', 'label')}


def atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix='.thoughts-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as output:
            output.write(text)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def notes_directory():
    override = os.environ.get('SIDE_CHAT_THOUGHTS_DIR')
    if override:
        return Path(override).expanduser().absolute()
    state = Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state'))
    settings = state / 'omarchy/settings/omathought.json'
    if settings.exists():
        try:
            value = json.loads(settings.read_text()).get('notesDir')
            if value:
                return Path(value).expanduser().absolute()
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError('The existing Omathought notesDir settings are invalid.') from exc
    return Path.home() / 'Documents/Thoughts'


def parse_document(text):
    """Keep unknown frontmatter verbatim, including YAML continuation lines."""
    match = re.match(r'\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)', text, re.S)
    if not match:
        return {}, {}, text
    chunks = {}
    key = ''
    for line in match[1].splitlines():
        field = re.match(r'^([\w-]+):\s*(.*)$', line)
        if field:
            key = field[1]
            chunks[key] = line + '\n'
        else:
            chunks[key] = chunks.get(key, '') + line + '\n'
    values = {}
    for key, chunk in chunks.items():
        if not key:
            continue
        raw = chunk.split(':', 1)[1].strip()
        try:
            values[key] = json.loads(raw)
        except ValueError:
            values[key] = raw.strip("\"'")
    body = text[match.end():]
    if body.startswith('\n'):
        body = body[1:]
    return values, chunks, body.rstrip('\n')


def tag_list(value):
    if isinstance(value, str):
        value = re.split(r'[,\s]+', value.strip('[]'))
    if not isinstance(value, list):
        return []
    return list(dict.fromkeys(str(t).strip().strip("\"'").lstrip('#').lower()
                             for t in value if str(t).strip().strip("\"'").lstrip('#')))[:20]


class ThoughtStore:
    def __init__(self, state, directory=None):
        self.state = Path(state) / 'thoughts'
        # Resolve lazily so a broken optional library cannot stop chat startup.
        self.directory = Path(directory) if directory is not None else None
        self.index_cache = {}
        self.cache_lock = threading.RLock()
        self.recovery_warnings = []

    @property
    def folder(self):
        return self.directory or notes_directory()

    @contextmanager
    def locked(self):
        self.state.mkdir(parents=True, exist_ok=True, mode=0o700)
        with (self.state / 'lock').open('a') as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            yield

    def path(self, identity, trashed=False):
        if (not isinstance(identity, str) or not identity or identity in ('.', '..')
                or any(c in identity for c in '/\\\x00\n\r') or len(identity.encode()) > 240):
            raise ValueError('Invalid thought identity.')
        folder = self.folder / '.thoughts/trash' if trashed else self.folder
        path = folder / (identity + '.md')
        if path.is_symlink():
            raise ValueError('Open linked notes in their original editor.')
        return path

    def read(self, identity, trashed=False):
        path = self.path(identity, trashed)
        if path.stat().st_size > 2_000_000:
            raise ValueError('This Markdown file is too large for Thoughts (2 MB limit).')
        raw = path.read_bytes()
        meta, _, body = parse_document(raw.decode('utf-8'))
        title = meta.get('title')
        title = title if isinstance(title, str) else ''
        tags = tag_list(meta.get('tags', []))
        inline = re.findall(r'(?:^|\s)#([\w][\w/-]*)', body)
        created = str(meta.get('created') or datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat())
        return dict(id=identity, title=title, body=body, tags=tags,
                    kind='todo' if meta.get('kind') == 'todo' else 'note', done=meta.get('done') is True,
                    due=valid_due(meta.get('due', 0)), source=item_source(meta.get('source')),
                    allTags=list(dict.fromkeys(tags + [t.lower() for t in inline])),
                    created=created, updated=str(meta.get('updated') or created),
                    pinned=meta.get('pinned') is True, archived=meta.get('archived') is True,
                    trashed=trashed, revision=hashlib.sha256(raw).hexdigest(), path=str(path))

    def drafts(self, locked=False):
        path = self.state / 'drafts.json'
        if not path.exists():
            return {}
        if not locked:
            with self.locked():
                return self.drafts(locked=True)
        try:
            data = json.loads(path.read_text())
            if not isinstance(data, dict) or any(not isinstance(v, dict) for v in data.values()):
                raise ValueError('Invalid draft records')
            return data
        except (ValueError, UnicodeError):
            backup = path.with_name('drafts-recovery-' + uuid.uuid4().hex + '.json')
            os.replace(path, backup)
            self.recovery_warnings.append('A damaged draft file was preserved at ' + str(backup))
            return {}

    def snapshot(self, locked=False):
        notes, warnings = [], []
        seen = set()
        for folder, trashed in ((self.folder, False), (self.folder / '.thoughts/trash', True)):
            for path in sorted(folder.glob('*.md')):
                try:
                    stat = path.stat()
                    signature = (stat.st_mtime_ns, stat.st_size, stat.st_ino)
                    with self.cache_lock:
                        cached = self.index_cache.get(str(path))
                        if cached is None or cached[0] != signature:
                            cached = (signature, self.read(path.stem, trashed))
                            self.index_cache[str(path)] = cached
                        notes.append(dict(cached[1]))
                        seen.add(str(path))
                except (OSError, UnicodeError, ValueError) as exc:
                    warnings.append(path.name + ': ' + str(exc))
        with self.cache_lock:
            self.index_cache = {key: value for key, value in self.index_cache.items() if key in seen}
        drafts = self.drafts(locked=locked)
        return dict(notes=sorted(notes, key=lambda n: n['created'], reverse=True),
                    drafts=drafts, directory=str(self.folder), warnings=warnings + self.recovery_warnings)

    def write_draft(self, draft):
        key = draft.get('key')
        if not isinstance(key, str) or not re.fullmatch(r'[a-zA-Z0-9_.-]{1,200}', key):
            raise ValueError('Invalid draft identity.')
        if len(str(draft.get('body', ''))) > MAX_TEXT:
            raise ValueError('Keep a thought under 100,000 characters.')
        with self.locked():
            drafts = self.drafts(locked=True)
            if draft.get('discard'):
                drafts.pop(key, None)
            else:
                drafts[key] = {k: draft.get(k, '') for k in ('key', 'id', 'title', 'body', 'tags', 'revision', 'kind', 'due', 'dueText', 'source')}
                drafts[key]['updated'] = time.time()
            atomic_write(self.state / 'drafts.json', json.dumps(drafts, ensure_ascii=False))

    def save(self, data):
        body = str(data.get('body', '')).rstrip()
        if not body.strip():
            raise ValueError('Write something before saving the thought.')
        if len(body) > MAX_TEXT:
            raise ValueError('Keep a thought under 100,000 characters.')
        with self.locked():
            key = data.get('key')
            drafts = self.drafts(locked=True) if key else {}
            token = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
            identity = data.get('id') or ('note-' + hashlib.sha256(str(key).encode()).hexdigest()[:24] if key else datetime.now().strftime('%Y%m%d-%H%M%S-') + uuid.uuid4().hex[:8])
            path = self.path(identity)
            # A save may have committed before its acknowledgment or draft cleanup failed.
            # Retrying that same operation returns the existing note.
            if path.exists() and key:
                previous, _, _ = parse_document(path.read_text())
                if previous.get('_sideChatSave') == token:
                    drafts.pop(key, None)
                    atomic_write(self.state / 'drafts.json', json.dumps(drafts, ensure_ascii=False))
                    return self.read(identity)
            now = datetime.now().astimezone().isoformat(timespec='seconds')
            meta, chunks = {}, {}
            if data.get('id'):
                original = self.read(identity)
                if original['revision'] != data.get('revision'):
                    raise ValueError('This note changed in another editor. Your draft is safe; save a copy or reload the original.')
                meta, chunks, _ = parse_document(path.read_text())
            elif path.exists():
                raise ValueError('A note with this name already exists. Try saving again.')
            fields = dict(created=meta.get('created', now), updated=now,
                          title=str(data.get('title', '')).strip()[:200], tags=tag_list(data.get('tags', [])),
                          kind='todo' if data.get('kind', meta.get('kind')) == 'todo' else 'note', done=meta.get('done') is True,
                          pinned=meta.get('pinned') is True, archived=meta.get('archived') is True)
            fields['due'] = valid_due(data.get('due', meta.get('due', 0))) if fields['kind'] == 'todo' else 0
            fields['source'] = item_source(data.get('source', meta.get('source')))
            if key:
                fields['_sideChatSave'] = token
            for field, value in fields.items():
                chunks[field] = field + ': ' + json.dumps(value, ensure_ascii=False) + '\n'
            atomic_write(path, '---\n' + ''.join(chunks.values()) + '---\n\n' + body + '\n')
            if key:
                drafts.pop(key, None)
                try:
                    atomic_write(self.state / 'drafts.json', json.dumps(drafts, ensure_ascii=False))
                except OSError as exc:
                    raise OSError('The note was saved, but its draft cleanup failed. Retry Save; this will not create a duplicate.') from exc
            return self.read(identity)

    def modify(self, identity, revision, operation):
        with self.locked():
            trashed = operation == 'restore'
            note = self.read(identity, trashed)
            if note['revision'] != revision:
                raise ValueError('This note changed outside Thoughts. Refresh before changing it.')
            path = self.path(identity, trashed)
            if operation in ('trash', 'restore'):
                dest = self.path(identity, not trashed)
                dest.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                if dest.exists():
                    raise ValueError('A note with this name already exists at the destination.')
                # Link/unlink avoids overwriting a note created concurrently.
                os.link(path, dest)
                path.unlink()
                return identity
            if operation not in ('pin', 'archive', 'complete', 'convert'):
                raise ValueError('Unknown thought operation.')
            meta, chunks, body = parse_document(path.read_text())
            if operation == 'convert':
                kind = 'note' if note['kind'] == 'todo' else 'todo'
                chunks['kind'] = 'kind: ' + json.dumps(kind) + '\n'
                chunks['done'] = 'done: false\n'
                chunks['due'] = 'due: 0\n'
            else:
                key = {'pin':'pinned', 'archive':'archived', 'complete':'done'}[operation]
                chunks[key] = key + ': ' + json.dumps(meta.get(key) is not True) + '\n'
            atomic_write(path, '---\n' + ''.join(chunks.values()) + '---\n\n' + body + '\n')
            return identity


class ThoughtsController:
    def __init__(self, bridge):
        self.bridge = bridge
        self.store = ThoughtStore(bridge.state)
        self.voice = None
        self.thread = None
        self.phase = 'idle'
        self.stop_requested = threading.Event()
        self.cancel_requested = threading.Event()
        self.last_reminder_check = 0

    @property
    def capturing(self):
        return self.phase in ('starting', 'recording', 'transcribing')

    def publish(self, **extra):
        self.bridge.emit(type='thoughts', **self.store.snapshot(), **extra)

    def dispatch(self, command):
        action = command['action']
        try:
            if action == 'thoughts_list':
                self.publish()
            elif action == 'thoughts_parse_due':
                try:
                    preview = parse_reminder(command.get('text', ''), separate=bool(command.get('separate')))
                    self.bridge.emit(type='thoughts_due_preview', serial=command.get('serial'), **preview, error='')
                except ValueError as exc:
                    self.bridge.emit(type='thoughts_due_preview', serial=command.get('serial'), body='', due=0, label='', error=str(exc))
            elif action == 'thoughts_open_id':
                note = self.store.read(command['id'])
                self.publish()
                self.bridge.emit(type='thoughts_open', kind=note['kind'], note=note)
            elif action == 'thoughts_reminder_action':
                self.reminder_action(command['id'], command['operation'], command.get('due'))
            elif action == 'thoughts_draft':
                self.store.write_draft(command)
                self.bridge.emit(type='thoughts_draft_saved', key=command['key'], serial=command.get('serial'))
            elif action == 'thoughts_save':
                note = self.store.save(command)
                self.publish(saved=note, key=command.get('key'))
            elif action == 'thoughts_modify':
                self.store.modify(command['id'], command['revision'], command['operation'])
                self.publish(modified=command['id'], operation=command['operation'])
            elif action == 'thoughts_discard':
                note = self.store.save(dict(command, id=''))
                self.store.modify(note['id'], note['revision'], 'trash')
                self.publish(modified=note['id'], operation='trash', key=command.get('key'))
            elif action == 'thoughts_voice_start':
                self.start_voice(command['key'], command.get('kind', 'note'))
            elif action == 'thoughts_voice_stop':
                self.stop_requested.set()
            elif action == 'thoughts_voice_cancel':
                self.cancel_voice()
            else:
                raise ValueError('Unknown Thoughts action.')
        except Exception as exc:
            self.bridge.emit(type='thoughts_error', text=str(exc), action=action, key=command.get('key'))

    def check_reminders(self, now=None):
        now = time.time() if now is None else now
        if now - self.last_reminder_check < 5:
            return
        self.last_reminder_check = now
        with self.store.locked():
            path = self.store.state / 'reminders.json'
            delivered = json.loads(path.read_text()) if path.exists() else {}
            # Reuse this lock while reading draft recovery; reacquiring flock on
            # another descriptor would block this process against itself.
            pending = [n for n in self.store.snapshot(locked=True)['notes'] if n['kind'] == 'todo' and not n['done']
                       and not n['trashed'] and 0 < n['due'] <= now and delivered.get(n['id']) != n['due']]
        for note in pending[:6]:
            self.notify_reminder(note)
            with self.store.locked():
                delivered[note['id']] = note['due']
                atomic_write(path, json.dumps(delivered))
            self.bridge.emit(type='thoughts_reminder', note=note)

    def notify_reminder(self, note):
        process = subprocess.Popen(['/usr/bin/python3', '-B', str(Path(__file__).with_name('reminder_notification.py')),
                          note['id'], str(note['due']), note['body'][:500]],
                         stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                         start_new_session=True)
        try:
            ready = select.select([process.stdout], [], [], 3)[0]
            if not ready or process.stdout.readline().strip() != b'ready':
                process.terminate()
                process.wait(timeout=1)
                raise ValueError('Desktop notifications are unavailable. The reminder will retry.')
        finally:
            process.stdout.close()

    def reminder_action(self, identity, operation, due=None):
        note = self.store.read(identity)
        if operation == 'open':
            self.bridge.emit(type='thoughts_open', kind=note['kind'], note=note)
            return
        if note['done'] or note['kind'] != 'todo' or (due is not None and note['due'] != valid_due(due)):
            raise ValueError('This reminder has changed. Open the task to review it.')
        if operation == 'done':
            self.store.modify(identity, note['revision'], 'complete')
        elif operation == 'snooze':
            self.store.save(dict(note, due=time.time() + 600))
        else:
            raise ValueError('Unknown reminder action.')
        self.publish(modified=identity, operation=operation)

    def start_voice(self, key, kind='note'):
        if self.capturing:
            return
        peek = self.bridge.peek
        if peek and (peek.want_listen or peek.state.get('listening') or peek.transcribing):
            raise ValueError('Pause Peek’s microphone before recording a thought.')
        from peek.voxtype import VoxtypeBridge
        self.voice = VoxtypeBridge(self.store.state / 'voice')
        self.phase = 'starting'
        self.stop_requested.clear()
        self.cancel_requested.clear()
        self.bridge.emit(type='thoughts_voice', phase=self.phase, key=key)

        def record():
            try:
                self.voice.start()
                self.phase = 'recording'
                self.bridge.emit(type='thoughts_voice', phase=self.phase, key=key)
                started = time.monotonic()
                while not self.stop_requested.wait(.1):
                    self.bridge.emit(type='thoughts_level', level=self.voice.level(), seconds=int(time.monotonic() - started))
                    if time.monotonic() - started >= 120:
                        break
                if self.cancel_requested.is_set():
                    self.voice.cancel()
                    return
                self.phase = 'transcribing'
                self.bridge.emit(type='thoughts_voice', phase=self.phase, key=key)
                text = self.voice.stop()
                if not self.cancel_requested.is_set():
                    if not text.strip():
                        raise ValueError('No speech was captured. Try again or type your thought.')
                    draft = dict(key=key, id='', title='', body=text, tags='', revision='',kind=kind)
                    self.store.write_draft(draft)
                    self.bridge.emit(type='thoughts_transcript', **draft)
            except Exception as exc:
                if not self.cancel_requested.is_set():
                    self.bridge.emit(type='thoughts_error', text=str(exc), action='thoughts_voice_start', key=key)
            finally:
                self.phase = 'idle'
                self.bridge.emit(type='thoughts_voice', phase='idle', key=key)
        self.thread = threading.Thread(target=record, daemon=True)
        self.thread.start()

    def cancel_voice(self):
        if not self.capturing:
            return
        self.cancel_requested.set()
        self.stop_requested.set()
        if self.phase == 'transcribing':
            # stop() waits holding the bridge lock; send cancellation independently.
            try:
                self.voice._run(['record', 'cancel'], 3)
            except Exception:
                pass

    def close(self):
        self.cancel_voice()
        if self.thread:
            self.thread.join(timeout=8)
