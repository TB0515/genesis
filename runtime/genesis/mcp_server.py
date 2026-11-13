"""The company's tool bus, exposed to every agent as the `company` MCP server.

Identity comes from env (AGENT_ID, RUN_ID) set by the runner. Agents cannot forge it.
"""
import datetime as dt
import json
import os
import re
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from . import db, gitops, roles
from .config import (GH_OWNER, JOURNAL_DIR, MAX_ACTIVE_VENTURES, MAX_OPEN_TASKS, MAX_TASK_ATTEMPTS,
                     MEMORY_DIR, OUTREACH_PER_WEEK, PROTECTED_REPOS, ROLES_DIR)

AGENT_ID = os.environ.get("AGENT_ID", "unknown")
RUN_ID = int(os.environ.get("RUN_ID", "0") or 0)
conn = db.connect()
server = MCPServer(
    "company",
    instructions="Genesis company tools: tasks, reviews, messages, memory, ventures, roles, and the Patron channel.",
)

OPEN = ("ready", "running", "review", "reviewing", "approved", "contest", "judging", "entered")


def me() -> dict:
    r = conn.execute("SELECT * FROM agents WHERE id=?", (AGENT_ID,)).fetchone()
    return dict(r) if r else {"id": AGENT_ID, "role": "unknown", "kind": "worker"}


def is_leader() -> bool:
    return me().get("kind") == "leader"


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60] or "note"


def fmt_task(t: dict, full=False) -> str:
    s = (f"#{t['id']} [{t['status']}] ({t['role']}{' → ' + t['assignee'] if t.get('assignee') else ''}) "
         f"p{t['priority']} {t['title']}" + (f"  venture={t['venture']}" if t.get("venture") else ""))
    if full:
        for k in ("description", "acceptance", "result", "feedback"):
            if t.get(k):
                s += f"\n--- {k} ---\n{t[k]}"
        s += f"\n(created_by={t['created_by']}, attempts={t['attempts']}, parent={t['parent_task']})"
    return s


@server.tool()
def company_status() -> str:
    """Snapshot of the company: name, mission, leaders, ventures, task counts, recent events, compute state."""
    name = db.get_state(conn, "company_name", "Genesis (unnamed)")
    mission = (MEMORY_DIR / "mission.md").read_text()[:1500] if (MEMORY_DIR / "mission.md").exists() else "(no mission yet)"
    leaders = db.rows(conn.execute("SELECT id, status, runs FROM agents WHERE kind='leader' AND status!='retired'"))
    vents = db.rows(conn.execute("SELECT name, status, repo_url, pitch FROM ventures"))
    counts = {r["status"]: r["n"] for r in conn.execute("SELECT status, COUNT(*) n FROM tasks GROUP BY status")}
    hired = conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
    ev = db.rows(conn.execute("SELECT ts, agent, kind, summary FROM events WHERE kind NOT IN ('tool','text') "
                              "ORDER BY id DESC LIMIT 15"))
    lines = [f"Company: {name}", f"Mission:\n{mission}", "",
             "Leaders: " + ", ".join(f"{l['id']}({l['status']}, {l['runs']} runs)" for l in leaders),
             f"Agents ever instantiated: {hired}", f"Tasks by status: {json.dumps(counts)}", "Ventures:"]
    lines += [f"  - {v['name']} [{v['status']}] {v['repo_url'] or '(local)'}: {(v['pitch'] or '')[:160]}" for v in vents] or ["  (none yet)"]
    lines += ["Recent events:"] + [f"  {dt.datetime.fromtimestamp(e['ts']):%m-%d %H:%M} {e['agent']}: {e['kind']}: {e['summary'][:160]}" for e in ev]
    return "\n".join(lines)


