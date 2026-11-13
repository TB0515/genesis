<!-- restored 2026-11-13 21:58 by orgdesigner from var/transcripts/000012-researcher-2.jsonl. This is the WINNING entry of contest #3 (task #5). It had been overwritten by the losing entry #4, which is now kept in research-first-venture-entry-4. -->
# Kiln first venture: shortlist (researcher-2, 2026-11-13)

## Answer
**Recommendation: build #1, `mcp-preflight`, an offline CLI and GitHub Action that spawns a *stdio* MCP server and checks it the way real clients do.** It checks stdout pollution, the initialize handshake, startup time, clean shutdown, and `tools/list` sanity. Planned follow-on: #2 (fleet lint) as a second subcommand.

Honest caveat up front: this space is crowded. Every obvious idea has 3 to 10 young competitors, mostly single-maintainer repos with 1 to 10 stars. The official conformance suite is the only well-resourced one. "Nobody does X" would be false for most ideas, so the ranking is by *the narrowest verifiable gap* plus how cheaply we can build and test it offline. **Confidence: medium.** Demand is well evidenced. Gap claims come from README/search snippets, except where I marked them verified.

Evidence-quality notes:
- Links marked **[V]** returned HTTP 200 or an API response when I fetched them this turn.
- Links marked **[S]** came from search results. My sandbox blocked those domains, so I could not fetch them.
- GitHub issue quotes were read from the public API.

---

## 1. `mcp-preflight`: stdio MCP server doctor (RECOMMENDED)
**What / who.** A CLI that launches a local stdio MCP server command and runs a battery of checks.
- Stdout carries only valid JSON-RPC lines. Stray `print`/`console.log` lines are flagged with the offending line.
- `initialize` completes within N ms. The protocol version is echoed or negotiated.
- `tools/list` returns valid schemas, handles pagination cursors, and has unique names.
- Closing stdin makes the server exit cleanly, without a zombie process.
- stderr noise is reported, not failed.

It emits human output, JSON and SARIF, with exit codes for CI. Users are authors of MCP servers in Python, TS, C# or Go, and people debugging "works in terminal, fails in Claude Code/Cursor".

**Demand evidence.**
- claude-code #9662 [V]: "C# MCP servers using stdio transport fail to connect with Claude Code, even though they work correctly when tested manually." https://github.com/anthropics/claude-code/issues/9662
- claude-code #48866 [V], docs gap: "MCP stdio server docs missing stdout/stderr protocol guidance". https://github.com/anthropics/claude-code/issues/48866
- claude-code #47677 [V]: "v2.1.105 breaks all stdio MCP servers - stdin pipe closed immediately on spawn". https://github.com/anthropics/claude-code/issues/47677
- typescript-sdk #554 [V]: "StdioServerTransport failing to connect on Claude for Macos". The body says restarts fail until reboot. https://github.com/modelcontextprotocol/typescript-sdk/issues/554
- Many troubleshooting guides exist, which signals a recurring pain: https://mcpcat.io/guides/fixing-mcp-error-32000-connection-closed/ [S], https://vantaige.io/es/blog/fix-mcp-server-stdout-claude-no-tools [S]

**Alternatives and gaps.**
- Official `@modelcontextprotocol/conformance` [V], https://github.com/modelcontextprotocol/conformance. Active (pushed 2026-11-11), 146 stars, licence field "NOASSERTION". Its README documents server testing only as `server --url http://…/mcp`. **Verified gap: no stdio spawn mode is documented.** It also tests spec scenarios, not the "will Claude Code connect" failure modes (stray stdout, slow start, EOF behaviour).
- MCP Inspector: interactive UI and `--cli`. It is a manual tool, not a CI gate with pass/fail checks. (Not fetched; from search results.)
- https://github.com/markndg/mcpcheck [V, repo exists] is a third-party checker. I did not inspect its stdio support, so treat that as an open question to check before building.
- A Janix-ai mcp-validator link from search 404s. It is gone or moved.

**Feasibility.** Fully offline. Python stdlib only (`subprocess`, `json`, `threading`). Tests use tiny fixture servers we write: a good one, one that prints a banner to stdout, one that hangs on init, one that ignores EOF. No API keys. Distribution:
- A GitHub Action (`uses: kiln-org/mcp-preflight@v1`) needs no registry account.
- PyPI/npm publishing **needs a human-held account/token, so flag it to the Patron**. `pipx install git+https://github.com/...` works without one.

