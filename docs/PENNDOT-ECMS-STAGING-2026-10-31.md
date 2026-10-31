# PennDOT District 4 — ECMS publisher review (2026-10-31)

## Verified official entrypoint

The Commonwealth of Pennsylvania Department of General Services [Find Opportunities](https://www.pa.gov/agencies/dgs/doing-business-with-the-commonwealth/business-inclusion-and-supplier-development/finding-opportunities) directs highway and bridge construction vendors to PennDOT's Engineering and Construction Management System (ECMS). The [official ECMS landing page](https://www.ecmssyst.penndot.pa.gov/ECMS/) describes construction projects, construction contracts and consultant agreements and offers guest entry and business-partner registration. This establishes an official **statewide procurement gateway**, not an authorized individual-notice extraction interface or a District 4-only feed.

The existing named target **PennDOT District 4** is retained, with `candidate_official_url` set to the ECMS landing page. `mode` remains `discovery_pending`, `url` remains empty and `verified_url` remains false. Do not count this target as direct monitoring or as evidence of any open tree-service contract.

## Activation blockers

1. Confirm ECMS robots/terms and permission for automated public guest extraction; do not bypass login or registration.
2. Identify a stable, permitted individual-notice list and document endpoint, with source-specific extraction tests and explicit notice identity.
3. Filter the actual **project worksite**, not just the PennDOT district or issuing office, to northern Pennsylvania and approximately two hours from Elmira; keep the separate longer-distance queue explicit.
4. Extract publisher-backed tree/stump, vegetation, clearing or separately labeled site-prep scope. Reject unrelated roadway work, demolition and generic statewide postings.
5. Verify current publisher status, submission cutoff (not merely opening/question dates), amendments and document accessibility before any live classification.
6. Run hosted Python 3.12/3.13, dashboard and Local Customer Lead Radar checks; probe live access only when permitted.

The historical Erie tree/stump example must stay expired; Owego demolition must remain unrelated. Neither example is a live seed. No contracts or private credentials were added.

## Public-host safety

The same change set tightens source and notice URL syntax validation against numeric IPv4 resolver aliases such as `0x7f.0.0.1`. This is only a **syntax guard**. It does not prove DNS resolution is public or protect against every DNS rebinding scenario; network fetchers must continue to enforce redirect, host and authorization checks.