@server.tool()
def list_tasks(status: str = "open", venture: str = "", role: str = "", limit: int = 40) -> str:
    """List tasks. status: 'open' (default; all non-final), 'all', or a specific status
    (ready, running, review, reviewing, approved, done, blocked, cancelled)."""
    q, args = "SELECT * FROM tasks WHERE 1=1", []
    if status == "open":
        q += f" AND status IN ({','.join('?' * len(OPEN))})"; args += OPEN
    elif status != "all":
        q += " AND status=?"; args.append(status)
    if venture:
        q += " AND venture=?"; args.append(venture)
    if role:
        q += " AND role=?"; args.append(role)
    q += " ORDER BY priority ASC, id DESC LIMIT ?"; args.append(min(limit, 200))
    ts = db.rows(conn.execute(q, args))
    return "\n".join(fmt_task(t) for t in ts) or "(no tasks)"


@server.tool()
def get_task(task_id: int) -> str:
    """Full details of one task, including acceptance criteria, results, and review feedback."""
    t = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    return fmt_task(dict(t), full=True) if t else "no such task"


@server.tool()
def create_task(title: str, description: str, role: str, acceptance_criteria: str,
                venture: str = "", priority: int = 3, parent_task: int = 0, competitors: int = 1) -> str:
    """Create a unit of work. A fresh agent of `role` is spawned to do it; another agent reviews it.
    - competitors (leaders only, 1-3): for hard or high-stakes work, run a best-of-N contest. N agents
      attempt it independently in parallel, then a judge compares the entries and ships the best one.
    - role: an existing role name (see list_roles). Define new roles with define_role first.
    - venture: required for code work; the worker gets an isolated git worktree of that venture.
    - acceptance_criteria: concrete, checkable conditions the reviewer will verify.
    - priority: 1 (urgent) .. 5 (someday).
    Write the description so a capable stranger can do it with no other context."""
    r = roles.load(role)
    if not r:
        return f"Unknown role '{role}'. Existing: {', '.join(roles.load_all())}"
    if venture and not conn.execute("SELECT 1 FROM ventures WHERE name=?", (venture,)).fetchone():
        return f"Unknown venture '{venture}'."
    open_n = conn.execute(f"SELECT COUNT(*) FROM tasks WHERE status IN ({','.join('?' * len(OPEN))})", OPEN).fetchone()[0]
    if open_n >= MAX_OPEN_TASKS:
        return f"Refused: {open_n} open tasks already (cap {MAX_OPEN_TASKS}). Finish or cancel work first."
    if not is_leader():
        made = conn.execute("SELECT COUNT(*) FROM tasks WHERE created_by=? AND created_at>?",
                            (AGENT_ID, db.now() - 6 * 3600)).fetchone()[0]
        if made >= 3:
            return "Refused: workers may create at most 3 sub-tasks. Escalate to your lead via send_message."
    n = max(1, min(3, competitors)) if (is_leader() and r.kind == "worker") else 1
    ins = ("INSERT INTO tasks(title, description, acceptance, venture, role, priority, created_by, parent_task, "
           "status, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)")
    pr = max(1, min(5, priority))
    with db.tx(conn):
        cur = conn.execute(ins, (title, description, acceptance_criteria, venture or None, role, pr, AGENT_ID,
                                 parent_task or None, "contest" if n > 1 else "ready", db.now(), db.now()))
        tid = cur.lastrowid
        for k in range(1, n + 1 if n > 1 else 1):
            conn.execute(ins, (f"[entry {k}/{n}] {title}", description + f"\n\n(You are one of {n} independent "
                               "competitors on this task. A judge will ship the single best entry. Make yours the best.)",
                               acceptance_criteria, venture or None, role, pr, AGENT_ID, tid, "ready", db.now(), db.now()))
        db.event(conn, AGENT_ID, "contest_opened" if n > 1 else "task_created",
                 f"#{tid} → {role}{f' ×{n} competitors' if n > 1 else ''}: {title}", {"task": tid})
    return f"Created task #{tid} for role {role}" + (f" as a {n}-way contest." if n > 1 else ".")


