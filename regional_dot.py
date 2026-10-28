"""Monitor official DOT procurement entry points without inventing contract notices."""
import datetime as dt
import json
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
def main():
    result={"updated":dt.datetime.now(dt.timezone.utc).isoformat(),
      "coverage_note":"Official procurement portals only. No individual bid extraction, open-contract confirmation, or 12-hour route verification yet.",
      "sources":[check_source(s) for s in SOURCES],"opportunities":[]}
    out=ROOT/"data"/"regional_dot_sources.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print("DOT procurement portals checked:",len(result["sources"]))
if __name__=="__main__": main()
