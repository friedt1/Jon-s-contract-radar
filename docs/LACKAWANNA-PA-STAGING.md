# Lackawanna County PA — official RFP/RFQ staging evidence

Verified on **2026-10-29** against the county's own public website:

- Official index: https://www.lackawannacounty.org/government/departments/rfp_rfq.php
- The page labels itself **RFP/RFQ**, lists separate description, opening, and closing date/time columns, and links to individual county bid-detail pages.
- The first three sampled county detail links (IDs `R255`, `R254`, and `R252`) returned **HTTP 404** during independent browser retrieval. This is a reproducible access/availability *observation*, not a determination that all detail links fail.
- The visible September 2026 listings were **past their deadlines** as of October 29. A listing link or historic closing date must not be treated as a currently open tree-service opportunity.

## Activation blockers

1. Review publisher terms and robots rules for automated listing and individual-detail requests.
2. Establish stable, permitted individual-detail retrieval. If bid detail pages remain inaccessible, report the exact blocked/fetch-error state rather than assuming content exists.
3. Implement a dedicated county table/list adapter that distinguishes **opening** from **closing** dates and does not mistake questions, site visits, or old notices for live solicitations.
4. Validate the actual worksite and driving time from Elmira. Lackawanna County's procurement office location is not necessarily the jobsite.
5. Verify live notice status, amendments, scope, and deadline before publishing as actionable.

The `sources.json` entry is intentionally `discovery_pending` with `verified_url: false`, an empty `url`, and only a `candidate_official_url`. It is **not directly monitored**. The 102 named-source invariant is unchanged, and no opportunity data is created or modified by this staging work.
