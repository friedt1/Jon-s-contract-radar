# Town of Union, NY — official bid index review (2026-10-31)

Source identity: `Town of Union NY` (one of the existing 102 named targets).

## Publisher evidence

- The [Town of Union official homepage](https://www.townofunion.com/) links under **Government → Public Hearings & Notices → Bid Opportunities** to its [official bid index](https://www.townofunion.com/government/public_notices/bid_opportunities.php).
- The publicly visible bid index contains item-level titles and opening/closing columns, but the visible deadlines are historical (2023–2024; newest visible closing date April 30, 2024, with other entries ending May 28, 2024). A stale index cannot establish that the municipality has no newer bids elsewhere.
- Attempting to retrieve the linked **North Arthur Ave** individual PDF from the official index returned HTTP **403** during the October 31 review. That result is an access blocker for the sample document, **not** permission to circumvent access controls or evidence that all individual documents are blocked.
- No current tree-service bid, live status, worksite, or submission cutoff was independently verified.

## Safe configuration

The source retains `mode: discovery_pending`, `url: ""`, and `verified_url: false`. The official bid index is recorded in `candidate_official_url` with a separate activation gate. This is **staged**, not direct monitoring. No notice was manually seeded and no archived bid was promoted.

## Activation requirements

1. Review publisher robots and terms; confirm permitted public access to an individual-notice interface (do not bypass HTTP 403).
2. Implement bounded, source-specific extraction of individual notice links and attached documents, with stable identity and distinct bid/addendum/result classifications.
3. Verify a current notice's actual submission deadline **and time**, amendments, status, scope, worksite, and geographic fit. The Town's 2023–2024 archive is not a current bid feed.
4. Add offline extraction tests and production-scan evidence before changing `mode` to `direct_page`.
5. Preserve Erie expired tree/stump and Owego unrelated demolition exclusions.

## Adjacent reliability correction

A separately configured provider-delegated source can have an old `direct blocked by robots policy` diagnostic. `source_health.classify` now keeps **access_required** as the primary source state when provider approval is mandatory; the raw robots diagnostic remains available. A non-delegated source continues to classify as `robots_blocked`. This prevents stale diagnostics from implying that changing robots access alone would activate a provider integration.
