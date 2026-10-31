# Towanda Borough official public announcements — October 31, 2026

Inventory target: **Towanda Borough**, Bradford County, Pennsylvania.
Official borough publisher: https://towandaborough.org/public-announcements/

## Verified publisher evidence

The borough's own homepage links to **Public Announcements**, and the
official page displays an individual solicitation for municipal solid waste
collection and recycling services. The posting specifies a **Tuesday,
October 27, 2026, 10:00 a.m.** bid deadline, with bids submitted at
724 Main Street, Towanda, PA. This solicitation is **expired as of
October 31** and **unrelated to tree removal or vegetation management**.
The contract term starting in January 2027 does not reopen its bid deadline.

Evidence:
- Official borough home page: https://towandaborough.org/
- Official public announcements: https://towandaborough.org/public-announcements/

The page is a mixed public-announcements entrypoint, **not a proven complete
or machine-readable current-bid feed**. One visible expired unrelated notice
does not prove the absence of other bids or that automated collection is
authorized.

## Activation blockers

1. Review the publisher's robots policy and terms for unattended extraction.
2. Determine whether individual notices have stable, permitted URLs and
   whether attachments, amendments, and closures can be retrieved safely.
3. Build and test an individual-notice adapter that keeps distinct notice
   scopes and deadlines separate. A page-level "cleanup" keyword must not
   convert the municipal waste bid into storm cleanup.
4. Verify exact tree-work scope, submission cutoff, open status and
   actual worksite/drive time before publication.

The source remains `mode=discovery_pending`, `verified_url=false`, with
blank active `url`. Its verified **candidate** publisher URL is staged
only. No direct scanner fetch is enabled and no opportunity was seeded.

The existing published scan timestamp is intentionally preserved; source
health is reconciled from the registry (45 staged / 39 not configured),
not represented as a new live scan. PRs #28 and #29 are already merged.
Historical Erie tree/stump and unrelated Owego demolition regression
protections remain in place.
