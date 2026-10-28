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

## October 28 negative-control checks — relevant words are not enough

- **PA DCNR Tioga State Forest timber sale 16-2025BC04, Elk Township:** [official PA DCNR bid openings](https://iframeapps.dcnr.pa.gov/forestry/timbersales/bidsiframe.aspx) lists a November 4, 2026 opening for 1,176.3 MBF on Cedar Mountain and Mill Run Roads; [official Bid Express agency listing](https://www.bidexpress.com/businesses/102544/home) independently lists **16-2025BC04 Rock Some Mitchell** due November 4, 2026 at 17:00 UTC. This is a **stumpage sale where the bidder purchases timber**, not an agency paying a tree contractor for removals. It requires substantial buyer capital/qualification; **exclude from paid tree-service lead counts** even though it is local, open and tree-related. The official Bid Express listing says solicitations and notifications are free for this agency; it does not authorize automated harvesting of its site.
- **Chemung County RFB-2816, Tree and Stump Removal (2026–2027):** [official county bid detail](https://www.chemungcountyny.gov/bids.aspx?bidID=31) labels the contract **Awarded**, with the bid closing October 23, 2025. It is an actual local tree-work procurement but **not currently open**. Archive as historical market intelligence only.
- **Status distinction:** A procurement may be (a) currently open but a timber purchase, (b) relevant paid work but already awarded, or (c) an active paid service bid. Only (c), after original-notice verification and eligibility checks, can become a qualified contract lead.

**Metrics remain:** 0 newly verified open paid tree-service opportunities, 0 qualified leads, 0 new automated sources. These records are manual classification examples only.


## October 28 prime-contractor prospect — **not a confirmed subcontract opening**

- **PennDOT I-180, Lycoming County (October 22, 2026 update):** [official project progress notice](https://www.pa.gov/agencies/penndot/news-and-media/newsroom/district-3/2026/highway-improvement-project-continues-on-i-180-in-lycoming-count16) identifies Glenn O. Hawbaker as the **prime contractor** for a two-year, **$14 million total highway improvement** project spanning Williamsport, Loyalsock, Fairfield, and Montoursville. The described scope explicitly includes **tree removal**, but that figure is the *entire road project value*, **not** a tree-removal subcontract value. PennDOT expects completion in fall 2026.
- **Qualification:** Existing awarded prime contract; **no evidence that tree work remains unperformed or that a subcontract is available**. Preserve as *manual prime-contractor outreach research only* and exclude from open-bid and qualified-lead counts. Confirm actual work scope, current subcontract availability, and location before outreach; do not treat the media release as an invitation to bid. No driving time from Elmira was verified.
- **Classifier rule:** Government construction press releases can identify useful prime contractors and real tree-work scope, but are not solicitations. Keep a separate `prime_contractor_prospect` research category with `subcontract_opening_verified=false` until the prime or official procurement notice confirms an actual opening. Do not count total highway project value as tree-service revenue.

**Metrics remain unchanged:** 0 newly verified open paid tree-service opportunities, 0 qualified leads, 0 new automated sources.

## October 28 active-but-out-of-scope procurement control

- **Tioga County NY, 67 Central Avenue Demolition Project Rebid (Owego):** [official Tioga County Public Works notice](https://tiogacountyny.gov/departments/public-works/) describes demolition of a roughly 2,136-square-foot, two-story building, foundation removal, off-site demolition-debris disposal, and site restoration. The notice specifies a **mandatory prime-bidder walkthrough on October 29, 2026 at 9:00 a.m.** (previous walkthrough attendees may already satisfy it), written questions due **November 5 at noon**, and bids due **November 13, 2026 at 11:00 a.m.** The work is genuinely advertised and geographically nearby, but the published summary **does not establish tree removal, vegetation clearing, or a tree-service subcontract**. Do not count it as a tree-work lead or claim the tree-service business is eligible to prime the demolition job.
- **Classifier rule:** An active demolition/site-restoration bid containing words such as *clearing*, *removal* or *debris* is **not** automatically a tree/land-clearing contract. Require explicit vegetation/tree/brush scope in the original solicitation or a confirmed suitable subcontract before promotion to the actionable tree-contract feed. Preserve this as a negative-control example, not an opportunity.

**No change to qualified lead count:** 0 newly verified open paid tree-service opportunities; no production source or data changes.


## October 28 urgent open paid tree-work notice — Erie PA (regional, not local)

- **City of Erie, PA, bid 6565-26, Tree & Stump Removal at Various Locations.** A [reproduction of the October 19, 2026 public notice](https://www.noticeregistry.com/pennsylvania/notice/bid-notice-erie-2483271) identifies an actual paid removal solicitation, **October 29, 2026 at 2:00 p.m. prevailing Erie time** deadline, online submission through [PennBid](https://pennbid.bonfirehub.com/portal/?tab=openOpportunities), and **$2,500 bid security**. [Independent procurement summary](https://bidscopeai.com/opportunities/e81b5aba-429c-4aa7-b2ee-78d85e5c7a2d) corroborates solicitation ID, scope and deadline (its 18:00 timestamp appears to be UTC, corresponding to 2 p.m. EDT). The [City of Erie's official May 1, 2026 PennBid announcement](https://cms2.revize.com/revize/erie/Pennbid%20Program%20Bidding%20Opportunities.pdf?t=202605071244360) confirms its use of PennBid, no-cost vendor registration and documents, and that an award fee may apply. This is the **City of Erie**, not Erie County procurement.
- **Scope evidence:** The published descriptions explicitly identify tree and stump removal and pruning at multiple Erie locations, including itemized pricing and disposal/restoration. Verify the actual addenda, item list, insurance, equipment, and crew qualifications in the original PennBid package; third-party summaries may contain errors. Questions reportedly closed October 27.
- **Verification limitation:** The official PennBid portal uses JavaScript and its live project record and addenda could not be independently inspected with the available read-only research browser. Do **not** assert the original portal still accepts submissions or that the bidder meets every requirement. Verify bid 6565-26 directly in PennBid before committing bid security or pricing. No login bypass or automated extraction attempted.
- **Classification:** Real, time-sensitive **published paid-tree-service bid notice** supported by a reproduced public notice and a second independent listing; **regional manual-action candidate**, not a fully verified original-source lead. Erie is outside the approximately two-hour Elmira local scope and belongs only in the separate up-to-12-hour regional research queue. Road driving time has not been verified. This record is **not** inserted into production qualified leads, which require original portal, current deadline, eligibility, and location verification.
- **Automation lesson:** The production scanner's empty qualified feed misses at least this publicly advertised regional bid. The next safe integration is a publisher-approved official procurement feed/API or opt-in bid alerts; do not scrape JavaScript portal internals or third-party listings without a terms review.

**Production metrics unchanged:** 0 automatically qualified published opportunities, 0 new automated integrations. This manual discovery is an open paid-work *candidate*, not an assertion of an eligible or accepted bid.

## October 28 official-feed availability check — no guessed endpoints

- [Steuben County's official RSS directory](https://www.steubencountyny.gov/rss.aspx) explicitly offers feeds for pages, agendas, alerts, calendar, jobs and news, **but does not list a bid-postings feed**. Do not construct an undocumented bid RSS URL or treat a county jobs/news feed as contract notices. Its [official bid-postings page](https://www.steubencountyny.gov/Bids.aspx) is a separate public listing, and its bid status and closing date must be checked on the original detail.
- [Chemung County's official bid-postings page](https://chemungcountyny.gov/Bids.aspx) offers email/text notifications for new bids. That is an opt-in alert mechanism, **not evidence of a public RSS or API**. The [Purchasing Department](https://chemungcountyny.gov/435/Purchasing) confirms BidNet Direct electronic submissions are supported but paper submission is also available; do not assume portal access or submission requirements are identical for every bid.
- [NYS Contract Reporter](https://www.nyscr.ny.gov/) advertises a free account and current opportunity counts. A homepage count is not a verified individual solicitation and does not establish a publicly permitted machine feed. Source integration requires documented access/terms and live original-notice checks.

**Admission decision:** These are official manual discovery resources only; no new automated sources, no qualified tree-work leads, and no production feed changes. An actual official RSS/API or publisher-approved alerts route remains to be verified.
