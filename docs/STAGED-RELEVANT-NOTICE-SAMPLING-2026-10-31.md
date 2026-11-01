# Staged individual-notice sampling: service relevance (2026-10-31)

The 102-source inventory has **18 configured direct sources**. The latest
published staged probe inspected **62 staged official entrypoints**; four
returned a parseable individual notice (Cortland County, Seneca County,
Livingston County and City of Binghamton). All four still require publisher
terms/permission review and live acceptance before activation. A sample
notice marked "Open" is **not** an actionable or verified open contract.
Yates County and seven other staged entrypoints were robots-blocked in that
probe. Source-specific blocked/access-required states must remain visible.

Previously, the staged probe inspected up to three individual notices in
listing order after sorting by date/status. On an index with several equally
current bids, three unrelated notices could exhaust that sample before a
fourth tree-removal bid. The new sort uses **isolated listing-card scope**
within the same temporal evidence tier:

1. Unexpired listings with a stated cutoff, then unknown deadlines.
2. Expired or contradictory dates/status, then explicitly closed notices.
3. Within each tier: tree removal, storm cleanup, tree trimming, vegetation
   management, land clearing, related site preparation, then unrelated work.

This changes only which permitted detail URLs are sampled for adapter
diagnostics; it does not raise the three-detail cap, override robots or
provider access gates, change `sources.json`, create leads, or infer
two-hour travel times. Expired Erie tree/stump examples remain lower priority
than future unrelated notices. Owego demolition with tree removal "by
others" is not a tree-service scope. The regression suite includes an
index with three unrelated cards ahead of a fourth tree-removal card.

**Acceptance gate for any staged source:** official URL, site robots/terms
review, permitted individual-notice retrieval, source-specific deadline and
status extraction, scope/worksite confirmation, offline regression tests,
hosted CI, and a subsequent live scan. No staging count should be reported
as direct monitoring or verified opportunities.

Evidence: `data/staged_probes.json` snapshot timestamp
`2026-11-01T00:22:12Z` and the existing `probe_staged_sources.py` output.
The snapshot predates this prioritization change. A fresh staged probe is
needed to measure its effect.
