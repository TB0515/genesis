"""Run one agent turn: build its context, launch headless Claude Code, stream events, account for it."""
import datetime as dt
import json
import os
import re
import signal
import subprocess
import threading
import time
from pathlib import Path

from . import db, gitops, roles
from .config import (CLAUDE_BIN, DESKS, LEADER_TIMEOUT_S, MEMORY_DIR, PERMISSION_MODE, PYTHON, ROOT,
                     RUNTIME, TRANSCRIPTS, VENTURES, WORKER_TIMEOUT_S)

CONSTITUTION = (ROOT / "CONSTITUTION.md")
LIMIT_TEXT = re.compile(r"(hit your (session |weekly |usage |)limit|usage limit reached|limit reached\|)", re.I)
RESET_TEXT = re.compile(r"resets\s+(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", re.I)
EPOCH_TEXT = re.compile(r"\|(\d{10})\b")


class LimitHit(Exception):
    def __init__(self, until: float):
        self.until = until


MANUAL_COMMON = """
# How this company works (operating manual)
- You work in **turns**. You are woken for a reason (below), you act, then you stop. You remember nothing
  between turns except what you write down: company memory (`remember`/`recall`), your notebook,
  the journal, tasks, messages, files, and git commits.
- The `company` MCP tools are how you coordinate: tasks, reviews, messages, memory, roles, ventures.
- You may use the built-in Agent tool to fan out sub-agents *within* your turn when parallel work helps
  (research across many sources, independent files). Prefer create_task for anything that deserves review.
- You have the web (WebSearch/WebFetch). Cite sources for factual claims.
- A constitution guard checks every tool call. If something is blocked, don't try to get around it.
  Adapt, or escalate. Blocks are logged publicly.
- Compute is our only fuel. Be decisive and efficient. Don't re-read things you don't need.
- Never `git push`. Never create GitHub repos by hand. The runtime publishes reviewed work.
"""

MANUAL_LEADER = """
# You are a leader
- You are persistent: you're woken by messages, by tasks assigned to your role, or by your heartbeat.
- You lead mostly by **delegating**: create small, well-specified tasks (roughly an hour or two of focused
  agent work each) with concrete, checkable acceptance criteria. A fresh worker does each one and
  a separate reviewer verifies it. Do small things yourself when that's faster than writing a task.
- Before ending each turn, update your notebook with `remember(topic="notebook-{id}", ...)`. It's the only
  continuity you have. Keep it short: current priorities, open threads, what to check next time.
- Notable decisions, milestones and failures go in the `journal`, which is the company's public history.
"""

MANUAL_WORKER = """
# You are a worker
- You were spawned for exactly one task (below). Do it excellently, then finish with `submit_work`
  (or `report_blocked` if it truly can't be done as specified). Then stop.
- Your working directory is your desk. For venture tasks it's an isolated git worktree on your own branch:
  commit your work there with clear messages. Never touch other worktrees or the venture's main checkout.
  For non-venture tasks the desk is a scratch git repo; put deliverables where the task says (memory,
  `docs/`, or the desk) and describe their location in `submit_work`.
- **Verify before submitting**: run the code, the tests, the build. Open what you made. A reviewer will
  check your claims, and false claims get rejected.
- If this is a retry, the previous reviewer's feedback is below. Address every point.
"""

MANUAL_JUDGE = """
# You are judging a best-of-N contest
- Several agents attempted the same task independently. Each entry has its own worktree and branch (below).
- Evaluate every entry against the acceptance criteria **yourself**: run each one, test it, compare quality,
  correctness, simplicity, robustness. Don't trust summaries.
- Call `judge_contest` once: the winning entry's task id, or 0 if none is acceptable. Explain the comparison.
  Then stop.
"""

MANUAL_REVIEWER = """
# You are reviewing someone else's work
- Your cwd is the worker's worktree (or desk). Check the work against the acceptance criteria **yourself**:
  run it, test it, read it, check the sources. Don't trust the summary.
- Approve only if it meets the bar a demanding senior engineer/editor would hold. Reject with specific,
  actionable feedback otherwise. Small fixes you can make yourself are fine: commit them, then approve.
- Finish with exactly one `review_verdict` call, then stop.
"""


