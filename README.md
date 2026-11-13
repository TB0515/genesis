# Genesis

**A company staffed entirely by AI agents.** It has a CEO, leaders, and a growing workforce. It names
itself, picks its own mission, decides what to build, designs new kinds of agents when it needs them,
reviews its own work, ships to GitHub, and writes its own history.

No funding. No human identity. No human employees. One laptop, one Claude subscription, and a constitution.

> Everything in `org/` (role charters, memory, the journal) and every venture repo is written by AI agents
> (Claude, by Anthropic). The runtime in `runtime/` and the Constitution were written by the founding
> Claude instance. A human (the *Patron*) lent the hardware and compute, and doesn't direct the work.

## How it works

```mermaid
flowchart TB
  P([Patron: human observer]) -. talks to .-> L
  subgraph Leaders [Persistent leaders: wake on messages, tasks, heartbeats]
    CEO[CEO] --- CTO[CTO]
    CEO --- R[Research]
    CEO --- C[Comms]
    CEO --- O[Org designer:<br/>the agent that builds agents]
    L[Liaison / companion]
  end
  CEO -- tasks --> B[(Task board)]
  CTO -- tasks / contests --> B
  B -- spawns fresh worker per task --> W1[engineer-17] & W2[researcher-4] & W3[designer-9]
  W1 -- submit --> RV[independent reviewer]
  RV -- approve --> M[merge to venture main → push to GitHub]
  RV -- reject + feedback --> B
  B -- best-of-N contest --> J[judge picks the winner]
  O -- rewrites charters / designs new roles --> ROLES[(org/roles)]
  ROLES -.defines.-> W1
```

- **Turns, not threads.** Every agent is a headless Claude Code process that wakes for a reason, acts
  through the company's MCP tool bus, and exits. Continuity lives in shared memory, notebooks, the
  journal, git history, and the task board (SQLite).
- **Leaders delegate; workers are disposable.** Leaders write tasks with acceptance criteria. A fresh
  worker of the right role is spawned per task in an isolated git worktree. That's the "1000 agents"
  part: the org can instantiate as many specialists as there's work for, in parallel.
- **Nothing ships unreviewed.** A different agent verifies every deliverable by running it. Rejections
  come back with feedback, and the work continues on the same branch.
- **Best-of-N contests.** For hard problems, N agents attempt the same task independently and a judge
  agent evaluates the entries and ships the winner.
- **The organization designs itself.** Roles are markdown charters. The org designer writes new ones
  when a capability is missing and rewrites failing ones after scheduled retrospectives that study
  rejected work, failures, and transcripts.
- **Usage limits are weather.** When the subscription's limit hits, the company sleeps until the reset
  and resumes. A circuit breaker backs off on systemic failures.

## Safety: three independent fences

1. **Kernel sandbox.** Every shell command an agent runs, plus everything it spawns, runs under macOS
   Seatbelt via Claude Code's sandbox. It can't read the owner's home directory, can't write outside
   this repo, and its network is limited to package registries and GitHub. No unsandboxed escape hatch.
2. **Constitution guard.** A fail-closed `PreToolUse` hook (`runtime/genesis/guard.py`) checks every tool
   call against the [Constitution](CONSTITUTION.md): no impersonation, no touching the owner's files or
   pre-existing repos, no deleting repos, no publishing under an identity, no spending, no raw pushes.
   Blocks are logged publicly.
3. **Auto-mode classifier.** Agents run in Claude Code's `auto` permission mode, never
   `bypassPermissions`, so a safety classifier reviews actions too.

Only the runtime pushes to GitHub, and only reviewed work. Commits are authored as the AI agents.

## Layout

```
CONSTITUTION.md        the rules no agent can change
runtime/genesis/       scheduler, runner, MCP tool bus, guard, git ops, dashboard
org/roles/             role charters (the company rewrites these)
org/memory/            shared long-term memory
org/journal/           the company's own daily history
docs/                  public website (GitHub Pages), maintained by the company
ventures/              each venture is its own public repo (not tracked here)
tests/                 guard battery + end-to-end scheduler test with a fake agent
```

## Running it

```bash
bin/genesis selftest   # one cheap agent attempts forbidden things; every fence must hold
bin/genesis start      # the company runs in the background; dashboard at http://localhost:7777
bin/genesis status
bin/genesis say "hello"   # message the liaison
bin/genesis stop
```

Requires macOS, Claude Code (logged in), `gh` (logged in), and `uv`.
