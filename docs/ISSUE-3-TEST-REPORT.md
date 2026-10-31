# Issue #3 — test report for Jarvis

Status: offline implementation validated; source-expansion acceptance remains blocked. Do not mark issue #3 complete or merge on the strength of synthetic tests. Review the [source inventory](LOCAL-SOURCE-REVIEW.md) and [runbook](LOCAL-RUNBOOK.md).

Base: `2cb4835e27a91e19ebe0b4bcae7e64c4f33008b6` on main. Branch: `dev/issue-3-local-lead-quality`. Verification ran October 28, 2026 (America/New_York). Python 3.12.14, Node v24.19.0, system Chromium and Poppler. CI continues to use Python 3.12 and Node 22; existing contract CI includes Python 3.13. Hosted CI and Python 3.13 were not executed here.

## GitHub-hosted regression verification (October 28, 2026)

After the initial Codex-environment report below, the draft PR was updated to reject seller-style "I recommend" statements and to prevent a later news article from reviving or downgrading a historical customer request. Three focused offline regression tests cover these cases.

At commit `bede2092ef0c34574685adaed96606233eb6ea6d`, GitHub-hosted **Local Customer Lead Radar** run `40688438882` completed successfully: **69 Python tests passed**, both Node dashboard test suites passed, and both published-feed validators passed. GitHub-hosted **Automatic Contract Radar Scanner** run `40688438821` also completed successfully with Python 3.12 and 3.13 test jobs. Both PR-triggered scan/publish jobs were **skipped as designed**; no live scan or deployment was performed by these checks.

**Acceptance still blocked:** no newly permitted direct-request source, no independently verified live customer examples, and no confirmed qualified local jobs. The PR remains a draft; hosted test success does not establish lawful new-source access or live usefulness. The historical test counts and environment limitations below describe the earlier Codex run, not the newer hosted verification.

## Changes under review

- Evidence snippet, stable duplicate key, explicit heuristic confidence, verification state and limitations accompany every new discovery. Existing original timestamp, first/last seen, source permalinks, service/location and customer type remain.
- Rejection categories and per-source checked-at/inspected/request/article counts explain empty scans. Deduplicated totals distinguish request candidates, news, verified requests (zero) and qualified leads (zero). Automated inference never becomes human verification.
- Additional negative-intent/seller filters, HTML-login response rejection, and reviewed RSS robots crawl-delay/request-rate handling. Local operator source configurations can be checked with matching scanner/validator `--sources` options.
- Complete history retention replaces automatic 2,000-entry truncation. Expiry and failed sources cannot purge history. Dashboard suppresses posts older than 30 days and warns when scans are over 12 hours old.
- Local workflow scans and validates in a staging directory before copying generated data. Publishing restricts staged paths and retries non-force push/rebase up to three times, aborting conflicts. Contract scanner/workflow, contract dashboard, 102 source definitions and all published JSON remain unchanged.
- Source inventory and admission decisions, zero-results diagnosis, recovery procedures, and honest unresolved live evidence.

## Results

| Check | Result / scope |
| --- | --- |
| `python -m unittest discover -s . -p 'test_*.py' -v` | **61 passed**, no skipped/expected failures. All original 27 contract tests and 22 local tests retained, plus 8 quality and 4 real Git publication tests. Includes real PDF extraction. |
| Quality tests | Evidence/verification fields, negative need and seller wording, zero-result rejection accounting, article/request separation, HTML error rejection, 2,005 historical records retained across partial failure/expiry, robots limits, schema-v2 artifacts and tampered verification metrics rejected. |
| Publication integration | Actual temporary bare Git remote, two clones and a pre-push race hook. Normal/repeated publish passes; concurrent contract update and local scan both survive; conflicting local update fails without remote overwrite; unrelated staged files refused. No network or production Git mutations in these tests. |
| `node test_website.js` | Contract feed/filter/search/count/escaping regression passed. |
| `node test_local_website.js` | Request/news separation, service/customer/state/score/search/history, escaping, unsafe links, empty/failed feeds, deterministic stale scan and expired-post suppression passed. |
| Both artifact validators | Passed against unchanged published files: 0 contract results / 102 statuses; 0 local results / 7 statuses. Published local feed is legacy schema and legitimately lacks new metrics. V2 output validated separately using synthetic data in a temporary directory. |
| Chromium functional smoke | Both pages served over local HTTP; assets and JSON loaded. At 390px and 1280px: no page errors or horizontal overflow. Local history/current switching and metrics rendered. Empty production data only; populated evidence tested by Node, not claimed live-browser verified. Incidental favicon 404 does not affect either app. |
| Workflow YAML | Both files parsed with PyYAML; workflow contents-read permissions retained, local scan alone has job contents-write; PR scan/publish gate remains disabled. Actual hosted schedule/manual execution unrun. |
| `git diff --check` | Passed. No public data artifacts changed, no new dependencies or secret files added. |

## Live attempts and blockers

`git ls-remote origin HEAD` succeeded through platform HTTPS authentication. GitHub GraphQL and REST issue reads failed `Forbidden`; the full public issue page was retrieved successfully from github.com. No token was requested or extracted.

Real probes for Mastodon Elmira timeline, Google News RSS, Reddit Ithaca RSS/robots/terms, Craigslist robots, and Freecycle terms all failed with proxy tunnel **403 Forbidden**. A complete `python local_scan.py --data-dir /tmp/issue3-live` attempted all seven configured endpoints sequentially, exited **1**, and reported seven URLError source failures. Seeded temporary history remained byte-for-byte identical; no current feed was produced; repository artifacts were untouched. This is environment policy denial, not proof of provider outage or zero customer demand.

Required domains and reusable `start_skill` were saved to the environment draft. No installation script is necessary: pinned workflow tools and installed standard-library runtimes suffice. Draft saving does not apply policy or publish a snapshot. Environment settings must be reviewed/saved and published before repeating blocked probes. No source was newly admitted on the basis of an unread terms page.

## Required Jarvis review before completion

1. Apply permitted outbound access; rerun the isolated live workflow and retain exact source counts/errors.
2. Complete new-source terms/API admission and obtain multiple actual public post examples as specified in the source review. Source expansion is **not delivered** until those checks support at least one lawful useful integration. No new sources or real leads are claimed here.
3. Review filters for precision/recall on those real examples; evaluate homeowner/commercial classification and geographic false positives. Town evidence and relevance score do not establish job site, drive time, availability or qualification.
4. Review PR and hosted checks; manually dispatch only after human merge approval. No automatic merge, deployment, paid services, private data or source-rule bypass is authorized by this report.

Known limits: bounded hashtag coverage, heuristic intent/geography, conservative cross-post merging, no human-verification persistence, increasing history size, atomic replacement per JSON file rather than a two-file transaction. CI validates the pair before publishing. A conflicting local publish intentionally fails and needs a fresh scan.

## Delivery state

Implementation commit `c985213` was pushed successfully to `origin/dev/issue-3-local-lead-quality`. `gh pr create --draft` was attempted with main as base and this development branch as head; GitHub GraphQL returned `Forbidden`. No PR creation is confirmed. The exact prepared description is saved in `docs/ISSUE-3-PR.md`; submit it when API access is available. The pushed branch can also be selected in GitHub's ordinary New pull request flow. Issue #3 remains open; there was no merge or production deployment.
