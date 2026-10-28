"""Page-segment checkpoints under an ImportQueue lease. No student evidence lives here."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .pdf_core import digest
from .store import ConflictError


class ImportCheckpoint:
    def __init__(self, queue, job):
        self.queue, self.job = queue, job
        self.root = queue.modules.root

    def _check_lease(self, c):
        row=c.execute("SELECT status,lease_owner,lease_until FROM import_jobs WHERE job_id=?",(self.job['job_id'],)).fetchone()
        if not row or row['status']!='running' or row['lease_owner']!=self.job['lease_owner'] or row['lease_until']<=self.queue.clock():
            raise ConflictError('Import checkpoint lease expired or changed')

    def prepare(self, key, ranges):
        with self.queue.store.connect(write=True) as c:
            self._check_lease(c)
            c.execute('INSERT INTO import_segment_heads VALUES(?,?) ON CONFLICT(job_id) DO UPDATE SET cache_key=excluded.cache_key',(self.job['job_id'],key))
            c.executemany("INSERT OR IGNORE INTO import_segments(job_id,cache_key,first_page,last_page,status) VALUES(?,?,?,?,'queued')",
                          [(self.job['job_id'],key,a,b) for a,b in ranges])
            self.queue._refresh(c,self.job['batch_id'])

    def load(self, key, first, last):
        with self.queue.store.connect() as c:
            self._check_lease(c)
            row=c.execute("SELECT * FROM import_segments WHERE job_id=? AND cache_key=? AND first_page=? AND last_page=?",
                          (self.job['job_id'],key,first,last)).fetchone()
        if not row or row['status']!='completed':return None
        try:
            path=(self.root/row['relative_path']).resolve()
            if not path.is_relative_to(self.root):return None
            data=path.read_bytes()
            if digest(data)!=row['sha256']:return None
            entries=json.loads(data)
            if [e['meta']['page'] for e in entries]!=list(range(first,last+1)):return None
            for entry in entries:
                a=entry['asset'];p=(self.queue.modules.assets/a['relative_path']).resolve()
                if not p.is_relative_to(self.queue.modules.assets) or digest(p.read_bytes())!=a['sha256']:return None
            return entries
        except (OSError,ValueError,KeyError,TypeError):return None

    def begin(self,key,first,last):
        with self.queue.store.connect(write=True) as c:
            self._check_lease(c)
            c.execute("UPDATE import_segments SET status='running',attempts=attempts+1,error=NULL WHERE job_id=? AND cache_key=? AND first_page=? AND last_page=?",
                      (self.job['job_id'],key,first,last))
            self.queue._refresh(c,self.job['batch_id'])

    def complete(self,key,first,last,entries):
        data=json.dumps(entries,ensure_ascii=False).encode();sha=digest(data)
        # Flat content-addressed paths avoid Windows' path-length limit. Existing
        # checkpoint paths remain readable through the unchanged DB relative_path.
        path=self.root/'import-checkpoints'/f'{sha}.json'
        path.parent.mkdir(parents=True,exist_ok=True)
        # Content-addressed final files and an atomic rename tolerate cancellation before DB commit.
        with tempfile.NamedTemporaryFile(dir=path.parent,prefix=sha[:8],suffix='.part',delete=False) as f:
            partial=Path(f.name);f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(partial,path)
        with self.queue.store.connect(write=True) as c:
            self._check_lease(c)
            c.execute("UPDATE import_segments SET status='completed',relative_path=?,sha256=?,error=NULL WHERE job_id=? AND cache_key=? AND first_page=? AND last_page=?",
                      (path.relative_to(self.root).as_posix(),sha,self.job['job_id'],key,first,last))
            self.queue._refresh(c,self.job['batch_id'])

    def fail(self,key,first,last,exc):
        with self.queue.store.connect(write=True) as c:
            self._check_lease(c)
            c.execute("UPDATE import_segments SET status='failed',error=? WHERE job_id=? AND cache_key=? AND first_page=? AND last_page=?",
                      ((type(exc).__name__+': '+str(exc))[:240],self.job['job_id'],key,first,last))
            self.queue._refresh(c,self.job['batch_id'])
