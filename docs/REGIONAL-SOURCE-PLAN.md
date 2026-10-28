# Regional / 12-hour large contract radar

- Keep local two-hour opportunities in their original feed. Regional results live only in data/regional_opportunities.json.
- Focus on major state DOT, FEMA-funded municipal disaster work, USACE disaster debris, federal solicitations, utility vegetation management, highway and road clearing, power-line and transmission/distribution right-of-way clearing, emergency road reopening, storm restoration, and prime-contractor subcontracting.
- Monitor official state procurement, SAM.gov, USACE, FEMA procurement guidance, and local/state disaster bid postings. FEMA may fund a local government procurement without being the buyer.
- Candidate records must contain a real HTTPS source link and relevant work scope. Record posted amount, contract duration, response deadline, buyer, worksite, mobilization requirements, equipment requirements, subcontracting options, and a verified route time from Elmira when available.
- Do not infer 12-hour eligibility from a state name or straight-line distance. Unknown drive time remains unverified. Never label an award notice or a closed bid as an open solicitation.
- regional_rank.py accepts a manually reviewed JSON array and produces a separate ranked feed. It is **not** a live source integration. Do not claim otherwise.
- Priority: $250k+ estimated value, week+ duration, disaster debris, state/federal buyer, and subcontracting availability. Unknown value must not be invented.
- Official resources: https://www.fema.gov/business-industry/doing-business ; https://www.usace.army.mil/Missions/Emergency-Operations/Contracting-in-Disasters/ ; https://sam.gov/opportunities ; https://www.nyscr.ny.gov/ ; https://www.emarketplace.state.pa.us/
- Next implementation: permission-reviewed source connectors, verified worksite extraction, route verification, open-deadline checks, and publishing CI. No unverified entries in live results.

- Flag utility line-clearance jobs requiring qualified personnel, minimum approach distances, electrical hazard training, utility authorization, or special insurance; never assume ordinary tree crews are eligible for energized-line work.
