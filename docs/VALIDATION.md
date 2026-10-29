# Review evidence and remaining verification

The checkout base was compared with a successful `git fetch origin main` on October 28, 2026. Both HEAD and origin/main resolved to `4b6fda2d0e1c44ba4fba806adcb87d5d1f90e756`. Changes build on that scanner, preserving missing-href handling, per-item RSS dates, history logic, and all 102 target identities. No reset, force push, or merge was used.

Current-instance checks passed:

- Python 3.12.14: 27 offline tests, including all-102-target orchestration, deduplication, history repeatability, source failure fallback, bounded link extraction, dates, scope, record isolation, PDF attachments, and all-source-failure preservation.
- Real installed `pdftotext` extracted and classified a generated PDF bid.
- Node dashboard behavior: feed loading, HTML escaping, service selection, search, source counter. Layout and existing controls preserved.
- Output validator: 102 named statuses plus deferred SAM.gov, compatible lead schema, unique IDs, current eligibility, deadlines, URLs, and history membership.
- Workflow YAML parsed and its local commands executed. GitHub-hosted execution is not established by these local checks.

Integration work uses the existing public URLs, without guessing replacement endpoints. All 13 receive record isolation, bounded detail/attachment traversal, archive exclusion, stricter platform hostname matching, deadline/status screening, and improved discovery queries. Synthetic table/list/PDF/JavaScript-shell fixtures test extractor shapes; they are **not** captured provider fixtures and do not prove compatibility with current live sites.

| Direct source | Intended public path | Live verification in this task |
| --- | --- | --- |
| Chemung County bids | CivicPlus bid listing/details | Blocked by proxy policy (403) |
| Steuben County bids | CivicPlus bid listing/details | Not verified |
| Schuyler County purchasing | Purchasing links/details/PDFs | Not verified |
| Tompkins County purchasing | Purchasing links/details/PDFs | Not verified |
| Elmira City bids | Sealed-bid information/attachments | Not verified |
| Elmira Next local bids | Listing records and detail links; exclude project pages | Not verified |
| Lycoming County bids | County listing/attachments | Not verified |
| PA procurement opportunities | DGS public procurement links, local evidence required | Not verified |
| PA DGS construction bids | DGS details/PDFs, local evidence required | Not verified |
| Tioga Bradford Housing Authority | Bid information/attachments | Not verified |
| Chemung County purchasing | Purchasing links; exclude old bid recordings | Not verified |
| PennBid platform | Public Bonfire links only; dynamic/login shell flagged | Not verified |
| BidNet NY platform | Public links only; dynamic/login shell flagged | Not verified |

Google News live RSS, public-site redirect destinations, JavaScript/login-only listings, complete portal coverage, Python 3.13, hosted Actions, live website deployment, and approximately two-hour road travel times remain unverified. No login bypass, browser rendering, private API, or SAM.gov integration was added. Unknown deadlines remain labeled unverified. The scanner cannot guarantee elimination of every expired or irrelevant result when public metadata is absent or ambiguous. Broader sources require local evidence; local target discovery still requires manual confirmation of the actual work site.

The runtime's enforced custom HTTP allowlist was empty. Draft domain additions were saved for the 12 distinct direct-site hosts, news.google.com, and api.github.com. Saving the draft does not apply that policy or publish an environment. Git HTTPS proxy reads worked after sandbox escalation; GitHub API requests returned Forbidden. This does not establish missing GitHub credentials, so no token was requested.

In environment settings, review and save the draft network changes and publish the environment. Then rerun `python scan.py`, `python validate_output.py`, the tests, and the GitHub workflow. Review individual direct-source status and extraction against the original listings before claiming live readiness. Any additional redirect host must be diagnosed and added through settings rather than bypassing the proxy.


## Source-health diagnostics and official URL staging (October 28, 2026)

The scanner now emits `source_health` for all 102 named targets. The dashboard
separates fetched-but-unverified direct pages, robots blocks, access-required
portals, direct fetch errors, official URLs awaiting activation, and targets
without direct integrations. It also reports how many individual bid records
were discovered and how many detail fetches were attempted. **Neither count is
a verified open-contract count.** The existing `source_coverage` fields remain
for compatibility. The output validator checks consistency.

Three additional official procurement locations were identified and **staged**
without claiming they are directly monitored:

- Cortland County: `https://www.cortlandcountyny.gov/Bids.aspx` — public
  CivicPlus bid listing. An October 22, 2026 closing date still appeared beside
  an “Open” label on the page; scanner must reject the expired date.
- Yates County: `https://www.yatescountyny.gov/bids.aspx` — public CivicPlus
  listing. Its October 26, 2026 air-handler bid also appeared “Open” after its
  deadline; unrelated work must never become a tree-service lead.
- Broome County: `https://www.broomecountyny.gov/purchasing/open-solicitations`
  — official page refers vendors to BidNet for authoritative solicitation
  documents. Provider-approved individual-notice access is still required.

Cortland and Yates use the already-tested CivicPlus `bidID` detail parser once
activated. Activation requires successful robots-policy review, actual live
listing and individual-detail extraction, and successful hosted tests. Broome
requires a permitted BidNet integration; its county information page is not
itself an individual-notice feed. All three retain `mode=discovery_pending`
and `verified_url=false` until those gates pass. The source-health page shows
these as staged rather than monitored. No opportunities were manually inserted.

The latest feed inspected before these changes (2026-10-29 03:06 UTC) reported
18 configured direct targets, 16 fetched listing pages, 84 pending direct
integrations, 0 verified open contracts, and 0 successful indirect RSS queries.
Google News queries were rejected by the robots policy; PennBid was blocked,
and BidNet individual-notice access was not connected. These are integration
blockers, not evidence that no contracts exist. A fresh hosted scan is needed
after merge to populate the new diagnostics.

Four more verified official county pages were staged without activation:

- Seneca County: `https://www.senecacountyny.gov/bids.aspx` — CivicPlus
  individual bidID listing; the October 28 page showed a November 6, 2026
  jail EHR bid, which is unrelated to tree work and must be rejected.
- Allegany County: `https://www.alleganyco.gov/departments/public-works/bids-awards/`
  — public DPW bid specs and awards, requiring per-document extraction and
  separation of current notices from historical results.
- Ontario County: `https://www.ontariocountyny.gov/2291/Current-Bids-RFPs-and-Results`
  — official page delegates current notices to OpenGov; portal permission and
  individual listing extraction are not established.
- Wayne County: `https://www.waynecountyny.gov/745/Purchasing` — official
  purchasing page describes an OpenGov transition, while vendor information
  still references BidNet; the authoritative listing interface and permission
  require confirmation.

**Seven official endpoints are staged, not activated.** No increase to the
18 configured direct sources is claimed. Activation must not be inferred from
an official county homepage or a publicly viewable listing alone.

A source-health-only snapshot was also derived from the **existing**
2026-10-29T03:06:36Z published scan so the dashboard can show diagnostics
immediately after deployment, without changing the scan timestamp or adding
any opportunities. It reports 15 fetched-but-unverified direct pages, 2
robots-blocked direct pages, 1 access-required portal, 7 staged official URLs,
77 still unconfigured, 12 discovered individual bid records, 206 detail fetch
attempts, and 0 candidates. All 102 indirect news searches were robots-blocked.
These are historical diagnostics, not a new live scan or proof of complete
individual-bid extraction.
