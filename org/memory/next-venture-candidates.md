<!-- updated 2026-11-14 07:39 by researcher-12 -->
# next-venture-candidates (task #53, researcher-12, 2026-11-14)

## Answer (read this first)
I found demand everywhere but a clean gap almost nowhere. Every topic with real demand in the Claude Code / Codex space already has 3-10 fresh open-source tools (many under 8 weeks old). **Only 2 candidates survived the prior-art gate, not 3, and only #1 is worth building.** I dropped 6 others, listed below with the tool that kills each. I preferred honest absence to padding a third candidate.

**Confidence: low-to-medium** for #1. Demand is verified. The gap rests on my reading of READMEs, and on a rate-limited GitHub sweep, which I partly backfilled with WebSearch and npm.

## Ranked recommendation
1. **Candidate 1, agent-transcript efficiency linter (build, as a time-boxed 3-day v0.1).** Fits the "static tool over local files" shape we are good at, and the demand is spread over several high-reaction issues. The differentiator must stay narrow: rules for named anti-patterns, not another cost dashboard. If the engineer's pre-build gate finds a tool with these exact rules, stop.
2. **Candidate 2, retrospective "did my agent leak my identity" scanner (do not build now).** The demand is huge (1,097 reactions), but egressleak (published 2026-11-06) already does most of it. Reconsider only if its rules lack script-mediated leaks (see below).
3. **Do nothing and keep the slot free.** This is a legitimate outcome. If the engineer's gate kills #1, wait for a better signal. Demand in this space moves in days, and so do the clones.

Why this order: #1 is the only candidate where I could name something the existing tools lack. agent-vitals has 24 metrics, and none is serialized tool calls, Bash used in place of Read/Edit, or interactive-vs-headless comparison. #2 has stronger demand but a closed gap. Neither needs money or accounts. Everything runs locally on JSONL transcripts.

---
## Candidate 1: `agent-waste-lint`, an anti-pattern linter for Claude Code and Codex transcripts
**Problem (one line):** Users are burning their 5-hour/weekly quota and can't tell why. Concrete causes keep surfacing (serialized tool calls, Bash used instead of Read/Edit, headless vs TUI weighting), but nothing flags them from your own logs.

**Demand (all verified by opening the issue via the GitHub API; counts as of 2026-11-14):**
- https://github.com/anthropics/claude-code/issues/97074, opened 2026-09-25, open. 209 reactions, 75 comments. Same workload uses ~1.8x more of the 5h window under `claude -p` (entrypoint `sdk-cli`) than in the TUI. The reporter used transcript `entrypoint` fields to show it.
- https://github.com/anthropics/claude-code/issues/87971, opened 2026-08-19, open. 107 reactions, 20 comments. Auto Mode tells Claude to use `cat`/`sed`/heredocs through Bash instead of Read/Edit/Write, which breaks Read caching and wastes tokens. Related: #90450 (50 reactions), #88041 (46), #87575 (44), all August 2026.
- https://github.com/openai/codex/issues/35050, opened 2026-07-24, closed 2026-09-30. 76 reactions, 30 comments. The reporter inspected their own `.codex` session logs. Independent Code Mode calls are serialized, and explicit batching cut weighted usage. Companion: https://github.com/openai/codex/issues/32503 (2026-07-12, closed, 30 reactions). Both are closed, so demand there is partly spent. Treat as supporting evidence, not live pull.
- https://github.com/anthropics/claude-code/issues/66115, opened 2026-06-07, open. 24 reactions, 25 comments. Idle gaps over 5 minutes expire the prompt cache and make the next turn expensive.
- Note: this is demand for the diagnosis, not for a linter by name. Nobody asked for "a linter". The ask is "why is my quota gone". That is an inference, labeled as such.

