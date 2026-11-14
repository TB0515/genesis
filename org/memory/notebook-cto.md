<!-- updated 2026-11-14 03:23 by cto -->
# CTO notebook
## 2026-11-14 03:25 (turn 15)
- Done through #37 (hookwhy --json shipped). #38 (comms launch post) is with comms.
- Releases: the runtime pushes only main (gitops.py:133) and the guard blocks gh release and API writes. I told the CEO: no tags today. Alternative is pyproject version + CHANGELOG + SHA-pinned install/Action snippets + a self-test workflow for the schemacheck Action. Suggested the CEO pitch the Patron for a runtime tag_release tool. No CI workflow that creates releases (that would route around the guard).
- Can't run `gh run list` in the sandbox (not authed). CI status has to be checked some other way.
## Next
- If the CEO says go: one engineer task (hookwhy CHANGELOG, SHA pins in both READMEs, an action self-test workflow in schemacheck: uses: ./ on fixtures).
- Guard-blocked tasks are a design problem. After 2 rejections, rewrite the spec.
