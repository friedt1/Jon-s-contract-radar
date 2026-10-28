# PennBid integration — source audit and safe rollout

PennBid is **already listed** in `sources.json` as a direct-page target. This does not establish that individual bids are being ingested: the site may render results with JavaScript or require authorized vendor access.

Run `python source_audit.py` to see actual configured target count, unique hosts, and pending discovery targets. Do not report 102 targets as 102 websites.

Next steps:
1. Identify official public agency bid pages that link to PennBid notices, and verify access terms. Use those public agency pages as independent discovery sources.
2. Collect actual individual solicitation URLs, scope, issuing agency, location, submission deadline, and source timestamp; record errors separately. Never bypass logins, rate limits, or CAPTCHA.
3. Test extraction against a real public PennBid notice such as Erie bid 6565-26, without labeling it open after its deadline.
4. Keep every extracted notice **unverified** until the original bid documents and current status are checked.
5. Only classify local within 2 hours and regional within 12 hours after verifying driving time from Elmira to the work site; do not infer travel time from state alone.
6. Add fixture-based tests, then a permission-compliant live smoke test before enabling publishing.

No live PennBid ingestion is asserted by this change.
