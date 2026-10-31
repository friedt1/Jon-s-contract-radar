# School district procurement gateway evidence — 2026-10-31

## Publisher-verified pages (staged only)

- **Elmira City School District:** Official district homepage
  https://www.elmiracityschools.com/ links under Departments to
  https://www.elmiracityschools.com/page/business-office .
  The official page identifies the district's Business Office, but inspection
  did **not** establish an individual solicitation index, permitted crawler,
  public deadline feed, or open tree-work bid.
- **Ithaca City School District:** Official district homepage
  https://www.ithacacityschools.org/ links under Departments to
  https://www.ithacacityschools.org/page/business-services .
  The official Business Services page is not proof of a public individual-bid
  feed. Newspaper legal advertisements and third-party listings are not
  equivalent to publisher-confirmed, live individual contract records.

Both are staged as `candidate_official_url` with `mode=discovery_pending`,
`url=""`, and `verified_url=false`. This distinction is deliberate:
official domain ownership does not establish monitoring permission, extraction
capability, a local worksite, a submission cutoff, or current bid eligibility.

## Remaining activation work

1. Find each district's official current procurement/bid publication channel
   or an explicitly authorized cooperative purchasing provider.
2. Verify robots/terms and whether unattended per-notice retrieval is allowed.
   Do not bypass registration, authentication or provider restrictions.
3. Implement and test an individual-notice adapter that captures solicitation
   ID, scope, worksite, status, amendments, and **submission** deadline.
4. Gate tree/removal/vegetation work separately from related site preparation;
   keep expired Erie and unrelated Owego examples excluded.
5. Confirm a successful live extraction and accurate diagnostics before
   changing a source to `direct_page` or any other active mode.

## Coverage after this change

102 named sources; 18 configured direct URLs; 84 without completed direct
monitoring; **58 staged official URLs**; **26 still requiring an official
entrypoint**. Neither staged school source is counted as operational.

No production opportunity data or scan timestamps were changed.
