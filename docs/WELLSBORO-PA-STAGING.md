# Wellsboro Borough, PA — official bid listing staged (2026-10-30)

**Official issuer:** https://www.wellsboroborough.com/

**Official bid listing:** https://www.wellsboroborough.com/blank-12
(Linked from the issuer homepage as **Open Bids & Bid Packets**.)

On October 30, 2026, the borough's own bid-listing page displayed
**"No Current Open Bids."** This is an issuer-reported empty state for that
visible listing at the time checked. It does not prove that other procurement
channels have no opportunities or that the website exposes an authorized,
complete individual-notice feed.

The borough has previously published directly linked PDF solicitations for
**street-tree risk mitigation, pruning, removal, stump grinding** and mowing.
The official street-tree PDF sets a **November 21, 2025, 4:00 PM** bid
deadline, with work completion by April 1, 2026. That deadline is **expired**
as of October 30, 2026. These historical notices must never be presented
as live contracts or seeded into the opportunity feed.

Historical issuer documents (reference only; not open bids):
- https://www.wellsboroborough.com/images/REQUEST%20FOR%20BIDS%20-%20STATE%20%26%20BOROUGH%20ROUTES.pdf
- https://www.wellsboroborough.com/images/REQUEST%20FOR%20BIDS%20-%20MOWING%202026-2028.pdf

## Registry and diagnostics

The existing `Wellsboro Borough` target in `sources.json` now has
`candidate_official_url=https://www.wellsboroborough.com/blank-12`.
It remains `mode=discovery_pending`, `verified_url=false`, `url=""`.
No direct source or opportunity was activated. Total targets remain 102.

The staged probe reports `listing_reachable_no_open_bids_reported` only
when an unadapted official page explicitly says there are no current open
bids, does not expose a potential individual notice link, and does not
delegate bid access to a known external provider. It retains a scoped note
and never emits a bid. A possible PDF notice link overrides the empty
message and returns an adapter-required diagnostic. Provider access
requirements take precedence.

## Activation blockers

Before direct monitoring: check robots.txt and publisher terms for the
official listing and individual PDF URLs; identify permitted stable links
and any amended deadlines; implement and test a bounded listing-to-document
adapter; reject historical/awarded/closed bids; confirm scope, site location,
travel time from Elmira and subcontracting requirements. The current
explicit empty state provides no live individual notice on which to
validate that adapter. Do not infer a live contract from a 2025 PDF.

Offline regression tests: `test_wellsboro_staging.py`.
