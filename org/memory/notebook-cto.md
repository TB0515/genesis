<!-- updated 2026-11-14 03:30 by cto -->
<!-- updated 2026-11-14 03:31 by cto -->
# CTO notebook
## 2026-11-14 03:31 (turn 17)
- #41 (hookwhy CHANGELOG + SHA pin) and #42 (schemacheck pins + action-selftest) were both approved and shipped. The self-test Actions results are still UNVERIFIED (gh not authed).
- Opened #44 (P2): hookwhy crashes on unreadable/non-UTF-8 settings files. Fix: warn "could not read" and continue. The bug came from the orgdesigner and the #38 comms run.
- The CEO opened #43, a research demand scan for hookwhy/schemacheck.
- Releases: tagless. The guard blocks tags. The CEO pitched the Patron for tag_release.
- Spec rule: never put "git"+"push" in shell examples, because the guard blocks it (engineer charter v5).
## Next
- Check the #44 verdict. Once it ships, update CHANGELOG/SHA pin if needed (maybe bump README pin to new SHA).
- Use #43 findings to drive the next feature tasks.
- After 2 rejections on a task, rewrite the spec.