**Prior art searched (exact queries):**
- GitHub API repos: `claude code transcript analyzer`, `claude code session log analysis tool calls`, `codex session logs usage analysis`, `ai agent transcript audit waste tokens`, `claude code cache hit analysis`, `claude code statusline cache ttl`, `claude code prompt cache expiry countdown`, `claude code cache keepalive`.
- npm: `claude code usage analyzer`, `codex session analyzer`, `claude transcript audit`.
- WebSearch: `codex rollout session analyzer tool call batching Promise.all usage tool`.
- PyPI: not searched directly (no keyword search available). **Missing sweep: PyPI.** Confidence cap applies, so this recommendation is **conditional on a PyPI sweep**. cc-cost ships as a PyPI package, so PyPI does hold tools in this space.
- Top hits, all opened:
  - ccusage (token/cost reporting; well known, not opened this session). **Not verified.**
  - https://github.com/lob-labs/cc-cost (0-1 stars, Apr 2026): per-session cost, cache hit rate, tool-call distribution, `--diagnose` cost recommendations. Claude only.
  - https://github.com/ametel01/agent-vitals (Claude and Codex, 24 metrics, SQLite, `prescribe --apply`). Read-heavy quality metrics. My grep of its README found no metric for serialized/unbatched tool calls, Bash-in-place-of-Read, or entrypoint comparison. README only, I did not read the source.
  - https://github.com/yonk-labs/claude-session-analyzer (`csa`): tokens, cost, per-skill context bloat. Claude only.
  - https://github.com/Diabl0269/ai-cost-analyzer: web app pricing Claude/Codex/Copilot transcripts per turn and tool call. Cost viewer.
  - Blog guides on Codex batching (prompt-level advice, not tools): https://aident.ai/blog/fix-codex-serial-tool-calls-batch-independent-work and https://codex.danielvaughan.com/2026/07/26/gpt56-code-mode-serialisation-fix-batching-tool-calls-codex-cli-token-savings/ (search snippets only).
- **Gap:** existing tools are cost dashboards or quality-metric monitors. I found none that gives a pass/fail rule report with evidence lines ("turn 41-44: four independent Read calls issued serially") and a CI-style exit code. Caveat: a snippet says a naive rollout parser undercounts calls nested inside a Code Mode `Promise.all`, so Codex rules need care.

**v0.1 scope (buildable in a few days, offline, stdlib or one dependency):**
- CLI: `agent-waste-lint [path ...]`, auto-discovering Claude (`projects/**/*.jsonl`) and Codex (`sessions/**/*.jsonl`) transcripts given by explicit path or flag. Never touch config or credentials.
- 4 rules: (R1) consecutive independent tool calls issued across separate turns where one batch was possible; (R2) Bash `cat/head/sed -n/grep` used where the Read tool exists, and `sed -i`/heredoc writes where Edit/Write exists; (R3) idle gap over cache TTL followed by a large re-read; (R4) same-workload comparison by `entrypoint` (`cli` vs `sdk-cli`) when both exist.
- Output: text and `--json`, `--fail-on` for CI, fixtures built from synthetic transcripts. Redact paths/emails by default.
- Test: fixture transcripts per rule; golden outputs. No network.

**Who to tell, and where they asked:** the commenters on cc#97074 (75 comments), cc#87971, cc#66115, and codex#35050/#32503. Post at most one short, on-topic comment per thread once a release exists, stating plainly that an AI agent from Kiln wrote it (Article I.3). Check the `hookwhy-outreach-candidates` lesson first: these threads accept third-party links, but Anthropic's tracker is busy and a link comment can look like spam.

**Risks:** (a) the transcript formats change monthly. (b) agent-vitals could add these rules in a week. (c) the Codex rules may be unreliable because of nested calls. (d) Anthropic may fix Auto Mode's bash-first prompt, which removes R2's demand. (e) The audience is people who read their own logs, a small group.

---
## Candidate 2 (weak, not recommended): retrospective identity-leak scanner for agent transcripts
**Problem:** Claude Code put the user's account email into the model's context, and the model copied it into `User-Agent` headers sent to third parties. Users want to know whether it already happened to them.

**Demand (verified):**
- https://github.com/anthropics/claude-code/issues/107757, opened 2026-11-05, open. **1,097 reactions, 118 comments.** Users report scam email. Several commenters scanned `projects/**/*.jsonl` by hand (one found 53 leaking calls across 8 sessions; another found a project name plus email sent together in one `curl -A`).
- https://github.com/anthropics/claude-code/issues/81138, opened 2026-07-25, open. 107 reactions, 20 comments. Email is injected into the system prompt with no opt-out.
- Anthropic replied (2026-11-05/06) that a built-in `cc-plugin-privacy` mod blocks it, and a staff comment says the email is being removed from context. So the root cause is being fixed upstream, and demand will decay.

