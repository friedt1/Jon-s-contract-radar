# Four school publisher entrypoints — verified 2026-11-01

These are **official entrypoints**, not direct procurement feeds. All four
remain `discovery_pending`, with blank active `url`, `verified_url: false`,
and no direct requests. The `candidate_official_url` identifies a verified
publisher page; it does **not** certify that individual bid notices are
public, that crawling is allowed, or that the agency currently has a bid.

| Named source | Official evidence | Activation blocker |
| --- | --- | --- |
| Waverly Central School District | [Official district site](https://www.waverlyschools.com/) | District homepage only; locate current individual RFP listing or authorized supplier invitation and review robots/terms. |
| Ithaca College | [Official supplier guidance](https://www.ithaca.edu/procurement/information-suppliers) and [Procurement](https://www.ithaca.edu/procurement) | Supplier guidance explicitly says bids and quotations are confidential and not made public. Permission/invitation is required; no unauthenticated public notice extraction. |
| Northern Tier Career Center | [Official school site](https://www.ntccschool.org/) | Homepage only; find authorized current individual-notice listing and review robots/terms. |
| Wellsboro Area School District | [Official business office](https://www.wellsborosd.org/page/business-office) and [official 2025 RFP example](https://www.wellsborosd.org/article/2098089) | Purchasing contact page is not a listing. The 2025 technology RFP was unrelated and expired April 14, 2025; no live opportunity inferred. |

**Source audit after staging:** 102 named sources, 18 direct configured
(not proof of successful extraction), 84 not directly monitored, 70 official
URLs staged, 14 without an official entrypoint. These four are **not** new
live feeds; the count of direct fetch targets is unchanged.

**Activation requirements:** Identify publisher-approved, individual-notice
extraction (or explicitly authorized supplier access); verify robots policy
and terms, per-notice current submission deadline including amendments,
open status, relevant tree/clearing scope, exact worksite, and geographic
qualification. Do not bypass login, reclassify old RFPs, or seed examples.

**Regression cases:** Erie tree/stump removal is historical/expired;
Owego demolition is unrelated; Wellsboro's 2025 technology RFP is both
unrelated and expired. They must never be published as live contracts.

Tracked in issue #73. PRs #28 and #29 were previously merged.
