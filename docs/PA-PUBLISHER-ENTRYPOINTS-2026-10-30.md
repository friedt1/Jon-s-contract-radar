# Pennsylvania county publisher-entrypoint review — 2026-10-30

This is **publisher identity evidence**, not permission to scrape, not a
verified procurement index, and not an activated individual-notice adapter.

| Named target | Verified official publisher entrypoint | Limitation / activation gate |
| --- | --- | --- |
| Tioga County PA | https://www.tiogacountypa.us/departments/commissioners | Official county commissioners page (118 Main St, Wellsboro). No comprehensive current solicitation listing or per-notice feed was verified. A historical third-party flood-debris advertisement had a **2025-10-03** submission deadline and is not a live lead. |
| Potter County PA | https://www.pottercountypa.gov/ | Official county homepage. The site hosts historical RFP-related materials, but a central current individual-solicitation index and automation permission were not verified. |
| Wyoming County PA | https://wyomingcountypa.gov/ | Official county homepage. It publishes county notices, but a complete individual-bid index and permitted automated extraction were not verified. |

These three source records remain `discovery_pending`, with empty `url`
and `verified_url: false`. Their `candidate_official_url` points to an
official publisher **entrypoint only**; `official_page_role` makes that
limitation machine-readable. Do not treat a reachable homepage or a
historical third-party listing as an active bid feed.

Before activation, establish the publisher's actual current bid channel,
terms/robots permission and retrieval frequency; prove stable individual
notice IDs, scopes, worksite locations, deadlines and amendments; and add
source-specific mocked and live acceptance tests. If a provider login or
contract is required, classify it as `access_required`, not fetched.

## Provider access diagnostics

Tompkins County Purchasing delegates current solicitations to BidNet Direct,
and the named PennBid and BidNet platforms have no approved individual-notice
integration. The source-health summary now retains the access-required count
even when a scan has no diagnostic status or a provider's robots policy blocks
retrieval. This prevents stale or missing scan output from inflating the
configured direct-fetch count. It does **not** change the number of working
individual-notice extractors.

## Regression and safety

Offline tests ensure the three new official entrypoints are staged only, never
directly fetched by the scanner, and do not add opportunities. The expired Erie
tree/stump example and unrelated Owego demolition example remain excluded from
live tree-service candidates. No fabricated bids, credentials, provider bypass,
or auto-promotion were introduced.
