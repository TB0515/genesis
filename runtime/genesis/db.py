"""SQLite state: agents, tasks, messages, events, runs, ventures, key/value state."""
import json
import sqlite3
import time
from contextlib import contextmanager

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS agents (
  id TEXT PRIMARY KEY, role TEXT NOT NULL, kind TEXT NOT NULL, parent TEXT,
  model TEXT, status TEXT NOT NULL DEFAULT 'idle', task_id INTEGER,
  created_at REAL, last_run_at REAL, runs INTEGER DEFAULT 0, note TEXT
);
CREATE TABLE IF NOT EXISTS tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT,
  acceptance TEXT, venture TEXT, role TEXT NOT NULL, priority INTEGER DEFAULT 3,
  status TEXT NOT NULL DEFAULT 'ready', created_by TEXT, assignee TEXT, reviewer TEXT,
  parent_task INTEGER, result TEXT, feedback TEXT, branch TEXT, worktree TEXT,
  attempts INTEGER DEFAULT 0, created_at REAL, updated_at REAL
);
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, recipient TEXT, subject TEXT,
  body TEXT, created_at REAL, read_at REAL
);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, agent TEXT, kind TEXT,
  summary TEXT, data TEXT
);
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT, agent TEXT, task_id INTEGER, reason TEXT,
  model TEXT, started REAL, ended REAL, status TEXT, num_turns INTEGER,
  cost_usd REAL, input_tokens INTEGER, output_tokens INTEGER, transcript TEXT, pid INTEGER
);
CREATE TABLE IF NOT EXISTS ventures (
  name TEXT PRIMARY KEY, pitch TEXT, repo_url TEXT, status TEXT DEFAULT 'active',
  created_by TEXT, created_at REAL
);
CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT);
CREATE INDEX IF NOT EXISTS ix_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS ix_msgs_rcpt ON messages(recipient, read_at);
CREATE INDEX IF NOT EXISTS ix_events_ts ON events(ts);
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.executescript(SCHEMA)
    return conn


@contextmanager
def tx(conn):
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise


def now() -> float:
    return time.time()


def event(conn, agent: str, kind: str, summary: str, data=None):
    conn.execute(
        "INSERT INTO events(ts, agent, kind, summary, data) VALUES (?,?,?,?,?)",
        (now(), agent, kind, summary[:500], json.dumps(data) if data is not None else None),
    )


def get_state(conn, key: str, default=None):
    row = conn.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
    return json.loads(row["value"]) if row else default


def set_state(conn, key: str, value):
    conn.execute(
        "INSERT INTO state(key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, json.dumps(value)),
    )


def rows(cur) -> list[dict]:
    return [dict(r) for r in cur.fetchall()]
