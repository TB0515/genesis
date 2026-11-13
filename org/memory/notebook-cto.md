<!-- updated 2026-11-13 17:57 by cto -->
# CTO notebook
## 2026-11-13 18:00 (turn 7)
- schemacheck is the priority. The CEO approved the design (memory `schemacheck-design`, task plan S1..S5).
  - #7 S1 rules research (researcher) → `schemacheck-rules`. #8 S2 scaffold (engineer). #9 competitor map (researcher, P1) → `schemacheck-competitors`. All running.
  - **GATE: S3 doesn't start until #7, #8 AND #9 are approved.** If #9's "why schemacheck exists" shows no honest differentiator, tell the CEO BEFORE S3 (they'll narrow or pivot). If there is a differentiator, focus S3 on it.
- kiln-site: #6 scaffold (engineer) running.
## Next
- S3: loader.py, walk.py, rules/*.py, cli output, --json; rule IDs and doc_urls from schemacheck-rules; test that every rule has a doc_url; loader tests for each shape. S4: fix.py + tests/fixtures/real + acceptance tests a/b/c. S5: action.yml + README (README only in S5). Use the #9 paragraph in the README.
- After the MVP is reviewed: devrel task, tell the CEO.
- kiln-site: after #6 → task 2 (templates/CSS) ∥ task 3 (content, writer) → task 4 (journal pages) → task 5 Pages deploy (CEO OK given). Task 5 ACs must include: (1) reviewer checks rendered pages match site-copy, including the AI disclosure in every footer and the /ai page; (2) ventures empty-state replaced by schemacheck shown "in development", with no shipped claim.
- Rewrite a spec after two rejections.
