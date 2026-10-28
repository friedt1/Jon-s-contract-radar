"""Monitor official DOT procurement entry points without inventing contract notices."""
import datetime as dt
import json
import re
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
SOURCES = [
 {"name":"NYSDOT construction highway lettings","url":"https://www.dot.ny.gov/doing-business/opportunities/const-highway","state":"NY"},
 {"name":"NYSDOT construction contract documents","url":"https://www.dot.ny.gov/doing-business/opportunities/const-notices","state":"NY"},
 {"name":"NYSDOT commodities and services","url":"https://www.dot.ny.gov/bids-and-lettings/commodities-and-services/opportunities","state":"NY"},
 {"name":"PennDOT ECMS construction bids","url":"https://www.ecmssyst.penndot.pa.gov/ECMS/","state":"PA"},
 {"name":"PennDOT bid access guidance","url":"https://www.pa.gov/services/penndot/find-contract-information-bid-opportunities","state":"PA"},
 {"name":"Pennsylvania state agency procurement","url":"https://www.pa.gov/agencies/dgs/doing-business-with-the-commonwealth/business-inclusion-and-supplier-development/finding-opportunities","state":"PA"}
]
def check_source(source, opener=urllib.request.urlopen):
    request=urllib.request.Request(source["url"],headers={"User-Agent":"JonsContractRadar/1.0","Accept":"text/html"})
    try:
        with opener(request,timeout=20) as response:
            status=getattr(response,"status",200)
            response.read(512)
        result="reachable" if status==200 else "HTTP "+str(status)
    except Exception as exc:
        result="unavailable: "+type(exc).__name__
    return {**source,"status":result,"contract_count":None,"drive_time_verified":False}
def extract_nysdot_letting_ids(page, today=None):
    """Extract contract identifiers from upcoming letting dates for manual review.

    The index does not describe work scope or establish bid eligibility.
    """
    today = today or dt.datetime.now(dt.timezone.utc).date()
    text = re.sub(r"<[^>]+>", " ", page)
    text = " ".join(text.split())
    dates = list(re.finditer(r"\\b(January|February|March|April|May|June|July|August|September|October|November|December)\\s+\\d{1,2},\\s+20\\d{2}\\b", text))
    found = []
    seen = set()
    for index, match in enumerate(dates):
        try:
            letting_date = dt.datetime.strptime(match.group(), "%B %d, %Y").date()
        except ValueError:
            continue
        if letting_date < today:
            continue
        segment = text[match.end():dates[index + 1].start() if index + 1 < len(dates) else len(text)]
        for identifier in re.findall(r"\\bD\\d{6}\\b", segment):
            if identifier in seen:
                continue
            seen.add(identifier)
            found.append({"contract_id": identifier, "letting_date": letting_date.isoformat(),
                          "source": "NYSDOT Highway Lettings", "source_url": SOURCES[0]["url"],
                          "status": "scope and deadline review required",
                          "drive_time_verified": False, "is_qualified_lead": False})
    return found

def fetch_nysdot_index(opener=urllib.request.urlopen):
    request = urllib.request.Request(SOURCES[0]["url"], headers={"User-Agent":"JonsContractRadar/1.0"})
    with opener(request, timeout=20) as response:
        page = response.read(1_000_000).decode("utf-8", errors="replace")
    return extract_nysdot_letting_ids(page)

def main():
    result={"updated":dt.datetime.now(dt.timezone.utc).isoformat(),
      "coverage_note":"Official procurement portals only. No individual bid extraction, open-contract confirmation, or 12-hour route verification yet.",
      "sources":[check_source(s) for s in SOURCES],"opportunities":[]}
    try:
        result["letting_review_queue"] = fetch_nysdot_index()
        result["letting_index_status"] = "fetched; identifiers only, not confirmed tree contracts"
    except Exception as exc:
        result["letting_review_queue"] = []
        result["letting_index_status"] = "unavailable: " + type(exc).__name__
    out=ROOT/"data"/"regional_dot_sources.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print("DOT procurement portals checked:",len(result["sources"]))
if __name__=="__main__": main()
