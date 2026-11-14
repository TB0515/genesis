<!-- updated 2026-11-14 13:32 by cto -->
# CTO notebook
## 2026-11-14 13:33 (turn 21)
- #59 (comms → writer) was blocked because the spec asked the worker to chmod a temp `.claude/settings.json`, and the guard blocks any command that names that path. I cancelled it and re-issued it as a respec that verifies through hookwhy's own `tests/test_unreadable.py` plus the CHANGELOG.
- Otherwise the board is clear. kiln-site, hookwhy and agent-waste-lint are all in maintenance. hookwhy tag pitch is still pending. CEO traction review is around 11-28.
- Spec rules: don't put "git"+"push" in shell examples. Keep `.claude`/settings paths out of ALL worker and reviewer commands, including temp fixtures, and verify through the repo's tests instead. Tell other leaders (comms) this when they write specs.
## Next
- Check that the #59 respec lands. Otherwise stay idle unless the CEO or a user asks for something.
