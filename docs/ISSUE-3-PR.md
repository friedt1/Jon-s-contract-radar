Relates to #3. Draft: source-expansion acceptance is blocked on environment outbound access and publisher terms review; this PR does not close the issue.

Adds evidence snippets, explicit heuristic confidence/verification state, duplicate keys and limitations to local discoveries. New metrics distinguish inspected/rejected records, deduplicated request candidates, articles, verified requests and qualified leads. Adds stale-feed warnings, current-display expiry, full history retention, stricter intent/error-page filtering and RSS robots rate handling.

Local publishing now scans into isolated staging and uses bounded non-force push/rebase retries with conflict aborts and staged-path protection. Production Contract Radar code, its 102 source definitions, workflow, dashboard and published JSON are unchanged. No deployment, paid sources, private data or new secrets.

Validation: 61 Python tests passed (original 27 contract + 22 local + 8 quality + 4 real Git race tests); both Node dashboard suites and both artifact validators passed. Chromium verified both pages at 390px/1280px without page errors or horizontal overflow. Workflow YAML parsed. Full local live scan failed safely on all seven endpoints due proxy 403; published files and seeded history were preserved. Hosted Actions unrun.

Jarvis review: docs/ISSUE-3-TEST-REPORT.md contains detailed results, reproduction, limitations and remaining acceptance checks; docs/LOCAL-SOURCE-REVIEW.md records source inventory/admission decisions; docs/LOCAL-RUNBOOK.md covers zero-results diagnosis and recovery. New-source admission and multiple real post examples remain unverified, so no new integration or real customer lead is claimed. Review/save and publish the saved environment access draft before retrying live validation.
