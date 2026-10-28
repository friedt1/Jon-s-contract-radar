# Local radar operating runbook

Use the existing isolated checkout at `/workspace/Jon-s-contract-radar`; do not create a worktree. Python 3.12+, Node and Git suffice for offline work; Poppler exercises the existing contract PDF tests. No pip/npm dependency, API key, or database is needed.

## Reproduce and scan safely

```sh
cd /workspace/Jon-s-contract-radar
python -m unittest discover -s . -p 'test_*.py' -v
node test_website.js
node test_local_website.js
python validate_output.py
python validate_local_output.py
mkdir -p /tmp/local-radar-review
cp data/local_history.json /tmp/local-radar-review/local_history.json
python local_scan.py --data-dir /tmp/local-radar-review
python validate_local_output.py --data-dir /tmp/local-radar-review
```

Use a unique scratch directory for each independent live attempt and seed it from the current history. Do not replace published files for a connectivity experiment. No-source success exits nonzero before writing either file. Corrupt history fails closed. Per-file replacement is atomic; pair consistency is validated before CI copies/stages it. A local interruption between replacements requires rerunning and validating; files are not a transactional database.

For an authorized RSS/Atom publisher, prepare a source configuration outside the checkout, retaining existing entries if desired. Each additional entry needs `name`, `kind: "rss"`, public HTTPS `url`, and `public_feed_reviewed: true` **only after terms/permission review**. Keep the permission decision and review date in the review report. Run both scanner and validator with `--sources /path/to/reviewed-sources.json`. Do not enable Reddit/Facebook/Nextdoor using this flag. Robots failures, redirects, non-feed HTML, disallow rules, or crawl delays over 60 seconds stop that source. Public feeds require no cookies or login. Respect explicit publisher API limits; never add retries to overcome denials.

## Diagnose zero results

1. Read `updated` and each `checked_at`: the dashboard warns after 12 hours. An old successful scan does not establish current source health. Posts older than 30 days disappear from current display even if automation stalls; history remains visible as history.
2. Read `request_sources_ok` and `failed_sources`. All failures preserve previous artifacts and fail Actions. If request sources are configured and all fail, news-only success now fails the scan before publication and preserves the previous feed/history. An intentional news-only configuration may still produce context records, but never verified requests. Error type/HTTP code is stored without response bodies or secrets. Check Actions logs for all-source failures; the website deliberately retains its last successful feed and shows its age.
3. Examine `records_inspected` and per-source `rejected`: `undated`, `expired_or_future`, `unsafe_permalink`, `outside_or_unknown_location`, `no_service_match`, `advertising_or_closed`, `article_or_discussion`. Counts cover bounded original public records processed, not an entire platform, boosts or private posts. A malformed source contributes no partial results or counters.
4. Compare deduplicated `request_candidates` with `news_context`. Per-source counts can include cross-post duplicates; totals deduplicate. `verified_requests` and `qualified_leads` stay zero: there is no human-verification store. Never convert relevance score into a verification claim.
5. Inspect source samples and terms before expanding. Zero requests in six hashtag feeds can mean low coverage; do not weaken location/date/intent filters or relabel articles to manufacture leads. Approximate town matches never verify a two-hour drive.

## Publishing and recovery

Local workflow: offline Python tests, both dashboard tests, both artifact validators, isolated live staging, generated artifact validation, then publication of **only** the two local JSON files. PRs cannot scan or publish. Scheduled scans and manual dispatch on main use job-scoped contents-write permission. Production Contract Radar scanner, sources, website, data and hosting remain unchanged by this PR.

`scripts/publish-local.sh` commits generated local outputs and attempts push up to three times. On a race it rebases to preserve concurrent contract/source/code changes; conflicting local results abort rather than overwrite newer remote output. No force push. A conflict or repeated network/authorization failure fails the job: inspect the remote latest state, rerun the scan, and review its counts. Never resolve by deleting history or replacing contract artifacts. The script is for the clean disposable CI checkout only, not an arbitrary dirty development checkout.

History has no automatic 2,000-entry truncation now; posts expire only from the current feed. Monitor artifact size as adoption grows. Archive/migrate history deliberately in a reviewed change if necessary. Source failures never delete history.

## Current access blockers

The October 28 cloud environment denies Mastodon, Google News, Reddit, Craigslist and Freecycle research destinations at the outbound proxy. Git read works, while `api.github.com` is denied. Required domain additions are saved as an environment draft; saving is not application/publication. Review and save environment settings, then publish and rerun the isolated live scan and source-admission review. Do not supply tokens in chat or bypass the proxy. Hosted Actions and new-task snapshot restoration require separate verification after publishing.
