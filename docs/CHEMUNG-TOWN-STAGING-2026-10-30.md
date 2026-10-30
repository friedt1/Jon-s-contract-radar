# Chemung town publisher entrypoints — October 30, 2026

This change improves source **identity discovery**, not live bid coverage.
All three existing targets remain `discovery_pending`; their `url` remains
empty and `verified_url` remains false. No crawler is activated and no
opportunity is inserted. Robots allowance alone would not establish
publisher permission for ongoing automated extraction.

| Named target | Official page checked | Evidence | Why not activated |
| --- | --- | --- | --- |
| Town of Big Flats | https://www.bigflatsny.gov/ | Official town website identifies the Town of Big Flats and its departments. | Government homepage; no authoritative current bid index or individual notices established. |
| Town of Elmira | https://townofelmira.gov/ | Official town homepage; its own https://townofelmira.gov/post/_docs/Concession_Stand_bid_specs.pdf shows a March 9, 2026 concession-stand RFP. | That document is unrelated and expired; no stable current solicitation index, terms review, or recurring individual-notice extraction established. |
| Town of Southport | https://townofsouthportny.gov/post.php?pid=44 | Official town homepage links to this Legal Notice page. On October 30 it displayed a truck-financing resolution, 2027 budget hearing, tax-levy and comprehensive-plan hearing notices. | Mixed public/legal notice index, not an authenticated current bid feed; no individual tree-service solicitation or extraction adapter established. |

## Activation gates

For each source, identify a stable, authoritative listing or permitted feed
of individual solicitations; review robots and applicable publisher terms;
implement bounded per-notice retrieval; extract solicitation scope, status,
submission deadline/time and worksite; and test against expired/awarded,
unrelated and inaccessible notices. Do not infer a job from the publisher's
homepage, an old PDF, a public hearing, or a budget resolution.

The existing Erie tree/stump removal example (deadline October 29, 2026)
and Owego demolition example remain regression **exclusions**, never
manually seeded or represented as live bids.

## Coverage accounting

The named inventory stays at 102. This patch adds three staged official
entrypoints, raising the staged count from 31 to 34, while leaving 18 direct
configurations and 84 not directly monitored. An official homepage does not
increase the count of permitted individual-notice integrations.

Source checks: official pages visited October 30, 2026. The linked
historical RFP was inspected for classification only, not offered as work.
