# Remaining two official entrypoints — 2026-11-01

Evidence checked 2026-11-01 (UTC). These are **official publisher/vendor pages**, not proof of permission to crawl individual notices or of an active bid.

## SUNY Corning Community College
- Official trustee/policies index: https://www.corning-cc.edu/rbot/index.php
- Current official policy manual: https://www.corning-cc.edu/about/regional-board-of-trustees/ccc-policy-manual-april26.pdf
- The college's policy describes competitive sealed bids, Finance Office coordination and newspaper advertisements. This does **not** establish a public individual-bid API, RSS feed, or continuously updated bid listing.
- Inventory: `discovery_pending`, `candidate_official_url` staged; `url` empty, `verified_url=false`. Do not fetch the trustee page as an operational contract feed.
- Activation: find a college-authorized current solicitation listing or obtain purchasing permission, review robots/terms, then test individual notice identity, scope, deadline, publisher status and local worksite.

## Wegmans regional properties
- Official supplier gateway: https://www.wegmans.com/service/for-our-suppliers
- The page offers supplier onboarding, buyer contacts and construction/non-construction contract terms. It does **not** advertise an anonymous current facilities/tree-maintenance RFP feed.
- Inventory: `discovery_pending`, `candidate_official_url` staged, `provider_access_required=true`; no direct fetch.
- Activation: obtain Wegmans facilities/procurement invitation or a separately authorized public per-notice listing. Confirm local worksite and scope before accepting any candidate.

## Honest coverage
- Total named sources: 102
- Directly configured: 18 (not all authorized fetch targets)
- Not directly monitored: 84
- Official URLs staged for pending targets: 84
- Pending targets without an official URL: 0
- New individual-notice adapters or verified open contracts created by this change: **0**

A URL discovery milestone is not the same as monitoring coverage. The current major blocker remains permitted individual-notice extraction and provider authorization, particularly for the local municipal and county publishers. The historical Erie tree/stump and unrelated Owego demolition examples remain regression-only and must never be seeded into the live feed.
