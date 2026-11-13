"""Live dashboard at http://localhost:7777: the AI office, the board, the feed, and the Patron's line."""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import db, roles
from .config import DASHBOARD_PORT, ROOT

STATIC = Path(__file__).parent / "static"


def snapshot(conn, after_event: int = 0) -> dict:
    q = lambda sql, *a: db.rows(conn.execute(sql, a))
    stats = {
        "agents_total": conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0],
        "live": conn.execute("SELECT COUNT(*) FROM runs WHERE status='running'").fetchone()[0],
        "runs": conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0],
        "shipped": conn.execute("SELECT COUNT(*) FROM tasks WHERE status='done'").fetchone()[0],
        "rejections": conn.execute("SELECT COUNT(*) FROM events WHERE kind='rejected'").fetchone()[0],
        "guard_blocks": conn.execute("SELECT COUNT(*) FROM events WHERE kind='guard_block'").fetchone()[0],
        "roles": len(roles.load_all()),
        "compute_usd": round(conn.execute("SELECT COALESCE(SUM(cost_usd),0) FROM runs").fetchone()[0], 2),
        "tokens": conn.execute("SELECT COALESCE(SUM(input_tokens),0)+COALESCE(SUM(output_tokens),0) FROM runs").fetchone()[0],
    }
    live = q("SELECT r.id run, r.agent, r.model, r.started, r.task_id, a.role, a.kind, a.parent FROM runs r "
             "JOIN agents a ON a.id=r.agent WHERE r.status='running'")
    for l in live:
        ev = conn.execute("SELECT summary, kind FROM events WHERE agent=? AND kind IN ('tool','text') ORDER BY id DESC LIMIT 1",
                          (l["agent"],)).fetchone()
        l["doing"] = ev["summary"] if ev else "waking up…"
    return {
        "company": db.get_state(conn, "company_name", "Genesis"),
        "tagline": db.get_state(conn, "tagline", ""),
        "paused_until": db.get_state(conn, "paused_until", 0),
        "halted": db.get_state(conn, "halted", False),
        "max_parallel": db.get_state(conn, "max_parallel", 6),
        "now": time.time(),
        "stats": stats,
        "leaders": q("SELECT id, role, model, status, runs, last_run_at FROM agents WHERE kind='leader' AND status!='retired'"),
        "roles": [{"name": r.name, "title": r.title, "kind": r.kind, "model": r.model, "version": r.version,
                   "description": r.description} for r in roles.load_all().values()],
        "live": live,
        "tasks": q("SELECT id, title, role, status, assignee, reviewer, venture, priority, attempts, parent_task, updated_at "
                   "FROM tasks WHERE status NOT IN ('done','cancelled') OR updated_at > ? ORDER BY id DESC LIMIT 200",
                   time.time() - 86400 * 3),
        "ventures": q("SELECT * FROM ventures"),
        "events": q("SELECT id, ts, agent, kind, summary FROM events WHERE id > ? ORDER BY id DESC LIMIT 250", after_event),
        "patron": q("SELECT id, sender, recipient, subject, body, created_at FROM messages "
                    "WHERE sender='patron' OR recipient='patron' ORDER BY id DESC LIMIT 60"),
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        conn = db.connect()
        try:
            if self.path.startswith("/api/state"):
                after = int(self.path.split("after=")[1]) if "after=" in self.path else 0
                return self._json(snapshot(conn, after))
            if self.path.startswith("/api/agent/"):
                aid = self.path.split("/api/agent/")[1]
                return self._json({
                    "agent": dict(conn.execute("SELECT * FROM agents WHERE id=?", (aid,)).fetchone() or {}),
                    "events": db.rows(conn.execute("SELECT ts, kind, summary FROM events WHERE agent=? ORDER BY id DESC LIMIT 120", (aid,))),
                    "runs": db.rows(conn.execute("SELECT id, reason, model, started, ended, status, num_turns, cost_usd FROM runs WHERE agent=? ORDER BY id DESC LIMIT 20", (aid,))),
                })
            if self.path.startswith("/api/role/"):
                p = ROOT / "org" / "roles" / f"{self.path.split('/api/role/')[1]}.md"
                return self._json({"text": p.read_text() if p.exists() else ""})
            if self.path.startswith("/api/task/"):
                t = conn.execute("SELECT * FROM tasks WHERE id=?", (int(self.path.split("/api/task/")[1]),)).fetchone()
                return self._json(dict(t) if t else {})
            name = "index.html" if self.path in ("/", "/index.html") else None
            if name:
                body = (STATIC / name).read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_error(404)
        finally:
            conn.close()

    def do_POST(self):
        conn = db.connect()
        try:
            n = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(n) or b"{}")
            if self.path == "/api/patron":
                to = data.get("to") or "liaison"
                if not conn.execute("SELECT 1 FROM agents WHERE id=? AND kind='leader'", (to,)).fetchone():
                    return self._json({"error": "no such leader"}, 400)
                conn.execute("INSERT INTO messages(sender, recipient, subject, body, created_at) VALUES (?,?,?,?,?)",
                             ("patron", to, data.get("subject") or "Message from the Patron", data["body"], time.time()))
                db.event(conn, "patron", "message", f"→ {to}: {data['body'][:200]}")
                return self._json({"ok": True})
            if self.path == "/api/control":
                if "halted" in data:
                    db.set_state(conn, "halted", bool(data["halted"]))
                    db.event(conn, "patron", "control", "Company halted by the Patron" if data["halted"] else "Company resumed by the Patron")
                if "max_parallel" in data:
                    db.set_state(conn, "max_parallel", max(1, min(24, int(data["max_parallel"]))))
                return self._json({"ok": True})
            self.send_error(404)
        finally:
            conn.close()


def serve(port: int = DASHBOARD_PORT):
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


def serve_in_background():
    threading.Thread(target=serve, daemon=True, name="dashboard").start()


if __name__ == "__main__":
    serve()
