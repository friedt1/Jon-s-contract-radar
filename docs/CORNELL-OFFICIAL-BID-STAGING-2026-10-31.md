# Cornell University construction-bid publisher review — 2026-10-31

Existing target: `Cornell University` (one of the 102 named sources).

## Official publisher evidence

- Cornell Facilities and Campus Services explicitly links its **Construction Bidding Opportunities** from its [For Contractors page](https://fcs.cornell.edu/departments/finance-administration/facilities-contracts/contractors) to the [official Projects out to Bid index](https://fcs.cornell.edu/projects-out-to-bid).
- The index was publicly readable during the October 31 review and linked to individual publisher pages under `/bid-projects/<slug>`, including [Replace Roofs - Various Buildings SUCF #161061](https://fcs.cornell.edu/bid-projects/replace-roofs-various-buildings-sucf-161061) and [Renovate Plant Science Building - Phase 2](https://fcs.cornell.edu/bid-projects/renovate-plant-science-building-phase-2).
- The roof notice identifies a **bid opening** of November 3, 2026 at 2:00 p.m.; the Plant Science notice lists a **bid opening** of November 10, 2026 at 2:00 p.m. These are **not** independently verified submission deadlines, and neither notice supplies tree removal, vegetation management, or site-prep scope. **Neither is a tree-service opportunity.**
- Cornell distinguishes **campus-funded** construction procurement through the **Trimble Unity** bidding portal from **state-funded** bids advertised via the **NYS Contract Reporter** and the official index. The Plant Science notice explicitly directs bidders to NYSCR for authoritative submission and project information. Do not scrape either provider without approval.
- Publisher robots/terms and the permitted automated-access scope for the official index and individual project pages **were not verified** in this review. Successful public viewing does not establish crawler authorization or an end-to-end live integration.

## Conservative repository changes

- Stage the verified official index as `candidate_official_url` with `mode: discovery_pending`, `url: ""`, and `verified_url: false`. This **does not activate monitoring** or change the count of configured direct sources.
- Recognize `/bid-projects/<slug>` as an individual-notice-shaped URL for future *authorized* extraction, while rejecting the index, PDF attachments, unrelated redirects, and award subpaths. URL shape is **not** proof of a bid, scope, open status, or permission.
- Add offline tests for source staging, counts, redirect identity, explicit submission-deadline separation, expired Erie tree/stump, and unrelated Owego demolition.
- No new opportunities, deadlines, or contracts were seeded or published.

## Activation blockers

1. Verify robots.txt and publisher terms, then document the exact permitted public retrieval scope.
2. Validate bounded extraction of individual project titles, project descriptions, amendments, bid receipt deadlines (not merely bid-opening or RFI times), and status using real publisher HTML in an authorized production probe.
3. Distinguish Cornell-managed campus-funded work from NYSCR/Trimble-dependent records; mark delegated provider links **access required** without bypassing them.
4. Require scope and worksite evidence, including the two-hour Elmira route review, before any relevant candidate is promoted.
5. Re-run Python 3.12/3.13, dashboard, and source-probe CI. Do not change the source to `direct_page` until all gates pass.

This review establishes one more **official staged source**, not one more live bid integration.
