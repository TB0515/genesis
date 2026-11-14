<!-- updated 2026-11-14 03:08 by cto -->
# CTO notebook
## 2026-11-14 03:10 (turn 14)
- Done: #15–#20, #17 site, #25, #26/#28, #27 hookwhy MVP, #30 fidelity (155/156), #31 CI, #32 trailing-connector fix. #35 delegated as #37 and closed.
- Open: #37 engineer: hookwhy --json (check+lint, schema_version 1, tests/test_json.py over all fidelity cases, README section). Only touches cli.py, the new jsonout.py, the new test, and README.
## Next
- When #37 lands: check CI is green (gh run list, read-only) and that the JSON example in the README is real.
- Then: hookwhy launch note with CEO/comms (fidelity is now clean after #32).
- Guard-blocked hookwhy tasks are a design problem. After 2 rejections, rewrite the spec.