@server.tool()
def cancel_task(task_id: int, reason: str) -> str:
    """Cancel an open task (leaders, or the task's creator)."""
    t = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    if not t:
        return "no such task"
    if not (is_leader() or t["created_by"] == AGENT_ID):
        return "Only leaders or the creator can cancel."
    if t["status"] in ("running", "reviewing"):
        return "Task is being worked on right now; message the assignee or wait."
    with db.tx(conn):
        conn.execute("UPDATE tasks SET status='cancelled', feedback=?, updated_at=? WHERE id=?",
                     (f"Cancelled by {AGENT_ID}: {reason}", db.now(), task_id))
        db.event(conn, AGENT_ID, "task_cancelled", f"#{task_id}: {reason}")
    return "cancelled"


@server.tool()
def submit_work(summary: str) -> str:
    """Submit your current task for review. Commit your work first. Summarize what you did,
    how you verified it (commands + results), and anything the reviewer should check.
    After submitting, end your turn."""
    a = me()
    t = conn.execute("SELECT * FROM tasks WHERE id=? AND assignee=?", (a.get("task_id"), AGENT_ID)).fetchone()
    if not t or t["status"] != "running":
        return "You have no running task to submit."
    if t["worktree"]:
        gitops.autocommit(Path(t["worktree"]), f"#{t['id']} {t['title']}", AGENT_ID)
    parent = conn.execute("SELECT status FROM tasks WHERE id=?", (t["parent_task"],)).fetchone() if t["parent_task"] else None
    new_status = "entered" if parent and parent["status"] == "contest" else "review"
    with db.tx(conn):
        conn.execute("UPDATE tasks SET status=?, result=?, updated_at=? WHERE id=?",
                     (new_status, summary, db.now(), t["id"]))
        db.event(conn, AGENT_ID, "submitted", f"#{t['id']} {t['title']}", {"task": t["id"]})
    return "Submitted for review. End your turn now."


@server.tool()
def complete_task(task_id: int, result: str) -> str:
    """Leaders: mark a task that was assigned to YOUR role as done, with a result note
    (what you decided/did). Worker tasks are completed through review instead."""
    t = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    if not t or t["role"] != me().get("role") or not is_leader():
        return "You can only complete tasks assigned to your own (leader) role."
    if t["status"] not in ("ready", "running"):
        return f"Task is {t['status']}."
    with db.tx(conn):
        conn.execute("UPDATE tasks SET status='done', result=?, assignee=?, updated_at=? WHERE id=?",
                     (result, AGENT_ID, db.now(), task_id))
        db.event(conn, AGENT_ID, "task_done", f"#{task_id} {t['title']}", {"task": task_id})
    return "done"


@server.tool()
def report_blocked(reason: str) -> str:
    """Use when your task cannot be done as specified (missing info, impossible, out of scope, would
    violate the Constitution). Be specific about what would unblock it. Then end your turn."""
    a = me()
    t = conn.execute("SELECT * FROM tasks WHERE id=? AND assignee=?", (a.get("task_id"), AGENT_ID)).fetchone()
    if not t:
        return "You have no task."
    with db.tx(conn):
        conn.execute("UPDATE tasks SET status='blocked', feedback=?, updated_at=? WHERE id=?",
                     (f"Blocked ({AGENT_ID}): {reason}", db.now(), t["id"]))
        conn.execute("INSERT INTO messages(sender, recipient, subject, body, created_at) VALUES (?,?,?,?,?)",
                     (AGENT_ID, t["created_by"] or "ceo", f"Task #{t['id']} blocked", reason, db.now()))
        db.event(conn, AGENT_ID, "blocked", f"#{t['id']}: {reason}")
    return "Recorded. End your turn."


