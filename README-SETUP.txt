JON'S CONTRACT RADAR — 102 NAMED SOURCE TARGETS

INSTALL:
1. Unzip this package.
2. In github.com/friedt1/Jon-s-contract-radar upload/replace scan.py in the repository root.
3. Upload sources.json in the same root directory.
4. Commit changes.
5. Actions > Automatic Contract Radar Scanner > Run workflow.
6. Open the website after the workflow succeeds.

WHAT IT DOES:
- Searches public indexed news for procurement-related mentions of EACH of the 102 named organizations.
- Also checks 13 configured public website pages directly for relevant bid links.
- Runs on the existing six-hour schedule.
- Keeps SAM.gov deferred.
- Reports individual source failures in source_status.

IMPORTANT LIMITATIONS:
- The 89 targets without verified direct procurement URLs are INDIRECT DISCOVERY SEARCHES, not direct website crawls.
- Some sites require logins, JS rendering, or bid portals and cannot be reliably scanned by this lightweight scanner.
- Results may be incomplete, irrelevant, expired, or outside the 2-hour radius; confirm on the original posting.
- Search providers can rate-limit requests, which will be reported as errors.
- This package is syntax-checked but requires a live GitHub Actions run to validate network access.
