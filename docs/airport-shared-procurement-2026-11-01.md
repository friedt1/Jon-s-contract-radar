# Elmira-Corning Regional Airport procurement gateway — 2026-11-01

## Official publisher evidence

- Chemung County's official airport page (https://chemungcountyny.gov/850/Elmira-Corning-Regional-Airport) identifies Elmira-Corning Regional Airport as **owned and operated by Chemung County**.
- The county's official purchasing page (https://chemungcountyny.gov/435/Purchasing) identifies the **Chemung County–City of Elmira Purchasing Department** as the buyer for county and city contracts, and explains that electronic bids may be submitted through BidNet Direct. This is not permission to crawl BidNet.
- The county's public CivicPlus procurement listing (https://chemungcountyny.gov/Bids.aspx) exposes individual bid notices; the official individual notice https://www.chemungcountyny.gov/bids.aspx?bidID=89 concerns airport-grade deicing sand, shows **Closed** and a September 10, 2026 submission deadline. This is evidence that the county publishes airport-related solicitations, **not** a relevant tree-work opportunity.

## Safe configuration and boundaries

The airport's `candidate_official_url` is staged as the **same** county CivicPlus Bids.aspx entrypoint already configured for Chemung County bids. It is not an independently monitored airport feed and must not increase direct source count. The existing county adapter may find an airport-specific notice only when individual scope, location, status and submission cutoff are confirmed. Do not infer that every airport contract is advertised there or that county homepage access authorizes provider-delegated BidNet ingestion.

This change adds no live bids, no manual seeds, and no newly permitted scraping. Source remains `discovery_pending`; activation requires publisher/robots/terms review, demonstrated complete permitted individual-notice extraction, airport worksite and tree/clearing relevance, and deadline/amendment checks. Historical Erie tree/stump and unrelated Owego demolition remain negative regression fixtures.

## Expected coverage accounting

102 named targets; 18 direct configured; 66 staged official entrypoints (including the airport); 84 targets without completed direct monitoring. The airport shares its canonical official URL with Chemung County bids, so distinct official gateway count must not increase due to this staging.
