# Corning-Painted Post district bid-document request and staged probe safety
_Reviewed October 31, 2026_

## Official publisher evidence

The Corning-Painted Post Area School District's official Business Services
page is https://www.corningareaschools.com/page/business-services .

Under **Request for Bid and/or RFP Documents**, the district directs vendors
to request copies of current advertised bid/RFP documents from its business
office. Submission instructions are in the requested documents. The page
provides a bid-opening video link, **not** a machine-readable list of active
individual solicitations or authoritative submission deadlines.

The entrypoint is now staged for the existing
`Corning-Painted Post Area School District` target. It remains
`mode=discovery_pending`, `url=""`, `verified_url=false`. The source
inventory remains 102, with 18 directly configured, 84 pending, and 47
staged official URLs (55 others not staged; 37 of the pending lack an official
entrypoint). **A document-request workflow is not a functioning automated
bid feed.** No current tree-service opportunity was identified or inserted.

**Activation blocker:** verify a publisher-permitted individual-notice
publication or authorized access path, including exact worksite, submission
deadline/time and amendment/closure status. Do not email the district
automatically, infer availability from the contact page, or scrape an
access-controlled document portal.

## Staged-source outbound URL diagnostics

The staged-source probe previously checked HTTPS and credentials on outbound
links but could still count links to private IPs/resolver aliases or paths
containing encoded control characters as PDF or provider evidence. The
diagnostic-only link resolver now applies the same public HTTPS hostname
and URL hygiene used by direct source configuration. Harmless PDF fragments
and signed document query parameters remain supported. It still never fetches
outbound links without a dedicated approved adapter.

Offline regression fixtures cover unsafe outbound links, false provider
delegation, false off-host PDF evidence, and the district's request-only
source status. These are synthetic fixtures, **not live contracts**. CI and
published-scan outcomes must be checked independently before merging.