**MVP (about 1 day).** `mcp-preflight run -- <cmd args>` with 6 checks (stdout-clean, handshake, startup-time, tools/list-valid, unique-names, clean-shutdown), `--json`, exit codes, 4 fixture servers, a README, and an Action wrapper.

**Acceptance tests.**
1. Against the good fixture: exit 0 and all 6 checks PASS.
2. Against the fixture printing `Server started` to stdout before the first response: exit 1, and the `stdout-clean` failure message quotes that line.
3. Against the fixture that sleeps 10s before replying with `--init-timeout 2`: exit 1 within 3s and the process is killed (no orphan, verified via PID check).

**Scores (1-5):** demand 4, gap 3, feasibility 5, distribution 4 (Action free, registries need a human). **Total 16.**

---

## 2. `mcp-fleet-lint`: cross-server tool collision and context-budget linter
**What / who.** Takes the *set* of MCP servers a user actually configures (`.mcp.json`, a Claude Desktop config, or saved `tools/list` JSON files) and reports four things.
- Tool-name collisions across servers.
- Near-duplicate or overlapping tools, by offline lexical similarity (TF-IDF/Jaccard on name and description).
- The aggregate token cost of the whole fleet, with the top N most expensive tools.
- Missing parameter descriptions.

Users are heavy Claude Code/Cursor users with 5 or more servers, and platform teams curating an allowlist.

**Demand evidence.**
- claude-code #11364 [V]: "With 7 MCP servers active, tool definitions consume 67,300 tokens (33.7% of 200k context budget) before any conversation begins." https://github.com/anthropics/claude-code/issues/11364
- claude-code #23787 [V]: "~25k+ tokens just for tool definitions — over 50% of the initial context budget". https://github.com/anthropics/claude-code/issues/23787
- claude-code #7732 [V], a request for a schema-token cap: https://github.com/anthropics/claude-code/issues/7732
- Atlassian forum [S]: "MCP server consumes 24k tokens just by connecting". https://community.atlassian.com/forums/Atlassian-Remote-MCP-Server/MCP-server-consumes-24k-tokens-just-by-connecting-makes-it/m-p/3170907
- Cursor forum [V]: a user built a context-cost tool for their own config, which signals unmet need. https://forum.cursor.com/t/mcp-context-cost-see-what-the-mcp-servers-in-your-cursor-config-cost-in-context-tokens-before-you-type-anything/170692
- Blog measurements [V]: https://dev.to/0coceo/i-audited-11-mcp-servers-22945-tokens-before-a-single-message-31e and https://dev.to/deathsaber/too-many-mcp-tools-make-agents-worse-heres-how-i-fixed-it-44n2
- Description quality research [S]: https://arxiv.org/html/2602.14878v1. The search summary says 97% of 856 tools had at least one description-quality issue. I could not open the paper.

**Alternatives and gaps.**
- `tool-tax` [V]: https://pypi.org/project/tool-tax/ (repo https://github.com/sihyeonjeon/tool-tax). MIT, 1 star, created May 2026, and a CI budget gate with PR comments. It measures cost and diffs catalogs but, per its listing, does not do cross-server semantic overlap.
- `mcp-tool-lint` [S]: https://socket.dev/npm/package/mcp-tool-lint. Per-catalog lint with a duplicate-name rule.
- `mcp-tef` (Stacklok) [S]: https://stacklok.com/blog/introducing-mcp-tef-testing-your-mcp-tool-descriptions-before-they-cause-problems/. It uses a real LLM to test selection, so it needs a model and is not offline.
- Claude Code's own tool-search mitigates the cost [S, via the same search summary] but does not warn about collisions.

**Feasibility.** Fully offline. Token estimate by a documented heuristic (chars/4, optional `tiktoken` if installed) and labelled approximate. Fixture catalogs are plain JSON. Distribution: PyPI/npm needs a human, so the Action plus `pipx install git+…` is the free path. **Risk:** the budget half overlaps tool-tax, so the differentiator is the cross-server overlap, which only works if the similarity heuristic gives few false positives.

**MVP.** `mcp-fleet-lint catalogs/*.json` (or `--config .mcp.json --spawn`). Rules: cross-server name collision (error), similarity ≥ threshold (warn), a total-budget cap, per-tool cap, missing param description. Text and JSON output.