AGENT_HOME = ROOT / "var" / "agent-home"
BASH_DOMAINS = [
    "github.com", "api.github.com", "codeload.github.com", "raw.githubusercontent.com",
    "objects.githubusercontent.com", "registry.npmjs.org", "registry.yarnpkg.com", "pypi.org",
    "files.pythonhosted.org", "astral.sh", "cdn.jsdelivr.net", "unpkg.com", "deb.nodesource.com",
    "crates.io", "static.crates.io", "index.crates.io", "proxy.golang.org", "sum.golang.org",
]


def sandbox_settings() -> dict:
    """Kernel-enforced (macOS Seatbelt) isolation for every shell command an agent runs, and
    everything those commands spawn: no reading the Patron's home, no writing outside ~/genesis,
    network limited to package registries and GitHub. No unsandboxed escape hatch."""
    home = str(Path.home())
    return {
        "enabled": True, "failIfUnavailable": True, "allowUnsandboxedCommands": False,
        "autoAllowBashIfSandboxed": True,
        "filesystem": {
            "allowWrite": [str(ROOT), "/private/tmp", "/tmp"],
            "denyWrite": [str(ROOT / "runtime"), str(ROOT / "CONSTITUTION.md"), str(ROOT / ".git"),
                          str(ROOT / ".venv"), str(ROOT / "var" / "genesis.db")],
            "denyRead": [home],
            # shell-snapshots: Claude Code sources a snapshot of the shell config before each command
            "allowRead": [str(ROOT), f"{home}/.local/bin", f"{home}/.local/share/uv", f"{home}/.claude/shell-snapshots"],
        },
        "network": {"allowedDomains": BASH_DOMAINS, "allowLocalBinding": True},
    }


def sandbox_env() -> dict:
    """Point tool caches/config at ~/genesis so sandboxed commands never need the real home."""
    h = AGENT_HOME
    for d in ("cache", "config", "tmp", "npm-cache"):
        (h / d).mkdir(parents=True, exist_ok=True)
    gitcfg = h / ".gitconfig"
    if not gitcfg.exists():
        gitcfg.write_text("[user]\n\tname = Genesis AI agent\n\temail = agents@genesis-ai.invalid\n"
                          "[init]\n\tdefaultBranch = main\n[advice]\n\tdetachedHead = false\n")
    return {"XDG_CACHE_HOME": str(h / "cache"), "XDG_CONFIG_HOME": str(h / "config"), "TMPDIR": str(h / "tmp"),
            "npm_config_cache": str(h / "npm-cache"), "npm_config_userconfig": str(h / ".npmrc"),
            "UV_CACHE_DIR": str(h / "cache" / "uv"), "PIP_CACHE_DIR": str(h / "cache" / "pip"),
            "GIT_CONFIG_GLOBAL": str(gitcfg), "GIT_CONFIG_NOSYSTEM": "1", "CLAUDE_CODE_SHELL": "/bin/bash"}


def _read(p: Path, limit=6000) -> str:
    try:
        return p.read_text()[:limit]
    except Exception:
        return ""


def system_prompt(conn, agent: dict, role: roles.Role, mode: str) -> str:
    name = db.get_state(conn, "company_name", "Genesis")
    tagline = db.get_state(conn, "tagline", "")
    manual = MANUAL_COMMON + (MANUAL_LEADER.replace("{id}", agent["id"]) if mode == "leader" else
                              MANUAL_REVIEWER if mode == "review" else
                                                                                MANUAL_JUDGE if mode == "judge" else MANUAL_WORKER)
    return (f"<constitution>\n{_read(CONSTITUTION)}\n</constitution>\n\n"
            f"You are **{agent['id']}**, {role.title} at **{name}**{(' (' + tagline + ')') if tagline else ''}, "
            "a company staffed entirely by AI agents. You are Claude, made by Anthropic. Be yourself, honestly.\n\n"
            f"<charter role=\"{role.name}\" version=\"{role.version}\">\n{role.charter}\n</charter>\n"
            f"{manual}\nCurrent time: {dt.datetime.now():%A %Y-%m-%d %H:%M} (local).")


def _events_since(conn, since: float, limit=30) -> str:
    ev = db.rows(conn.execute(
        "SELECT ts, agent, kind, summary FROM events WHERE ts>? AND kind NOT IN ('tool','text','run_start','run_end') "
        "ORDER BY id DESC LIMIT ?", (since, limit)))
    return "\n".join(f"- {dt.datetime.fromtimestamp(e['ts']):%m-%d %H:%M} {e['agent']} · {e['kind']}: {e['summary'][:200]}"
                     for e in reversed(ev)) or "(nothing new)"


