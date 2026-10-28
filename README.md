# Jon's Tree Service Contract Radar

Static dashboard and six-hour public procurement discovery for tree removal, trimming, land clearing, forestry mulching, vegetation work, and storm cleanup near Elmira, NY, including northern Pennsylvania. SAM.gov remains deferred.

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

All 102 named targets retain news discovery. The 13 configured direct pages also receive bounded public HTML/list/table/detail/PDF extraction, including linked procurement portals. The remaining 89 targets are indirect discovery only. Query overrides remove administrative labels from the first 13 news queries. Statewide/platform and broad corporate/utility news searches require local place evidence.

Filtering rejects explicit closed/awarded/canceled notices, labeled deadlines before today's date in America/New_York, old/undated/future news, archive/result/recording links, and generic site-preparation/grounds-maintenance/right-of-way-vacation noise. Each listing record keeps its own scope and deadline. Same-day closing times, extensions, unlabeled dates, exact job location, agency eligibility, and actual driving times remain unverified. Local place names and target organizations are a conservative geographic screen, not a routing calculation. A news mention or unknown deadline never establishes an open solicitation.

`.github/workflows/scan.yml` is the authoritative workflow. Pull requests and relevant main pushes run offline Python 3.12/3.13 and dashboard tests without write permission. Scheduled runs and manual runs on main test first, install Poppler, scan, validate all 102 source statuses, and commit both output and history. Complete network failure fails the run and preserves the previous files. Partial failures are reported per source. Repository Actions must permit scanner commits. Existing website hosting is preserved; this change does not change Pages configuration or publish a deployment.

See [validation and integration limitations](docs/VALIDATION.md). Live procurement extraction and hosted Actions execution must still be verified after network access is enabled. Do not merge until reviewed.
