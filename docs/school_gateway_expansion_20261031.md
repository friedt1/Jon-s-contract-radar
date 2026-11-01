# School publisher gateways: verification and activation blockers (2026-10-31)

These are **official entrypoints**, not monitored bid feeds. The scanner must
not extract individual opportunities from them without permission checks and a
tested publisher-approved notice index. All four remain `discovery_pending`,
with `url=""` and `verified_url=false`.

| Named source | Verified publisher page | Evidence and limitation |
| --- | --- | --- |
| Horseheads Central School District | https://www.horseheadsdistrict.com/ | Official district homepage. The district's October 7, 2026 custodial-supplies notice (https://classifieds.gannettclassifieds.com/marketplace/elm/advert/HORSEHEADS-CENTRAL-SCHOOL-DISTRICT-HORSEHEADS-NEW-YORK-NOTICE-TO-BIDDERS-Retail_1487289) required contacting its Purchasing Department and closed October 13. This is **not** a tree-work contract or a public individual-bid feed. |
| Binghamton City School District | https://www.binghamtonschools.org/ | District homepage independently linked by the City of Binghamton school directory (https://www.binghamton-ny.gov/community/education/binghamton-city-school-district). Do **not** substitute the City of Binghamton's separate Bids & RFPs page. A reported district site-work capital-outlay solicitation closed April 24, 2026; it is not a live tree bid. |
| Watkins Glen Central School District | https://www.wgcsd.org/page/business-office | District's own Business Office & School Budget Information page; identifies operations staff but does not expose a verified current individual-bid index. |
| Bath Central School District | https://www.bathcsd.org/page/business-office | District's own Business Office page; accounting and budget information, not a public current bid index. Historical capital-project documents may be hosted by third-party planrooms with registration/payment. |

## Required before direct activation

1. Find the district's current official legal notice index, approved cooperative
   purchaser, or publisher-authorized planroom.
2. Check publisher robots/terms, rate limits, registration and automated
   access permissions. Never bypass login, paywalls, or robots restrictions.
3. Implement per-notice extraction with stable bid ID, actual issuing entity,
   local worksite, scope, submission cutoff **date and time**, amendments,
   and current publisher status. Distinguish tree/vegetation work from
   separately reviewed related site-prep.
4. Test against actual individual notices and negative synthetic fixtures.
   Expired Erie tree/stump and unrelated Owego demolition remain exclusions.
5. Only then promote a source to an implemented direct adapter; a reachable
   homepage or a legal advertisement alone is not operational monitoring.

## Audited counts after staging

102 named sources; 18 configured direct URLs; 84 without direct integration;
62 staged official URLs; 22 still lacking a verified official entrypoint.
No opportunity records were added. The published scan timestamp was preserved,
not represented as a new scan.
