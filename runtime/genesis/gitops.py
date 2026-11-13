"""Git/GitHub operations. Only the runtime pushes, and only reviewed work.

Commits are authored as the AI agents, never as the Patron.
"""
import os
import re
import subprocess
from pathlib import Path

from .config import GH_OWNER, PROTECTED_REPOS, ROOT, VENTURES, WORKTREES

AI_EMAIL = "agents@genesis-ai.invalid"
VENTURE_RE = re.compile(r"^[a-z][a-z0-9-]{1,38}[a-z0-9]$")


def agent_git_env(agent_id: str = "genesis-runtime") -> dict:
    name = f"{agent_id} (Genesis AI agent)"
    return {"GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": AI_EMAIL,
            "GIT_COMMITTER_NAME": "Genesis runtime (AI)", "GIT_COMMITTER_EMAIL": AI_EMAIL}


def git(args, cwd, check=True, agent="genesis-runtime", timeout=120):
    env = {**os.environ, **agent_git_env(agent), "GIT_TERMINAL_PROMPT": "0"}
    p = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, env=env, timeout=timeout)
    if check and p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {p.stderr.strip() or p.stdout.strip()}")
    return p


def gh(args, cwd=None, timeout=120):
    return subprocess.run(["gh", *args], cwd=cwd, capture_output=True, text=True, timeout=timeout)


def repo_exists_remote(name: str) -> bool:
    return gh(["repo", "view", f"{GH_OWNER}/{name}", "--json", "name"]).returncode == 0


def create_venture_repo(name: str, pitch: str, public: bool = True, publish: bool = True) -> tuple[str, str | None]:
    """Create ventures/<name> with an initial commit; optionally a new public GitHub repo."""
    if not VENTURE_RE.match(name):
        raise ValueError("venture name must be lowercase kebab-case, 3-40 chars")
    if name in PROTECTED_REPOS or name.lower() in {r.lower() for r in PROTECTED_REPOS} or name == "genesis":
        raise ValueError("that name belongs to the Patron")
    path = VENTURES / name
    if path.exists():
        raise ValueError("venture already exists locally")
    if publish and repo_exists_remote(name):
        raise ValueError(f"a GitHub repo {GH_OWNER}/{name} already exists and isn't ours. Pick another name")
    path.mkdir(parents=True)
    git(["init", "-q", "-b", "main"], path)
    (path / "README.md").write_text(
        f"# {name}\n\n{pitch.strip()}\n\n---\n\n"
        "> **Built by AI.** This project is designed, written, reviewed, and maintained by autonomous AI agents "
        "(Claude, by Anthropic) working as the [Genesis](https://github.com/"
        f"{GH_OWNER}/genesis) AI company. No human wrote this code. Issues are read by AI agents.\n"
    )
    (path / ".gitignore").write_text("node_modules/\n.venv/\n__pycache__/\n.DS_Store\ndist/\n.env\n")
    git(["add", "-A"], path)
    git(["commit", "-q", "-m", f"Found venture: {name}"], path)
    url = None
    if publish:
        vis = "--public" if public else "--private"
        desc = (pitch.strip().splitlines()[0][:200] + " [Built entirely by AI agents]")
        p = gh(["repo", "create", f"{GH_OWNER}/{name}", vis, "--source", str(path), "--remote", "origin",
                "--push", "--description", desc], cwd=path, timeout=180)
        if p.returncode != 0:
            raise RuntimeError(f"gh repo create failed: {p.stderr.strip()}")
        url = f"https://github.com/{GH_OWNER}/{name}"
    return str(path), url


def ensure_worktree(venture: str, task_id: int) -> tuple[Path, str]:
    repo = VENTURES / venture
    branch = f"task-{task_id}"
    wt = WORKTREES / f"{venture}--{task_id}"
    if wt.exists():
        return wt, branch
    WORKTREES.mkdir(parents=True, exist_ok=True)
    exists = git(["rev-parse", "--verify", "--quiet", branch], repo, check=False).returncode == 0
    if exists:
        git(["worktree", "add", "-q", str(wt), branch], repo)
    else:
        git(["worktree", "add", "-q", "-b", branch, str(wt), "main"], repo)
    return wt, branch


def autocommit(path: Path, message: str, agent: str) -> bool:
    if not path.exists():
        return False
    git(["add", "-A"], path, check=False)
    p = git(["commit", "-q", "-m", message], path, check=False, agent=agent)
    return p.returncode == 0


def diff_summary(venture: str, branch: str) -> str:
    repo = VENTURES / venture
    p = git(["diff", "--stat", f"main...{branch}"], repo, check=False)
    return p.stdout.strip()[-3000:]


def integrate(venture: str, task_id: int) -> tuple[bool, str]:
    """Rebase the task branch onto main and fast-forward main. Push if there's a remote."""
    repo = VENTURES / venture
    wt, branch = WORKTREES / f"{venture}--{task_id}", f"task-{task_id}"
    if wt.exists():
        p = git(["rebase", "main"], wt, check=False)
        if p.returncode != 0:
            git(["rebase", "--abort"], wt, check=False)
            return False, ("Rebase onto latest main hit conflicts. Run `git rebase main` in your worktree, "
                           "resolve the conflicts, make sure everything still works, commit, and resubmit.")
    p = git(["merge", "--ff-only", branch], repo, check=False)
    if p.returncode != 0:
        return False, f"Could not fast-forward main: {p.stderr.strip()[:500]}"
    pushed = push(repo)
    return True, "merged into main" + (" and pushed" if pushed else "")


def remove_worktree(venture: str, task_id: int):
    repo = VENTURES / venture
    wt = WORKTREES / f"{venture}--{task_id}"
    if wt.exists():
        git(["worktree", "remove", "--force", str(wt)], repo, check=False)
    git(["branch", "-D", f"task-{task_id}"], repo, check=False)


def has_remote(repo: Path) -> bool:
    return git(["remote", "get-url", "origin"], repo, check=False).returncode == 0


def push(repo: Path) -> bool:
    if not has_remote(repo):
        return False
    return git(["push", "-q", "origin", "main"], repo, check=False, timeout=180).returncode == 0


def commit_root(message: str) -> bool:
    """Commit org/, docs/ and top-level company files in the genesis repo itself."""
    git(["add", "-A", "org", "docs", "README.md"], ROOT, check=False)
    p = git(["commit", "-q", "-m", message], ROOT, check=False)
    return p.returncode == 0
