"""Contract Radar: context-aware public bid discovery, 102 targets.
Only 13 configured sources have direct URLs; remaining sources use indirect RSS searches.
A successful fetch is not proof that all procurement listings were extracted.
"""
import concurrent.futures
import datetime as dt
import email.utils
import hashlib
from html.parser import HTMLParser
import json
import pathlib
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / 'data' / 'opportunities.json'
SOURCES = ROOT / 'sources.json'
CATEGORIES = {
    'Tree removal': ['tree removal','tree cutting','tree felling','hazard tree','tree services','tree work','tree clearing'],
    'Tree trimming': ['tree trimming','tree pruning','tree maintenance','arborist','tree care','tree management'],
    'Land clearing': ['land clearing','site clearing','lot clearing','clearing and grubbing','site preparation','stump removal'],
    'Vegetation management': ['vegetation management','brush clearing','brush removal','brush cutting','right of way','right-of-way','line clearance','roadside mowing','forestry mowing','invasive species','grounds maintenance','landscape maintenance','vegetation control','brush hogging'],
    'Storm cleanup': ['storm debris','storm cleanup','debris removal','disaster debris','emergency tree','storm damage'],
}
BID_TERMS = ('bid','rfp','rfq','solicitation','tender','proposal','contract','procurement','invitation','request for','quotes','bids.aspx','bidid=','opportunity','advertisement')
LINK_HINTS = ('bid','rfp','rfq','solicitation','proposal','contract','procurement','opportunity','notice','advertisement','document','download','details','view','pdf','bidid=')
NOW = dt.datetime.now(dt.timezone.utc)

def norm(s): return re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',s or '')).strip()
def matches(text):
    t=text.lower()
    return next((name for name,terms in CATEGORIES.items() if any(term in t for term in terms)),None)