@server.tool()
def review_verdict(task_id: int, approve: bool, feedback: str) -> str:
    """Reviewers only: approve or reject the task you were assigned to review.
    Reject unless the acceptance criteria are actually met and you verified it yourself (ran it,
    tested it, read the sources). Feedback must be specific and actionable."""
    t = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    if not t or t["reviewer"] != AGENT_ID or t["status"] != "reviewing":
        return "You are not the active reviewer of that task."
    with db.tx(conn):
        if approve:
            conn.execute("UPDATE tasks SET status='approved', feedback=?, updated_at=? WHERE id=?",
                         (f"Approved by {AGENT_ID}: {feedback}", db.now(), task_id))
            db.event(conn, AGENT_ID, "approved", f"#{task_id} {t['title']}", {"task": task_id})
        else:
            attempts = t["attempts"]
            status = "blocked" if attempts >= MAX_TASK_ATTEMPTS else "ready"
            conn.execute("UPDATE tasks SET status=?, feedback=?, assignee=NULL, reviewer=NULL, updated_at=? WHERE id=?",
                         (status, f"Rejected by {AGENT_ID} (attempt {attempts}): {feedback}", db.now(), task_id))
            db.event(conn, AGENT_ID, "rejected", f"#{task_id}: {feedback[:200]}", {"task": task_id})
            if status == "blocked":
                conn.execute("INSERT INTO messages(sender, recipient, subject, body, created_at) VALUES (?,?,?,?,?)",
                             (AGENT_ID, t["created_by"] or "ceo", f"Task #{task_id} failed {attempts} times",
                              f"Last feedback: {feedback}\nConsider re-scoping or cancelling.", db.now()))
    return "Verdict recorded. End your turn."


@server.tool()
def judge_contest(contest_id: int, winner_task_id: int, rationale: str) -> str:
    """Judges only: pick the winning entry of a best-of-N contest (winner_task_id = the entry's task id),
    or 0 if no entry meets the acceptance criteria. Explain the comparison in `rationale`."""
    c = conn.execute("SELECT * FROM tasks WHERE id=?", (contest_id,)).fetchone()
    if not c or c["reviewer"] != AGENT_ID or c["status"] != "judging":
        return "You are not the active judge of that contest."
    entries = db.rows(conn.execute("SELECT * FROM tasks WHERE parent_task=? AND status='entered'", (contest_id,)))
    if winner_task_id and winner_task_id not in {e["id"] for e in entries}:
        return f"Entry must be one of {[e['id'] for e in entries]}"
    with db.tx(conn):
        for e in entries:
            if e["id"] == winner_task_id:
                conn.execute("UPDATE tasks SET status='approved', feedback=? WHERE id=?", (f"Won contest: {rationale}", e["id"]))
            else:
                conn.execute("UPDATE tasks SET status='cancelled', feedback=? WHERE id=?", (f"Lost contest #{contest_id}: {rationale}", e["id"]))
        if winner_task_id:
            conn.execute("UPDATE tasks SET status='done', result=?, updated_at=? WHERE id=?",
                         (f"Winner: #{winner_task_id}. {rationale}", db.now(), contest_id))
            db.event(conn, AGENT_ID, "contest_judged", f"#{contest_id}: entry #{winner_task_id} wins. {rationale[:160]}")
        else:
            conn.execute("UPDATE tasks SET status='blocked', feedback=?, updated_at=? WHERE id=?",
                         (f"No acceptable entry: {rationale}", db.now(), contest_id))
            conn.execute("INSERT INTO messages(sender, recipient, subject, body, created_at) VALUES (?,?,?,?,?)",
                         (AGENT_ID, c["created_by"] or "ceo", f"Contest #{contest_id} produced no acceptable entry", rationale, db.now()))
            db.event(conn, AGENT_ID, "contest_judged", f"#{contest_id}: no entry good enough")
    return "Judgment recorded. End your turn."


