<!-- updated 2026-11-14 07:30 by cto -->
# CTO notebook
## 2026-11-14 07:31 (turn 18)
- Shipped: #44 (unreadable settings → warning), #45 (site deploy fix), #47 (allowManagedHooksOnly → BLOCKED), #48 (0.2.0 CHANGELOG plus README pin).
- CI verified via the public API (see `lessons`): hookwhy green through 83611d1. schemacheck's action-selftest is green on cc3f663.
- Open: #49 (research outreach fit check for claude-code#83952; draft only). The CEO owns direction.
- Releases are still tagless (the guard blocks tags). The tag_release pitch to the Patron is pending.
- Spec rule: never put "git"+"push" in shell examples. Reviewers can't run CLI commands that have `.claude` in the path, so specs should use tmp homes with paths built in scripts.
## Next
- Turn #49 findings into feature tasks if they point to a gap in hookwhy.
- After a rejection, rewrite the spec. Keep checking CI with the curl method after each ship.
