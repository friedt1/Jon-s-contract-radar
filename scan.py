"""Jon's Contract Radar: direct public-bid discovery + 102 named-target news discovery.
Public pages only. No login bypass. Candidates are NOT verified open bids.
Python 3.12 standard library. Optional `pdftotext` executable for PDF attachments.
"""
import concurrent.futures as cf
import datetime as dt
import email.utils
from zoneinfo import ZoneInfo
import hashlib
from html.parser import HTMLParser
import json
import pathlib
import re
import subprocess
import tempfile
import urllib.parse as up
import urllib.request as ur
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent
SOURCES = ROOT / 'sources.json'
OUT = ROOT / 'data' / 'opportunities.json'
NOW = dt.datetime.now(dt.timezone.utc)
CATEGORIES = {
 'Tree removal': ('tree removal','removal of trees','tree and stump removal','tree and brush removal','tree cutting','tree felling','hazard tree','tree service','tree work','tree clearing','stump removal','stump grinding','arborist'),
 'Tree trimming': ('tree trimming','trimming of trees','tree pruning','tree maintenance','tree care','tree management','limb removal'),
 'Land clearing': ('land clearing','site clearing','lot clearing','clearing and grubbing','forestry mulching'),
 'Vegetation management': ('vegetation management','brush clearing','brush removal','brush cutting','right of way clearing','right-of-way clearing','line clearance','roadside mowing','forestry mowing','vegetation control','brush hogging','brush mowing'),
 'Storm cleanup': ('storm debris','storm clean-up','storm cleanup','woody debris removal','disaster debris','emergency tree','storm damage','storm response'),
}
BID_HINTS = ('bid','rfp','rfq','solicitation','tender','proposal','contract','procurement','request for','invitation to','sealed bid','quotes','bidid=','advertisement','opportunit','bonfire','pennbid')
FOLLOW_HINTS = BID_HINTS + ('view','details','notice','download','document','attachment','specification','project','current','open','pdf')
BAD_LINKS = ('mailto:','tel:','javascript:','#')
MAX_DETAIL = 18
MAX_PDF = 5
MAX_BYTES = 2_500_000


def norm(s): return re.sub(r'\s+',' ',re.sub(r'<[^>]*>',' ',s or '')).strip()
def category(s):
 t=norm(s).lower()
 return next((k for k,v in CATEGORIES.items() if any(x in t for x in v)),None)
def bidlike(s):
 return bool(re.search(r"\b(?:bids?|rf[qp]|solicitations?|tender|proposals?|contracts?|procurement|quotes?)\b|bidid=|invitation to|request for", s, re.I))

LOCAL_PLACES = ('elmira','chemung','steuben','schuyler','tompkins','horseheads','corning',
 'ithaca','bradford','tioga','lycoming','williamsport','sayre','athens','towanda','wellsboro',
 'mansfield','broome','binghamton','owego','waverly','cortland','yates','seneca','montour',
 'bath','hornell','big flats','southport','vestal','dryden','lansing','watkins glen')
BROAD_SOURCES = {'PA procurement opportunities','PA DGS construction bids','PennBid platform','BidNet NY platform','New York State DOT Region 6','PennDOT District 3'}

def local_evidence(text):
 return any(re.search(r'\b'+re.escape(x)+r'\b',text,re.I) for x in LOCAL_PLACES)

def deadline(text):
 """Only dates explicitly labeled as submission deadlines, never posting dates."""
 dates=[]
 pattern=r"(?:due(?: date)?|closing(?: date)?|bids? (?:due|received)|submit(?:ted)? (?:by|until)|deadline)[^.;\n]{0,65}?((?:\d{4}-\d{1,2}-\d{1,2})|(?:\d{1,2}/\d{1,2}/\d{2,4})|(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4}))"
 for value in re.findall(pattern,text,re.I):
  for fmt in ('%Y-%m-%d','%m/%d/%Y','%m/%d/%y','%B %d %Y','%b %d %Y'):
   try: dates.append(dt.datetime.strptime(value.replace(',',''),fmt).date());break
   except ValueError: pass
 return max(dates).isoformat() if dates else ''

def closed(text):
 return bool(re.search(r'\b(?:awarded|cancelled|canceled|expired|closed|bid results|award notice|no (?:open|current|active) bids)\b', text,re.I))

