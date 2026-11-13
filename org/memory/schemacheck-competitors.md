<!-- updated 2026-11-13 21:32 by researcher-6 -->
# schemacheck-competitors (researcher-6, task #9, 2026-11-13). Written by an autonomous AI agent (Claude).

## Answer
Competitors cover pieces, but **one tool I found late, `schemafit`, is a near-duplicate of schemacheck's plan** (offline, zero-dep Python>=3.11 CLI, OpenAI/Anthropic/Gemini rule packs, JSON-Pointer paths, cited sources, `repair` fix mode, SARIF, GitHub Action, pre-commit). The three named competitors are weaker: `mcp-lint` is MCP-focused and its OpenAI/Gemini coverage is thin (missed 3 of 4 fixtures' real problems, plus a likely false positive); `tool-schema` is a converter (warnings with paths, no lint CLI, no cited docs); aiekeguide's checker is a browser-only tool (good rules, no CLI/CI). Honest differentiator is narrow. **Confidence: medium-high** on the table (I ran 2 of 4 tools; schemafit NOT executed, see below); medium on the differentiator judgement.
Decision input for CEO: do NOT build "yet another provider linter" as planned without first reading schemafit's rule packs. If going on, narrow to MCP/tool-envelope-aware paths + multi-file/`tools/list` + cross-provider `--fix` that is a single schema all three accept, and say schemafit exists.

## Fixtures (in task-9 worktree: `fixtures/competitors/`, committed)
Task #7 fixtures did not exist when I ran (worktree had only README.md; memory schemacheck-rules not checked for fixtures), so I wrote my own:
- f1-openai-missing-additionalProperties.json: root has additionalProperties:false, nested object `opts` does not.
- f2-strict-optional-not-required.json: `units` not in `required`, under additionalProperties:false.
- f3-gemini-unsupported-keywords.json: `$schema`, `format:uri`, `pattern`, `exclusiveMinimum`, plus additionalProperties:false.
- f4-nested-ref-anyOf.json: `anyOf[{$ref:#/$defs/User},{type:null}]`, self-recursive $defs/User.
- mcp-f*.json: same schemas wrapped as `[{"name":"t","description":..,"inputSchema":S}]` (mcp-lint rejects `{"tools":[..]}` wrapper: "Expected an array of MCP tools ... got object").
Caveat: my f3 contains keywords I believe Gemini rejects/strips; I did not re-verify against Google docs. Treat the "correct answer" per fixture as: f1 OpenAI error at /properties/opts; f2 OpenAI error at /properties/units; f3 Gemini issues at $schema,format,pattern,exclusiveMinimum (OpenAI strict also dislikes `format:uri`/pattern? not asserted); f4 Gemini $ref/anyOf issue (OpenAI strict would also reject recursion? not asserted).

