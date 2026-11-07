"""Private, persistent job queue for Podcast Outreach AI.

Research is performed by a separate local worker. The web UI only enqueues work;
no outbound email is ever sent. SQLite lives under the independent instance data/.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import csv
from dataclasses import asdict
import io
import json
import os
import sqlite3
import uuid

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / 'data' / 'podcast-outreach.sqlite3'


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(path), timeout=20, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('PRAGMA busy_timeout=20000')
    db.executescript('''CREATE TABLE IF NOT EXISTS research_runs (
        id TEXT PRIMARY KEY, query TEXT NOT NULL, guest_profile TEXT NOT NULL DEFAULT '',
        model TEXT NOT NULL, max_candidates INTEGER NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('queued','running','completed','failed','interrupted')),
        progress REAL NOT NULL DEFAULT 0, stage TEXT NOT NULL DEFAULT 'Queued',
        created_at TEXT NOT NULL, started_at TEXT, completed_at TEXT,
        error TEXT NOT NULL DEFAULT '', results_json TEXT NOT NULL DEFAULT '[]',
        details_json TEXT NOT NULL DEFAULT '{}');
        CREATE TABLE IF NOT EXISTS activity (
        id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL, at TEXT NOT NULL,
        message TEXT NOT NULL, FOREIGN KEY (run_id) REFERENCES research_runs(id));
        CREATE INDEX IF NOT EXISTS idx_activity_run ON activity(run_id, id);''')
    return db


def queue_research(db, query: str, *, guest_profile='', model='llama3.2:3b', max_candidates=8) -> str:
    query = query.strip()
    if len(query) < 5 or len(query) > 4000:
        raise ValueError('Enter a research request between 5 and 4,000 characters.')
    if not 3 <= int(max_candidates) <= 20:
        raise ValueError('Choose between 3 and 20 podcasts.')
    if len(guest_profile) > 2000 or len(model) > 150:
        raise ValueError('Guest profile or model name is too long.')
    # Avoid accidentally starting two copies from repeated clicks while a run is active.
    active = db.execute("SELECT id FROM research_runs WHERE status IN ('queued','running') LIMIT 1").fetchone()
    if active:
        return active['id']
    ident = uuid.uuid4().hex
    db.execute('INSERT INTO research_runs(id,query,guest_profile,model,max_candidates,status,created_at) VALUES(?,?,?,?,?,?,?)',
               (ident,query,guest_profile,model,int(max_candidates),'queued',timestamp()))
    add_activity(db,ident,'Research queued for the local worker.')
    return ident


def add_activity(db, run_id: str, message: str):
    db.execute('INSERT INTO activity(run_id,at,message) VALUES(?,?,?)', (run_id,timestamp(),str(message)[:1200]))


def list_runs(db, limit=20):
    return [dict(x) for x in db.execute('SELECT * FROM research_runs ORDER BY created_at DESC,id DESC LIMIT ?', (int(limit),))]


def latest_run(db):
    row=db.execute('SELECT * FROM research_runs ORDER BY created_at DESC,id DESC LIMIT 1').fetchone()
    return dict(row) if row else None


def get_run(db, run_id: str):
    row=db.execute('SELECT * FROM research_runs WHERE id=?',(run_id,)).fetchone()
    return dict(row) if row else None


def events(db, run_id: str, limit=30):
    return [dict(x) for x in db.execute('SELECT at,message FROM activity WHERE run_id=? ORDER BY id DESC LIMIT ?', (run_id,int(limit)))]


def interrupt_stale(db):
    db.execute("UPDATE research_runs SET status='interrupted',stage='Worker stopped before completion',completed_at=? WHERE status='running'",(timestamp(),))


def claim_next(db):
    db.execute('BEGIN IMMEDIATE')
    try:
        row=db.execute("SELECT * FROM research_runs WHERE status='queued' ORDER BY created_at,id LIMIT 1").fetchone()
        if row:
            db.execute("UPDATE research_runs SET status='running',stage='Starting investigation',started_at=? WHERE id=?",(timestamp(),row['id']))
        db.execute('COMMIT')
    except Exception:
        db.execute('ROLLBACK');raise
    return dict(row) if row else None


def execute_one(db, agent=None) -> bool:
    """Process one research job, returning whether one was claimed.

    Worker passes an injected agent during deterministic unit tests.
    """
    row=claim_next(db)
    if not row:return False
    if agent is None:
        from podcast_agent.agent import run_agent as agent
    ident=row['id']
    def progress(fraction,message):
        db.execute('UPDATE research_runs SET progress=?,stage=? WHERE id=?',
                   (max(0,min(1,float(fraction))),str(message)[:500],ident))
    def activity(message):add_activity(db,ident,message)
    def status(event):
        if event.get('kind')=='stage':progress(event.get('progress',0),event.get('message','Working'))
        elif event.get('kind') in ('start','retry','retry_failed'):
            add_activity(db,ident,event.get('message',event['kind']))
    try:
        result=agent(row['query'],model=row['model'],max_candidates=row['max_candidates'],
                     guest_profile=row['guest_profile'],progress=progress,
                     on_activity=activity,on_status=status)
        rows=[p.to_row() for p in result.podcasts]
        details={k:getattr(result,k) for k in (
            'queries','tool_calls','research_errors','ollama_requests','model_decisions',
            'fallback_used','uk_only','region_excluded','rejected_leads','suitable_contacts_found')}
        db.execute("UPDATE research_runs SET status='completed',progress=1,stage='Research complete',completed_at=?,results_json=?,details_json=? WHERE id=?",
                   (timestamp(),json.dumps(rows,ensure_ascii=False),json.dumps(details),ident))
        add_activity(db,ident,f'Research completed: {len(rows)} podcasts in the shortlist. Nothing was sent.')
    except Exception as exc:
        db.execute("UPDATE research_runs SET status='failed',stage='Research failed',completed_at=?,error=? WHERE id=?",
                   (timestamp(),str(exc)[:1200],ident))
        add_activity(db,ident,'Research stopped: '+str(exc)[:500])
    return True


def csv_for_run(run: dict) -> str:
    rows=json.loads(run['results_json'])
    if not rows:return ''
    out=io.StringIO()
    writer=csv.DictWriter(out,fieldnames=list(rows[0].keys()),extrasaction='ignore')
    def safe_cell(v):
        if isinstance(v, str) and v.lstrip().startswith(('=', '+', '-', '@')):
            return "'" + v
        return v
    writer.writeheader()
    for row in rows:
        writer.writerow({key:safe_cell(row.get(key,'')) for key in rows[0]})
    return out.getvalue()
