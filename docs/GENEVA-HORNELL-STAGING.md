# Geneva and Hornell official bid-page staging (October 30, 2026)

These are **staged candidates only**. Neither source has been activated for
direct monitoring, and no bid has been inserted into the live feed.

## City of Geneva, New York

- Official procurement entry point: https://cityofgenevany.gov/Bids.aspx
- The city-hosted CivicPlus **Bid Postings** page was publicly readable in the
  October 30 research check. It stated **"There are no open bid postings at
  this time."** This is a statement about that listing, not proof that all
  procurement channels are empty.
- Added the city to the *staged* CivicPlus bidID-format probe registry.
  A later real probe must check robots rules, publisher terms, and public
  individual-notice extraction if listings appear.
- No active tree-service solicitation was established.

## City of Hornell, New York

- Official procurement entry point:
  https://www.cityofhornell.gov/upcoming-bid-projects
- The official **Upcoming Bid Projects** page contained procurement PDF links
  hosted at `irp.cdn-website.com`, plus a link for past bid projects.
  Visible entries included vehicle purchases and an intermunicipal RFQ;
  none was verified as an open tree-removal or clearing contract.
- A new staged diagnostic identifies **off-host PDF hosts** on procurement
  pages, without downloading documents or assuming CDN authorization.
  A same-host HTML listing is not equivalent to approved per-document access.
- Required before activation: publisher and CDN terms/robots review, a
  permitted bounded document adapter, current-versus-past record isolation,
  individual deadlines/status, service scope, and worksite/travel checks.

## Regression and boundaries

`test_city_official_staging.py` covers the 102-source inventory, both
staged URLs, Geneva's empty-listing diagnostic, Hornell's off-host PDF
diagnostic, provider-access precedence, and non-procurement PDF pages.
All fixtures are synthetic; they do **not** assert that any live solicitation
is open. The scanner must never fetch third-party documents merely because
an official government page links to them. Erie tree/stump and Owego
demolition remain historical regression cases, not seeded leads.