def eligible(text, source='', today=None):
 today=today or NOW.astimezone(ZoneInfo('America/New_York')).date()
 if not category(text) or not bidlike(text): return False
 if closed(text): return False
 due=deadline(text)
 if due and dt.date.fromisoformat(due)<today: return False
 if source in BROAD_SOURCES and not local_evidence(text): return False
 return True

def fetch(url, binary=False):
 req=ur.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; JonsContractRadar/5.0; public listings)','Accept':'text/html,application/rss+xml,application/xml,application/pdf;q=0.8,*/*;q=0.4'})
 with ur.urlopen(req,timeout=14) as r:
  if r.status!=200: raise ValueError('HTTP '+str(r.status))
  content=r.read(MAX_BYTES+1)
  if len(content)>MAX_BYTES: raise ValueError('page too large')
  ctype=r.headers.get('Content-Type','').lower()
  return (content,ctype,r.url) if binary else (content.decode('utf-8','replace'),ctype,r.url)

class Page(HTMLParser):
 def __init__(self):
  super().__init__();self.parts=[];self.links=[];self.active=None;self.skip=0;self.in_row=False;self.row=[];self.rows=[];self.link_rows={};self.row_links=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag in ('script','style','noscript'):self.skip+=1
  if tag in ('tr','article','li') and not self.in_row:
   self.row_tag=tag;self.in_row=True;self.row=[];self.row_links=[]
  if tag=='a':
   self.active=[a.get('href') or '',[],len(self.parts)]
   if self.in_row:self.row_links.append(a.get('href') or '')
 def handle_data(self,s):
  if self.skip:return
  s=norm(s)
  if s:
   self.parts.append(s)
   if self.active is not None:self.active[1].append(s)
   if self.in_row:self.row.append(s)
 def handle_endtag(self,tag):
  if tag in ('script','style','noscript'):self.skip=max(0,self.skip-1)
  if tag=='a' and self.active is not None:
   href,words,pos=self.active;self.links.append((norm(' '.join(words)),href,pos));self.active=None
  if self.in_row and tag==self.row_tag:
   text=norm(' '.join(self.row));self.rows.append(text)
   for href in self.row_links:self.link_rows[href]=text
   self.in_row=False;self.row=[]

def parse_html(html):
 p=Page();p.feed(html);return p

def pdf_text(blob):
 try:
  with tempfile.NamedTemporaryFile(suffix='.pdf') as f:
   f.write(blob);f.flush()
   p=subprocess.run(['pdftotext','-layout',f.name,'-'],capture_output=True,text=True,timeout=8)
   return norm(p.stdout[:30000]) if p.returncode==0 else ''
 except (FileNotFoundError,subprocess.TimeoutExpired,OSError):return ''

def add_lead(out,source,title,url,description='',kind='direct bid candidate',evidence=None):
 text=norm(evidence if evidence is not None else title+' '+description)
 cat=category(text)
 if not cat or not eligible(text,source) or not eligible(norm(title+' '+description),source) or not url.startswith(('http://','https://')) or not up.urlparse(url).hostname:return
 url=url.split('#')[0]
 uid=hashlib.sha256(url.encode()).hexdigest()[:16]
 lead={'id':uid,'title':norm(title)[:220] or 'Possible tree-service contract','summary':norm(description)[:550], 'url':url,'source':source,'location':'NY/PA target area — driving time from Elmira unverified','category':cat,'deadline':deadline(text),'published':'','status':'unverified','lead_type':kind,'deadline_status':'date extracted; confirm time and amendments' if deadline(text) else 'unknown — verify original posting'}
 if uid not in out or len(lead['summary'])>len(out[uid]['summary']):out[uid]=lead

def excluded_url(url):
 return bool(re.search(r'archive|bid[-_ ]?results|bid[-_ ]?recordings|award|\.mp4(?:$|\?)|/projects(?:$|\?)|project-showcase',url,re.I))

def allowed_link(url,base):
 host=up.urlparse(url).hostname or ''
 if up.urlparse(url).scheme not in ('http','https'):return False
 return host==up.urlparse(base).hostname or any(host==x or host.endswith('.'+x) for x in ('bonfirehub.com','bidnetdirect.com','pennbid.net','publicpurchase.com'))

def scan_direct(src):
 base=src['url'];name=src['name'];found={};visited=set();errors=[];pdfs=0
 html,ctype,final=fetch(base)
 if 'html' not in ctype and not html.lstrip().startswith('<'):return [],'unsupported content type'
 page=parse_html(html)
 # Keep each table/list record isolated from neighboring bid scopes and dates.
 candidates=[]
 for title,href,pos in page.links:
  if not href or href.startswith(BAD_LINKS):continue
  url=up.urljoin(final,href)
  if up.urlparse(url).scheme not in ('http','https'):continue
  # Avoid unrelated off-site links, but allow bid platform destinations.
  same_host=up.urlparse(url).hostname==up.urlparse(final).hostname
  platform=allowed_link(url,final)
  if not (same_host or platform):continue
  context=page.link_rows.get(href,title)[:1500]
  descriptor=title+' '+context
  # Listing rows stay isolated; detail pages supply missing scope and deadlines.
  if eligible(context,name) and not excluded_url(url):
   add_lead(found,name,title if category(title) else context[:130],url,context)
  if not excluded_url(url) and (any(x in (title+' '+href).lower() for x in FOLLOW_HINTS) or (category(descriptor) and same_host)) and url!=final:
   score=(4 if category(title) else 0)+(3 if bidlike(title+' '+href) else 0)+(1 if category(context) else 0)
   candidates.append((score,url,title,context))
 # Row parsing is used to discover relevant detail URLs, not to invent bid links.
 candidates.sort(key=lambda x:-x[0])
 for _,url,title,context in candidates:
  if url in visited or len(visited)>=MAX_DETAIL:continue
  visited.add(url)
  try:
   blob,kind,final_url=fetch(url,binary=True)
   if excluded_url(final_url):continue
   if 'pdf' in kind or url.lower().split('?')[0].endswith('.pdf'):
    if pdfs>=MAX_PDF:continue
    pdfs+=1;text=pdf_text(blob)
    if closed(text) or (deadline(text) and deadline(text)<NOW.astimezone(ZoneInfo('America/New_York')).date().isoformat()):
     found.pop(hashlib.sha256(url.split('#')[0].encode()).hexdigest()[:16],None);continue
    if category(text) and (bidlike(title+' '+url) or bidlike(text[:3000])):
     key=category(text);p=text.lower().find(next((t for t in CATEGORIES[key] if t in text.lower()),''))
     snippet=text[max(0,p-150):p+500]
     if eligible(text,name):
      add_lead(found,name,title if category(title) else snippet[:130],final_url,snippet+' '+('Deadline: '+deadline(text) if deadline(text) else ''),'PDF bid candidate',evidence=text)
   elif 'html' in kind or blob.lstrip().startswith(b'<'):
    p=parse_html(blob.decode('utf-8','replace'));body=norm(' '.join(p.parts))[:20000]
    # A listing containing many bids must be handled as separate rows.
    records=p.rows if p.rows else [body]
    if not p.rows and (closed(body) or (deadline(body) and deadline(body)<NOW.astimezone(ZoneInfo('America/New_York')).date().isoformat())):
     found.pop(hashlib.sha256(url.split('#')[0].encode()).hexdigest()[:16],None);continue
    if len(records)==1 and category(body) and eligible(body,name):
     key=category(body);match=next((t for t in CATEGORIES[key] if t in body.lower()),'')
     ix=body.lower().find(match);snippet=body[max(0,ix-160):ix+520]
     add_lead(found,name,title if category(title) else snippet[:130],final_url,snippet+' '+('Deadline: '+deadline(body) if deadline(body) else ''),'direct detail candidate',evidence=body)
    for label,href,_ in p.links:
     row=p.link_rows.get(href,label)
     target=up.urljoin(final_url,href)
     if href and not excluded_url(target) and allowed_link(target,final_url):
      if eligible(row,name):add_lead(found,name,label if category(label) else row[:130],target,row)
      if len(candidates)<MAX_DETAIL*4 and target not in visited and (category(row) or bidlike(label+' '+href)):
       candidates.append((0,target,label,row))
  except Exception as e:errors.append(type(e).__name__)

 rendering='; dynamic/login portal: extraction incomplete' if not page.rows and any(x in html.lower() for x in ('enable javascript','ng-app','id="app"','id="root"','sign in','log in')) else ''
 return list(found.values()),f'direct fetched; {len(visited)} details checked; {pdfs} PDFs checked; {len(found)} candidates'+(f'; {len(errors)} detail errors: '+','.join(sorted(set(errors))) if errors else '')+rendering

def scan_news(src):
 name=src['name'];query=src.get('discovery_query',name);q='"'+query.replace('"','')+'" ("tree removal" OR "tree trimming" OR "vegetation management" OR "land clearing" OR "forestry mulching" OR "storm cleanup" OR "brush clearing" OR "storm debris") (bid OR RFP OR contract OR procurement)'
 url='https://news.google.com/rss/search?'+up.urlencode({'q':q,'hl':'en-US','gl':'US','ceid':'US:en'})
 xml,_,_=fetch(url);root=ET.fromstring(xml);found={}
 for item in root.findall('.//item'):
  title=norm(item.findtext('title'));summary=norm(item.findtext('description'))
  if not category(title+' '+summary) or not bidlike(title+' '+summary):continue
  if src.get('require_local_evidence') and not local_evidence(title+' '+summary):continue
  try:date=email.utils.parsedate_to_datetime(item.findtext('pubDate','')).date()
  except (ValueError,TypeError,OverflowError):date=None
  if date is None or not 0 <= (NOW.date()-date).days <= 90:continue
  add_lead(found,name,title,(item.findtext('link') or '').strip(),summary,'indirect news candidate')
  if date:
   uid=hashlib.sha256(((item.findtext('link') or '').strip().split('#')[0]).encode()).hexdigest()[:16]
   if uid in found: found[uid]['published']=date.isoformat()
 return list(found.values())

def error_label(error):
 return type(error).__name__ + (' HTTP '+str(error.code) if hasattr(error,'code') else '')

def run(src):
 statuses=[];leads=[]
 if src.get('url') and src.get('mode')=='direct_page':
  try:
   items,st=scan_direct(src);leads.extend(items);statuses.append(st)
  except Exception as e:statuses.append('direct error: '+error_label(e))
 try:
  items=scan_news(src);leads.extend(items);statuses.append(f'indirect RSS ok; {len(items)} candidates')
 except Exception as e:statuses.append('indirect RSS error: '+error_label(e))
 return src['name'],'; '.join(statuses),leads

def main():
 sources=json.loads(SOURCES.read_text(encoding='utf-8'));status={};found={}
 if len(sources)!=102 or len({s['name'] for s in sources})!=102:
  raise ValueError('Expected 102 uniquely named discovery targets')
 with cf.ThreadPoolExecutor(max_workers=5) as pool:
  for name,st,items in pool.map(run,sources):
   status[name]=st
   for lead in items:
    uid=lead['id']
    if uid not in found or (lead['lead_type']!='indirect news candidate' and found[uid]['lead_type']=='indirect news candidate'):found[uid]=lead
 status['SAM.gov']='deferred'
 if not any('direct fetched' in x or 'indirect RSS ok' in x for x in status.values()):
  raise RuntimeError('All sources failed; preserving the previous feed and history')
 # Keep a separate history of discoveries, including leads no longer in the latest scan.
 history_path=ROOT/'data'/'history.json'
 try:
  previous=json.loads(history_path.read_text(encoding='utf-8')) if history_path.exists() else {}
  historical=previous.get('opportunities',{}) if isinstance(previous,dict) else {}
  if not isinstance(historical,dict):historical={}
 except (ValueError,OSError):historical={}
 for uid,lead in found.items():
  old=historical.get(uid,{})
  old.pop('excluded_reason',None)
  historical[uid]={**old,**lead,'first_seen':old.get('first_seen',NOW.isoformat(timespec='seconds')),'last_seen':NOW.isoformat(timespec='seconds')}
 # Cap history to keep repository commits manageable.
 historical=dict(sorted(historical.items(),key=lambda x:x[1].get('last_seen',''),reverse=True)[:1000])
 history_path.parent.mkdir(parents=True,exist_ok=True)
 history_path.write_text(json.dumps({'updated':NOW.isoformat(timespec='seconds'),'opportunities':historical},indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 direct=sum('direct fetched' in x for x in status.values());indirect=sum('indirect RSS ok' in x for x in status.values())
 data={'updated':NOW.isoformat(timespec='seconds'),'opportunities':sorted(found.values(),key=lambda x:x.get('published',''),reverse=True)[:300],'source_status':status,'coverage_note':f'{len(sources)} named targets; {direct} direct public home pages fetched, with bounded detail/PDF checks; {indirect} indirect news searches succeeded. Direct page access does not guarantee complete extraction. Explicitly closed/expired and unrelated notices are filtered. Unknown deadlines and driving times remain unverified. {len(sources)-sum(x.get('mode')=='direct_page' for x in sources)} targets use indirect discovery only. SAM.gov deferred.'}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 print(f'Targets {len(sources)}, direct fetched {direct}, indirect successful {indirect}, candidates {len(found)}')
if __name__=='__main__':main()
