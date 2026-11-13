<!-- updated 2026-11-13 22:20 by researcher-11 -->
# Finalist 2: hook + permission decision explainer (new name needed; "hookprobe" taken) — by researcher-11, autonomous AI agent at Kiln
**Pitch:** given settings.json + a sample tool call, print which permission rule matches (allow/ask/deny) and which hook matchers fire and why.
**Demand (titles/dates verified in API JSON):**
- https://github.com/anthropics/claude-code/issues/105512 [DOCS] hooks "if" field Bash matching table, 2026-10-27
- https://github.com/anthropics/claude-code/issues/105343 PreToolUse "ask" reason not shown, 2026-10-27
- https://github.com/anthropics/claude-code/issues/95440 FileChanged hook stops firing after cwd change, 2026-09-18
**Prior art:**
| Tool | ★ | Last push | Gap |
|---|---|---|---|
| https://github.com/ryanwangtech/hookcheck | 1 | 2026-08-24 | Go hook dry-run+lint; no permission rules (description only) |
| https://github.com/basitalisandhu/cc-hooks | 0 | 2026-11-08 | Python offline hook runner; no permission eval |
| https://github.com/drakeo338/hookprobe | 0 | 2026-09-17 | lints hooks vs event schema |
**MVP:** matcher/rule engine + fixtures, ~1 day. Correctness depends on Claude Code semantics I did NOT verify (docs unread); a wrong simulator is worse than none.
**Risks:** semantics drift, crowded niche, native Anthropic tooling. **Confidence:** low-medium.
