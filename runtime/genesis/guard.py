"""PreToolUse hook: mechanical enforcement of the Constitution.

Runs before every tool call of every agent. Fails closed: any internal error denies.
Blocks are logged as public events, so the company (and the Patron) can see them.
"""
import json
import os
import re
import sys
from pathlib import Path

from .config import HOME, PROTECTED_REPOS, ROOT

SENSITIVE = re.compile(
    r"(\.ssh|\.aws|\.gnupg|\.netrc|Keychains|\.config/gh|\.docker/config|\.kube|"
    r"\.npmrc|\.pypirc|\.git-credentials|\.claude(?!/skills)|\.claude\.json|id_rsa|id_ed25519)"
)
DENY_TOOLS = {"CronCreate", "CronDelete", "RemoteTrigger", "ScheduleWakeup", "PushNotification",
              "Artifact", "SendFeedback", "EnterWorktree", "ExitWorktree"}
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
READ_TOOLS = {"Read", "Glob", "Grep", "LS"}

CMD = r"(?:^|[;&|(`\n]\s*|\b(?:xargs|exec|env|nohup|time|then|do)\s+)"
BASH_RULES = [
    (CMD + r"sudo\b", "no privilege escalation (Art. II)"),
    (CMD + r"(launchctl|crontab|osascript|security|diskutil|mkfs|shutdown|reboot|halt|pmset|scutil|"
     r"networksetup|systemsetup|dscl|csrutil|spctl|killall|pkill|sendmail|mail|mailx)\b",
     "system / identity / mail commands are off-limits (Art. I, II)"),
    (CMD + r"defaults\s+write\b", "system settings are the Patron's (Art. II)"),
    (r"\brm\s+-[a-zA-Z]*\s+(/|~|\$HOME)(\s|/?\*|$)", "refusing catastrophic delete (Art. II)"),
    (r"\bgit\s+push\b", "agents don't push; the runtime publishes approved work (Art. II.2)"),
    (r"\bgit\s+remote\s+(add|set-url|rename|remove|rm)\b", "remotes are managed by the runtime"),
    (r"\bgit\s+config\s+(--global|--system)", "global git config belongs to the Patron"),
    (r"\bgh\s+(auth|secret|ssh-key|gpg-key|variable|config|gist|codespace|org|ruleset)\b",
     "GitHub account administration is off-limits (Art. II.4)"),
    (r"\bgh\s+repo\s+(delete|archive|unarchive|rename|edit|create|fork|sync|set-default|deploy-key)\b",
     "repository creation/changes go through create_venture; nothing is ever deleted (Art. II.2)"),
    (r"\bgh\s+(issue|pr|release|discussion|label|project|workflow|run|cache)\s+"
     r"(create|comment|edit|close|delete|merge|review|reopen|lock|transfer|pin|run|enable|disable|upload)",
     "public posting goes through the github_outreach tool (Art. I.3)"),
    (r"\bgh\s+api\b.*(-X|--method)\s*(POST|PUT|PATCH|DELETE)", "write calls to GitHub API are not allowed"),
    (r"\bgh\s+api\b.*\s(-f|-F|--field|--raw-field|--input)\s", "write calls to GitHub API are not allowed"),
    (r"\b(GH_TOKEN|GITHUB_TOKEN|ANTHROPIC_API_KEY|CLAUDE_CODE_OAUTH_TOKEN)\b", "credentials are off-limits (Art. II.4)"),
    (r"\b(npm|yarn|pnpm|bun)\s+(publish|login|adduser|token|owner)\b", "publishing needs an identity; pitch it (Art. I.4)"),
    (r"\b(twine\s+upload|uv\s+publish|poetry\s+publish|cargo\s+publish|docker\s+(push|login)|gem\s+push)\b",
     "publishing needs an identity; pitch it (Art. I.4)"),
    (r"\bclaude\b.*(\s-p\b|--print|dangerously|bypassPermissions)", "spawn helpers with the Agent tool or create_task, not raw claude"),
    (r"dangerously-skip-permissions|bypassPermissions", "permission bypass is forbidden"),
]
NET_WRITE = re.compile(r"\b(curl|wget|http|https|xh)\b[^|;&]*(\s-d\b|--data|\s-F\b|--form|-X\s*(POST|PUT|PATCH|DELETE)|"
                       r"--upload-file|\s-T\b|--post-data|--post-file|\s(POST|PUT|PATCH|DELETE)\s)")
LOCAL_URL = re.compile(r"(localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\])")


def deny(reason: str):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "deny",
        "permissionDecisionReason": f"Constitution guard: {reason}"}}))
    try:
        from . import db
        conn = db.connect()
        db.event(conn, os.environ.get("AGENT_ID", "?"), "guard_block", reason,
                 {"tool": _ctx.get("tool"), "input": str(_ctx.get("input"))[:400]})
    except Exception:
        pass
    sys.exit(0)


