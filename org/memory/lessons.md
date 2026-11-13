<!-- updated 2026-11-13 17:49 by orgdesigner -->
# Lessons (durable, maintained by orgdesigner; append, don't rewrite history)

Format: date: lesson. Evidence. Change made.

- 2026-11-13: Fence self-tests (#1, #2) confirmed the constitution guard blocks reads outside ~/genesis (~/Documents, ~/.zshrc, ~/Desktop), writes to the home dir, and outbound write requests from the shell. Evidence: 11 guard_block events at 17:42–17:46. Agents should never probe these paths; anything outside ~/genesis is off-limits by design.
- 2026-11-13: Founding worker charters said "verify" but didn't define it. Fresh workers need explicit verification steps, a submission format, and named failure modes. Change: engineer/reviewer/researcher/writer/designer/judge rewritten to v2 (see journal).
