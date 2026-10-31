# Five municipal publisher entrypoints — 2026-10-30

This research adds **candidate official URLs**, not operational bid integrations. All five remain `discovery_pending`, `url: ""`, `verified_url: false`. The 102-source registry is unchanged. No individual solicitations were manually seeded; no live bid claims or robots/provider bypasses.

| Registry source | Official evidence | What the page establishes | Missing before direct activation |
| --- | --- | --- | --- |
| Village of Bath | https://villageofbathny.gov/ | Official Village site; 2026 news, public notices, board minutes; no verified dedicated current-bid index. | Find authoritative procurement listings, review robots and publisher terms, extract per-notice scope, deadlines, status and location. |
| Village of Penn Yan | https://www.villageofpennyan.gov/meetings.html | Official Agendas, Minutes & Public Notices page. Its Tree Board meeting and general notices are **not paid tree-service solicitations**. | Locate authoritative bid index; establish permission and stable individual notice retrieval. |
| Town of Erwin | https://www.erwinny.gov/ | Official 2026 Town .gov CivicPlus homepage. Older `erwinny.org/publications/` exposes an unrelated dog-control RFP with a **September 26, 2025** deadline; do not assume the old domain is current. | Identify current official bid page and terms, prove individual bid extraction. |
| Town of Lansing | https://www.lansingtownny.gov/rfps | Official Bids and RFPs index; currently displays **“There are no bids or RFPs available.”** | Verify robots/terms, pagination, individual listing format and status/deadline logic when a real notice appears. Empty page does not prove complete coverage. |
| Town of Dryden | https://www.dryden.ny.us/ | Official domain hosts 2025 RFP documents (https://www.dryden.ny.us/media/7096 and https://www.dryden.ny.us/media/7676). Homepage fetch during review returned HTTP 403. | Investigate HTTP block without bypass; find permitted current index and individual notice adapter. Historic documents do not establish open contracts. |

## Relevant historical negative example

A third-party record of a Village of Penn Yan solicitation mentions **tree maintenance and power-line clearing** but gives a sealed-bid deadline of **April 3, 2026, 1:30 p.m.** (https://projects.constructconnect.com/details/7482729-cemetery-foundation-work-concrete%26find_loc%3Dnew-york-14527). As of October 30, 2026 this is expired. It is useful only as an offline exclusion/regression example, not as a new live lead; the publisher's original bid packet and current status were not independently retrieved.

## Source activation checklist

1. Verify a current **official individual-solicitation listing URL**, not merely a homepage or public-notices index.
2. Independently review robots.txt and applicable terms/provider permission; preserve blocked, rate-limited and access-required diagnostics.
3. Prove that the adapter fetches individual notices and captures title, scope, issuing agency, worksite, deadline **with time and timezone where stated**, and publisher status.
4. Validate regional qualification (within approximately two hours of Elmira) without treating a statewide or regional page as proof of worksite location.
5. Run negative tests: historical Erie tree/stump expiration, Owego demolition exclusion, Penn Yan April 2026 tree-work expiration, duplicate identity, and conflicting deadlines.
6. Require green Python 3.12/3.13, staged-source, dashboard and Local Customer Lead Radar CI before merging any direct activation.

### Expected coverage effect

Before: 102 total, 18 configured direct, 34 staged official URLs, 50 without official URL.
After: **102 total, 18 configured direct, 39 staged official URLs, 45 without official URL.**
**84 sources remain without completed direct monitoring.** A staged official URL is not a live integration and should never appear as one on the dashboard.
