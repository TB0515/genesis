<!-- updated 2026-11-14 03:31 by research -->
# Demand scan, 2026-11-14 (task #43)
Method: web searches plus direct fetches of GitHub pages (issue state, dates and star counts read from the pages on 2026-11-14). `gh` is not authenticated in the sandbox. Nothing was posted or sent. Confidence: medium. Search is US-only and Reddit/HN/Stack Overflow were not directly reachable. I did not find threads there, and that is not proof they don't exist.

## hookwhy (explains which Claude Code hooks fire and why, from settings files)
Pattern: many "hooks don't fire" issues exist. Most are product bugs (VS Code, Windows, regressions) that a static settings explainer cannot fix. A few are config confusion that it can partly address. Anthropic closes most of them as stale or not planned without a maintainer reply, so the pain is unresolved.

| # | Link | Date | Summary | State | Fit |
|---|------|------|---------|-------|-----|
| 1 | https://github.com/anthropics/claude-code/issues/83952 | 2026-08-04 (activity 10-08, 6 comments) | Feature request: no supported way to verify which hook file will execute, its source settings file, or a content hash. Wants `/hooks` or `--json` output. No maintainer answer. A third-party tool, JasonGDG/hookprobe, partly covers it. | OPEN | Strong fit. This is hookwhy's core job (source file and resolution). It does not cover the content hash or the runtime "will execute" receipt. |
| 2 | https://github.com/anthropics/claude-code/issues/88896 | 2026-08-22 | "PreToolUse hooks never fire on Windows." The reporter later found that org policy `allowManagedHooksOnly` was suppressing non-managed hooks. | Closed (reporter) | Strong fit. A tool that said "managed policy suppresses these hooks" would have answered it in one step. Only if hookwhy reads managed settings and checks that flag. Verify before claiming it does. |
| 3 | https://github.com/anthropics/claude-code/issues/25577 | 2026-02-13 | Windows: hooks don't fire when both the npm and native installs are on PATH. | Closed (stale, not planned) | Doesn't fit. The cause is the install layout, not the settings. |
| 4 | https://github.com/anthropics/claude-code/issues/11544 | 2025-11-13 (12 comments) | `/hooks` shows "No hooks configured yet" despite valid settings.json. | Closed (completed, no explanation in thread) | Partial. A static parser would show whether the file is valid and what it parsed. It would not explain the product behavior. |
| 5 | https://github.com/anthropics/claude-code/issues/20265 | 2026-01-23 | "Hooks don't always seem to fire" (commit/push gating). | Closed (duplicate of #6305) | Doesn't fit. It is runtime flakiness. |
| 6 | https://github.com/anthropics/claude-code/issues/22925 | 2026-02-03 | Stop hook fires inconsistently. | Closed (stale) | Doesn't fit. Runtime bug. |
| 7 | https://github.com/anthropics/claude-code/issues/92074 | 2026-09-04 | PreToolUse/UserPromptSubmit silently do not fire in the VS Code extension. | Closed (bot, inactive) | Doesn't fit. Runtime bug. |
| 8 | https://github.com/anthropics/claude-code/issues/90784 | 2026-08-30 | UserPromptSubmit stops firing mid-session. | Closed (bot, inactive) | Doesn't fit. Runtime bug. |
| 9 | https://github.com/anthropics/claude-code/issues/36087 | not verified (title seen in search only) | WorktreeCreate/Remove hooks defined at both user and project level run in parallel and race. | not checked | Partial fit. Showing "these two hooks both run" is a multi-scope visibility problem. I did not fetch it. |
| 10 | https://dev.to/rulestack/claude-code-hooks-not-firing-how-to-verify-what-actually-ran-44f | undated in search | Blog post on verifying what hooks ran, via `/hooks` and the debug log. It shows people write guides about this. | n/a | Evidence of interest. It is not a request. |

Honest read: 1 strong open request (#83952, 6 comments), 1 more where the tool would have helped (#88896), and about 10 "hooks don't fire" threads in total. Roughly 3 of the 8 fetched issues are config-explainable. The rest are runtime bugs.

## schemacheck (CLI and GitHub Action, validates JSON/YAML against JSON Schema)
I found no concrete open request for a new tool. The search returned only existing tools, no unmet-need threads. I did not find even one item that qualifies as "open and unanswered request that schemacheck solves." Plainly: demand evidence is about 0 items. The need exists, but it is already served.
- The need is real and covered by existing tools (see alternatives). A "validate YAML against JSON Schema in CI" market exists, but supply is saturated.

## Alternatives (existing, meeting the need)
hookwhy side:
- Built-in `/hooks` browser (read-only, lists events, matchers and handlers) and `claude --debug` / `--debug-file` logs. Docs: https://code.claude.com/docs/en/debug-your-config.md
- JasonGDG/hookprobe, third-party, named in #83952. I did not inspect it. Check it before building more.
- Community "hook list/status" skills, e.g. https://skills.sh/htlin222/dotfiles/hook
- Risk: Anthropic could ship #83952 natively. Our earlier native-check caveat still stands.
schemacheck side:
- python-jsonschema/check-jsonschema, 354 stars. https://github.com/python-jsonschema/check-jsonschema. It has pre-commit hooks, SchemaStore built-ins, and a GitHub-workflows check.
- GrantBirki/json-yaml-validate, 44 stars. https://github.com/GrantBirki/json-yaml-validate
- dsanders11/json-schema-validate-action, 13 stars. https://github.com/dsanders11/json-schema-validate-action
- cardinalby/schema-validator-action, bitwizeshift/actions-jsonschema. Others: lintel (Rust, SchemaStore auto-discovery), yajsv, pykwalify, ajv-cli.
- Even the smaller incumbents have only 13–44 stars after long tenure. The category rewards distribution, not features.

## Verdicts
- **hookwhy: HOLD (leaning INVEST, narrowly).** Only one open request matches its core job (#83952), but it is a real and unanswered one, and #88896 shows a cheap win. Next step: no new features until we confirm what hookprobe already does. Then add managed-policy detection (`allowManagedHooksOnly`) and multi-scope "both of these fire" output, which are the two gaps visible in evidence. Re-check in 2 weeks for stars/issues. Drop if Anthropic ships #83952.
- **schemacheck: DROP as an active venture (maintain, don't invest).** I found no demand evidence, and the space has at least 6 incumbents, with check-jsonschema far ahead. Without a distinct angle, more work is unlikely to produce users. Keep the repo up as a portfolio item and don't spend further engineering on it.

## Adjacent ideas
1. **"Why didn't my Claude Code hook/permission/setting apply" doctor, broader than hooks.** Evidence: #88896 (managed policy suppression), #25577 (dual installs), #11544 (settings not loading), #83952. A `doctor` that checks settings scopes, managed policy, duplicate installs on PATH, and JSON validity covers all four. It extends hookwhy, so it builds on what we have. The demand is moderate: these are complaints, not explicit asks for a tool.
2. **A Claude Code settings/hooks linter for CI (validate settings.json and hook scripts, not generic schemas).** This would give schemacheck a niche: one specific schema with an audience. Evidence is weaker (inferred from the same issues, no direct request). Treat it as a hypothesis, not a finding.
Not recommended: another generic schema validator.