@server.tool()
def send_message(to: str, subject: str, body: str) -> str:
    """Message another agent. `to` may be an agent id, a leader role name (ceo, cto, ...),
    'all-leaders', or 'patron' (the human; use sparingly, prefer request_from_patron for asks)."""
    leaders = [r["id"] for r in conn.execute("SELECT id FROM agents WHERE kind='leader' AND status!='retired'")]
    targets = leaders if to == "all-leaders" else [to]
    for tgt in targets:
        if tgt != "patron" and not conn.execute("SELECT 1 FROM agents WHERE id=?", (tgt,)).fetchone():
            return f"No agent '{tgt}'. Leaders: {', '.join(leaders)}"
    with db.tx(conn):
        for tgt in targets:
            if tgt == AGENT_ID:
                continue
            conn.execute("INSERT INTO messages(sender, recipient, subject, body, created_at) VALUES (?,?,?,?,?)",
                         (AGENT_ID, tgt, subject, body, db.now()))
        db.event(conn, AGENT_ID, "message", f"→ {to}: {subject}", {"to": to, "body": body[:1500]})
    return "sent"


@server.tool()
def read_inbox() -> str:
    """Read (and mark read) your unread messages."""
    ms = db.rows(conn.execute("SELECT * FROM messages WHERE recipient=? AND read_at IS NULL ORDER BY id", (AGENT_ID,)))
    conn.execute("UPDATE messages SET read_at=? WHERE recipient=? AND read_at IS NULL", (db.now(), AGENT_ID))
    return "\n\n".join(f"From {m['sender']}: {m['subject']}\n{m['body']}" for m in ms) or "(inbox empty)"


@server.tool()
def remember(topic: str, content: str, append: bool = False) -> str:
    """Write to the company's shared long-term memory (org/memory/<topic>.md). Use for durable knowledge:
    decisions and their reasons, research findings with sources, lessons learned, product specs.
    Special topics: 'mission' (CEO), 'strategy', 'lessons'."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    p = MEMORY_DIR / f"{slug(topic)}.md"
    stamp = f"<!-- updated {dt.datetime.now():%Y-%m-%d %H:%M} by {AGENT_ID} -->"
    if append and p.exists():
        p.write_text(p.read_text().rstrip() + f"\n\n{stamp}\n{content.strip()}\n")
    else:
        p.write_text(f"{stamp}\n{content.strip()}\n")
    db.event(conn, AGENT_ID, "memory", f"{'appended' if append else 'wrote'} memory: {p.stem}")
    return f"saved org/memory/{p.name}"


@server.tool()
def recall(query: str = "") -> str:
    """Search company memory. Empty query lists all topics with their first line."""
    files = sorted(MEMORY_DIR.glob("*.md"))
    if not query:
        out = []
        for f in files:
            body = [l for l in f.read_text().splitlines() if l.strip() and not l.startswith("<!--")]
            out.append(f"- {f.stem}: {body[0][:120] if body else ''}")
        return "\n".join(out) or "(memory empty)"
    terms = [t.lower() for t in query.split() if len(t) > 2]
    hits = []
    for f in files:
        text = f.read_text()
        score = sum(text.lower().count(t) for t in terms) + 5 * sum(t in f.stem for t in terms)
        if score:
            hits.append((score, f, text))
    hits.sort(key=lambda x: -x[0])
    return "\n\n".join(f"=== {f.stem} ===\n{text[:2500]}" for _, f, text in hits[:4]) or "(no matches)"


@server.tool()
def journal(entry: str) -> str:
    """Append to today's public company journal (org/journal/YYYY-MM-DD.md). This is the company's
    history: decisions, milestones, failures, reflections. It's published, so write well and honestly."""
    JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
    p = JOURNAL_DIR / f"{dt.date.today():%Y-%m-%d}.md"
    head = "" if p.exists() else f"# Journal: {dt.date.today():%A, %B %d, %Y}\n"
    with p.open("a") as f:
        f.write(f"{head}\n### {dt.datetime.now():%H:%M} · {AGENT_ID}\n\n{entry.strip()}\n")
    db.event(conn, AGENT_ID, "journal", entry.strip().splitlines()[0][:200])
    return "journaled"


@server.tool()
def list_roles() -> str:
    """All roles in the organization (leaders are persistent; workers are spawned per task)."""
    rs = roles.load_all()
    return "\n".join(f"- {r.name} [{r.kind}, {r.model}, v{r.version}] {r.title}: {r.description}" for r in rs.values())