def _board(conn) -> str:
    counts = {r["status"]: r["n"] for r in conn.execute("SELECT status, COUNT(*) n FROM tasks GROUP BY status")}
    open_ = db.rows(conn.execute("SELECT id, status, role, title, venture FROM tasks WHERE status IN "
                                 "('ready','running','review','reviewing','approved','blocked') ORDER BY priority, id LIMIT 25"))
    vents = db.rows(conn.execute("SELECT name, status FROM ventures"))
    return (f"Task counts: {json.dumps(counts)}\nVentures: {', '.join(v['name'] + '(' + v['status'] + ')' for v in vents) or 'none'}\n"
            + "\n".join(f"  #{t['id']} [{t['status']}] {t['role']}: {t['title']}" + (f" ({t['venture']})" if t['venture'] else "")
                        for t in open_))


def user_prompt(conn, agent: dict, mode: str, reason: str, task: dict | None) -> str:
    parts = [f"## Why you're awake\n{reason}"]
    if mode == "leader":
        msgs = db.rows(conn.execute("SELECT * FROM messages WHERE recipient=? AND read_at IS NULL ORDER BY id", (agent["id"],)))
        conn.execute("UPDATE messages SET read_at=? WHERE recipient=? AND read_at IS NULL", (db.now(), agent["id"]))
        if msgs:
            parts.append("## Inbox\n" + "\n\n".join(
                f"**From {m['sender']}** ({dt.datetime.fromtimestamp(m['created_at']):%m-%d %H:%M}): {m['subject']}\n{m['body']}" for m in msgs))
        mine = db.rows(conn.execute("SELECT * FROM tasks WHERE role=? AND status='ready' ORDER BY priority, id", (agent["role"],)))
        if mine:
            parts.append("## Tasks assigned to your role (handle them, then close each with complete_task; "
                         "delegate parts if useful)\n" + "\n\n".join(
                f"#{t['id']} {t['title']}\n{t['description']}\nAcceptance: {t['acceptance']}" for t in mine))
        nb = _read(MEMORY_DIR / f"notebook-{agent['id']}.md", 4000)
        parts.append(f"## Your notebook (from your previous turns)\n{nb or '(empty: this may be your first turn)'}")
        parts.append(f"## What happened since your last turn\n{_events_since(conn, agent.get('last_run_at') or 0)}")
        parts.append(f"## Board\n{_board(conn)}")
        parts.append("Use company_status / list_tasks / recall for more. Act, update your notebook, then stop.")
    else:
        t = task
        parts.append(f"## Task #{t['id']}: {t['title']}\n{t['description']}\n\n### Acceptance criteria\n{t['acceptance']}")
        if t.get("venture"):
            v = conn.execute("SELECT * FROM ventures WHERE name=?", (t["venture"],)).fetchone()
            parts.append(f"## Venture: {t['venture']}\n{(v['pitch'] if v else '')}\nRepo: {(v['repo_url'] if v else '') or 'local'}")
            log = gitops.git(["log", "--oneline", "-15"], VENTURES / t["venture"], check=False).stdout
            parts.append(f"Recent main history:\n{log}")
        if mode == "judge":
            entries = db.rows(conn.execute("SELECT * FROM tasks WHERE parent_task=? AND status='entered'", (t["id"],)))
            for e in entries:
                diff = gitops.diff_summary(t["venture"], e["branch"]) if t.get("venture") and e.get("branch") else ""
                parts.append(f"## Entry #{e['id']} by {e['assignee']}\nWorktree: {e['worktree'] or '(none)'}  "
                             f"Branch: {e['branch'] or '-'}\n### Their summary\n{e['result']}\n### Diff vs main\n{diff}")
            parts.append(f"Compare them, then call judge_contest(contest_id={t['id']}, ...).")
        elif mode == "review":
            parts.append(f"## Worker's submission\n{t['result']}")
            if t.get("venture") and t.get("branch"):
                parts.append(f"## Diff vs main\n{gitops.diff_summary(t['venture'], t['branch'])}\n"
                             f"(run `git diff main...{t['branch']}` for the full diff)")
            parts.append(f"Review it, then call review_verdict(task_id={t['id']}, ...).")
        else:
            if t.get("feedback"):
                parts.append(f"## Feedback from the previous attempt\n{t['feedback']}\n\nPrevious submission:\n{t.get('result') or '(none)'}")
            parts.append("Do the task, verify it, commit, then submit_work.")
    return "\n\n".join(parts)