def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; ContractRadar/4.0; public bid discovery)','Accept':'text/html,application/rss+xml,application/xml;q=0.9,*/*;q=0.5'})
    with urllib.request.urlopen(req,timeout=12) as r:
        if r.status!=200: raise ValueError('HTTP '+str(r.status))
        if 'pdf' in r.headers.get('Content-Type','').lower(): return ''
        return r.read(1_000_000).decode('utf-8','replace')

class Page(HTMLParser):
    def __init__(self):
        super().__init__();self.links=[];self.text=[];self.active=None;self.skip=0
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag in ('script','style'): self.skip+=1
        if tag=='a': self.active=[a.get('href') or '',[],len(self.text)]
    def handle_data(self,s):
        if self.skip:return
        s=norm(s)
        if s:
            self.text.append(s)
            if self.active is not None:self.active[1].append(s)
    def handle_endtag(self,tag):
        if tag in ('script','style'):self.skip=max(0,self.skip-1)
        if tag=='a' and self.active is not None:
            href,parts,pos=self.active
            self.links.append((norm(' '.join(parts)),href,pos))
            self.active=None

def make_lead(source,title,url,description='',published='',kind='unverified candidate'):
    cat=matches(title+' '+description)
    if not cat or not url.startswith(('https://','http://')):return None
    url=url.split('#')[0]
    uid=hashlib.sha256(url.encode()).hexdigest()[:16]
    return uid,{'id':uid,'title':norm(title)[:220],'summary':norm(description)[:500], 'url':url,'source':source,'location':'Unverified â confirm within 2 hours of Elmira','category':cat,'published':published,'status':'unverified','lead_type':kind}

def direct(source):
    base=source['url'];page=Page();page.feed(fetch(base));found=[];candidates=[]
    for title,href,pos in page.links:
        url=urllib.parse.urljoin(base,href)
        if not url.startswith(('https://','http://')):continue
        if urllib.parse.urlparse(url).netloc!=urllib.parse.urlparse(base).netloc:continue
        context=norm(' '.join(page.text[max(0,pos-18):pos+22]))[:650]
        descriptor=(title+' '+context)
        if matches(descriptor) and (any(w in (title+' '+href).lower() for w in BID_TERMS) or any(w in context.lower() for w in BID_TERMS)):
            item=make_lead(source['name'],title if matches(title) else context[:130],url,context,kind='direct page candidate')
            if item:found.append(item)
        if any(w in (title+' '+href).lower() for w in LINK_HINTS) and url!=base and not url.lower().split('?')[0].endswith(('.pdf','.doc','.docx','.zip')):
            candidates.append((title,url))
    # Visit a bounded number of same-host listing pages, including generic "View bid" links.
    seen=set()
    for title,url in candidates[:12]:
        if url in seen:continue
        seen.add(url)
        try:
            detail=Page();detail.feed(fetch(url))
            body=norm(' '.join(detail.text))[:10000]
            if matches(body) and (any(w in (title+' '+url).lower() for w in BID_TERMS) or any(w in body[:1800].lower() for w in BID_TERMS)):
                # Context around first matching service term, not the generic navigation header.
                lower=body.lower();hits=[lower.find(term) for group in CATEGORIES.values() for term in group if term in lower]
                p=min(hits) if hits else 0
                snippet=body[max(0,p-180):p+450]
                lead_title=title if matches(title) else snippet[:130]
                item=make_lead(source['name'],lead_title,url,snippet,kind='direct detail candidate')
                if item:found.append(item)
        except Exception:pass
    return found,len(candidates),len(seen)

def indirect(source):
    name=source['name'];q='"'+name.replace('"','')+'" ("tree removal" OR "tree trimming" OR "vegetation management" OR "land clearing" OR "grounds maintenance" OR "right of way" OR "brush clearing" OR "storm debris") (bid OR RFP OR contract OR procurement)'
    url='https://news.google.com/rss/search?'+urllib.parse.urlencode({'q':q,'hl':'en-US','gl':'US','ceid':'US:en'})
    root=ET.fromstring(fetch(url));found=[]
    for item in root.findall('.//item'):
        title=norm(item.findtext('title'));summary=norm(item.findtext('description'))
        if not matches(title+' '+summary) or not any(w in (title+' '+summary).lower() for w in BID_TERMS):continue
        try:date=email.utils.parsedate_to_datetime(item.findtext('pubDate','')).date();published=date.isoformat()
        except (TypeError,ValueError,OverflowError):published=''
        if published and (NOW.date()-date).days>90:continue
        candidate=make_lead(name,title,(item.findtext('link') or '').strip(),summary,published,'indirect news candidate')
        if candidate:found.append(candidate)
    return found

def run(source):
    statuses=[];leads=[];name=source['name']
    if source.get('url') and source.get('mode')=='direct_page':
        try:
            items,links,visited=direct(source);leads.extend(items)
            statuses.append(f'direct fetched; {links} detail candidates; {visited} detail checks; {len(items)} matches')
        except Exception as e:statuses.append('direct error: '+type(e).__name__)
    try:
        items=indirect(source);leads.extend(items)
        statuses.append(f'indirect RSS ok; {len(items)} matches')
    except Exception as e:statuses.append('indirect RSS error: '+type(e).__name__)
    return name,'; '.join(statuses),leads

def main():
    sources=json.loads(SOURCES.read_text(encoding='utf-8'))
    found={};statuses={};direct_count=0;indirect_count=0
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        for name,status,leads in pool.map(run,sources):
            statuses[name]=status
            if 'direct fetched' in status:direct_count+=1
            if 'indirect RSS ok' in status:indirect_count+=1
            for uid,lead in leads:
                if uid not in found or (lead['lead_type'].startswith('direct') and not found[uid]['lead_type'].startswith('direct')):found[uid]=lead
    statuses['SAM.gov']='deferred'
    data={'updated':NOW.isoformat(timespec='seconds'),'opportunities':sorted(found.values(),key=lambda x:x.get('published',''),reverse=True)[:300], 'source_status':statuses,'coverage_note':f'{len(sources)} target searches configured; {indirect_count} indirect RSS searches completed; {direct_count} direct home pages fetched. Detail pages checked where discoverable. Results are unverified, not a complete bid inventory; confirm bid status, deadline and drive time. SAM.gov deferred.'}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(f'Sources {len(sources)}, indirect {indirect_count}, direct {direct_count}, leads {len(found)}')
if __name__=='__main__':main()
