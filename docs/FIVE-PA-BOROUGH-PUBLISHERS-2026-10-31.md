# Five northern Pennsylvania borough publisher entrypoints — October 31, 2026

This source-discovery change concerns five **already named** targets in
`sources.json`. It verifies municipal publisher identity, **not** the
existence of a complete, automatable procurement feed. These remain
`mode=discovery_pending`, `verified_url=false`, and active `url=""`.

| Named target | Official publisher evidence | Procurement evidence / blocker |
| --- | --- | --- |
| Sayre Borough | https://sayreborough.org/ — borough homepage, Public Works, news and council documents; official Bradford County municipality directory https://www.bradfordcountypa.gov/225/Sayre-Borough | No current bid index or individual-notice feed established. Calendar community clean-up events are not tree contracts. |
| Athens Borough | https://athensboroughpa.org/ — municipal Public Works, council documents and official contact information; official Bradford County directory https://www.bradfordcountypa.gov/202/Athens-Borough | Shade Tree meeting is an event, not a solicitation. No verified current bid index or per-notice feed. |
| Mansfield Borough | https://mansfieldborough.org/ — borough government, contact and news pages, municipal identity | No current individual procurement notices or stable bid listing verified. |
| Troy Borough | https://troyborough.com/officials.php — borough officials page displays a 2026 paving-bid/results notice; Bradford County official directory https://www.bradfordcountypa.gov/237/Troy-Borough links municipal contact | The June 25, 2026 paving solicitation is expired, unrelated to tree work, and asks bidders to request packets by phone/email. The page is not a complete live bid feed. |
| Montrose Borough | https://www.montroseborough.com/ — borough council agendas/minutes and municipal office contacts | No current individual bid listing verified; agendas are not automatically bid notices. |

## Activation blockers

1. Locate each borough's authoritative *current* solicitation publication
   channel; a homepage or council agenda alone does not establish one.
2. Review publisher robots.txt and terms, and obtain any needed approval
   before unattended collection or individual-document requests.
3. Verify stable individual notice URLs and permitted extraction of scope,
   issuing agency, worksite, submission cutoff, amendments and closure.
   Troy's old paving notice is historical evidence only.
4. Enforce tree/vegetation work classification, keep related site prep
   separately labeled, and independently confirm worksite travel from Elmira.
5. Add source-specific live acceptance evidence and passing GitHub Actions
   tests before any `discovery_pending` source can become direct.

The existing published feed timestamp is preserved; only registry-aligned
source-health metadata is updated from 47 staged / 37 not configured to
**52 staged / 32 not configured**. Still **18 directly configured, 84
pending**, with **zero verified open contracts** in the inspected feed.
No bid is seeded or claimed live. The Erie expired tree/stump and Owego
unrelated demolition regression cases remain excluded. PRs #28 and #29
were already merged; issue #73 tracks actual direct integration.
