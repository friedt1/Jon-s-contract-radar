# Town of Ithaca, NY — official procurement source staging

Evidence checked 2026-10-29: the Town's official [Bid/RFP Announcements](https://townithacany.gov/home/bid-anouncements/) page says **all Bid/RFP/RFQ packets are available from BidNet or the Town Clerk** and that it uses the Empire State Purchasing Group. The [BidNet Town of Ithaca listing](https://www.bidnetdirect.com/new-york/townofithaca/solicitations/closed-bids) says registration or login is required for details of open opportunities.

This is **not a direct monitored source**. Its official announcement page is staged as a candidate entry point only; `mode` stays `discovery_pending`, `url` stays empty and `verified_url` stays false. The staged probe distinguishes the agency's reachable announcement page from the external provider's access-controlled individual notices. It does not fetch BidNet pages, add leads, or assert that any solicitation is open.

**Activation blocker:** obtain provider-approved access to individual notices (or a separately verified official Town feed with individual records), confirm robots and publisher terms, test notice identity/deadline/closed status, and run the live scanner. Do not treat old Town RFQs or a BidNet landing page as an actionable tree contract.
