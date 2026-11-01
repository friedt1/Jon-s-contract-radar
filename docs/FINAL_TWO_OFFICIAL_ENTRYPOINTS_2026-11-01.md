# Final two named official entrypoints — checked 2026-11-01T21:38:41.097+00:00

These are **official information pages, not live contract feeds**. The two named targets were previously missing any verified official entrypoint. Both remain `discovery_pending` with blank active `url` and `verified_url: false`. They are not direct monitoring integrations and must not produce published opportunities.

| Target | Official source evidence | Activation blocker |
| --- | --- | --- |
| SUNY Corning Community College | [Official 2023 policy manual — Purchasing and Procurement](https://www.corning-cc.edu/about/regional-board-of-trustees/ccc_policy_manual-2023.pdf) | The college's own policy describes competitive bids and quotations, but the document is **not a current bid index**. No permitted individual solicitation extraction has been demonstrated. Confirm the campus purchasing notice channel, robots/terms, scope, deadlines, open status, and Elmira-area worksite. |
| Wegmans regional properties | [Official For Our Suppliers](https://www.wegmans.com/service/for-our-suppliers) | The page links W-Buy purchasing tools and construction/non-construction contract terms. It does **not** publish individual facilities/tree-service solicitations. W-Buy access and local facilities procurement require authorized channels. Do not scrape the supplier portal or mistake product vendor forms for property maintenance bids. |

**Configuration audit after this change:** 102 distinct named targets; 18 configured direct URLs; 84 staged official information entrypoints; 0 targets missing an official entrypoint; **84 still without completed direct monitoring**. These numbers do not establish successful extraction from any newly staged source. Live source success, publisher permissions and open contracts must be separately verified from actual scanner evidence.

No manual opportunities were added. Historical Erie tree/stump removal remains expired; Owego demolition remains unrelated. PRs #28 and #29 are already merged. Related to issue #73.
