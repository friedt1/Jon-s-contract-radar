# Town of Vestal NY: official procurement entrypoint (staged only)

Reviewed 2026-10-30. The Town of Vestal's own website links a **Bids and RFPS Requested** page under Town Clerk:
https://www.vestalny.gov/page/bids-and-rfps-requested

Evidence: the Town homepage at https://www.vestalny.gov/ links to that
specific page; the page identifies itself as Town of Vestal, 605 Vestal
Parkway W, Vestal, NY. It is an official procurement entrypoint, **not**
evidence of an individual active solicitation.

The page uses an Apptegy-hosted municipal website, not CivicPlus Bids.aspx.
The publicly visible page title does not establish any current tree-work
notice or prove that an empty page means no open solicitations.

Activation checklist:
1. Verify the town's robots policy and applicable automated-access terms.
2. Confirm a permitted, complete source for individual bid/RFP postings
   (including documents, amendments, closing date/time and status).
3. Add and test an Apptegy-specific extraction adapter, with safe redirects,
   bounded fetches, and explicit missing/blocked/access-required diagnostics.
4. Validate on a real individual notice without promoting a historical,
   unrelated, expired, or unsupported listing as verified open.
5. Independently verify geographic fit and eligibility before promoting
   any lead to the local tree-service feed.

Until then, `Town of Vestal` stays `discovery_pending` with only
`candidate_official_url`. It is not one of the operational direct sources.

Related regression: a duplicate Erie-style same-day tree/stump bid with
conflicting 9 AM/2 PM cutoffs remains review-only even after the 9 AM copy
expires. The Owego demolition example stays excluded from the tree feed.
Both are synthetic test fixtures, not manually seeded opportunities.
