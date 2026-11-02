# Wayne County NY: current solicitations gateway (2026-11-02)

## Official evidence

- County Purchasing: https://www.waynecountyny.gov/745/Purchasing
  - County states its OpenGov eProcurement transition began **January 9, 2026**.
  - The Purchasing page is general agency information, not an individual bid listing.
- Current county solicitations gateway: https://www.waynecountyny.gov/922/Solicitations-After-192026
  - This is linked under the county Purchasing section and explicitly titled **Solicitations After 1/9/2026**.
  - The page says the list of current solicitations is supplied through an embedded OpenGov portal, with free vendor registration, follow/addendum notifications and electronic responses.
  - Official OpenGov portal linked by county: https://procurement.opengov.com/portal/co-wayne-ny-us

These observations establish the official *gateway* and provider delegation, not an authorized, complete or machine-readable individual-notice feed. The iframe is not proof that its contents are included in the parent page's HTML. Do not infer a bid is open from an old search result or from the county's general purchasing text.

## Change and safeguards

- Update the Wayne County `candidate_official_url` to the county's post-transition current-solicitations page.
- Record `delegated_provider=OpenGov` and `provider_access_required=true`.
- **Keep `mode=discovery_pending`, `url=""`, `verified_url=false`**; the staged probe may read the county gateway but must not follow the iframe or activate it as a live notice feed.
- Synthetic regression checks ensure the probe reports provider access required, no individual notice, no live contract, and preserves the 102 named / 18 configured / 84 staged baseline. Erie expired tree/stump and unrelated Owego demolition are negative controls.

## Activation blockers

1. Confirm OpenGov and county automation terms and robots policy for the *provider* listing and individual-notice paths; no access restriction bypass.
2. Obtain a permitted public/API/approved vendor feed and verify stable per-notice extraction, including amendments and closing dates.
3. Validate scope, worksite and travel qualification, timezone, status, deadlines and deduplication against actual official individual notices.
4. Run hosted CI, a live staged probe and a scan before promoting the source. Until then no Wayne County opportunities may be published from this change.

This is a corrected **staged official entrypoint**, not an increase in operational coverage or a claim of available tree-service work. Related: #73, #28, #29.
