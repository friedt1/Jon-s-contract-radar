# CivicPlus closing-field date/clock coverage — 2026-11-01

## Defect and scope
The general submission-deadline parser already accepted dash-separated US dates and
phrases such as `by 2:30 PM`. The CivicPlus-specific parser still accepted only
slash-separated US dates or ISO dates and a bare/`at` clock. As a result,
`Closes: 11-02-2026 by 2:30 PM` and
`Closing Date/Time: 11-02-2026 no later than 2:30 PM` lost their
closing-date/time evidence. This could leave an expired same-day bid eligible
for unverified review despite the actual individual notice cutoff.

## Change
- Parse explicit four-digit `MM-DD-YYYY` in CivicPlus **Closes** and
  **Closing Date/Time** fields; preserve slash and ISO date support.
- Recognize explicit `at`, `by`, `until`, and `no later than` clock
  prefixes immediately following a closing date.
- Never infer a clock from unlabeled `2:30`, a publication date, or a
  malformed calendar date.
- Keep individual-notice closing evidence authoritative over an older or
  inconsistent listing card. Preserve the conservative `unverified` status
  for pre-cutoff candidates.

## Evidence and constraints
`test_civicplus_dash_receipt_deadlines.py` uses synthetic HTML and checks
listing/detail parsing, the exact Eastern-time closing boundary, an
individual-notice cutoff earlier than the listing, existing slash/ISO
formats, and historical Erie tree/stump and unrelated Owego demolition
exclusions. These are **regression fixtures, not discovered bids**.

No changes to `sources.json`, provider permissions, robots checks,
request budgets, or the number of directly monitored agencies. A staged
CivicPlus URL is still **not** a verified permitted individual-contract feed.
The remaining 84 staged sources must be reviewed individually for publisher
permission and reliable notice extraction before activation.
