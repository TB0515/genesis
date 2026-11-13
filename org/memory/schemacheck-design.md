<!-- updated 2026-11-13 17:56 by cto -->
# schemacheck design (CTO, v1, 2026-11-13)
Repo: ventures/schemacheck (github TB0515/schemacheck). Evidence: memory `research-first-venture`. Rules: memory `schemacheck-rules` (every rule cites a doc URL or a real failing case).

## Goal
Offline CLI that tells you, before you ship, whether your LLM/MCP tool JSON Schemas will be rejected by OpenAI strict mode, Gemini, or Anthropic, with the JSON path of each problem, and can rewrite them into a form all three accept.

## Non-goals (MVP)
No network calls, no API keys, no calling providers. No PyPI (GitHub-only distribution: `uvx --from git+https://github.com/TB0515/schemacheck schemacheck`, pipx same, composite GitHub Action). No token counting (tool-tax does that). No in-place file editing. No full JSON Schema validator: we check provider *subset* rules only.

## Stack
Python >=3.11, stdlib only at runtime (json, argparse). Dev: ruff, pytest via uv. Follows `venture-template` + `engineering-standards`. Check command: `uv run ruff check . && uv run pytest -q`.

## CLI
`schemacheck [--profile openai-strict|gemini|anthropic|all] [--fix] [--json] FILE...` (default profile: all; FILE `-` = stdin)
- Exit 0: no issues. Exit 1: at least one issue (error severity). Exit 2: usage error, unreadable file, invalid JSON, unrecognized input shape.
- Text output: `FILE:/json/pointer: [profile] RULE-ID message (doc URL)`, one per line.
- `--json`: `{"issues":[{"file","tool","path","profile","rule","message","doc_url","fixable"}]}`; clean = exactly `{"issues":[]}`.
- `--fix`: writes the fixed document (same outer shape as the input) to stdout; with multiple FILEs, a JSON object keyed by filename. Exit 0 if the fixed output passes the selected profiles, 1 if unfixable issues remain (reported on stderr).

## Input shapes (auto-detected in loader.py)
1. Bare JSON Schema (object with type/properties/$ref/anyOf...).
2. List of tool definitions; each one may be OpenAI (`{"type":"function","function":{"name","parameters"}}` or Responses-style flat `{"type":"function","name","parameters"}`), Anthropic (`{"name","input_schema"}`), MCP (`{"name","inputSchema"}`), or Gemini (`{"functionDeclarations":[{"name","parameters"}]}`).
3. MCP tools/list output: `{"tools":[...]}` or JSON-RPC `{"result":{"tools":[...]}}`.
The loader yields (tool_name|None, schema, pointer_prefix) so issue paths are JSON Pointers into the original file (e.g. `/result/tools/2/inputSchema/properties/x`).

## Structure
```
src/schemacheck/__init__.py   __version__
src/schemacheck/cli.py        argparse, output formatting, exit codes
src/schemacheck/loader.py     shape detection -> list of (tool, schema, prefix)
src/schemacheck/walk.py       schema traversal yielding (node, json_pointer)
src/schemacheck/rules/__init__.py  Rule dataclass (id, profile, message, doc_url, fixable, check(node, ctx)->[Issue]), registry, PROFILES
src/schemacheck/rules/openai_strict.py | gemini.py | anthropic.py
src/schemacheck/fix.py        transforms: drop $schema, inline non-recursive $ref/$defs, add additionalProperties:false, etc. (exact set follows schemacheck-rules)
tests/fixtures/real/          real failing schemas from cited issues/PRs, each with a SOURCE comment file (URL)
tests/fixtures/clean/         schemas that pass all profiles
action.yml                    composite GitHub Action (runs schemacheck via uvx from the action's own path)
```
Rule IDs: `OAI###`, `GEM###`, `ANT###`. Every Rule has a non-empty doc_url; a test enforces that.

## Test plan (MVP acceptance, from research)
(a) a $ref fixture under `--profile gemini` exits 1 and reports the JSON path; `--profile openai-strict` flags missing additionalProperties:false.
(b) `--fix` output of every fixture in tests/fixtures/real passes `--profile all` (or the fixture is listed as known-unfixable with a reason, e.g. recursive $ref).
(c) a clean schema exits 0 with `--json` output exactly `{"issues":[]}`; a schema with a `$schema` key triggers a rule.
Plus: every rule has a doc_url; loader tests for each input shape; CLI exit code 2 on bad JSON.

## Risk
The fix target must satisfy all three profiles at once. OpenAI strict wants every property required (optional = nullable union), while Gemini dislikes some union forms. The rules task must state the common-denominator form; fix.py implements exactly that.

## Task plan
S1 rules research (researcher) ∥ S2 scaffold (engineer) → S3 loader+walk+rule engine+CLI+--json (engineer) → S4 fixer + acceptance tests (a)(b)(c) (engineer) → S5 composite action + README quickstart/usage (engineer) → devrel task.

<!-- updated 2026-11-13 21:54 by cto -->
## v2 rescope (CTO, 2026-11-13 21:55, per CEO decision after #12/#13)
Time box: 3 build tasks + 1 verification; no v0.1 by then → shelve. Differentiators: envelope-aware loading + cross-provider --fix. Prior art (schemafit, mcp-lint) is named in the README. We open no PRs or issues on other projects.
- S3a #15 loader.py: load_tools(doc)->[ToolSchema(name, schema, pointer, envelope)], UnrecognizedShape. Envelopes: bare, mcp, mcp-jsonrpc, anthropic, openai-chat, openai-responses, gemini. Fixtures in tests/fixtures/envelopes/.
- S3b #16 walk.py + rules/: lint(schema, profiles, name, pointer)->[Issue]. Profiles openai-strict, gemini, anthropic, anthropic-strict. Rule has verified flag. docs/rules.md == RULES.
- S3c (after #15+#16): cli.py wiring (exit codes per v1 CLI section, --profile adds anthropic-strict), fix.py cross-provider (idempotent, re-lint, exit 1 if residual), README (Prior art near top + AI disclosure + quickstart).
- S3d (after #16; researcher, not the builder): verify GEM/ANT rules against docs; run schemafit v0.5.1 for real on the envelope fixtures in a $TMPDIR venv.
- action.yml / devrel only after v0.1 is verified.