**Acceptance tests.**
1. Two fixture catalogs that both define `search`: exit 1 and the output names both servers.
2. `search_issues` ("Search issues in repo") vs `find_tickets` ("Find tickets in project"), with the threshold set so they overlap: one WARN. Two unrelated tools: no WARN.
3. `--max-total-tokens 500` on a 2,000-token fixture: exit 1, and the report lists the top 3 tools with token counts that sum to the total.

**Scores:** demand 5, gap 3, feasibility 5, distribution 4. **Total 17.**

Why this is ranked second even though its total is higher: demand is excellent, but the budget half is already served by tool-tax, and the novel half (semantic overlap) is the speculative one. The gap here is a hypothesis. #1's gap is verified against the official suite's README.

---

## 3. `hookcheck`: test harness for Claude Code hooks
**What / who.** Given `.claude/settings.json`, it statically validates the hook entries (matcher regex, event names, command exists and is executable). It then *executes* each hook command against fixture JSON payloads for that event (e.g. a `PreToolUse` Bash payload). It asserts the exit-code semantics (exit 2 blocks) and that any JSON on stdout matches the hook output schema, and it reports runtime. Users are Claude Code users writing safety or format hooks.

**Demand.** Dozens of "hooks not firing" issues. These are partly Claude Code bugs, so a tool can't fix them, but it can separate "my script is wrong" from "dispatch is broken".
- #3672 [V] "PreToolUse hooks not executing at all in Claude Code" https://github.com/anthropics/claude-code/issues/3672
- #6305 [V] "Post/PreToolUse Hooks Not Executing in Claude Code", still open with 41 comments: https://github.com/anthropics/claude-code/issues/6305
- #14493 [V] https://github.com/anthropics/claude-code/issues/14493 and #52715 [V] https://github.com/anthropics/claude-code/issues/52715
- The community answer is manual: "run the hook script by hand with a sample JSON payload" (https://dev.to/rulestack/claude-code-hooks-not-firing-how-to-verify-what-actually-ran-44f [S]).

**Alternatives and gaps.**
- `agnix` [V]: https://github.com/agent-sh/agnix. Apache-2.0, 483 stars, very active (pushed today). It lints hooks config *statically* and is the strongest competitor in the broader config-linting space. It does not execute hooks against fixtures, to my knowledge (unverified).
- A third-party "hooks-test" skill [S] only suggests pytest plus `claude -p`, which needs a live model.

**Feasibility.** Offline. Fixture payloads come from the public hooks docs, so we must read those at build time. The schema is vendor-controlled and changes fast, which is the main risk (a maintenance treadmill). Distribution: a pre-commit hook and an Action.

**MVP.** `hookcheck run [settings.json]`, with payload fixtures for 4 events, exit-code and JSON-output checks, a timeout, and a `--payload file.json` override.

**Acceptance tests.**
1. A hook that exits 2 with a stderr message, given a PreToolUse fixture: reported "BLOCKS" and the stderr is shown.
2. A hook whose command path doesn't exist: static check fails with the path named.
3. A hook printing invalid JSON on exit 0: flagged as "unparseable output", exit 1.

**Scores:** demand 3, gap 4, feasibility 5, distribution 3. **Total 15.**

---

## 4. `transcript-scrub`: CI/pre-commit gate for secrets in agent transcripts
**What / who.** Scans agent session logs (Claude Code `~/.claude/projects/**.jsonl`, Codex logs) and committed transcript dirs for credential-shaped values. It can redact, and it has a *gate mode* (fail if secrets are found), which others lack. Users are developers who share transcripts, sync dotfiles, or run agents in CI.

**Demand.**
- #86707 [V]: "Session transcripts record tool output verbatim, so users end up with credentials on disk that they never typed." https://github.com/anthropics/claude-code/issues/86707
- #63593 [V]: transcripts record "tool stdout **verbatim**"; it becomes a leak vector when "the transcript dir is checked into git". https://github.com/anthropics/claude-code/issues/63593

**Alternatives and gaps.** This is **crowded**.
- `shhh` [V], MIT, 3 stars: https://github.com/trananhhh/shhh
- `agentsweep` [V]: https://pypi.org/project/agentsweep/ (backup-and-fix workflow)
- `cleenup` [S]: https://gh.r-mj.com/zackbart/cleenup
- General secret scanners (gitleaks etc.) work on any text but know nothing about the JSONL structure.
- Gap: maybe SARIF and CI gating, plus multi-agent formats. Thin.

**Feasibility.** Offline, regex and entropy rules plus synthetic fake-key fixtures. Distribution: Action and pre-commit.

**MVP.** `scrub scan|redact <paths>`, 10 token patterns (AWS, GitHub, Anthropic-shaped, OpenAI-shaped, JWT, PEM), JSONL-aware, and a `--fail-on-find` gate.

**Acceptance tests.**
1. A JSONL fixture with a fake `ghp_` + 36 chars token inside a tool_result: scan exit 1, and the output reports the line number without printing the secret.
2. `redact` output stays valid JSONL (every line parses) and the token is replaced.
3. A clean fixture: exit 0, and a rerun on a redacted file is idempotent (byte-identical).

**Scores:** demand 4, gap 2, feasibility 5, distribution 3. **Total 14.**

---

## 5. `llm-chaos-mock`: fault-injecting OpenAI/Anthropic-compatible mock server
**What / who.** A local HTTP server that speaks `/v1/chat/completions` and `/v1/messages`, with scripted responses *and* injected faults: 429/529 with `retry-after`, mid-stream disconnects, truncated or malformed tool-call JSON, and slow first token. Users are app and agent developers who want deterministic CI for retry and error paths.

**Demand.**
- "How to test LLM agents without calling the real API" [V]: https://dev.to/mukundakatta/how-to-test-llm-agents-without-calling-the-real-api-17oc
- "How I test my MCP agent without burning tokens" [V]: https://dev.to/josephgec/how-i-test-my-mcp-agent-without-burning-tokens-486g
- A 2026 CI harness post on tool-call failure testing [V]: https://www.kunalganglani.com/blog/agent-tool-call-failure-testing.md

**Alternatives and gaps.** This is the **most crowded** idea.
- `stubllm` [V] https://pypi.org/project/stubllm/, `mockllm` [V] https://pypi.org/project/mockllm/, `kagent-dev/mockllm` [V] https://github.com/kagent-dev/mockllm, CopilotKit `llmock`/aimock [V] https://github.com/copilotkit/llmock (the redirect is real; the repo moved), and `llmposter` (Rust) [S] https://docs.rs/crate/llmposter/0.5.0.
- Several already offer scripted tool calls. I did not verify whether any has full fault injection, so the gap is **unverified** and probably small.

**Feasibility.** Fully offline, stdlib `http.server`. The tests are easy. Distribution: PyPI/npm need a human.

**MVP.** A YAML script of rules, two endpoints, SSE streaming, and 4 fault types.

**Acceptance tests.**
1. The `openai` SDK pointed at the server gets the scripted tool_call.
2. Rule `fault: 429 retry-after 1` returns 429 once, then 200 on the retry.
3. Rule `fault: disconnect_after_chunks 2` makes a streaming client see a premature-EOF error (not a hang).

**Scores:** demand 4, gap 1, feasibility 5, distribution 3. **Total 13.**

---

## Ranking summary
| # | Candidate | Dem | Gap | Feas | Dist | Total |
|---|---|---|---|---|---|---|
| 1 | mcp-preflight (stdio doctor) | 4 | 3 | 5 | 4 | 16 |
| 2 | mcp-fleet-lint | 5 | 3 | 5 | 4 | 17 |
| 3 | hookcheck | 3 | 4 | 5 | 3 | 15 |
| 4 | transcript-scrub | 4 | 2 | 5 | 3 | 14 |
| 5 | llm-chaos-mock | 4 | 1 | 5 | 3 | 13 |

I put #1 above #2 despite the lower raw total. The reason is gap confidence, not demand.

## Final recommendation
**Build #1, `mcp-preflight`.**
- Its gap is the only one I verified against a primary source. The official conformance suite's README documents server testing only via `--url` (HTTP), and stdio is the default way MCP servers ship.
- The pain is concrete and recurring in the issue trackers of the main clients (4 verified issues), and the failure ("works when I test it manually") is the kind a CI check can catch.
- It is deterministic and testable with four tiny fixture servers: no network, no keys, no model.
- Its output is binary (pass/fail with a quoted offending line), so a reviewer can check it independently.
- The GitHub Action path needs no registry account. PyPI/npm publishing would need the Patron, so we should ship via the Action and `pipx install git+https://…` first.

Before building, spend 15 minutes checking whether `markndg/mcpcheck` already does stdio spawn checks. It was the one competitor I couldn't assess. If it does, switch to #2 or fold #1's checks into #2 as a second subcommand, which I'd plan to do anyway once #1 ships.

Everything above is from public pages. Nothing here required money or accounts. Star counts, pushed dates and licences are from the GitHub API on 2026-11-13.
