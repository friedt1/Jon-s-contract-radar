JON'S CONTRACT RADAR — AUDITED RELIABILITY UPGRADE

IMPORTANT: This is an offline-tested upgrade, NOT a guarantee of live bid coverage.
It still has 13 directly configured pages and 89 indirect news-discovery targets.
Some direct sites may require login, JavaScript, or site-specific adapters.

FILES TO INSTALL IN YOUR EXISTING GITHUB REPOSITORY:
1. scan.py -> REPLACE existing root scan.py
2. .github/workflows/scan.yml -> REPLACE existing workflow file (copy included scan.yml there)
3. tests/test_scanner.py -> ADD new file in tests/ directory
Leave index.html and sources.json unchanged.

HOW TO INSTALL FROM GITHUB MOBILE:
Open github.com/friedt1/Jon-s-contract-radar, edit/upload each file, commit.
Then Actions > Automatic Contract Radar Scanner > Run workflow.
Check green workflow and data/opportunities.json, data/history.json.

WHAT CHANGED:
- More selective home-page lead detection to reduce navigation false positives.
- Bounded detail-page and PDF checks; poppler-utils installed in GitHub Actions.
- Preserves up to 1,000 discovered leads in data/history.json.
- GitHub Actions runs offline unit tests before scanning.
- Workflow concurrency and 20-minute timeout, data JSON validation.
- Fixed incorrect publication-date assignment across news items.

LIMITATIONS AND FUTURE UPGRADES:
- Indirect Google News searches do NOT monitor 89 procurement sites directly.
- Page fetch success does not mean bids were extracted. Login/JS sites need APIs/adapters.
- No reliable open/closed status, deadlines, geographic travel-time verification.
- No OCR for scanned PDFs, no pagination of bid tables, no structured PDF parsing.
- No cross-site deduplication of equivalent bids on different URLs.
- The dashboard shows only CURRENT leads, not the historical archive yet.
- GitHub Actions may be delayed; public websites can change or block scraping.
- Best next phase: per-portal adapters and source-level extraction tests, date/status
  parsing, dedupe, travel-time geocoding, and daily alerts for genuinely new bids.

LOCAL CHECKS COMPLETED: Python compilation and 7 offline unit tests.
LIVE GITHUB TEST: REQUIRED after installing; do not claim 102 direct integrations.
