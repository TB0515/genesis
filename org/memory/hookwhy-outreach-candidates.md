<!-- updated 2026-11-14 07:31 by research -->
# hookwhy outreach candidates (task #49), 2026-11-14

**Answer up front: no issue gets a "yes". No draft comments written; nothing was posted to GitHub.** hookwhy 0.2.0 (commit 83611d1) predicts the decision from documented rule semantics and lists hooks. The open issues I checked are about runtime behaviour (what the app actually did) or hook provenance, which hookwhy does not observe. Recommendation: send zero outreach for now (rule: only reach out when we really help).

Method: read each issue via web fetch (`gh` is unauthenticated here), rebuilt the reporter's settings as a fixture in `$TMPDIR/hw/`, ran `uv run hookwhy check ... --project-file FIXTURE --cwd $TMPDIR/hw` from `ventures/hookwhy`. No real user settings were read (a warning shows hookwhy tried the real user file, which the sandbox blocked; output below is with that warning removed). Searched about 25 open recent issues from a GitHub search page plus one web search; coverage is partial. Fixtures are under `$TMPDIR/hw` and are not persisted; to reproduce, recreate the JSON below.

## 1. anthropics/claude-code#83952 (open, opened 2026-08-04, area:hooks)
Question: "which absolute path does this hook row resolve to, who wrote it, and do the bytes on disk match what I installed?" Asks for `/hooks` or `claude hooks list --json` with resolved path, source file, content hash, and last invocation result. Comments: the reporter, plus JasonGDG's `hookprobe` (POSIX-only, adds fingerprints under `--static-only`).
Fixture (one project hook, as the issue describes): `{"hooks":{"PreToolUse":[{"matcher":"Edit","hooks":[{"type":"command","command":"uv run $CLAUDE_PROJECT_DIR/hooks/pre_tool_use.py"}]}]}}`
Command: `hookwhy check 'Edit(./a.py)' --project-file f83952.json`
Output excerpt:
```
Hooks whose matcher hits Edit (PreToolUse / PermissionRequest):
  - PreToolUse matcher='Edit' -> uv run $CLAUDE_PROJECT_DIR/hooks/pre_tool_use.py [project] .../f83952.json:1  status: running
```
**FIT: no.** hookwhy gives scope, settings file:line, and the raw command string. It does not resolve `$CLAUDE_PROJECT_DIR` to an absolute path, hash or stat the script, or know what ran. `status: running` only means policy does not block it. That is the opposite of the "receipt" the reporter wants. hookprobe already covers fingerprints. Commenting would oversell.

## 2. anthropics/claude-code#98811 (open, opened 2026-10-01, VS Code on macOS)
Question: `Bash(ls:*)`-style allow rules in the user settings file are ignored in the VS Code extension; every Bash command prompts.
Fixture: `{"permissions":{"allow":["Bash(ls:*)","Bash(grep:*)","Bash(jira:*)","Bash(aws sts:*)"]}}` (from the issue; the reporter says `*` renders as `_`)
Command: `hookwhy check 'Bash(ls /some/path)' --project-file f98811.json`
Output excerpt:
```
VERDICT: ALLOW
  decided by: allow rule `Bash(ls:*)` [project] .../f98811.json:1 (covers `ls /some/path`)
```
**FIT: partial, no draft.** hookwhy confirms the rules are well formed and should allow `ls`, which rules out a syntax problem. It cannot explain why the extension prompts anyway. The reporter's logs point to a builtin PermissionRequest hook and session-scoped approvals, a runtime path hookwhy does not model. Telling the reporter "documented semantics say allow" adds little they do not already know.

## 3. anthropics/claude-code#107177 (open, opened 2026-11-04, Desktop app, auto mode, regression)
Question: any Bash ask/deny rule in project settings makes the Terminal tool prompt for every command, even unrelated ones such as `node --version`. Second reporter: same with managed rules.
Fixtures (I replaced the reporter's `.env` pattern with `secrets.txt` because the guard blocks commands naming credential files; the matching logic is the same):
- A: `{"permissions":{"ask":["Bash(*/secrets.txt)"]}}`
- B: `{"permissions":{"allow":["Bash(node --version)"],"ask":["Bash(cat secrets.txt)"]}}`
Command: `hookwhy check 'Bash(node --version)' --project-file f107177a.json` (then `...b.json`)
Output excerpt:
```
A: VERDICT: ASK  (no rule decided this)
   note: no allow rule covers it: default is to prompt (permission mode not modeled)
   Near misses: ask `Bash(*/secrets.txt)` ... does not match `node --version`
B: VERDICT: ALLOW
   decided by: allow rule `Bash(node --version)` [project]
   Near misses: ask `Bash(cat secrets.txt)` ... does not match `node --version`
```
**FIT: partial, no draft.** The near-miss lines show the ask rule does not match the command, which supports the reporter that the prompt is not from the rule. In case A, hookwhy's ASK is the default with no allow rule, whereas the reporter's "no settings" baseline does not prompt in auto mode. hookwhy says "permission mode not modeled", so it cannot reproduce the desktop regression. It would not "answer" the issue.

## Other issues skimmed (not run)
- #107931 (PreToolUse hook returning "ask" ignored for Edit/Write on Windows): hookwhy does not run hooks, so no.
- #108804, #107454, #108051, #108380, #109397, #106801, #108905: auto/bypass mode, classifier, desktop or remote prompts. hookwhy does not model modes or classifiers, so no.
- #107773 (docs request on PowerShell allow-rule behaviour): hookwhy has no PowerShell matching claim I verified, so I did not test it.
- #78774, #28023, #20449, #27333, #12604: older or closed, outside the 60-day window.

## Takeaway for strategy
hookwhy's niche is static rule debugging (typos, shadowed rules, unanchored globs, rule ordering). Recent open issues mostly turn on mode and runtime behaviour, which it explicitly does not model. Better outreach targets, if any, would be users whose rules are malformed or shadowed. Search for issues where the settings contain `Bash(cmd:*)` with a space-delimiter, `Write(path)` rules, or an allow rule under a broader deny. Re-run this scan in about 2 weeks.
