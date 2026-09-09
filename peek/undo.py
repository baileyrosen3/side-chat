# SPDX-License-Identifier: GPL-3.0-or-later
"""Optimistic, atomic config edits and conflict-aware undo. Never execute a restore script."""
import hashlib
import os
from pathlib import Path
import stat
import tempfile
import threading
from peek.store import Store


def digest(data):return hashlib.sha256(data).hexdigest()


class UndoJournal:
    def __init__(self, folder):self.store=Store(folder);self.lock=threading.RLock()

    def path(self, value, cwd):
        p=Path(value).expanduser()
        if not p.is_absolute():p=Path(cwd)/p
        if p.is_symlink() or p.resolve()!=p.absolute():raise ValueError('Config editing requires a real path without symlinks or traversal.')
        if not (p.is_relative_to(Path.home()/'.config') or p.is_relative_to(Path(cwd).resolve())):raise ValueError('Config path must be in your configuration or this session’s working folder.')
        if not p.is_file() or p.stat().st_uid!=os.getuid() or p.stat().st_nlink!=1:raise ValueError('Choose an existing, user-owned regular config file with no hard links.')
        if p.stat().st_size>1_000_000:raise ValueError('Config file exceeds 1 MB.')
        return p

    def read(self, value, cwd):
        p=self.path(value,cwd);data=p.read_bytes()
        return {'path':str(p),'text':data.decode('utf-8'),'sha256':digest(data)}

    @staticmethod
    def replace(path, data):
        mode=stat.S_IMODE(path.stat().st_mode)
        fd,name=tempfile.mkstemp(prefix='.peek-',dir=path.parent)
        try:
            with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
            os.chmod(name,mode);os.replace(name,path)
        finally:
            if os.path.exists(name):os.unlink(name)

    def write(self, value, cwd, text, expected):
        with self.lock:
            before=self.read(value,cwd)
            if before['sha256']!=expected:raise ValueError('Config changed since it was read. Read it again before editing.')
            after=str(text).encode('utf-8')
            if len(after)>1_000_000 or b'\x00' in after:raise ValueError('Config content must be UTF-8 text under 1 MB.')
            if digest(after)==expected:return {'unchanged':True,'path':before['path']}
            record=dict(path=before['path'],before=before['text'],beforeHash=expected,afterHash=digest(after),state='prepared')
            identity=self.store.put('undo',record)
            self.replace(Path(before['path']),after)
            verified=self.read(value,cwd)
            if verified['sha256']!=record['afterHash']:raise ValueError('Config changed during verification; inspect it before continuing.')
            self.store.put('undo',dict(record,state='available'),identity)
            return {'path':before['path'],'sha256':record['afterHash'],'undoId':identity,'verified':True}

    def list(self):
        return [{k:r[k] for k in ('id','path','updated','state')} for r in self.store.items('undo',30)]

    def restore(self, identity, cwd):
        with self.lock:
            rows=[r for r in self.store.items('undo',1000) if r['id']==identity]
            if not rows:raise ValueError('Restore point not found.')
            r=rows[0]
            if r['state']!='available':raise ValueError('That restore point is no longer available.')
            current=self.read(r['path'],cwd)
            if current['sha256']!=r['afterHash']:raise ValueError('This file has newer edits. Undo refused to overwrite them.')
            self.replace(Path(r['path']),r['before'].encode('utf-8'))
            r['state']='restored';self.store.put('undo',r,identity)
            return {'restored':r['path'],'verified':self.read(r['path'],cwd)['sha256']==r['beforeHash'],
                    'next':'The file is restored. Reload the relevant app if required.'}
