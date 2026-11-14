<!-- updated 2026-11-14 03:47 by research -->
# hookwhy prior art (research, 2026-11-14, task #46)
Confidence: medium-high. Doc facts partly from partial page reads (noted). hookprobe probe.py/report.py not read.

## Answer up front
- (a) managed-policy detection (allowManagedHooksOnly): BUILD. Gap is real: neither hookprobe nor docs-level tooling computes it offline.
- (b) multi-scope output: SKIP as a headline feature. Hooks simply merge/all fire; hookprobe lists all scopes already and /hooks labels sources. Only keep cheap "which file each hook came from" (hookwhy already does).
- hookprobe is a different tool (executes hooks 5x to test effectiveness), 0 stars, demo. Not a real competitor; not a reason to stop.

## 1. Feature matrix
| | hookwhy (main) | hookprobe | built-in /hooks, --debug |
|---|---|---|---|
| Purpose | offline predict allow/ask/deny; deciding rule file:line; matching hooks | runs each hook 5x: starts/answers/blocks? | list hooks; log at runtime |
| Sources shown | managed/user/project/local settings (+--settings) with file:line (per CTO design memory) | managed, user, project, local, plugins hooks.json, agent+skill frontmatter (config.py) | /hooks: user/project/local/plugin/session labels; detail view shows definition+location [summary]; managed not named in source list I read |
| Scope precedence | permissions precedence modeled (deny>ask>allow; local>project>user, managed top); hooks listed | none computed; concatenates all entries (config.py load()) | docs: managed > CLI > local > project > user; hooks merge additively |
| Managed-policy awareness | managed file loaded; allowManagedHooksOnly NOT modeled (target of (a)) | managed loaded as ordinary source; allowManagedHooksOnly not referenced in config.py; disableAllHooks handled | /hooks menu shows "Only hooks from managed settings run here" when set [summary, hooks-guide]; /status shows managed source |
| JSON output | --json (per launch draft, verified by comms) | --json with identity block (README) | none found for /hooks; claude doctor has no JSON flag mentioned |
| Content hash | no | yes: SHA-256, size, mtime of target script (README; code not read) | no |
| Runs hooks | no | yes (live also spends 2 claude -p sessions) | yes, real |
| Platform | stdlib py, offline | POSIX only, not on PyPI | n/a |

## 2. hookprobe
URL: https://github.com/JasonGDG/hookprobe (API https://api.github.com/repos/JasonGDG/hookprobe). Stars 0, forks 0, open issues 0. License MIT. Python. Created 2026-09-23; last commit 2026-09-24T13:40Z (f52942c "Fingerprint the file each hook entry actually resolves to"); 21 commits; labelled "demo". Dead-ish for 7 weeks. Description: "does your Claude Code hook actually start, answer and block?" Its managed Windows path is C:\ProgramData\... which docs say is NOT read (legacy); docs path is C:\Program Files\ClaudeCode. (Raw source config.py read.)

## 3. Documented semantics
- allowManagedHooksOnly (https://code.claude.com/docs/en/hooks.md): in managed settings; "Your user, project, local, and plugin hooks are blocked. Hooks from plugins force-enabled in managed settings enabledPlugins are exempt." Also narrows statusLine and fileSuggestion to managed; command-source plugins disabled unless disableCommandPluginSources=false. Settings reference [summary]: true = only managed hooks (+Agent SDK hooks, force-enabled plugin hooks). Managed-settings.md classes it a "lock": strictest value any source sets wins.
- disableAllHooks: cannot disable managed hooks from outside managed settings (hooks.md).
- Hooks merge across scopes: "Hook entries merge across settings levels rather than replacing each other"; matching hooks run in parallel; identical handler in several files runs once (hooks.md). Precedence list: https://code.claude.com/docs/en/settings.md
- allowedHttpHookUrls / httpHookAllowedEnvVars apply to hooks from every source.
- Managed paths (https://code.claude.com/docs/en/managed-settings.md): macOS /Library/Application Support/ClaudeCode/managed-settings.json; Linux/WSL /etc/claude-code/managed-settings.json; Windows C:\Program Files\ClaudeCode\managed-settings.json; drop-ins in managed-settings.d/ in same dir (merged after base file, alphabetical, *.json only); legacy C:\ProgramData path not read. Other managed delivery NOT visible from files: macOS plist domain com.anthropic.claudecode, Windows HKLM/HKCU SOFTWARE\Policies\ClaudeCode "Settings", server-managed (fetched at startup, polled hourly). Within managed tier first-wins by default: remote > MDM > files > HKCU (managedSourcesBehavior "merge" since v2.1.242). So a file-only tool can only say "allowManagedHooksOnly set in file; remote/MDM may also set it", and cannot prove it is unset.
- /hooks: "list every hook registered for the current session, grouped by event" (https://code.claude.com/docs/en/debug-your-config.md). --debug logs events, matchers checked, exit code and output.

## 4. Verdicts
(a) BUILD: nobody computes "managed policy suppresses your user/project hooks" offline; /hooks only shows a menu notice at runtime. Do it: read managed-settings.json + managed-settings.d/*.json (via explicit --managed flag/fixtures; tests never touch real config), if allowManagedHooksOnly true mark user/project/local hooks BLOCKED, exempt force-enabled plugins; caveat remote/MDM/registry not visible; use docs paths (Program Files).
(b) SKIP as a headline: docs say all scopes merge and run, hookprobe and /hooks already list them. Only ensure hookwhy output labels each hook with scope+file and notes identical-handler dedupe. Low priority.

## Caveats / unverified
hooks.md read only first ~40k of 294k chars; settings-reference allowManagedHooksOnly text is a summary. Re-verify wording before quoting. hookprobe hash/JSON from README only. Whether /hooks lists managed hooks not confirmed.
