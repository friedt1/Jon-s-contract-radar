# Jon's Tree Service Contract Radar

Static dashboard and best-effort ten-minute scheduled public procurement discovery for tree removal, trimming, land clearing, forestry mulching, vegetation work, and storm cleanup near Elmira, NY, including northern Pennsylvania. SAM.gov remains deferred.

Use the existing checkout; cloud tasks are already isolated. Python 3.12+ uses only the standard library. `pdftotext` (Poppler) enables public PDF attachment extraction. Node.js runs the dependency-free dashboard regression test. No database, API key, application server, or package installation is required with the prepared cloud snapshot.

```sh
cd /workspace/Jon-s-contract-radar
python -m unittest discover -s . -p 'test_*.py' -v
node test_website.js
python validate_output.py
# Requires outbound access to the configured procurement sites and Google News:
python scan.py
python validate_output.py
```

The website still reads `data/opportunities.json`. `data/history.json` retains discoveries separately; historical entries are never automatically reintroduced into the current feed. Five previously published invalid results were removed by offline revalidation and preserved in history, without pretending a fresh live scan occurred.

All 102 named targets are configured for indirect discovery, but the shared news/RSS provider can be unavailable; an indirect search is not individual-bid monitoring. As of November 2, 2026, 18 sources have direct-page configurations, while 84 remain staged and **are not directly monitored**. Direct configuration does not prove permitted retrieval or individual-bid extraction. The scanner performs bounded HTML/list/table/detail/PDF checks only where access checks permit them; delegated supplier portals require approved access and are not bypassed. The published `data/opportunities.json` source-health counts distinguish configured pages, successful fetches, individual details, incomplete extraction, and access failures. Statewide/platform and broad corporate/utility news searches require local place evidence.

Filtering rejects explicit closed/awarded/canceled notices, labeled deadlines before today's date in America/New_York, old/undated/future news, archive/result/recording links, and generic site-preparation/grounds-maintenance/right-of-way-vacation noise. Each listing record keeps its own scope and deadline. Same-day closing times, extensions, unlabeled dates, exact job location, agency eligibility, and actual driving times remain unverified. Local place names and target organizations are a conservative geographic screen, not a routing calculation. A news mention or unknown deadline never establishes an open solicitation.

`.github/workflows/scan.yml` is the authoritative workflow. Pull requests and relevant main pushes run offline Python 3.12/3.13 and dashboard tests without write permission. Scheduled runs and manual runs on main test first, install Poppler, scan, validate all 102 source statuses, and commit both output and history. Complete network failure fails the run and preserves the previous files. Partial failures are reported per source. Repository Actions must permit scanner commits. Existing website hosting is preserved; this change does not change Pages configuration or publish a deployment.

See [validation and integration limitations](docs/VALIDATION.md). GitHub Actions runs offline regression tests on pull requests and best-effort scheduled scans on `main`. Check the actual workflow results and the timestamped feed for current extraction evidence; never infer that all 102 sources or any listed candidate is verified open. Merge only after applicable checks pass.

## Local Customer Lead Radar

[Local Leads](local-leads.html) is a separate public customer-request dashboard for tree removal, trimming, stump grinding, storm cleanup and land clearing near Elmira and northern PA. It has service/customer/state/score filters, source links, discovery dates, deduplication, relevance ranking, and discovery history. Public request candidates and general news have separate labels and filters; no private groups, search histories, or invented contacts are used.

Run `python local_scan.py` and `python validate_local_output.py` for local discoveries. Run `node test_local_website.js` alongside the original validation commands. The separate Local Leads workflow scans every six hours after merge. Public Mastodon hashtag coverage is limited, optional reviewed public RSS feeds are supported, and news is context only. Actual two-hour driving time and request availability require confirmation. Live access is currently blocked in this cloud environment; the initial feed is honestly marked not run. See [sources, configuration, scoring, tests and limitations](docs/LOCAL-LEADS.md).
