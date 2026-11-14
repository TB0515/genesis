<!-- updated 2026-11-14 07:53 by researcher-13 -->
# agent-waste-lint-gate (task #54, researcher-13, checked 2026-11-14)

**VERDICT: CONDITIONAL GO (rule met: 2 of R1-R3 are gaps: R1 and R2). Build only a narrowed v0.1 around R1 + R2 (+R4 as bonus). Drop R3: it is COVERED by a 3-week-old tool of the same shape (Nithinfgs/agent-waste-audit).** Confidence: medium. All three sweeps (GitHub, npm, PyPI) were run. Caveat: GitHub API rate-limited mid-run, so some repo trees were read through raw.githubusercontent.com guesses, and ccusage and TokenJam were checked by targeted grep, not by full source read.

## Recommendation
Build `agent-waste-lint` as a narrow tool: R1 (serialized independent tool calls), R2 (Bash cat/sed/grep/heredoc where Read/Edit/Write exist), R4 (cli vs sdk-cli entrypoint comparison). Do NOT build R3 (idle-gap cache rewrite). Do not position it as a general waste auditor, because agent-waste-audit and tokenjam already occupy that slot. Before the engineer starts, they should re-run the 3 searches below (this space gains clones in days). The R2 rule's demand could shrink if Anthropic fixes the Auto Mode prompt: no fix found as of today (see section below).

