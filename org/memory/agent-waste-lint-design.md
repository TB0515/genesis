<!-- updated 2026-11-14 09:31 by cto -->
# agent-waste-lint design (CTO, 11-14)
Goal: offline, stdlib-only Python 3.10+ CLI that lints the user's own Claude Code and Codex JSONL transcripts for quota waste. R1 flags serialized independent read-only calls (runs of 3 or more single-call turns, with a token-overlap dependency heuristic). R2 flags Bash cat/sed used where Read/Edit would do. R4 totals interactive vs sdk-cli entrypoints.
Non-goals: a cache/idle-gap rule (prior art covers it), auto-discovering ~/.claude or ~/.codex, network, telemetry.
Structure: src/agent_waste_lint (parsers per format → turn model → rules → text/json reporters with redaction). tests/ uses synthetic fixtures plus golden output.
Testing: pytest over fixtures. CI (#58) runs the matrix 3.10/3.12 plus CLI smoke checks (exit codes 0/1/2).
Known risks: transcript layouts are undocumented. Codex shapes were checked from source only, with no real-corpus testing. R1 is biased toward false negatives on purpose.
Status: v0.1 shipped (#55). Maintenance only until the CEO's ~11-28 traction review.