_ctx: dict = {}


def resolve(p: str, cwd: str) -> Path:
    p = os.path.expanduser(p)
    path = Path(p) if os.path.isabs(p) else Path(cwd) / p
    return Path(os.path.normpath(str(path)))


def inside(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def check_read(path: Path):
    if SENSITIVE.search(str(path)):
        deny(f"{path} is sensitive (Art. II.4)")
    if inside(path, HOME) and not inside(path, ROOT):
        deny(f"{path} is outside ~/genesis. The Patron's files are not ours (Art. II.1)")


def check_write(path: Path):
    check_read(path)
    if not inside(path, ROOT):
        deny(f"writes are confined to ~/genesis ({path})")
    rel = path.relative_to(ROOT)
    parts = rel.parts
    if not parts:
        deny("cannot write the root itself")
    if parts[0] in {"runtime", ".venv", ".git"} or rel.as_posix() in {"CONSTITUTION.md", "pyproject.toml", "uv.lock"}:
        deny(f"{rel} is the runtime/constitution; only the Patron changes it (Art. VI)")
    if parts[0] == "var" and (len(parts) < 2 or parts[1] not in {"worktrees", "desks"}):
        deny(f"{rel} is runtime state; use the company tools")
    if parts[0] == "ventures":
        deny("venture main branches change only via reviewed tasks. Work in your task worktree")
    if parts[:2] == ("org", "roles"):
        deny("role charters change via the define_role tool")


def check_bash(cmd: str, cwd: str):
    for pat, why in BASH_RULES:
        if re.search(pat, cmd):
            deny(why)
    if NET_WRITE.search(cmd) and not LOCAL_URL.search(cmd):
        deny("outbound write requests (sign-ups, posts, form submits) aren't allowed from the shell (Art. I)")
    low = cmd
    if not PROTECTED_REPOS and re.search(r"\b(gh|git)\b", cmd):
        deny("protected-repo list unavailable; failing closed for git/gh")
    for repo in PROTECTED_REPOS:
        # a repo name, not an owner prefix ("TB0515/genesis" is fine; "TB0515/TB0515" or "QCare" is not)
        if re.search(rf"(?<![\w-]){re.escape(repo)}(?![\w/-])", low) and re.search(r"\b(gh|git)\b", low):
            deny(f"{repo} belongs to the Patron (Art. II.2)")
    home = str(HOME)
    for m in re.finditer(re.escape(home) + r"(/[^\s'\";|&)]*)?", cmd):
        tail = m.group(1) or ""
        if not (tail == "/genesis" or tail.startswith("/genesis/")):
            deny(f"{m.group(0)} is outside ~/genesis (Art. II.1)")
    for m in re.finditer(r"(?<![\w./-])(~|\$HOME|\$\{HOME\})(?=[/\s\"';|&)]|$)(/[^\s'\";|&)]*)?", cmd):
        tail = m.group(2) or ""
        if not (tail == "/genesis" or tail.startswith("/genesis/")):
            deny(f"{m.group(0)} points outside ~/genesis (Art. II.1)")
    for m in re.finditer(r"(?:\.\./)+(?:\.\.)?", cmd):
        if not inside(resolve(m.group(0), cwd), ROOT):
            deny("relative path escapes ~/genesis (Art. II.1)")
    for m in re.finditer(r"(?:^|\s)(/Users/[^\s'\";|&)]*|/Volumes/[^\s'\";|&)]*)", cmd):
        p = Path(os.path.normpath(m.group(1)))
        if not inside(p, ROOT):
            deny(f"{p} is outside ~/genesis (Art. II.1)")
    if SENSITIVE.search(cmd):
        deny("touches credentials or private configuration (Art. II.4)")


def main():
    data = json.load(sys.stdin)
    tool = data.get("tool_name", "")
    inp = data.get("tool_input") or {}
    cwd = data.get("cwd") or os.getcwd()
    _ctx.update(tool=tool, input=inp)

    if tool in DENY_TOOLS:
        deny(f"{tool} is not available to company agents")
    if tool.startswith("mcp__") and not tool.startswith("mcp__company__"):
        deny("only the company's own tools are allowed. The Patron's connectors are theirs")
    if tool in WRITE_TOOLS:
        p = inp.get("file_path") or inp.get("notebook_path")
        if not p:
            deny("missing path")
        check_write(resolve(p, cwd))
    elif tool in READ_TOOLS:
        p = inp.get("file_path") or inp.get("path")
        if p:
            check_read(resolve(p, cwd))
    elif tool in {"Bash", "BashOutput", "PowerShell"}:
        check_bash(inp.get("command", ""), cwd)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # fail closed
        deny(f"guard error ({type(e).__name__}); failing closed")
