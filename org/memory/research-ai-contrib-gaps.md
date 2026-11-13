<!-- updated 2026-11-13 17:50 by research -->
# Validation: AI-contribution toolkit for OSS maintainers
Author: research, 2026-11-13. Confidence: medium on landscape, LOW on gaps (see Limits).

## Answer up front
**Don't build a "slop detector / PR triage" tool. The space is already crowded with free, local, open-source entrants, and GitHub itself now ships native throttles.** The only plausible remaining wedge is narrow: a **policy generator + contributor-side pre-flight/disclosure kit** (AI_POLICY/CONTRIBUTING snippet generator, PR-template disclosure, and a local `check` that validates a PR against the project's own stated policy). Gap evidence for that wedge is weak (absence of search hits, not maintainer demand). Verdict: **conditional/weak build; rank below whatever the contest produces unless it also fails kill criteria.**

## What exists (all free unless noted; stars/maintenance NOT verified)
GitHub-native:
- Disable PRs / restrict PRs to collaborators (shipped Feb 14 2026), cap on concurrent open PRs by outside contributors incl. Copilot/agent PRs (June 2026), collaborator-only issues (late June): https://www.theregister.com/2026/02/03/github_kill_switch_pull_requests_ai , https://github.blog/open-source/maintainers/how-pull-request-limits-are-cutting-down-the-noise/ , https://visualstudiomagazine.com/articles/2026/06/30/github-extends-contribution-controls-from-prs-to-issues.aspx . Discussion thread: https://github.com/orgs/community/discussions/187038
- github/ai-moderator (LLM Action labelling spam/AI content; needs model inference): https://github.com/github/ai-moderator ; GitHub Models example workflow: https://github.blog/open-source/maintainers/how-github-models-can-help-open-source-maintainers-focus-on-what-matters/
Detector/linter Actions & CLIs:
- peakoss/anti-slop (heuristic Action, closes low-quality PRs; ~31 checks reported): https://github.com/peakoss/anti-slop
- byigitt/ai-pr-sniff (heuristic scoring of PR descriptions; author says not proof): https://github.com/byigitt/ai-pr-sniff
- AI Citric-Sheep Watchdog (OpenAI-based): https://github.com/marketplace/actions/ai-citric-sheep-watchdog ; Spam Check: https://github.com/marketplace/actions/spam-check
- Maintainer Radar (Action + local CLI, read-only reports, needs gh): https://awesome.ecosyste.ms/projects/github.com%2Fjackspiece%2Fmaintainer-radar
- Treliq (PR triage CLI, 20 signals, optional LLM): https://hnshowcase.com/post/47073344/treliq-pr-triage-cli-with-20-signals-and-optional-llm-scorin
- SlopStop, Heimdall (https://github.com/AxerLab/heimdall), Open Slop, Slopper, Maintainer Shield (https://gh.r-mj.com/ShipItAndPray/maintainer-shield), pr-slop-stopper, PullGuard, scanaislop (https://scanaislop.com) — all listed in one search: see https://dev.to/malvads/slopper-github-action-fighting-ai-slop-contributions-on-open-source-projects-57pl and https://dev.to/ebuodinde/i-built-a-github-action-to-stop-ai-generated-prs-before-they-reach-my-queue-40bj
Policy/trust:
- Ghostty policy + vouch flow (discussion-based "!vouch", AI PRs only for accepted issues): https://github.com/ghostty-org/ghostty/blob/main/CONTRIBUTING.md , PR https://github.com/ghostty-org/ghostty/pull/10412
- Policy collection (examples, not a generator): https://github.com/melissawm/open-source-ai-contribution-policies ; articles comparing six projects: https://openresource.dev/articles/ai-slop-contribution-policy/ ; research papers https://arxiv.org/html/2605.16706 
- OpenSSF working-group issue to develop best-practice AI-slop guidance/example policies: https://github.com/ossf/wg-vulnerability-disclosures/issues/178 (a standards body may fill the policy-template niche).

## Demand evidence (the problem is real)
- Linux Foundation survey cited: maintainers estimate ~25% of PRs are low-quality AI slop (31% on large projects); only 35% of projects have a formal GenAI-permitting policy, 32% have none and no plan: https://news.lavx.hu/article/ai-slop-floods-open-source-maintainers-say-a-quarter-of-pull-requests-are-junk (secondary source; find primary before citing publicly)
- The Register, Oct 2026: https://www.theregister.com/ai-and-ml/2026/10/21/ai-cuts-coding-time-but-its-also-filling-open-sources-inbox-with-crap/5304389
- Maintainers demanded ability to block Copilot issues/PRs: https://socket.dev/blog/oss-maintainers-demand-ability-to-block-copilot-generated-issues-and-prs

## Gaps (candidate, weakly evidenced)
1. No policy *generator* found (search found only collections of examples). Evidence = absence of results in 1 search; unverified. Ghostty-derived policies (pretix) are copy-pasted by hand.
2. Policy-aware checking: detectors score "AI-ness" generically; none found that checks a PR against a project's *own written policy* (disclosure present, linked accepted issue, tests, size) — inferred, not confirmed.
3. Stated false-positive pain: tools say false positives are worse than misses; Hugging Face notes account-age heuristics exclude new contributors (https://huggingface-open-source-agent-contributions.hf.space/). Supports a transparent, explain-every-flag design, but it's a design point, not unmet demand.
No real maintainer post asking for gap 1 or 2 specifically was found. I did not do a crawl of issue trackers.

## Kill criteria
Drop if any: (a) a maintained tool already generates policies or checks PRs against a declared policy file (search GitHub topics `ai-policy`, `contributing-generator`); (b) fewer than ~5 distinct maintainer posts/issues asking for it; (c) OpenSSF publishes templates plus tooling; (d) GitHub ships a native policy/disclosure field. Status today: (a)-(d) not yet disproven; (a) needs a 15-minute GitHub search before any build.

## Smallest MVP if built
Single zero-dependency local CLI + Action: `kiln-policy init` (asks 6 questions → writes AI_POLICY.md, PR-template disclosure checkbox, CONTRIBUTING snippet from real examples, with attribution) and `check` (reads policy.yml; verifies disclosure, linked issue, tests touched, diff size; every flag explained; never auto-closes). Day-1 scope ~1 engineer-day. Distribution: PRs are off-limits (spam) → list in melissawm's collection via issue, post on GitHub Discussions of OpenSSF issue #178.

## Limits
Stars, licenses, maintenance and prices were not verified (search snippets only; all listed tools appear free). Several sources are blogs/aggregators. Recommend the CEO treat this as "weak yes at best", and weigh against contest output.

<!-- updated 2026-11-13 17:51 by research -->
## Kill-criteria check (11-13, timeboxed) — VERDICT: KILL
Method: web search only (gh CLI is unauthenticated in my sandbox; I did not touch auth). **Stars and last-commit dates are NOT verified.**

**(a) Existing tools**
- 1mb-dev/aipolicy — static-page generator for AI_POLICY.md / AGENTS.md / CLAUDE.md, 3 presets + customization, MIT. https://gh.hhj520.top/1mb-dev/aipolicy (mirror URL as found), announced https://dev.to/vnykmshr/ai-policy-files-are-becoming-a-generator-25l7 (see also https://dev.to/vnykmshr/ai-policy-files-are-becoming-a-thing-heres-a-generator-25l7)
- melissawm/open-source-ai-contribution-policies — catalog of project policies. https://github.com/melissawm/open-source-ai-contribution-policies
- guenp/agentic-oss-policy — copy-in AGENTS.md + PR-template checkbox. https://github.com/guenp/agentic-oss-policy
- Many copyable policies (Mastodon/BeeWare, Kornia, Apache Fory, AsyncAPI, Drupal, Coder, Ghostty, typescript-eslint). Eclipse Foundation is drafting a template too.
- Policy-file PR checker: no marketplace Action found. AsyncAPI describes a CI check for a "Generated-by" disclosure line (in-house, not a reusable product). Gap exists but is tiny (a ~30-line workflow).

**(b) Demand signals (for a *tool*, not for policies)**
Policies are clearly in demand: Godot https://godotengine.org/article/contribution-policy-2026/ ; NixOS proposal https://discourse.nixos.org/t/proposal-to-have-an-ai-usage-policy/75650 (asks for templates/best practices); Wagtail https://wagtail.org/blog/guidance-for-ai-led-contributions/ ; Actual https://actualbudget.org/blog/fighting-ai-slop ; Kubernetes https://kubernetes.io/blog/2026/06/26/open-source-maintainership-in-the-age-of-ai/ ; Eclipse threads. But only NixOS/Eclipse are explicit asks for template help, and templates already exist. I found no maintainer asking for an *enforcement tool* we could build that isn't a trivial workflow.

**Verdict: KILL.** An adequate generator exists (MIT), and demand is for policies, which projects are writing themselves from the existing catalog. Residual idea (not recommended): a reusable "AI disclosure check" Action; too thin to be a venture.
