"""The company's heartbeat: decides who wakes, spawns workers/reviewers, integrates approved work,
sleeps through usage limits, and keeps the public record up to date."""
import datetime as dt
import json
import logging
import os
import signal
import subprocess
import threading
import time
import traceback
from pathlib import Path

from . import db, gitops, roles
from .config import (DEFAULT_MAX_PARALLEL, DEFAULT_PAUSE_S, DOCS, IDLE_WAKE_CEO_S, LOGS, MAX_TASK_ATTEMPTS,
                     RETRO_EVERY_N_TASKS, ROOT, TICK_SECONDS)
from .runner import LimitHit, run_turn

log = logging.getLogger("genesis")


class Scheduler:
    def __init__(self):
        self.conn = db.connect()
        self.running: dict[str, threading.Thread] = {}
        self.lock = threading.Lock()
        self.stopping = False
        self.last_publish = 0.0
        self.last_export = 0.0
        self.consecutive_errors = 0
        self.breaker_trips = 0

    # ---------- bookkeeping ----------
    def recover(self):
        c = self.conn
        with db.tx(c):
            c.execute("UPDATE runs SET status='interrupted', ended=? WHERE status='running'", (db.now(),))
            c.execute("UPDATE tasks SET status='ready', assignee=NULL WHERE status='running'")
            c.execute("UPDATE tasks SET status='review', reviewer=NULL WHERE status='reviewing'")
            c.execute("UPDATE tasks SET status='contest', reviewer=NULL WHERE status='judging'")
            c.execute("UPDATE agents SET status='idle' WHERE status='running' AND kind='leader'")
            c.execute("UPDATE agents SET status='done' WHERE status='running' AND kind='worker'")
            db.event(c, "runtime", "boot", "Runtime started")

    def sync_leaders(self):
        rs = roles.load_all()
        for r in rs.values():
            if r.kind == "leader" and not self.conn.execute("SELECT 1 FROM agents WHERE id=?", (r.name,)).fetchone():
                self.conn.execute("INSERT INTO agents(id, role, kind, model, status, created_at) VALUES (?,?,?,?,?,?)",
                                  (r.name, r.name, "leader", r.model, "idle", db.now()))
                db.event(self.conn, "runtime", "hired", f"Leader '{r.name}' ({r.title}) joined the company")
        for a in self.conn.execute("SELECT id, role, model FROM agents WHERE kind='leader' AND status!='retired'").fetchall():
            r = rs.get(a["role"])
            if r is None or r.kind != "leader":
                self.conn.execute("UPDATE agents SET status='retired' WHERE id=?", (a["id"],))
            elif r.model != a["model"]:
                self.conn.execute("UPDATE agents SET model=? WHERE id=?", (r.model, a["id"]))

    def paused_until(self) -> float:
        return db.get_state(self.conn, "paused_until", 0) or 0

    def max_parallel(self) -> int:
        return int(db.get_state(self.conn, "max_parallel", DEFAULT_MAX_PARALLEL))

    def new_worker(self, role: roles.Role, task_id: int, parent: str | None) -> str:
        n = self.conn.execute("SELECT COUNT(*) FROM agents WHERE role=?", (role.name,)).fetchone()[0] + 1
        aid = f"{role.name}-{n}"
        while self.conn.execute("SELECT 1 FROM agents WHERE id=?", (aid,)).fetchone():
            n += 1
            aid = f"{role.name}-{n}"
        self.conn.execute("INSERT INTO agents(id, role, kind, parent, model, status, task_id, created_at) "
                          "VALUES (?,?,?,?,?,?,?,?)", (aid, role.name, "worker", parent, role.model, "running", task_id, db.now()))
        db.event(self.conn, "runtime", "spawned", f"{aid} spawned for task #{task_id}", {"task": task_id, "parent": parent})
        return aid

    # ---------- integration of approved work ----------
    def integrate_approved(self):
        for t in db.rows(self.conn.execute("SELECT id, venture FROM tasks WHERE status IN ('cancelled','blocked') "
                                           "AND worktree IS NOT NULL AND venture IS NOT NULL")):
            if t["venture"] and (ROOT / "ventures" / t["venture"]).exists():
                gitops.remove_worktree(t["venture"], t["id"])
            self.conn.execute("UPDATE tasks SET worktree=NULL WHERE id=?", (t["id"],))
        for t in db.rows(self.conn.execute("SELECT * FROM tasks WHERE status='approved'")):
            if t["venture"]:
                try:
                    ok, msg = gitops.integrate(t["venture"], t["id"])
                except Exception as e:
                    ok, msg = False, f"integration error: {e}"
                if not ok:
                    status = "blocked" if t["attempts"] >= MAX_TASK_ATTEMPTS else "ready"
                    self.conn.execute("UPDATE tasks SET status=?, feedback=?, assignee=NULL, reviewer=NULL, updated_at=? WHERE id=?",
                                      (status, (t["feedback"] or "") + "\n\nIntegration failed: " + msg, db.now(), t["id"]))
                    db.event(self.conn, "runtime", "integration_failed", f"#{t['id']}: {msg[:200]}")
                    continue
                gitops.remove_worktree(t["venture"], t["id"])
                db.event(self.conn, "runtime", "shipped", f"#{t['id']} {t['title']} → {t['venture']} main ({msg})", {"task": t["id"]})
            else:
                db.event(self.conn, "runtime", "shipped", f"#{t['id']} {t['title']}", {"task": t["id"]})
            self.conn.execute("UPDATE tasks SET status='done', updated_at=? WHERE id=?", (db.now(), t["id"]))

    # ---------- choosing work ----------
    def busy(self, aid: str) -> bool:
        return aid in self.running

    def pick(self, slots: int) -> list[tuple]:
        jobs, c, rs = [], self.conn, roles.load_all()
        if slots <= 0:
            return jobs
        leaders = {a["id"]: dict(a) for a in c.execute("SELECT * FROM agents WHERE kind='leader' AND status!='retired'")}

        def add_leader(aid, reason):
            if len(jobs) < slots and aid in leaders and not self.busy(aid) and all(j[0] != aid for j in jobs):
                jobs.append((aid, "leader", reason, None))

        # 1) messages to leaders (the Patron's messages to the liaison come first)
        for m in c.execute("SELECT recipient, COUNT(*) n, MAX(sender='patron') p FROM messages WHERE read_at IS NULL "
                           "GROUP BY recipient ORDER BY p DESC"):
            add_leader(m["recipient"], f"You have {m['n']} unread message(s)." + (" One is from the Patron." if m["p"] else ""))
        # 2a) contests whose entries are all in → a judge
        for ct in db.rows(c.execute("SELECT * FROM tasks WHERE status='contest' ORDER BY priority, id")):
            if len(jobs) >= slots:
                break
            st = [r["status"] for r in c.execute("SELECT status FROM tasks WHERE parent_task=?", (ct["id"],))]
            if not st or any(x not in ("entered", "blocked", "cancelled") for x in st):
                continue
            if "entered" not in st:
                c.execute("UPDATE tasks SET status='blocked', feedback='every entry failed' WHERE id=?", (ct["id"],))
                db.event(c, "runtime", "contest_failed", f"#{ct['id']}: every entry failed")
                continue
            judge = rs.get("judge") or rs.get("reviewer")
            aid = self.new_worker(judge, ct["id"], ct["created_by"])
            c.execute("UPDATE tasks SET status='judging', reviewer=?, updated_at=? WHERE id=?", (aid, db.now(), ct["id"]))
            jobs.append((aid, "judge", f"Judge contest #{ct['id']} ({st.count('entered')} entries).", ct["id"]))
        # 2b) reviews waiting
        for t in db.rows(c.execute("SELECT * FROM tasks WHERE status='review' ORDER BY priority, id")):
            if len(jobs) >= slots:
                break
            role = rs.get((rs.get(t["role"]).meta.get("reviewed_by") if rs.get(t["role"]) else None) or "reviewer") or rs.get("reviewer")
            if not role:
                continue
            aid = self.new_worker(role, t["id"], t["assignee"])
            c.execute("UPDATE tasks SET status='reviewing', reviewer=?, updated_at=? WHERE id=?", (aid, db.now(), t["id"]))
            jobs.append((aid, "review", f"Review task #{t['id']} submitted by {t['assignee']}.", t["id"]))
        # 3) ready tasks
        for t in db.rows(c.execute("SELECT * FROM tasks WHERE status='ready' ORDER BY priority, id")):
            if len(jobs) >= slots:
                break
            role = rs.get(t["role"])
            if role is None:
                c.execute("UPDATE tasks SET status='blocked', feedback='role no longer exists' WHERE id=?", (t["id"],))
                continue
            if role.kind == "leader":
                add_leader(role.name, f"Task #{t['id']} was assigned to your role: {t['title']}")
                continue
            if t["venture"] and not (ROOT / "ventures" / t["venture"]).exists():
                c.execute("UPDATE tasks SET status='blocked', feedback='venture repo missing' WHERE id=?", (t["id"],))
                continue
            aid = self.new_worker(role, t["id"], t["created_by"])
            c.execute("UPDATE tasks SET status='running', assignee=?, attempts=attempts+1, updated_at=? WHERE id=?",
                      (aid, db.now(), t["id"]))
            jobs.append((aid, "work", f"You were spawned to do task #{t['id']}.", t["id"]))
        # 4) heartbeats
        now = db.now()
        for aid, a in leaders.items():
            r = rs.get(a["role"])
            if r and r.heartbeat_minutes and now - (a["last_run_at"] or 0) > r.heartbeat_minutes * 60:
                add_leader(aid, f"Scheduled check-in (every {r.heartbeat_minutes} min). Review progress, steer, unblock.")
        # 5) idle company → wake the CEO
        active = c.execute("SELECT COUNT(*) FROM tasks WHERE status IN ('ready','running','review','reviewing','approved','contest','judging','entered')").fetchone()[0]
        ceo = leaders.get("ceo")
        if ceo and not active and not self.running and not jobs and now - (ceo["last_run_at"] or 0) > IDLE_WAKE_CEO_S:
            add_leader("ceo", "The company is idle: no open tasks. Decide what we do next and get people working.")
        return jobs

    # ---------- executing ----------
    def launch(self, job):
        aid, mode, reason, task_id = job
        if mode == "leader":
            self.conn.execute("UPDATE agents SET status='running' WHERE id=?", (aid,))

        def go():
            try:
                res = run_turn(aid, mode, reason, task_id)
                self.track(res["status"])
                self.after(aid, mode, task_id, res["status"])
            except LimitHit as lh:
                self.on_limit(aid, mode, task_id, lh.until)
            except Exception as e:
                log.error("run failed %s: %s\n%s", aid, e, traceback.format_exc())
                db.event(self.conn, aid, "error", f"run crashed: {e}"[:300])
                self.track("error")
                self.after(aid, mode, task_id, "error")
            finally:
                with self.lock:
                    self.running.pop(aid, None)

        th = threading.Thread(target=go, name=aid, daemon=True)
        with self.lock:
            self.running[aid] = th
        th.start()

    def after(self, aid, mode, task_id, status):
        c = db.connect()
        if mode == "leader":
            c.execute("UPDATE agents SET status='idle' WHERE id=? AND status='running'", (aid,))
            return
        c.execute("UPDATE agents SET status='done' WHERE id=?", (aid,))
        t = c.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if not t:
            return
        if mode == "work" and t["status"] == "running":
            if t["worktree"]:
                gitops.autocommit(Path(t["worktree"]), f"WIP #{task_id} (turn ended without submit)", aid)
            st = "blocked" if t["attempts"] >= MAX_TASK_ATTEMPTS else "ready"
            c.execute("UPDATE tasks SET status=?, assignee=NULL, feedback=?, updated_at=? WHERE id=?",
                      (st, (t["feedback"] or "") + f"\n\n[{aid}'s turn ended ({status}) without submit_work. "
                       "Any work was committed as WIP on the task branch; continue from it.]", db.now(), task_id))
            db.event(c, "runtime", "no_submit", f"#{task_id}: {aid} ended without submitting ({status})")
        elif mode in ("judge", "review") and t["status"] in ("judging", "reviewing"):
            db.event(c, "runtime", "no_verdict", f"#{task_id}: {aid} gave no verdict ({status})", {"task": task_id})
            fails = c.execute("SELECT COUNT(*) FROM events WHERE kind='no_verdict' AND json_extract(data,'$.task')=?",
                              (task_id,)).fetchone()[0]
            if fails >= 3:
                c.execute("UPDATE tasks SET status='blocked', reviewer=NULL, feedback=COALESCE(feedback,'')||? WHERE id=?",
                          (f"\n\n[{fails} {mode} turns ended without a verdict; escalated]", task_id))
                c.execute("INSERT INTO messages(sender, recipient, subject, body, created_at) VALUES (?,?,?,?,?)",
                          ("runtime", "cto", f"Task #{task_id} could not be {mode}ed",
                           f"{fails} {mode} attempts ended without a verdict. Inspect var/transcripts and re-scope.", db.now()))
            else:
                c.execute("UPDATE tasks SET status=?, reviewer=NULL WHERE id=?",
                          ("contest" if mode == "judge" else "review", task_id))

    def track(self, status: str):
        """Circuit breaker: many failed runs in a row means something systemic (CLI broken, auth expired,
        network down). Pause with exponential backoff instead of burning through retries."""
        with self.lock:
            if status == "ok":
                self.consecutive_errors, self.breaker_trips = 0, 0
                return
            self.consecutive_errors += 1
            if self.consecutive_errors < 6:
                return
            self.consecutive_errors = 0
            self.breaker_trips += 1
            wait = min(15 * 60 * 2 ** (self.breaker_trips - 1), 4 * 3600)
        c = db.connect()
        db.set_state(c, "paused_until", time.time() + wait)
        db.event(c, "runtime", "circuit_breaker", f"6 failed runs in a row; pausing {wait // 60} min (trip {self.breaker_trips})")
        if self.breaker_trips == 2:
            c.execute("INSERT INTO messages(sender, recipient, subject, body, created_at) VALUES (?,?,?,?,?)",
                      ("runtime", "patron", "[REPORT] The runtime keeps failing",
                       "Agent runs are failing repeatedly (see var/logs and var/transcripts). This may need a human: "
                       "e.g. `claude` logged out or updated. The company is backing off and will keep retrying.", time.time()))

    def on_limit(self, aid, mode, task_id, until):
        c = db.connect()
        until = max(until, time.time() + 120)
        if until > time.time() + 8 * 86400:
            until = time.time() + DEFAULT_PAUSE_S
        if until > self.paused_until():
            db.set_state(c, "paused_until", until)
            db.event(c, "runtime", "sleeping",
                     f"Usage limit reached. Company sleeps until {dt.datetime.fromtimestamp(until):%a %H:%M}.")
        if mode == "leader":
            c.execute("UPDATE agents SET status='idle' WHERE id=?", (aid,))
        elif mode == "work":
            c.execute("UPDATE tasks SET status='ready', assignee=NULL, attempts=MAX(attempts-1,0) WHERE id=? AND status='running'", (task_id,))
            c.execute("UPDATE agents SET status='done' WHERE id=?", (aid,))
        elif mode == "review":
            c.execute("UPDATE tasks SET status='review', reviewer=NULL WHERE id=? AND status='reviewing'", (task_id,))
            c.execute("UPDATE agents SET status='done' WHERE id=?", (aid,))
        elif mode == "judge":
            c.execute("UPDATE tasks SET status='contest', reviewer=NULL WHERE id=? AND status='judging'", (task_id,))
            c.execute("UPDATE agents SET status='done' WHERE id=?", (aid,))

    # ---------- periodic company rituals ----------
    def rituals(self):
        c, now = self.conn, db.now()
        # Retrospective: the org designer studies outcomes and rewrites the agents.
        finished = c.execute("SELECT COUNT(*) FROM tasks WHERE status IN ('done','blocked')").fetchone()[0]
        last = db.get_state(c, "retro_at_count", 0)
        if finished - last >= RETRO_EVERY_N_TASKS and roles.load("orgdesigner"):
            db.set_state(c, "retro_at_count", finished)
            c.execute("INSERT INTO tasks(title, description, acceptance, role, priority, created_by, created_at, updated_at) "
                      "VALUES (?,?,?,?,?,?,?,?)",
                      (f"Retrospective after {finished} finished tasks",
                       "Study what happened since the last retrospective: rejected and blocked tasks (their feedback), "
                       "runs that ended without submitting, guard blocks, timeouts, and what got shipped. Read a few "
                       "transcripts under var/transcripts for the worst failures. Then improve the organization: rewrite "
                       "role charters that keep failing, design new roles if a capability is missing, retire useless ones. "
                       "Record lessons in memory topic 'lessons' and summarize in the journal.",
                       "Concrete charter changes made (or a justified decision not to change), lessons recorded, journal entry written.",
                       "orgdesigner", 2, "runtime", now, now))
            db.event(c, "runtime", "retro_called", f"Retrospective scheduled after {finished} tasks")
        # Daily brief for the Patron, from the liaison.
        today = dt.date.today().isoformat()
        if dt.datetime.now().hour >= 8 and db.get_state(c, "brief_date") != today and roles.load("liaison"):
            db.set_state(c, "brief_date", today)
            c.execute("INSERT INTO messages(sender, recipient, subject, body, created_at) VALUES (?,?,?,?,?)",
                      ("runtime", "liaison", "Write today's brief for the Patron",
                       "Write the Patron's daily brief: what the company did in the last 24h, what shipped (with links), "
                       "what failed, what's next, and anything that needs them. Warm, concise, honest. Send it with "
                       "send_message(to='patron'). Also journal a one-paragraph version.", now))
        # Public record: export status for the site, commit org/docs, push.
        if now - self.last_export > 300:
            self.last_export = now
            try:
                self.export_status()
            except Exception as e:
                log.warning("export failed: %s", e)
        if now - self.last_publish > 900:
            self.last_publish = now
            try:
                if gitops.commit_root(f"Company record {dt.datetime.now():%Y-%m-%d %H:%M}"):
                    gitops.push(ROOT)
            except Exception as e:
                log.warning("publish failed: %s", e)

    def export_status(self):
        c = self.conn
        data = {
            "company": db.get_state(c, "company_name", "Genesis"),
            "tagline": db.get_state(c, "tagline", ""),
            "updated": dt.datetime.now().isoformat(timespec="minutes"),
            "agents_total": c.execute("SELECT COUNT(*) FROM agents").fetchone()[0],
            "leaders": [dict(r) for r in c.execute("SELECT id, role, model, runs FROM agents WHERE kind='leader' AND status!='retired'")],
            "roles": len(roles.load_all()),
            "runs": c.execute("SELECT COUNT(*) FROM runs").fetchone()[0],
            "tasks": {r["status"]: r["n"] for r in c.execute("SELECT status, COUNT(*) n FROM tasks GROUP BY status")},
            "ventures": [dict(r) for r in c.execute("SELECT name, pitch, repo_url, status FROM ventures")],
            "compute_usd_equiv": round(c.execute("SELECT COALESCE(SUM(cost_usd),0) FROM runs").fetchone()[0], 2),
            "shipped": [dict(r) for r in c.execute("SELECT ts, summary FROM events WHERE kind='shipped' ORDER BY id DESC LIMIT 30")],
        }
        (DOCS / "data").mkdir(parents=True, exist_ok=True)
        (DOCS / "data" / "status.json").write_text(json.dumps(data, indent=1))
        journal = [{"date": p.stem, "markdown": p.read_text()}
                   for p in sorted((ROOT / "org" / "journal").glob("*.md"), reverse=True)[:60]]
        (DOCS / "data" / "journal.json").write_text(json.dumps(journal, indent=1))

    # ---------- main loop ----------
    def loop(self):
        self.recover()
        while not self.stopping:
            try:
                self.sync_leaders()
                self.integrate_approved()
                self.rituals()
                pu = self.paused_until()
                if pu and time.time() < pu:
                    time.sleep(TICK_SECONDS * 6)
                    continue
                if pu:
                    db.set_state(self.conn, "paused_until", 0)
                    db.event(self.conn, "runtime", "waking", "Usage limit window reset. The company wakes up.")
                if not db.get_state(self.conn, "halted", False):
                    with self.lock:
                        slots = self.max_parallel() - len(self.running)
                    for job in self.pick(slots):
                        self.launch(job)
            except Exception as e:
                log.error("tick error: %s\n%s", e, traceback.format_exc())
            time.sleep(TICK_SECONDS)

    def stop(self, *_):
        self.stopping = True
        for r in self.conn.execute("SELECT pid FROM runs WHERE status='running' AND pid IS NOT NULL"):
            try:
                os.killpg(r["pid"], signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass


def main():
    LOGS.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=LOGS / "scheduler.log", level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    s = Scheduler()
    signal.signal(signal.SIGTERM, s.stop)
    signal.signal(signal.SIGINT, s.stop)
    from .dashboard import serve_in_background
    serve_in_background()
    s.loop()


if __name__ == "__main__":
    main()