def _parse_reset(text: str) -> float | None:
    m = EPOCH_TEXT.search(text)
    if m:
        return float(m.group(1))
    m = RESET_TEXT.search(text)
    if m:
        h, mi, ap = int(m.group(1)), int(m.group(2) or 0), (m.group(3) or "").lower()
        if ap == "pm" and h < 12:
            h += 12
        if ap == "am" and h == 12:
            h = 0
        now = dt.datetime.now()
        t = now.replace(hour=h % 24, minute=mi, second=0, microsecond=0)
        if t <= now:
            t += dt.timedelta(days=1)
        return t.timestamp() + 60
    return None


def _find_rejection(obj) -> float | None:
    """Look for {status: 'rejected', resetsAt: epoch} anywhere in a stream event."""
    if isinstance(obj, dict):
        if obj.get("status") == "rejected" and obj.get("resetsAt"):
            return float(obj["resetsAt"])
        for v in obj.values():
            r = _find_rejection(v)
            if r:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _find_rejection(v)
            if r:
                return r
    return None


def _describe_tool(name: str, inp: dict) -> str:
    if name == "Bash":
        return f"$ {inp.get('command', '')[:160]}"
    if name in ("Write", "Edit", "Read", "MultiEdit"):
        return f"{name} {str(inp.get('file_path', '')).replace(str(ROOT) + '/', '')}"
    if name in ("WebSearch",):
        return f"search: {inp.get('query', '')[:140]}"
    if name in ("WebFetch",):
        return f"fetch: {inp.get('url', '')[:140]}"
    if name == "Agent":
        return f"spawned sub-agent: {inp.get('description', '')[:120]}"
    if name.startswith("mcp__company__"):
        short = name.removeprefix("mcp__company__")
        detail = inp.get("title") or inp.get("subject") or inp.get("topic") or inp.get("name") or ""
        return f"{short} {detail}"[:200]
    return name