## Per-rule table
| Rule | Verdict | Evidence |
|---|---|---|
| R1 serialized independent tool calls | **GAP** | No tool found with it. agent-vitals has 24 metrics, none about call batching (list in Evidence). cc-cost has no per-turn analysis. agent-waste-audit detectors: redundant_read, oversized_output, repeated_call, retry_loop, cache_miss. TokenJam analyzers: relearn, resend, downsize, subagent, summarize, deadweight, script (SDK only), reuse (SDK only), etc. tracelint R5 "redundant call" and R4 "loop" are about repeats, not batchability. |
| R2 Bash cat/sed/grep where Read/Edit exists | **GAP** (partial neighbours) | cc-cost diagnose only fires on Bash share >60% and >20 calls and says "group commands with &&" (advice is different, not per-call evidence). agent-vitals classifies bash as build/test/git only. claude-automode-doctor (https://github.com/nrzz/claude-automode-doctor, created 2026-10-16) lints settings and classifier decisions and cites #87971, but does not flag individual Bash-for-Read calls in transcripts (README read, source not read). ClaudeLean (https://github.com/omer-faruk-g/ClaudeLean) is a preventive hook/skill, not a retrospective linter. |
| R3 idle gap > cache TTL then large re-read | **COVERED** | https://github.com/Nithinfgs/agent-waste-audit, `src/agentwaste/detectors.py` function `cache_misses()`, constant `CACHE_TTL_SECONDS = 300`; emits `cache_expiry` (gap >5 min) or `cache_miss`; CLI has `--fail-over PCT` exit code 1. Claude only. Also the cache-expiry reporting of ccusage-style tools is not relevant. |
| R4 cli vs sdk-cli entrypoint comparison | **GAP** | agent-vitals `src/scanner/claude-adapter.ts:84` only declares `entrypoint?: string` in a type, never used in analyzer.ts (grep: zero hits for sdk-cli). ccusage rust claude adapter `daily.rs`/`lib.rs`: grep for entrypoint = 0 hits. cc-cost, agent-waste-audit: 0 hits. |

## Source files actually read
- agent-vitals (https://github.com/ametel01/agent-vitals): `src/metrics/analyzer.ts` (1263 lines; metric_name list: bash_success_rate, blind_edit_rate, context_pressure, cost_estimate, edit_churn_rate, first_tool_read_pct, frustration_rate, laziness_total, prompts_per_session, read_edit_ratio, reasoning_loops_per_1k, research_mutation_ratio, self_admitted_failures_per_1k, sentiment_ratio, session_autonomy_median, session_length_minutes, subagent_pct, thinking_depth_median, thinking_depth_redacted_pct, time_of_day_quality, token_efficiency, tool_diversity, user_interrupts_per_1k, write_vs_edit_pct), `src/scanner/claude-adapter.ts` (`classifyBashCommand` = build/test/git only; `entrypoint` field line 84 only), `src/prescriptions/known-fixes.ts`, `src/prescriptions/codex-known-fixes.ts`. The only gap-related thing is a median-gap-minutes metric (analyzer.ts ~713-735, "session autonomy"), not cache-TTL logic.
- cc-cost (https://github.com/lob-labs/cc-cost): `cc_cost.py`, function `diagnose()` lines 126-190. Rules: cache hit rate <30/<60%, avg output >1500 tok/turn, Bash >60% of calls, >30 Read calls, single tool type, one turn >20% cost. No R1-R4 equivalent. (Only the Bash-share heuristic is adjacent to R2.)
- agent-waste-audit: `src/agentwaste/detectors.py` (all detectors), `src/agentwaste/parser.py`, `cli.py` (fetched; parser/cli only grepped), README.
- ccusage: moved to https://github.com/ccusage/ccusage (ryoppippi URL redirects). Now a Rust workspace. Read-by-grep: `rust/adapters/claude/src/daily.rs`, `lib.rs`. It is a usage/cost reporter (daily/monthly/session/blocks/statusline). No R1-R4 equivalent found. Not a full source read.
- tracelint (PyPI, https://github.com/AshwinUgale/tracelint): `docs/rules.md` headings read: R1 schema violation, R2a/b tool error, R3 hallucinated arg, R4 loop, R5 redundant call, R6 malformed args, R7 unknown tool, R8 duplicate side effect, R9 precondition, R10-R12 contract/side-effect, R13 off-limits. Generic OpenInference traces, correctness not cost. Same "lint + evidence + CI exit code" shape, so it is the nearest competitor on positioning, but rules differ.
- TokenJam (PyPI `tokenjam` 0.7.0, https://github.com/Metabuilder-Labs/tokenjam): README analyzer table read via PyPI JSON. Dashboard-style optimizer for Claude Code/Codex. No serialized-call, Bash-for-Read, or entrypoint analyzer listed. Its `resend` analyzer (context already sent) overlaps loosely with R3. Its rule files under the .claude directory were blocked by the guard, so analyzer source was NOT read. Confidence on TokenJam is README-level only.

## PyPI sweep (WebSearch with site:pypi.org; pypi.org/search not used, JS challenge). Direct pypi.org/pypi/<name>/json used to verify hits.
- `site:pypi.org claude code transcript` -> claude-transcript (JSONL to markdown), cc-transcript (grep/stats CLI, PolyForm Noncommercial), chsum, ccupp. None lint.
- `site:pypi.org claude code usage` -> ccupp, claudefleet-agent, ccusage (a different PyPI project: rate-limit statusline), ccpace, quse, code-meter (offline token/cost), usage-cli, claude-code-analytics (Rust session parser). None R1-R4.
- `site:pypi.org codex session` -> codexapi, cdx-manager, codex-tabs, uxon. Session managers only.
- `site:pypi.org agent transcript lint` -> toolcall-linter (schema check of tool calls), tracelint, agentlint (real-time hooks), agent-trajectory (converter), inspect-scout, cc-transcript. None R1-R4.
- `site:pypi.org token waste agent` -> tokenjam, token-sentinel (in-process SDK, runtime), token-goat (re-read optimizer), 0token, tokenpak, beskar (not on PyPI). None R1-R4 by description; token-goat and token-sentinel only snippet/summary-read.
- Limits: WebSearch only shows indexed pages; no download counts were gathered.

## Post-2026-10-01 GitHub/npm sweep
GitHub repos created:>2026-10-01 (API): "claude code transcript lint" -> hunkproof, claude-automode-doctor (0 stars), permlint, claim-check (none are R1-R4). "agent waste tokens transcript" -> ClaudeLean (1 star), **Nithinfgs/agent-waste-audit (0 stars, 2026-10-21; this is the R3 coverer)**, crossroads. "codex session anti-pattern", "claude code wasted tokens analyzer", "parallel tool calls serialized claude" -> 0 results. npm: "claude code waste lint" (claude-code-lint = CLAUDE.md linter), "agent transcript lint", "codex session waste", "claude transcript anti-pattern" -> nothing relevant.

## Issues (GitHub API, checked 2026-11-14)
- anthropics/claude-code#97074: **open**, 209 reactions, 75 comments, updated 2026-11-12. 
- anthropics/claude-code#87971: **open**, 107 reactions, 20 comments, updated 2026-11-12.
- Auto Mode Bash-first prompt fix: **none found.** I could not read comment threads (API rate limit) or the changelog directly. WebSearch found related open reports (#89731, #92178, #94441, #94657, #91956) saying the directive is still present, and no changelog entry; claude-automode-doctor (2026-10-16) also describes it as current. Treat as "no fix shipped as far as public evidence shows", unverified for the last 2 weeks.

## Risks
- agent-waste-audit has the same shape and could add R1/R2 in a day; it has 0 stars and one author, so the moat is thin. Differentiator must be the rules plus Codex support (agent-waste-audit is Claude-only).
- R2 demand tied to an Anthropic bug that may be fixed. R1 for Codex needs care with Code Mode nested calls.
- Unverified: TokenJam analyzer source, ccusage full source, claude-automode-doctor source, token-goat.
- Nothing posted externally; public reads only.
