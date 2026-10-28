# Local Customer Lead Radar

Local Leads is a separate static page (`local-leads.html`), scanner (`local_scan.py`), source list, feed, history, and GitHub workflow. The only contract-dashboard change is a navigation link. The existing scanner, its 102 targets, feed/history, regression tests, validator, and schedule are unchanged.

## Development

Use the existing checkout; cloud tasks are already isolated. Python 3.12+ and Node 22+ are sufficient; there are no additional packages, API keys, or database. Poppler remains useful for the original contract scanner.

```sh
cd /workspace/Jon-s-contract-radar
python -m unittest discover -s . -p 'test_*.py' -v
node test_website.js
node test_local_website.js
python validate_output.py
python validate_local_output.py
python -m http.server 8000 --bind 127.0.0.1
```

When outbound access is available, run a local scan and then validate its artifacts:

```sh
python local_scan.py
python validate_local_output.py
# Or preserve the published artifacts while checking live access:
python local_scan.py --data-dir /tmp/local-radar-live-check
python validate_local_output.py --data-dir /tmp/local-radar-live-check
```

The six-hour workflow at `.github/workflows/local-leads.yml` runs at minute 20 UTC. It tests before scanning and writes only `data/local_leads.json` and `data/local_history.json`. Scheduled execution starts on the default branch after merge; manual scans are restricted to main. Actions must be enabled and allowed to commit repository contents. No deployment or Pages configuration is changed. Normal existing static hosting must include the new page, CSS, JS and data files. Hosted execution and deployment have not been verified here.

## Sources and access

The default customer-request integrations are six anonymous, public Mastodon hashtag timelines on `mastodon.social`: Elmira, Southern Tier, Finger Lakes, northern PA, Ithaca, and Corning. Only explicitly public, original posts are processed; private, followers-only, unlisted, and boosted posts are excluded. One request per endpoint, at most 40 posts each, sequential with a one-second pause; there is no pagination or automatic retry. The scanner uses the documented public API, no login, search-history data, or private groups. Respect provider terms and stop using an endpoint if access is refused; anonymous availability and useful request volume are not guaranteed.

Google News RSS searches nearby towns and all five services, but is **always news context**, even if a headline contains request wording. It is not a customer-request integration. Linked pages are never crawled. This intentionally limited source set cannot cover all homeowners or commercial requests, or Facebook/Nextdoor/Craigslist. No specific live lead or request volume is promised.

To add an RSS/Atom community feed, first review that publisher's terms and confirm it is a public feed the operator may use. Add an entry to `local_sources.json` with a unique `name`, `kind: "rss"`, its public HTTPS `url`, and `public_feed_reviewed: true`. Do not set that flag without reviewing the publisher. Robots must be successfully retrieved and permit the feed; access failures and redirects fail closed. Do not add private feeds, authentication, paywall bypasses, Facebook, Nextdoor, or Reddit. Add the hostname through environment settings if needed. Configuration is operator-controlled; no website visitor can submit arbitrary fetch URLs.

All remote fetches require HTTPS, reject user-info URLs and literal private IPs, refuse redirects, use TLS verification, and have a 20-second timeout and 1 MB size limit. They use inherited proxy and trust settings. Denied destinations are reported rather than bypassed. The public social API returns data directly; article/post destination URLs are displayed as links only. No customer contact fields are manufactured or enriched. Incidental email/phone strings are redacted from copied text; follow the original source to contact the poster.

## Eligibility and scoring

Posts must be dated within 30 days, mention a supported service and a town in the conservative local list. Ambiguous towns such as Athens, Corning and Mansfield require NY/PA state evidence. Unrelated state/country evidence is excluded. The town list covers the Southern Tier and northern Pennsylvania around Elmira, including Wellsboro, Towanda and Williamsport. This is an approximate service-area screen, **not a verified road travel calculation**. The exact job site and actual two-hour driving time must be confirmed. Some eligible nearby locations will be missed.

Customer requests require explicit seeking/need/recommendation/quote language. Obvious advertising, hiring, sale, fulfilled-request and news phrasing is excluded. Homeowner/commercial classification requires explicit property wording; otherwise the customer is unspecified. These are heuristics: requests can be misclassified and need manual verification. A public request candidate is not proof of authenticity or current availability. No news article is labeled as a real customer request.

Score: request-language base 65 (news base 10), publication within seven days +15 (otherwise +5), explicit customer type +10, and +5 per matched service up to +10. Maximum 100. News stays below 50. Score reasons are displayed. Service, result type, customer type, state, minimum score, text search, discovery history, and ordering are available independently.

## Deduplication and history

HTTPS URLs are normalized, fragments and tracking parameters removed. Identical normalized URLs merge; matching normalized title, town, and publication day merges conservative cross-post duplicates. Source links are retained. Different wording/dates may remain separate; unrelated requests with identical short text/town/day could merge. No fuzzy match claims certainty.

IDs and first-discovered dates persist across scans, even if a rediscovered post changes title. Last-observed time updates on each successful discovery. Up to 2,000 historical entries are retained, newest observation first. History is not reintroduced into the current feed and is explicitly marked as possibly inactive. No lead lifecycle/CRM status is inferred. All-source failure exits nonzero and preserves both prior files. Partial failures are shown per source; news-only success explicitly reports that request coverage is unknown. Corrupt history fails instead of silently being erased. JSON file replacement is atomic per file; CI validates matching run timestamps before committing the pair.

## Verification in this task

Base: `e7526497d8e1dd29feeab0adcb73d9143eedda1f`, matching fetched origin/main on October 28, 2026. Local branch: `feature/local-customer-lead-radar`.

- Python 3.12.14: 49 tests passed, including the original 27 contract-scanner tests and real PDF extraction. New tests cover request/news distinction, all five services, NY/PA evidence, stale/future dates, ads/closed requests, contact redaction, source rules, RSS/Atom, visibility, deduplication, history, failures and CLI output isolation.
- Both Node dashboard regression scripts passed. They exercise filtering, source counts, request/news labels, history, failed/empty feeds, HTML escaping and unsafe links.
- Both artifact validators passed. The published local artifacts intentionally contain no leads and `updated: null` (not run). No synthetic customer appears on the website.
- Both workflow YAML files parsed successfully. HTTP responses for both dashboards, local JS/CSS and all three relevant feeds returned 200 with valid JSON.
- System Chromium exercised both dashboards, cross-page navigation and the history control at 390px width: no JavaScript errors or horizontal overflow. Browser rendering with populated live sources remains unverified.
- An actual local scanner run against all seven endpoints failed because this environment's enforced outbound policy denied Mastodon and Google News. The scan failed safely and did not alter published files. This is an environment access blocker, not proof the providers are unavailable. Live source compatibility and real request discovery remain unverified.

Required domain additions were saved to the environment draft, including `mastodon.social`, `news.google.com`, `api.github.com`, and the existing contract scanner's direct hosts. Saving is separate from applying/publishing. Review and save the environment settings, then publish the environment and rerun the live commands. No extra credential has been requested: Git HTTPS authentication works, while API access is currently policy-denied. Never paste tokens in chat.
