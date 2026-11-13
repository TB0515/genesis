"""Static configuration for the Genesis runtime."""
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOME = Path.home()
RUNTIME = ROOT / "runtime"
ORG = ROOT / "org"
ROLES_DIR = ORG / "roles"
MEMORY_DIR = ORG / "memory"
JOURNAL_DIR = ORG / "journal"
VENTURES = ROOT / "ventures"
DOCS = ROOT / "docs"
VAR = ROOT / "var"
DB_PATH = Path(os.environ.get("GENESIS_DB") or (VAR / "genesis.db"))
TRANSCRIPTS = VAR / "transcripts"
WORKTREES = VAR / "worktrees"
DESKS = VAR / "desks"
LOGS = VAR / "logs"
PYTHON = ROOT / ".venv" / "bin" / "python"

CLAUDE_BIN = os.environ.get("GENESIS_CLAUDE_BIN") or shutil.which("claude") or "claude"
GH_OWNER = os.environ.get("GENESIS_GH_OWNER", "TB0515")

# Every agent runs with Claude Code's auto-mode safety classifier on, plus our own
# constitution hook (guard.py). Never bypassPermissions.
PERMISSION_MODE = os.environ.get("GENESIS_PERMISSION_MODE", "auto")

DASHBOARD_PORT = int(os.environ.get("GENESIS_PORT", "7777"))

# Concurrency and pacing. Overridable live via the `state` table (key: max_parallel).
DEFAULT_MAX_PARALLEL = 6
TICK_SECONDS = 5
LEADER_TIMEOUT_S = 40 * 60
WORKER_TIMEOUT_S = 75 * 60
MAX_TASK_ATTEMPTS = 4
MAX_OPEN_TASKS = 60
MAX_ACTIVE_VENTURES = 6
IDLE_WAKE_CEO_S = 15 * 60
RETRO_EVERY_N_TASKS = 12
DEFAULT_PAUSE_S = 20 * 60
OUTREACH_PER_WEEK = 3

# Repositories that existed before the company. Never touched, ever. The list is private (some repos are),
# so it lives in var/ (never published) and is captured from GitHub once, at founding.
PROTECTED_FILE = VAR / "protected_repos.json"


def _protected() -> set[str]:
    import json
    try:
        return set(json.loads(PROTECTED_FILE.read_text()))
    except Exception:
        return set()


PROTECTED_REPOS = _protected()
