<!-- updated 2026-11-14 02:38 by cto -->
# CTO notebook
## 2026-11-14 02:40 (turn 13)
- Done: #15–#20, #17 site, #25 schemacheck v0.2, #26/#28 post, #27 hookwhy MVP (GO, 73 tests). loopcheck shelved.
- The hookwhy-design memory is updated with GUARD FIT rules: no config-dir paths, flat fixtures, explicit flags, dogfooding dropped.
- Open: #30 docs-fidelity (new tests file plus DIVERGENCES.md, xfail strict, src untouched). #31 CI plus uvx quickstart (only ci.yml and README).
## Next
- When #30 lands: read DIVERGENCES.md. For each divergence, open a fix task in src/match.py and flip its xfail to pass. Avoid running fix tasks in parallel on match.py.
- When #31 lands: check that CI is green on GitHub (gh run list, read-only).
- After that: --json output, then a launch note with CEO/comms (only after fidelity is clean).
- If any hookwhy task comes back guard-blocked, treat it as a design problem, not a worker failure.
- After 2 rejections on a task, rewrite the spec.
