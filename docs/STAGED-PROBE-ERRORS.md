# Staged official-source probe status semantics (October 29, 2026)

These probes are **diagnostics only**. A retrieved listing or a well-shaped
individual notice does not authorize crawling, prove a bid is currently open,
or activate a `discovery_pending` source. The live feed remains separate.

## Access and reliability evidence

The staged probe now distinguishes HTTP 401 (authentication required),
403 (access forbidden, **not** necessarily a login requirement), 404/410
(not found), 429 (rate limited), and 5xx (publisher/server error), separately
for listing pages and individual notice pages. It preserves the HTTP status
without storing response bodies, credentials, or speculative explanations.
Robots denial remains a separate state.

The fetcher also refuses redirects to unapproved hosts, insecure HTTP
endpoints, or different solicitation identities **before** making the
redirected request. These refusals are recorded as
`listing_redirect_blocked` / `individual_notice_redirect_blocked`, or
`listing_insecure_redirect` / `individual_notice_insecure_redirect`
for HTTPS downgrades. These states do not prove the destination was fetched
or that a provider granted access.

An individual bid can be sign-in-gated even when its listing is public.
A same-host sign-in landing or a password form with a login heading is
recorded as `individual_notice_authentication_required`, rather than a
broken parser. An ordinary login link on an otherwise readable notice does
not establish an authentication wall. No credential attempt is made.

Public agency pages that delegate procurement to BidNet, OpenGov, Bonfire,
PennBid, or Public Purchase are marked as requiring provider-approved
individual-notice access. The agency's public announcement page is **not**
an approved portal adapter.

For CivicPlus and Granicus diagnostic samples, future-dated notices are
sampled before unknown-deadline, expired, and closed notices, subject to
the existing three-detail-request cap. This helps test current notice
formats without publishing or declaring any notice actionable. A
stale "Open" label is still not evidence of an open solicitation.

## Regression and live-source caveats

Offline fixtures cover HTTP errors, provider delegation, and sample order.
The existing Erie tree/stump and Owego demolition cases must continue to
reject expired/unrelated work. The official Tioga County NY Public Works
page showed a 67 Central Avenue demolition rebid with a mandatory
October 29, 2026 site inspection; it is **not** a tree-service contract
and must not be manually seeded into the live feed.

Activation still requires source-specific terms/robots review, successful
permitted listing and individual-notice extraction, status/deadline and
worksite checks, and passing hosted CI. None of the 84 pending targets
is promoted by this patch.