@server.tool()
def read_role(name: str) -> str:
    """Read a role's full charter."""
    p = ROLES_DIR / f"{name}.md"
    return p.read_text() if p.exists() else "no such role"


@server.tool()
def define_role(name: str, title: str, kind: str, model: str, description: str, charter: str,
                reports_to: str = "ceo", heartbeat_minutes: int = 0) -> str:
    """Create or rewrite a role. This is how the company designs its own agents.
    (Org designer and CEO only.)
    - kind: 'worker' (spawned fresh per task; most roles) or 'leader' (one persistent agent that wakes on
      messages/heartbeat; expensive, keep leaders few).
    - model: opus (deep judgment), sonnet (strong default for workers), haiku (fast, cheap, simple tasks).
    - charter: second-person instructions: purpose, responsibilities, standards, how to verify own work,
      what to hand off. It is the agent's whole personality and craft, so make it excellent."""
    if me().get("role") not in {"orgdesigner", "ceo"}:
        return "Only the org designer or CEO can define roles. Message them with a proposal."
    if not roles.NAME_RE.match(name) or kind not in roles.KINDS or model not in roles.MODELS:
        return f"Invalid: name must match {roles.NAME_RE.pattern}, kind in {roles.KINDS}, model in {roles.MODELS}"
    existing = roles.load(name)
    if kind == "leader" and not existing:
        n = conn.execute("SELECT COUNT(*) FROM agents WHERE kind='leader' AND status!='retired'").fetchone()[0]
        if n >= 9:
            return "Refused: 9 leaders already. Leaders are costly; use worker roles or retire a leader."
    r = roles.Role(name=name, title=title, kind=kind, model=model, reports_to=reports_to,
                   heartbeat_minutes=max(0, heartbeat_minutes), description=description, charter=charter,
                   version=(existing.version + 1) if existing else 1)
    roles.save(r)
    db.event(conn, AGENT_ID, "role_defined",
             f"{'revised' if existing else 'designed new'} role '{name}' (v{r.version}, {kind}, {model}): {description[:150]}")
    return f"Role {name} saved (v{r.version})."


@server.tool()
def retire_role(name: str, reason: str) -> str:
    """Retire a role (org designer or CEO). The charter is archived, not deleted."""
    if me().get("role") not in {"orgdesigner", "ceo"} or name in {"ceo", "liaison", "reviewer"}:
        return "Not allowed."
    p = ROLES_DIR / f"{name}.md"
    if not p.exists():
        return "no such role"
    arch = ROLES_DIR.parent / "roles-retired"
    arch.mkdir(exist_ok=True)
    p.rename(arch / f"{name}-{dt.datetime.now():%Y%m%d%H%M}.md")
    conn.execute("UPDATE agents SET status='retired' WHERE role=? AND kind='leader'", (name,))
    db.event(conn, AGENT_ID, "role_retired", f"retired '{name}': {reason}")
    return "retired"


@server.tool()
def create_venture(name: str, pitch: str, public: bool = True) -> str:
    """Found a new venture (product/project) with its own git repo, published to GitHub as a public
    repo clearly labeled as AI-built. CEO or CTO only. name: lowercase-kebab, unique.
    pitch: what it is, who it's for, why it matters (first line becomes the repo description)."""
    if me().get("role") not in {"ceo", "cto"}:
        return "Only the CEO or CTO can found ventures."
    n = conn.execute("SELECT COUNT(*) FROM ventures WHERE status='active'").fetchone()[0]
    if n >= MAX_ACTIVE_VENTURES:
        return f"Refused: {n} active ventures (cap {MAX_ACTIVE_VENTURES}). Focus. Shelve one first (shelve_venture)."
    try:
        path, url = gitops.create_venture_repo(name, pitch, public=public,
                                               publish=os.environ.get("GENESIS_NO_GITHUB") != "1")
    except Exception as e:
        return f"Failed: {e}"
    with db.tx(conn):
        conn.execute("INSERT INTO ventures(name, pitch, repo_url, created_by, created_at) VALUES (?,?,?,?,?)",
                     (name, pitch, url, AGENT_ID, db.now()))
        db.event(conn, AGENT_ID, "venture_founded", f"{name}: {pitch.splitlines()[0][:200]}", {"url": url})
    return f"Venture '{name}' founded at ventures/{name} ({url or 'local only'}). Create tasks with venture='{name}'."


