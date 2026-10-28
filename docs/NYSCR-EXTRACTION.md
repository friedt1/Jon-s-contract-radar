# NYSCR individual notice extraction (Issue #12)

NYSCR exposes a public-looking list at `https://www.nyscr.ny.gov/Ads/IframeSearch` showing contract titles, CR numbers, agencies and deadlines. Its website also describes registration and terms governing access. **Do not activate scheduled retrieval of this service before obtaining explicit authorized automated access and confirming usage terms.** A publicly viewable page is not automatically a permitted bulk feed.

`nyscr_extract.py` safely parses **text supplied through an authorized export** into separately identified contract research records. It does not fetch, authenticate, follow links, generate individual notice URLs, or silently publish leads. `promotable` requires original HTTPS detail URL and independently confirmed active status, deadline, location and authorized access. These are candidates only: the listing itself cannot prove eligibility or a two-hour/12-hour driving radius.

Next: obtain an approved listing/API or export mechanism, inspect original posting URLs, add location/routing verification and deterministic feed hand-off. Only then enable the connector in scheduled workflow. BidNet and PennBid require separate permission review and adapters. No purported live NYSCR records or traffic are introduced by this PR.

Run `python -m unittest test_nyscr_extract -v`.