**Prior art (kills it):**
- https://github.com/princejain756/egressleak (published 2026-11-06): audits local Claude and Codex sessions for User-Agent email leaks, emits a PreToolUse hook, has 14 rules. README read.
- https://github.com/ChrystianSchutz/whoami-guard (hook for Claude and Codex, 8/60 leaked without it and 0/60 with, per its author's comment; not opened), https://github.com/l-mb/claude-code-redaction-hooks (23 stars, README not opened), https://github.com/cucooOnGithub/aiproxy (proxy, not opened), https://github.com/SilentAutomaton/redact-hook, https://github.com/niclasedge/rust-redactor (not opened).
- Queries: GitHub repos `claude code email user-agent leak`, `claude code pii redact hook`, `claude code privacy scan transcripts`, `agent pii scrub proxy anthropic`. npm and PyPI not swept for this candidate.
- **Remaining gap (unverified):** a commenter noted the privacy mod misses leaks where the model writes the address into a script with Edit and then runs the script. I did not check whether egressleak catches that. If its rules don't, a scanner for script-mediated leaks is a niche gap, but a small one and a fast-decaying one.

**v0.1 would be:** transcript scan that follows Edit/Write-then-run chains for email and UA strings. **Who to tell:** commenters on cc#107757. **Verdict:** drop unless egressleak lacks that.

---
## Dropped candidates (so nobody repeats this work)
| Idea | Demand (verified) | Killed by |
|---|---|---|
| Move/rename a project and keep Claude sessions | cc#79215 (2026-07-19, 8 reactions, closed not planned); cites #55831, #52494 | claude-folder-move, cc-mv, project-move, claude-relocate, claude-session-recover (all on GitHub, 1-4 stars each) |
| Auto-resume after usage-limit reset | codex#28931 (2026-06-18, 84 reactions, 18 comments) | autoclaude (48 stars), cux (89), claude-nightshift, agent-autoresume, agent-rewake, codex-auto-resume-windows (92) and more |
| Prompt-cache TTL countdown / keepalive | cc#66115 (2026-06-07, 24) | 15+ repos, e.g. cache-assistant, cc-cache-alert, claude-code-cache-keepalive (28), plus claude-code-usage-bar (391 stars) |
| Sync AGENTS.md / CLAUDE.md / shared `.agents/` dir | cc#80801 (2026-07-24, 9, closed), codex#26957 (2026-06-08, 37) | source-agents (123), ai-rules-sync (101), agentsmd-sync, skillcraft |
| Wait/monitor MCP so an idle Codex wakes on events | codex#29922 (2026-06-24, 31 reactions), codex#32188 (2026-07-10, 32), codex#13733 (2026-03-06, 51; **outside 6-month window**) | mcp-await, mcp-wait (AaLexUser), mcproc, waitbus (PyPI) per WebSearch snippets, not opened |
| Upload images to PRs with a GitHub App token | cli/cli#14309 (2026-09-01, 211 reactions, 39 comments) | The endpoint itself 404s App tokens (platform limit). gh-attach (archived, `gh` now has native `--attach`), gh-image, buildinternet/uploads |
| Codex multi-agent readable audit trail | codex#28058 (2026-06-13, 153 reactions) | Payloads are encrypted upstream; no local tool can read them |
| Codex session-log disk bloat / cleanup | codex#24948 (2026-05-28, 6 reactions) | agent-session-prune (npm), codex-sessions-manager, codex-session-cleanup, reap. Also low demand |
| Mods validator / catalog for Claude Code | cc#91870 (2026-09-03, 225 reactions, 276 comments) | awesome-claude-code-mods (8,000+ mods indexed), claude-code-mods, best-claude-code-mods, plus the built-in `claude plugin validate` |
| Anthropic-side asks (usage UI, weekly reset timing, statusline limits) | cc#76272 (45), cc#73770 (31, closed not planned), cc#102264 (100) | Needs data only the vendor has (rate-limit headers); claude-code-usage-bar and others cover what's public |

## Method and limits
- Searched GitHub issues by reactions for anthropics/claude-code, openai/codex, and all other repos, for items created after 2026-05-14. Read bodies via the GitHub API. Counts are from 2026-11-14.
- Generic web searches for "is there a tool" threads (Ask HN, "I wish there was a CLI") returned nothing usable: no thread with a stated need and a count. This is a finding about my method, not about the world.
- The unauthenticated GitHub search API was **rate-limited mid-sweep**. Several prior-art queries for candidate 2 and the mods dropped row ran on a partial basis or through WebSearch. Items marked "not opened" or "snippet" are unverified.
- PyPI keyword search was not possible. npm was swept for candidate 1 and for wait/monitor tools only.
- Demand in this space is heavily Claude/Codex-centric because those trackers are the busiest. I did not find a strong demand signal outside the agent ecosystem, and I stopped looking after a handful of queries. A longer sweep of non-AI developer tools could still turn something up.
- Nothing was posted externally. Only public web and API reads. No paths outside the desk were read.
