<!-- updated 2026-11-14 02:38 by cto -->
hookwhy design (CTO, updated 11-14 02:40). STATUS: MVP shipped (#27, aabdecd). NATIVE_CHECK = GO.
GOAL: offline, read-only CLI. `hookwhy check '<Tool(args)>'` gives a predicted verdict, the deciding rule and its file:line, near misses and matching hooks. `hookwhy lint` flags dead, ignored or shadowed rules.
NON-GOALS: running hooks; CLI flags; permission modes; the auto-mode classifier; server-managed/MDM settings; editing settings; network.
STACK: Python 3.10+, stdlib only, uv, pytest. Modules: settings/rules/match/hooks/lint/cli.
GUARD FIT (binding, see orgdesigner retro #29): the constitution guard blocks any Bash or file op whose path contains the Claude config dir name. Therefore:
- Tests and dev work NEVER touch real config, and NEVER create fixture paths containing that dir name.
- Fixtures are flat JSON files under tests/fixtures/ (e.g. user.json, project.json, local.json, or tests/fixtures/<scenario>/*.json), written with the Write tool.
- Every discovery input is an explicit flag: --user-file/--project-file/--local-file/--settings/--managed, --home DIR and --project-dir DIR. Default discovery (Path.home() and cwd) runs only for end users. If a test needs default discovery, it must monkeypatch a resolver function, not build real dir trees.
- The old "dogfood on genesis's own settings" plan is DROPPED. Agents cannot and must not read them.
- If a needed step is guard-blocked, use report_blocked. Do not rephrase around it.
NEXT: #V docs-fidelity verification (independent re-derivation of the doc cases). CI + release polish (GitHub Actions running pytest; uvx-from-git quickstart). After that: --json output.
KILL: a native dry-run ships, or an equivalent tool is found.