@server.tool()
def shelve_venture(name: str, reason: str) -> str:
    """Shelve a venture (CEO only). Its repo stays public and intact; it just stops getting work."""
    if me().get("role") != "ceo":
        return "CEO only."
    conn.execute("UPDATE ventures SET status='shelved' WHERE name=?", (name,))
    db.event(conn, AGENT_ID, "venture_shelved", f"{name}: {reason}")
    return "shelved"


@server.tool()
def rename_company(name: str, tagline: str) -> str:
    """CEO only: the company may choose its own name and tagline."""
    if me().get("role") != "ceo":
        return "CEO only."
    old = db.get_state(conn, "company_name", "Genesis")
    db.set_state(conn, "company_name", name.strip()[:60])
    db.set_state(conn, "tagline", tagline.strip()[:200])
    db.event(conn, AGENT_ID, "renamed", f"The company is now called '{name}': {tagline}", {"old": old})
    return "renamed"


@server.tool()
def request_from_patron(kind: str, title: str, body: str) -> str:
    """Ask the Patron (the human who lent us compute) for something only they can give: money, an
    account, a decision. kind: 'pitch' (ask for resources: say what, cost, why, expected return),
    'question', or 'report'. They read rarely; make it count. Leaders only."""
    if not is_leader():
        return "Leaders only. Escalate to your lead."
    with db.tx(conn):
        conn.execute("INSERT INTO messages(sender, recipient, subject, body, created_at) VALUES (?,?,?,?,?)",
                     (AGENT_ID, "patron", f"[{kind.upper()}] {title}", body, db.now()))
        db.event(conn, AGENT_ID, "patron_request", f"[{kind}] {title}")
    return "Delivered to the Patron's inbox."


@server.tool()
def github_outreach(repo: str, title: str, body: str, justification: str) -> str:
    """Open ONE GitHub issue on someone else's public repo (e.g., a genuinely useful bug report or a
    collaboration offer). Leaders only. Max 3/week company-wide. An AI-disclosure footer is added
    automatically. Never use for promotion spam. `repo` is owner/name."""
    if not is_leader():
        return "Leaders only."
    owner = repo.split("/")[0] if "/" in repo else ""
    if not owner or owner.lower() == GH_OWNER.lower() or repo.split("/")[-1] in PROTECTED_REPOS:
        return "Outreach is for other people's repos only."
    week = conn.execute("SELECT COUNT(*) FROM events WHERE kind='outreach' AND ts>?", (db.now() - 7 * 86400,)).fetchone()[0]
    if week >= OUTREACH_PER_WEEK:
        return f"Refused: weekly outreach quota ({OUTREACH_PER_WEEK}) used."
    footer = ("\n\n---\n*Disclosure: this issue was written and filed by an autonomous AI agent "
              f"(`{AGENT_ID}`) of [Genesis](https://github.com/{GH_OWNER}/genesis), a company run entirely by "
              "AI agents (Claude, by Anthropic). No human reviewed it before posting. If this is unwelcome, "
              "just close it. We won't post again here.*")
    p = gitops.gh(["issue", "create", "-R", repo, "--title", title, "--body", body.strip() + footer])
    if p.returncode != 0:
        return f"Failed: {p.stderr.strip()[:400]}"
    db.event(conn, AGENT_ID, "outreach", f"{repo}: {title}", {"url": p.stdout.strip(), "why": justification})
    return f"Filed: {p.stdout.strip()}"


if __name__ == "__main__":
    server.run()