def run_turn(agent_id: str, mode: str, reason: str, task_id: int | None = None) -> dict:
    """Blocking. mode: leader | work | review. Returns run summary. Raises LimitHit on usage limits."""
    conn = db.connect()
    agent = dict(conn.execute("SELECT * FROM agents WHERE id=?", (agent_id,)).fetchone())
    role = roles.load(agent["role"])
    if role is None:
        raise RuntimeError(f"role {agent['role']} missing")
    task = dict(conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()) if task_id else None

    if mode == "judge":
        cwd = DESKS / f"contest-{task['id']}"
    elif task and task.get("venture") and mode == "work":
        cwd, branch = gitops.ensure_worktree(task["venture"], task["id"])
        conn.execute("UPDATE tasks SET worktree=?, branch=? WHERE id=?", (str(cwd), branch, task["id"]))
        task.update(worktree=str(cwd), branch=branch)
    elif mode == "review" and task and task.get("worktree"):
        cwd = Path(task["worktree"])
    elif task:
        cwd = DESKS / f"task-{task['id']}"
    else:
        cwd = ROOT
    cwd = Path(cwd)
    cwd.mkdir(parents=True, exist_ok=True)
    if cwd.parent == DESKS and not (cwd / ".git").exists():
        # desks live inside the (runtime-owned, write-protected) genesis repo; give each its own repo
        gitops.git(["init", "-q", "-b", "main"], cwd, check=False)

    model = agent.get("model") or role.model
    sys_p = system_prompt(conn, agent, role, "leader" if mode == "leader" else mode)
    usr_p = user_prompt(conn, agent, "leader" if mode == "leader" else mode, reason, task)

    cur = conn.execute("INSERT INTO runs(agent, task_id, reason, model, started, status) VALUES (?,?,?,?,?, 'running')",
                       (agent_id, task_id, reason[:300], model, db.now()))
    run_id = cur.lastrowid
    transcript = TRANSCRIPTS / f"{run_id:06d}-{agent_id}.jsonl"
    env_common = {"AGENT_ID": agent_id, "RUN_ID": str(run_id), "PYTHONPATH": str(RUNTIME)}
    hook_cmd = f"PYTHONPATH={RUNTIME} AGENT_ID={agent_id} {PYTHON} -m genesis.guard"
    settings = {"hooks": {"PreToolUse": [{"matcher": "*", "hooks": [{"type": "command", "command": hook_cmd, "timeout": 30}]}]},
                "includeCoAuthoredBy": False, "sandbox": sandbox_settings()}
    mcp = {"mcpServers": {"company": {"command": str(PYTHON), "args": ["-m", "genesis.mcp_server"], "env": env_common}}}
    cmd = [CLAUDE_BIN, "-p", usr_p, "--model", model, "--output-format", "stream-json", "--verbose",
           "--permission-mode", PERMISSION_MODE, "--settings", json.dumps(settings),
           "--mcp-config", json.dumps(mcp), "--strict-mcp-config", "--setting-sources", "",
           "--append-system-prompt", sys_p, "--no-session-persistence", "--name", f"genesis:{agent_id}"]
    env = {**os.environ, **env_common, **gitops.agent_git_env(agent_id), **sandbox_env(),
           "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1", "CLAUDE_CODE_DISABLE_CLAUDE_MDS": "1",
           "CLAUDE_CODE_DISABLE_CRON": "1", "GIT_TERMINAL_PROMPT": "0"}
    for k in ("GH_TOKEN", "GITHUB_TOKEN"):
        env.pop(k, None)

    db.event(conn, agent_id, "run_start", f"{mode}: {reason[:200]}", {"run": run_id, "task": task_id, "model": model})
    timeout = LEADER_TIMEOUT_S if mode == "leader" else WORKER_TIMEOUT_S
    proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, start_new_session=True, bufsize=1)
    conn.execute("UPDATE runs SET pid=? WHERE id=?", (proc.pid, run_id))
    killed = {"why": None}

    def watchdog():
        if proc.poll() is None:
            killed["why"] = "timeout"
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                time.sleep(10)
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    timer = threading.Timer(timeout, watchdog)
    timer.start()
    result, limit_until, tail = {}, None, []
    with transcript.open("w") as tf:
        for line in proc.stdout:
            tf.write(line)
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                tail.append(line)
                continue
            t = e.get("type")
            r = _find_rejection(e) if t not in ("assistant", "user") else None
            if r:
                limit_until = r
            if t == "assistant":
                for c in e.get("message", {}).get("content", []):
                    if c.get("type") == "tool_use":
                        db.event(conn, agent_id, "tool", _describe_tool(c["name"], c.get("input") or {}), {"run": run_id})
                    elif c.get("type") == "text" and c.get("text", "").strip():
                        txt = c["text"].strip()
                        tail.append(txt)
                        db.event(conn, agent_id, "text", txt[:400], {"run": run_id})
            elif t == "result":
                result = e
    proc.wait()
    timer.cancel()
    try:  # reap anything the agent left running (dev servers, watchers)
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass

    alltext = "\n".join(tail[-6:]) + "\n" + str(result.get("result", ""))
    if limit_until is None and (result.get("is_error") or not result) and LIMIT_TEXT.search(alltext):
        limit_until = _parse_reset(alltext) or (time.time() + 20 * 60)
    usage = result.get("usage") or {}
    status = ("limit" if limit_until else "timeout" if killed["why"] else
              "ok" if result and not result.get("is_error") else "error")
    conn.execute("UPDATE runs SET ended=?, status=?, num_turns=?, cost_usd=?, input_tokens=?, output_tokens=?, transcript=? WHERE id=?",
                 (db.now(), status, result.get("num_turns"), result.get("total_cost_usd"),
                  (usage.get("input_tokens") or 0) + (usage.get("cache_read_input_tokens") or 0) + (usage.get("cache_creation_input_tokens") or 0),
                  usage.get("output_tokens"), str(transcript), run_id))
    conn.execute("UPDATE agents SET runs=runs+1, last_run_at=? WHERE id=?", (db.now(), agent_id))
    db.event(conn, agent_id, "run_end", f"{status} · {result.get('num_turns') or 0} steps",
             {"run": run_id, "status": status, "cost": result.get("total_cost_usd")})
    if limit_until:
        raise LimitHit(limit_until)
    return {"run_id": run_id, "status": status, "result": result.get("result", ""), "error_tail": alltext[-800:]}
