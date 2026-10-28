"""Jon's Contract Radar — 102 named-source discovery checks plus direct public pages.
Indirect searches do NOT imply direct integration with a buyer's procurement site.
Python 3.12 standard library; no keys required. SAM.gov deferred.
"""
import concurrent.futures
import datetime as dt
import email.utils
import hashlib
from html.parser import HTMLParser
import json
import pathlib
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / 'data' / 'opportunities.json'
SOURCES = ROOT / 'sources.json'
AREAS = ['Elmira','Horseheads','Corning','Bath','Ithaca','Binghamton','Owego','Waverly','Watkins Glen','Penn Yan','Sayre','Towanda','Cortland','Geneva','Hornell','Mansfield','Chemung','Steuben','Schuyler','Tompkins','Tioga','Bradford','Broome','Lycoming']
TERMS = {'Tree removal':['tree removal','tree cutting','tree felling','hazard tree','tree services'], 'Tree trimming':['tree trimming','tree pruning','tree maintenance','arborist'], 'Land clearing':['land clearing','site clearing','lot clearing'], 'Vegetation management':['vegetation management','brush clearing','brush removal','right of way','right-of-way','line clearance'], 'Storm cleanup':['storm debris','storm cleanup','debris removal']}
BID_WORDS = ['bid','rfp','rfq','solicitation','tender','proposal','contract','procurement','invitation to bid']
SEARCH_TERMS = '("tree removal" OR "tree trimming" OR "vegetation management" OR "land clearing" OR "brush clearing" OR "storm debris") (bid OR RFP OR contract OR solicitation)'

def clean(s): return re.sub(r'\s+', ' ', re.sub(r'<[^>]*>', ' ', s or '')).strip()
def fetch(url):
    req = urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; JonsContractRadar/3.0)','Accept':'text/html,application/rss+xml,application/xml;q=0.9,*/*;q=0.5'})
    with urllib.request.urlopen(req,timeout=15) as r:
        if r.status != 200: raise ValueError('HTTP '+str(r.status))
        return r.read(1_500_000).decode('utf-8','replace')

class Anchors(HTMLParser):
    def __init__(self): super().__init__(); self.links=[]; self.href=None; self.parts=[]
    def handle_starttag(self,tag,attrs):
        if tag=='a': self.href=dict(attrs).get('href',''); self.parts=[]
    def handle_data(self,data):
        if self.href is not None: self.parts.append(data)
    def handle_endtag(self,tag):
        if tag=='a' and self.href is not None:
            self.links.append((clean(' '.join(self.parts)),self.href)); self.href=None; self.parts=[]

def category(text):
    text=text.lower()
    return next((k for k,words in TERMS.items() if any(w in text for w in words)),None)

def lead(source,title,url,summary='',published='',kind='indirect search candidate'):
    if not category(title+' '+summary) or not url.startswith('https://'): return None
    uid=hashlib.sha256(url.encode()).hexdigest()[:16]
    return uid,dict(id=uid,title=title[:220],summary=summary[:500],url=url,source=source,location='Unverified — check driving distance',category=category(title+' '+summary),published=published,status='unverified',lead_type=kind)

def scan_direct(source):
    html=fetch(source['url']); p=Anchors(); p.feed(html); leads=[]
    for title,href in p.links:
        dest=urllib.parse.urljoin(source['url'],href)
        if category(title) and any(w in (title+' '+href).lower() for w in BID_WORDS):
            result=lead(source['name'],title,dest,kind='direct website candidate')
            if result: leads.append(result)
    return leads

def scan_indirect(source):
    # Target-specific indexed news search. It does not fetch the organization's website.
    query='"'+source['name'].replace('"','')+'" '+SEARCH_TERMS
    url='https://news.google.com/rss/search?'+urllib.parse.urlencode({'q':query,'hl':'en-US','gl':'US','ceid':'US:en'})
    root=ET.fromstring(fetch(url)); leads=[]
    for item in root.findall('.//item'):
        title=clean(item.findtext('title')); summary=clean(item.findtext('description'))
        if not category(title+' '+summary): continue
        if not any(w in (title+' '+summary).lower() for w in BID_WORDS): continue
        # Require at least one meaningful part of the target's name in the result.
        key=re.sub(r'\b(county|town|village|city|district|school|area|of|ny|pa|bids|purchasing|central|region|regional|the|university|college|borough|group|properties|property|management|incorporated)\b','',source['name'].lower()).strip()
        keyparts=[w for w in re.findall(r'[a-z]{4,}',key) if w not in ('state','public','contract')]
        if keyparts and not any(w in (title+' '+summary).lower() for w in keyparts): continue
        try: published=email.utils.parsedate_to_datetime(item.findtext('pubDate','')).date().isoformat()
        except (ValueError,TypeError,OverflowError): published=''
        if published and (dt.datetime.now(dt.timezone.utc).date()-dt.date.fromisoformat(published)).days>60: continue
        result=lead(source['name'],title,(item.findtext('link') or '').strip(),summary,published)
        if result: leads.append(result)
    return leads

def run(source):
    name=source['name']; all_leads=[]; statuses=[]
    if source.get('url') and source.get('mode')=='direct_page':
        try: all_leads+=scan_direct(source); statuses.append('direct page ok')
        except Exception as e: statuses.append('direct page error: '+type(e).__name__)
    # Every target receives a named-source indirect discovery search.
    try: all_leads+=scan_indirect(source); statuses.append('indirect search ok')
    except Exception as e: statuses.append('indirect search error: '+type(e).__name__)
    return name,'; '.join(statuses),all_leads

def main():
    sources=json.loads(SOURCES.read_text(encoding='utf-8'))
    found={}; status={}; direct_ok=0; indirect_ok=0
    # Limit concurrency to avoid overwhelming public services.
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        for name,st,leads in pool.map(run,sources):
            status[name]=st
            if 'direct page ok' in st: direct_ok+=1
            if 'indirect search ok' in st: indirect_ok+=1
            for uid,item in leads:
                if uid not in found or item['lead_type']=='direct website candidate': found[uid]=item
    status['SAM.gov']='deferred'
    data={'updated':dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
          'opportunities':sorted(found.values(),key=lambda x:x.get('published',''),reverse=True)[:250],
          'source_status':status,
          'coverage_note':f'{len(sources)} named targets configured for indirect public-news discovery; {indirect_ok} indirect searches succeeded; {direct_ok} direct procurement pages fetched successfully. Indirect search is NOT direct website monitoring. Leads are unverified; check active bid status, deadlines, location and 2-hour drive time. SAM.gov deferred.'}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(f'Targets: {len(sources)}; indirect searches succeeded: {indirect_ok}; direct pages succeeded: {direct_ok}; candidate leads: {len(found)}')

if __name__=='__main__': main()