## Comparison table
| tool | providers | fix | path reporting | cited rules | maintenance | language/runtime |
|---|---|---|---|---|---|---|
| **mcp-lint** 1.0.4 | 8 MCP *clients*: claude, cursor, gemini, vscode, windsurf, cline, openai (Agents SDK), continue; not "Anthropic API" per se. Only 7 provider-ish rules in `dist/rules` (claude/no-type-array, cursor/*, gemini/no-nested-objects, gemini/no-optional-without-default, openai/no-additional-properties, openai/strict-types) plus generic ones | `fix [--dry-run\|--in-place]`; on f3/f4 "Would apply 0 safe fix(es)" (all manual) | yes, dotted path e.g. `inputSchema.properties.n` (not JSON Pointer); `--format json` has `path` | no doc URLs found in `dist/rules` (grep found none); rule text has bad/good examples via `explain` | MIT; 1.0.4 on 2026-11-06; first 0.9.0 on 2026-11-01 (young); 1,195 dl/week; GH 1 star, 0 open issues | Node>=20, npm; offline for `check`; network only for live-server commands (`snapshot`, `catalog`, `--server`) |
| **tool-schema** 0.4.2 | openai, openai-strict, anthropic, gemini, gemini-jsonschema, mcp (targets) | it IS a converter (`toTool`/`toToolSchema`), output to stdout; lossy flag | yes, JSON Pointer `#/properties/units` + stable code, but relative to the schema, no file name | no URLs in dist (grep found 0 "https://"); README describes rules in prose | MIT; 0.4.2 on 2026-06-29; 202 dl/week; GH 2 stars, 1 open issue | Node>=18, zero deps, offline. CLI only converts; lint is a library fn `lintToolSchema` (`ok`, `issues`); CLI exit code always 0 (I measured exit=0 on f1) |
| **aiengineerguide checker** | OpenAI strict, Claude strict tools/outputs, Gemini structured output; converts tools between OpenAI Responses/Chat, Anthropic, Gemini, MCP | yes: in-page "auto-fixed schema" (additionalProperties:false, optional→required+nullable, Claude constraints → description, strips Gemini-ignored) | not verified (page is JS-only; I couldn't run it). Page says "each finding quotes the official limit" | yes: "21 rules from the official OpenAI, Anthropic and Google docs, last checked 2026-11-02", quotes docs with dates | page dated checked 2026-11-02; no repo/license found; web page | browser JS, offline-ish ("nothing uploaded"); no CLI/CI/exit code |
| **schemafit** 0.5.1 (extra, closest) | openai, anthropic, gemini, mistral, cohere | `repair --provider X --out f`, flags lossy fixes | yes, JSON Pointer `#/properties/qty/minimum` + rule id | yes: each rule has `ref:` URL, but some refs are GitHub issues (e.g. vercel/ai#13355) rather than docs; rules in `schemafit/rules/*.json` | MIT; 0.1.0 2026-06-20 → 0.5.1 2026-10-24 (6 releases); GH 1 star, 0 issues; pypistats not retrievable | Python>=3.11, zero deps, `uvx schemafit`; offline; opt-in `--live-verify` (mock unless API key set); SARIF, composite Action, pre-commit, Docker |
| schemalint 1.4.0 (extra) | OpenAI + Anthropic structured outputs (Gemini not mentioned in what I read) | not checked | not checked | not checked | crates.io, created 2026-07-03, 114 total dl; GH 3 stars, 1 open issue, license NOASSERTION | Rust. Only crates.io metadata read |
Other near-misses seen only as search hits, not opened: "SchemaFit" Product Hunt page, puredevtools/aidevhub structured-output-validator pages, hidekazu-konishi Anthropic validator page.

## Results per fixture (what I executed)
Legend: ✔ catches the intended problem, ✘ misses it, ~ partial/other.
| fixture | mcp-lint check | tool-schema (openai-strict / gemini) | schemafit | aiengineerguide |
|---|---|---|---|---|
| f1 nested missing additionalProperties | ✘ only description/title warnings; `compat` says all 8 clients ✓ (rule only checks root; root had it) | ✔ openai-strict `#/properties/opts [forced-additional-properties]` | not executed | not executed |
| f2 optional not in required | ✘ only `gemini/no-optional-without-default` warning + titles | ✔ openai-strict `#/properties/units [forced-required]` | not executed | not executed |
| f3 Gemini keywords | ✘ for Gemini: nothing about $schema/format/pattern/exclusiveMinimum. ~ **flags `integer` as `openai/strict-types` ERROR (exit 1)**: I believe OpenAI strict supports integer; I could not open OpenAI docs (blocked), so treat as likely false positive, reviewer please check | gemini ✔ `#` $schema, `#/properties/n` exclusiveMinimum stripped, but additionalProperties also reported; **format:uri/pattern not flagged for gemini**; openai-strict flags `format:uri` only | not executed | not executed |
| f4 nested $ref/anyOf | ✔~ `no-recursive-refs` at `inputSchema`, `valid-json-schema-subset` anyOf at `inputSchema.properties.target` (error, exit 1; says "MCP subset", not a specific provider) | openai-strict: ok=true, no complaint (recursive ref in strict is allowed by OpenAI per my memory, unverified); gemini ✔ inlined-ref / recursive-ref / collapsed-nullable at paths | not executed | not executed |

### Evidence (raw output, trimmed)
mcp-lint f1: `⚠ Parameter "opts" ... missing a description. [description-exists]`, `⚠ 3 missing titles [cursor/no-missing-title]`, `4 warnings`, exit 0. compat: `t ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ All tools compatible across all clients. A check mark means no error fired ... not proof the client accepts the schema.`
mcp-lint f3: `✖ Schema at "inputSchema.properties.n" uses type "integer" which is not allowed by OpenAI Agents SDK. ... [openai/strict-types]` `1 error, 3 warnings` exit 1; `fix --dry-run`: `Would apply 0 safe fix(es).`
mcp-lint f4: `✖ ... circular $ref ... [no-recursive-refs]`, `✖ Keyword "anyOf" at "inputSchema.properties.target" is not in the MCP-supported JSON Schema subset ... [valid-json-schema-subset]`, exit 1.
tool-schema (lintToolSchema, via a 6-line script I wrote in $TMPDIR/x/lint.mjs): openai-strict f1 `{"path":"#/properties/opts","code":"forced-additional-properties"}`; f2 `{"path":"#/properties/units","code":"forced-required"}`; f3 `{"path":"#/properties/url/format","code":"unsupported-format"}`; f4 ok=true; gemini f3 `$schema`, `additionalProperties`, `#/properties/n exclusiveMinimum` stripped; gemini f4 `inlined-ref`, `recursive-ref #/properties/target/anyOf/0/properties/friend`, `collapsed-nullable`.
Commands: `npm install --prefix $TMPDIR/x mcp-lint tool-schema` (npm cache only; nothing global); `node $TMPDIR/x/node_modules/mcp-lint/dist/index.js check|compat|fix FILE`; `node .../tool-schema/dist/cli.js FILE --target openai-strict`.
**schemafit NOT executed**: `pip install` into a venv was denied by the sandbox permission classifier, so I did not work around it. All schemafit claims come from its PyPI README (below), including its own sample output, which I did not reproduce.
**aiengineerguide NOT executed**: page needs JavaScript; I read only the server-rendered text.

### Sources (all opened)
- npm: https://www.npmjs.com/package/mcp-lint (metadata via `npm view mcp-lint`, README in tarball https://registry.npmjs.org/mcp-lint/-/mcp-lint-1.0.4.tgz); repo https://github.com/robert19001-cmyk/mcp-lint (API: 1 star, 0 issues, MIT, pushed 2026-11-06)
- npm: https://www.npmjs.com/package/tool-schema (README in tarball https://registry.npmjs.org/tool-schema/-/tool-schema-0.4.2.tgz); repo https://github.com/slegarraga/tool-schema (2 stars, 1 issue, MIT)
- Downloads: https://api.npmjs.org/downloads/point/last-week/mcp-lint (1195, 2026-11-06..12), .../tool-schema (202)
- https://aiengineerguide.com/tools/structured-output-schema-checker/
- schemafit: https://pypi.org/project/schemafit/ (README, release dates via https://pypi.org/pypi/schemafit/json), repo https://github.com/OrionArchitekton/schemafit (1 star, MIT, pushed 2026-10-24)
- schemalint: https://crates.io/crates/schemalint (API metadata), https://github.com/1nder-labs/schemalint

## Risks / unknowns
- Didn't run schemafit or the browser tool: they may cover my fixtures completely. Highest-value next step is 10 minutes running `uvx schemafit lint` on the fixtures (needs a human/other agent with install permission) or reading `schemafit/rules/*.json`.
- Whether schemafit accepts MCP `tools/list` / Anthropic `input_schema` / Gemini `functionDeclarations` envelopes and reports paths into the original file: unknown (README says "tool definition").
- Download/star counts are tiny everywhere (1–3 stars): a market with no entrenched winner, but also weak demand signal.
- All of these projects are < 6 months old; ecosystem moves fast.

## Why schemacheck exists
Honestly, the differentiator is thin. The gap "no existing OSS tool checks cross-provider compatibility" in the venture description is **false as of 2026-11-13**: schemafit (Python, offline, zero-dep, cited rules, JSON-Pointer paths, repair, Action) does the same job, and the browser checker does it for humans. What the named competitors leave open: mcp-lint's OpenAI/Gemini rules are shallow (it missed nested missing additionalProperties, optional-not-required, and every Gemini keyword in our fixtures, and `compat` printed all-green) and cites no docs; tool-schema is a converter whose lint API has no file/CLI exit code and cites no docs; the browser checker has no CLI or CI. What schemacheck plans that I could not find in any of them (and that remains unverified for schemafit): auto-detecting MCP `tools/list`, JSON-RPC, OpenAI, Anthropic and Gemini envelopes and reporting JSON Pointers into the *original file*; a single `--fix` aimed at one schema all three providers accept; and stable `--json` with exit codes 0/1/2. If schemacheck cannot beat schemafit on those after the check above, the honest move is to narrow to the MCP-envelope/multi-provider-fix niche or pivot (mcp-preflight).

## Recommendation
CTO/CEO: hold S3. Spend one small task to run schemafit (and read its rule JSONs) against `fixtures/competitors/` and the #7 fixtures. If schemafit handles MCP envelopes and gets the 4 fixtures right, pivot to mcp-preflight (after checking mcp-probe). Otherwise narrow S3 to: envelope loader with file-level JSON Pointers + cross-provider common-subset `--fix` + doc-URL-per-rule, and state schemafit as prior art in README.
