"""Optional SAM.gov federal opportunity feed. Requires SAM_API_KEY GitHub secret.

Federal notices are candidate records, not verified awards or verified travel times.
The API is queried once per scheduled daily run to conserve rate limits.
"""
import datetime as dt
import json
import os
import pathlib
import urllib.parse
import urllib.request

from regional_rank import build

API = "https://api.sam.gov/opportunities/v2/search"
OUT = pathlib.Path(__file__).resolve().parent / "data" / "regional_opportunities.json"
TERMS = ("tree", "vegetation", "debris", "clearing", "storm", "right of way", "roadside", "line clearance")
def parse_notice(item):
    title = str(item.get("title") or "")
    desc = str(item.get("description") or "")
    # Description may be a URL in SAM; title is required for safe matching.
    if not any(word in (title + " " + desc).lower() for word in TERMS):
        return None
    notice_id = str(item.get("noticeId") or "")
    link = str(item.get("uiLink") or "")
    if not link.startswith("https://") and notice_id:
        link = "https://sam.gov/opp/" + urllib.parse.quote(notice_id, safe="") + "/view"
    if not link.startswith("https://"):
        return None
    location = item.get("placeOfPerformance") or {}
    if not isinstance(location, dict):
        location = {}
    state = location.get("state") or {}
    if isinstance(state, dict):
        state = state.get("name") or state.get("code") or ""
    city = location.get("city") or {}
    if isinstance(city, dict):
        city = city.get("name") or ""
    return {
        "title": title, "summary": desc[:600], "url": link,
        "source": "SAM.gov", "agency": str(item.get("department") or item.get("fullParentPathName") or ""),
        "location": ", ".join(str(x) for x in (city, state) if x),
        "deadline": str(item.get("responseDeadLine") or ""),
        "notice_type": str(item.get("type") or ""),
        "notice_id": notice_id, "drive_hours": None, "travel_verified": False,
        "estimated_value_usd": None, "estimated_duration_days": None,
        "subcontracting_available": None,
    }

def fetch_notices(api_key, opener=urllib.request.urlopen, today=None):
    today = today or dt.datetime.now(dt.timezone.utc).date()
    start = today - dt.timedelta(days=14)
    params = {"api_key": api_key, "postedFrom": start.strftime("%m/%d/%Y"),
              "postedTo": today.strftime("%m/%d/%Y"), "limit": 100, "offset": 0}
    url = API + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "JonsContractRadar/1.0"})
    with opener(request, timeout=25) as response:
        data = json.load(response)
    items = data.get("opportunitiesData") or []
    if not isinstance(items, list):
        raise ValueError("Unexpected SAM.gov response")
    return [n for x in items if isinstance(x, dict) and (n := parse_notice(x)) is not None]

def main():
    key = os.environ.get("SAM_API_KEY", "").strip()
    if not key:
        print("SAM_API_KEY missing: regional feed unchanged; no false success.")
        return
    notices = fetch_notices(key)
    result = build(notices)
    result["source_status"] = {"SAM.gov": "API fetched; first 100 recent notices only; not exhaustive"}
    result["coverage_note"] = "Federal candidate notices only. Not exhaustive; 12-hour drive time, active status, qualifications, and deadlines unverified."
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("SAM.gov candidate notices:", len(result["opportunities"]))
if __name__ == "__main__":
    main()
