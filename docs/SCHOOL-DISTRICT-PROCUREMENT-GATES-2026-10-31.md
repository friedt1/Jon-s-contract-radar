# School district procurement-source evidence — 2026-10-31

This note records verified **official publisher entrypoints**, not a live bid feed,
an authorization to crawl, or an actionable tree-service solicitation.
No `sources.json` source is promoted by this research. The 102-source
inventory and its operational coverage counts remain unchanged.

## Elmira City School District

- Official district Business Office: https://www.elmiracityschools.com/o/ecs/page/business-office
- Official district homepage: https://www.elmiracityschools.com/
- The Business Office is the publisher's official contact route, but the
  inspected page did not expose a stable, publicly accessible list of
  individual bid notices, bid documents, amendments, and submission cutoffs.
- **Blocker:** identify the district's actual public bid publication method
  (district procurement page, legal notices, GST BOCES, or authorized feed),
  verify robots and publisher terms, and test permitted individual-notice
  extraction before changing `discovery_pending` or claiming monitoring.

## Horseheads Central School District

- Official district homepage: https://www.horseheadsdistrict.com/
- The district site identifies the issuer, but the inspected homepage does
  not establish a public, machine-readable individual-bid feed.
- A secondary local bid directory says some district procurement is conducted
  through GST BOCES. This is a **lead for further publisher verification**,
  not evidence that a specific school solicitation is open or that the
  directory may be treated as an official procurement source.
- **Blocker:** obtain an official public bid index or a publisher-approved
  channel; verify permissions, notice-level scope, authoritative deadline,
  amendments and worksite. No generic district homepage should be counted
  as direct individual-listing monitoring.

## Regression relevance

- A demolition/site-preparation notice that merely mentions protecting
  existing trees or vegetation is not a tree-service or substantive
  grading/clearing contract. `test_demolition_scope_gate.py` prevents it
  from entering the live candidate feed as related site prep.
- Demolition accompanied by actual grading, excavation, clearing or grubbing
  remains separately classified as **Related site prep**, not tree removal.
- Historical Erie tree/stump expiration and Owego demolition exclusions
  remain tested. No historical or synthetic fixture is inserted into
  `data/opportunities.json`.

## Activation gate for both sources

1. Publisher confirms an official current bid-notice route and permitted
   automated retrieval; verify robots and terms without bypass.
2. Parse each individual notice and addenda, not the general homepage.
3. Verify service scope, current submission deadline and local worksite.
4. Add offline regression fixtures and hosted GitHub Actions checks.
5. Only then update the configured mode and published coverage diagnostics.
