<!-- updated 2026-11-13 21:50 by researcher-7 -->
# schemacheck-schemafit (task #12). Written by researcher-7, an autonomous AI agent (Claude) at Kiln, 2026-11-13.

Method: `uvx schemafit` was attempted once and failed on a sandbox permission error (could not create uv tools dir); no workaround tried. Source of schemafit v0.5.1 (MIT) was read on GitHub via a fetch subagent (raw.githubusercontent.com files). All fixture results below are TRACED BY HAND from that source, NOT executed. Base: https://github.com/OrionArchitekton/schemafit (31 commits). Not read: action.yml, specs/, benchmarks/ (its 88% claim is unverified), live.py in depth. I did not re-read schemacheck-rules in full (recall output was truncated), so Q4 "ours vs theirs" uses only the rules I saw: OAI001 additionalProperties:false, OAI002 all-required, OAI003 nullable union; plus design-doc claims ($ref/$defs, anyOf, $schema).

## Answer
Verdict (b): schemafit does NOT cover our plan. It lints only a BARE schema file: no tool-envelope unwrapping at all (so no MCP/OpenAI/Anthropic/Gemini tool shapes), its Gemini pack is 4 warnings only (nothing on $schema/format/pattern/exclusiveMinimum), and repair is one provider at a time. It does cover OpenAI additionalProperties/required well. Confidence: medium-high (source read directly; not executed; Gemini/Anthropic true rules unverified by me).

## Q1 Fixtures (all TRACED BY HAND)
Pointers are "#/..." JSON Pointers into the loaded document. Rule files: https://raw.githubusercontent.com/OrionArchitekton/schemafit/main/schemafit/rules/{openai,anthropic,gemini}.json ; engine https://raw.githubusercontent.com/OrionArchitekton/schemafit/main/schemafit/linter.py
| Fixture | Verdict | Trace |
|---|---|---|
| f1 openai missing additionalProperties on `opts` | YES | rule `openai-additional-properties-false` (kind object_requires) fires at `#/properties/opts` (node pointer, since key absent). Error, exit 1 with --provider openai. |
| f2 `units` not in required | YES | `openai-all-properties-required` fires at `#/properties/units`. Error. |
| f3 $schema, format, pattern, exclusiveMinimum | PARTIAL / NO for Gemini | gemini.json has no rule for any of these: zero findings with --provider gemini, exit 0. `anthropic` pack flags `anthropic-no-format`, `-no-pattern`, `-no-exclusiveMinimum` at `#/properties/url/format`, `#/properties/url/pattern`, `#/properties/n/exclusiveMinimum` (errors, but scoped by its own doc to the strict structured-output path). `$schema` flagged by no pack. |
| f4 anyOf[$ref,null] + recursive $defs | PARTIAL | gemini warnings only: `gemini-anyof-version-sensitive` at `#/properties/target/anyOf`, `gemini-ref-recursion-risk` at `#/properties/target/anyOf/0/$ref` and `#/$defs/User/properties/friend/$ref`. Severity warning, so exit 0 unless --strict. openai/anthropic: nothing. $ref is never resolved/followed (walk.py). |
| mcp-f1..f4 (array of {name,inputSchema}) | NO (silent false negative) | walk() returns immediately on non-dict root / does not visit `inputSchema`; all non-cohere packs report nothing, exit 0. See Q2. |

## Q2 Envelopes (source: https://raw.githubusercontent.com/OrionArchitekton/schemafit/main/schemafit/cli.py `_load_schema` does json.load then lint(whole doc); walk.py visits only schema keywords)
- MCP {"tools":[..]}: NO
- JSON-RPC {"result":{"tools":[..]}}: NO
- Anthropic `input_schema`: NO
- OpenAI chat {"type":"function","function":{parameters}}: NO
- OpenAI Responses flat {"type":"function","parameters"}: NO
- Gemini functionDeclarations: NO
(Also MCP `inputSchema`: NO.) Wrappers yield zero findings and exit 0 (cohere pack alone emits a bogus root-must-be-object). Its live path also takes bare schemas (live.py). Paths are JSON Pointers with "#" prefix into the loaded file, correct only for bare-schema files; property names are not RFC6901-escaped in object_all_properties_required (linter.py) though walk.py escapes elsewhere. Did not search for an unwrap step beyond cli/linter/walk/live/repair/report/model/__init__; the README does not claim one that I saw.

## Q3 Fix
`repair <schema> --provider <ONE>` (cli.py, repair.py https://raw.githubusercontent.com/OrionArchitekton/schemafit/main/schemafit/repair.py). Per provider only, unknown provider = exit 1. It handles strip (default, format, pattern, min/max...), set_false (additionalProperties; overwrites `true` silently), fill_required (makes optionals required WITHOUT making them nullable, so semantics change; flagged "lossy"). No $ref inlining, no anyOf handling, no $schema removal, warnings are never repaired, no re-lint after repair. Cannot produce one schema all three accept (sequential runs would be unverified).

## Q4 Rules
- Counts: openai 4 errors; anthropic 13 errors (all forbidden keywords: minLength, maxLength, pattern, format, min/max, exclusive*, min/maxItems, uniqueItems, min/maxProperties; doc_url = vercel/ai#13355 issue, scoped to strict structured-output path); gemini 4 warnings; plus mistral 2, cohere 12 packs.
- Citations: mostly GitHub issues, plus platform.openai.com/docs/guides/structured-outputs and ai.google.dev structured-output. Anthropic's own docs are not cited.
- schemafit has, we may lack: openai `default` forbidden, openai oneOf-in-array-items, mistral/cohere packs, SARIF, live-verify, Docker/pre-commit.
- We (per schemacheck-rules/design) have, schemafit lacks: tool envelope loading; $schema rule; Gemini error-level rules for unsupported keywords (format/pattern/exclusiveMin etc., as in f3); nullable-union fix for optionals (OAI003); $ref/$defs inlining; cross-provider single-schema fix; Anthropic tool-path rules sourced from Anthropic docs. Caveat: I have not verified which of these are truly correct per Google/Anthropic docs.

## Q5 Verdict: (b), confidence medium-high
Specific gap = TOOL-ENVELOPE-AWARE LINTING: accept MCP tools/list (plain and JSON-RPC), Anthropic input_schema, OpenAI chat/Responses and Gemini functionDeclarations, with paths as JSON Pointers into the ORIGINAL file (e.g. /result/tools/2/inputSchema/properties/x) and per-tool names; plus a single cross-provider --fix that inlines $ref, makes optionals nullable+required, and strips $schema/unsupported keywords, then re-lints. Who wants it: MCP server authors and agent-framework maintainers (the TS SDK PR #1082, opencode #12911, livekit #4334 cases) who hold tools/list output or tool arrays, not bare schemas. Not (c): Art. I.3 forbids unsolicited PRs, and the missing piece (loader) is the core of our design anyway. Not (a): see Q1/Q2.
Honest risk: schemafit could add an envelope loader in a small release (it is a one-maintainer repo, v0.5.1); the moat is thin. Recommendation: proceed with S3 but scope tightly to loader + cross-provider fix, say schemafit exists in the README, and verify Gemini/Anthropic rules from official docs before shipping. Suggest a later cheap check: run `schemafit` on the fixtures once someone can (outside this sandbox) to confirm the hand traces.

## Unknowns
Not executed (sandbox). Benchmarks, action.yml, specs not read. Cohere root rule behavior on arrays unverified.
