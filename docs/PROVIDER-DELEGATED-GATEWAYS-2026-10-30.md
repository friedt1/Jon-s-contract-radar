# Official provider delegation audit — October 30, 2026

**Scope:** Three existing configured direct pages, not three new sources. All 102 named source identities remain unchanged. These pages are official purchasing *gateways*, not verified individual-bid feeds.

| Registry identity | Publisher evidence | Current authoritative listing route | Scanner classification |
| --- | --- | --- | --- |
| Schuyler County purchasing | https://www.schuylercountyny.gov/174/Purchasing — County says vendors can register with Empire State Purchasing Group/BidNet to view all available bids and RFPs. | BidNet Direct; provider-approved individual-listing access not established. | `access_required`; skip county gateway's generic links |
| Elmira City bids | https://www.cityofelmirany.gov/264/Sealed-Bid-Information — City says joint Chemung County/City Purchasing posts bid packages, addenda, tabulations and awards to BidNet. | BidNet Direct; registration/provider-approved extraction not connected. | `access_required`; do not count City sealed-bid information page as a current individual feed |
| Lycoming County bids | https://lycomingcountypa.gov/government/departments/financial_management/bids.php — County explicitly says **all current open bid/proposal solicitations** are on PennBid. | PennBid; approved per-notice feed not connected. County's Municibid surplus auctions are unrelated. | `access_required`; skip generic county page |

## Implementation and accounting

- Preserve the original official URLs and `direct_page` configuration for traceability. Add `delegated_provider`, `provider_access_required: true`, and explicit `activation_gate` to each.
- Block direct page crawling through the existing `scan.run` access gate, while leaving the separate public indirect discovery path unchanged. This is **not** a bypass of provider terms, authentication, or robots policies.
- Keep the independent Chemung County CivicPlus `Bids.aspx` adapter intact. Its presence does not authorize reading the City of Elmira's BidNet notices.
- Coverage after change: **102 named**, **18 configured direct URLs**, **6 provider-access-required**, **12 configured direct fetch targets**, **40 staged official URLs**, **44 still needing discovery**, **84 without configured direct URLs**. These are configuration counts, not verified individual-notice monitoring.
- The previously published scan reported 14 fetched pages and 0 verified open tree-service contracts; this change must not be represented as an increase in operational coverage. The next successful production scan should show the three newly gated sources as access-required and should not attempt generic document extraction from those gateways.

## Activation requirements

1. Obtain explicit provider-approved individual-notice access (or identify a genuinely independent official public notice feed whose terms permit retrieval).
2. Implement and test per-notice identity, issuing agency, scope, worksite, current publisher status, deadline including time/timezone where stated, and addenda/amendments.
3. Recheck robots/terms and the source's actual live notice format. Do not infer a current contract from a gateway, archived award, or news item.
4. Require successful Python 3.12/3.13 scanner tests, staged-source tests, dashboard/local-lead tests, and a production scan before reporting operational coverage.
5. Preserve regression exclusions for expired Erie tree/stump removal and unrelated Owego demolition.

**Remaining blocker:** Provider-approved BidNet/PennBid individual listings are not connected. This PR intentionally creates no opportunities and does not activate a new feed.
