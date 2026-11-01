# Shared indirect RSS provider diagnostics — October 31, 2026

## Observed production failure

The published scan at 2026-11-01 01:06:26 UTC reported `indirect RSS error: RobotsDenied` for all **102** named targets. The indirect query for every target goes to the **same** host, Google News RSS; these errors do **not** establish that 102 counties, school districts, utilities, or procurement publishers blocked their own public bids.

The same published feed reported 18 configured direct sources, 11 successful direct listing fetches, 12 retrieved individual bid details from four sources, 33 deferred detail candidates, 575 PDF budget skips, and **zero verified open contracts**. These are observations from that specific scan, not new opportunities.

## Change

* Construct each source's exact indirect RSS search URL once and check it against the shared provider's robots policy **before** requesting its feed. The robots-policy module caches the provider origin; each per-query check still honors URL-specific rules.
* When Google News denies the URL or its policy is unavailable, skip the prohibited request and record `indirect RSS provider unavailable (Google News): <reason>`. Never misattribute that refusal to the named source.
* Continue permitted direct bid scans independently. A Google News failure must not suppress CivicPlus or other official source extraction.
* Expose `indirect_provider_unavailable_targets` in source coverage and source-health diagnostics; retain the legacy `indirect_robots_blocked` metric only for older per-target error strings.
* Preserve all 102 names, existing activation gates, the Erie tree/stump and Owego demolition negative regressions, and the unverified/expired filters.

## Limits and next gates

This is a **diagnostic and efficiency fix**, not an expansion of individual-bid integrations. It does not grant Google News access, promote any of the 84 pending sources, or create live contracts. The 62 staged official entrypoints still require publisher permission and individual-notice extraction verification. Next: review Cortland, Seneca, Livingston and City of Binghamton notice adapters and terms; independently confirm any actionable deadline, scope and worksite.

Validation: run Python 3.12/3.13 unit tests, dashboard tests, feed validators and GitHub Actions on the PR. Merge only after passing checks.
