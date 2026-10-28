# Public opportunity review queue

This is a **manual research queue**, not verified leads or an automated source integration. Never publish private contact details. Check each original notice and its closing date before outreach. Do not scrape these pages without a separate terms/robots/access review.

| Publisher | Official page | Type | Evidence / caveat | Status |
|---|---|---|---|---|
| Chemung County / City of Elmira | https://chemungcountyny.gov/Bids.aspx | Public procurement | Official public bid notices; current listed bids are not verified tree-work opportunities. County offers email/text notifications. | Review only |
| Steuben County | https://www.steubencountyny.gov/Bids.aspx | Public procurement | Official bid list; evaluate individual scopes and dates. | Review only |
| Chemung purchasing | https://chemungcountyny.gov/439/Sealed-Bid-Information | Vendor access | Free search-only registration is described; matching service may be paid. Do not purchase. | Review only |

## Qualification checklist

- [ ] Original public permalink and publisher verified
- [ ] Posting date and deadline confirmed on official page
- [ ] Tree removal, trimming, storm cleanup, stump grinding or hauling explicitly requested
- [ ] Job location and approximately two-hour Elmira service radius manually checked; never claim routed time without routing
- [ ] Buyer type and bid eligibility confirmed
- [ ] Terms, robots and syndication permission reviewed before any automated polling
- [ ] Duplicate checked against existing contract and local lead history
- [ ] Contact details limited to officially published procurement channels

**Metrics:** 3 discovery resources; 0 verified tree-work requests; 0 qualified leads; 0 new automated sources. Government procurement belongs in the contract review workflow, not homeowner-request counts. Existing scanners and published data are unchanged.


## Verified historical procurement — **not an open lead**

- **Steuben County PW-26-018-B, Tree Services:** [official one-page award summary](https://steubencountyny.gov/ArchiveCenter/ViewFile/Item/2757) confirms a November 20, 2025 bid date, December 1, 2025 Public Works Committee award, and contract period **January 1, 2026 through December 31, 2028**. Scope includes tree cutting at county locations and emergency callouts requiring a response within two hours. Beers Tree Service and Terry Tree Service are listed with 2026–2028 pricing. The PDF says the winning selection is shaded; do **not** infer which firm won from text-only extraction.
- **Classification:** historical awarded contract, **closed to bidding**, **zero current opportunities**. Retain as a concrete example for detecting awarded notices and tracking the likely future rebid cycle; do not imply that renewal/rebid timing or subcontracting is available without an official new notice.
- **Automation lesson:** A tree-work keyword match on an archive page is insufficient. Require the original bid date, award/closure status, deadline, and job location before adding anything to a live opportunities feed. Award summaries should enter a separate market-intelligence archive, not the open-bid count.

## October 28 source discovery — no automatic admission

- [Elmira Next regional bid directory](https://elmiranext.com/bids) publishes a regional bid index and explicitly links an RSS feed at `https://elmiranext.com/bids/feed.xml`. Its website identifies itself as an independent aggregator, **not** the purchasing authority. A web retrieval attempt returned an unsupported RSS content-type, not verified parsed feed records. No automated access/republishing permission has been established. **Candidate for publisher permission review only**, not a live source.
- [Chemung County purchasing calendar](https://chemungcountyny.gov/calendar.aspx?CID=25) and [official roof replacement notice RFB-2925](https://www.chemungcountyny.gov/bids.aspx?bidID=93) demonstrate official dated bid records. The roof bid closes October 29, 2026 and is **not** a verified tree-service contract; do not inflate lead counts.
- [Chemung official purchasing information](https://chemungcountyny.gov/439/Sealed-Bid-Information) states free search-only access is available, with optional paid matching. No paid account is needed for manual review.

**Admission gate:** Confirm RSS permission/terms and robots, inspect actual entries and their original government permalinks, verify timestamps and tree-work relevance, then implement a bounded parser in a separate tested change. Do not feed procurement bids into homeowner counts. Avoid scraping the aggregator HTML or bypassing access controls.

**Metrics unchanged:** 0 verified tree-work requests, 0 qualified leads, 0 new automated integrations.
