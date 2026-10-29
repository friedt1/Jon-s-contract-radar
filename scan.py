"""Jon's Contract Radar: direct public-bid discovery + 102 named-target news discovery.
Public pages only. No login bypass. Candidates are NOT verified open bids.
Python 3.12 standard library. Optional `pdftotext` executable for PDF attachments.
"""
import concurrent.futures as cf
import datetime as dt
import email.utils
from zoneinfo import ZoneInfo
import notice_identity
from html.parser import HTMLParser
import json
import pathlib
import re
import subprocess
import tempfile
import urllib.parse as up
import urllib.request as ur
import xml.etree.ElementTree as ET
import local_bid_rss
import public_bid_pagination as public_pages
import civicplus_bids
import robots_policy
import source_health
import opportunity_triage
from submission_deadlines import submission_deadline, submission_deadline_details, explicit_closing_passed

ROOT = pathlib.Path(__file__).resolve().parent
SOURCES = ROOT / 'sources.json'
OUT = ROOT / 'data' / 'opportunities.json'
NOW = dt.datetime.now(dt.timezone.utc)
CATEGORIES = {
 'Tree removal': ('tree removal','removal of trees','removal of hazardous trees','hazardous tree','tree and stump removal','tree and brush removal','tree cutting','tree felling','hazard tree','tree service','tree work','tree clearing','stump removal','stump grinding','arborist'),
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
 return submission_deadline(text)

def closed(text):
 """Recognize closed solicitations, not ordinary worksite road closures.

 A notice about removing trees on a closed road is not a closed bid.
 Bare 'Closed' is still accepted for explicit status-only fields.
 """
 text = norm(text)
 if re.fullmatch(r'(?:closed|awarded|cancelled|canceled|expired)', text, re.I):
  return True
 return bool(re.search(
  r'\b(?:awarded|cancelled|canceled|expired|bid results|award notice|'
  r'no (?:open|current|active) bids)\b'
  r'|\b(?:bid(?:ding)?|solicitation|rfp|rfq|contract|opportunity|status)'
  r'\s+(?:is\s+)?(?:now\s+)?closed\b'
  r'|\bstatus\s*:\s*closed\b'
  r'|\bclosed\s+(?:for|to)\s+(?:bids?|proposals?|submissions?)\b',
  text, re.I))

def eligible(text, source='', today=None):
 today=today or NOW.astimezone(ZoneInfo('America/New_York')).date()
 if not category(text) or not bidlike(text): return False
 if closed(text): return False
 due=deadline(text)
 if due and dt.date.fromisoformat(due)<today: return False
 if source in BROAD_SOURCES and not local_evidence(text): return False
 return True

class RobotsAwareRedirect(ur.HTTPRedirectHandler):
 def redirect_request(self, req, fp, code, msg, headers, newurl):
  robots_policy.assert_allowed(newurl)
  return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url, binary=False):
 robots_policy.assert_allowed(url)
 req=ur.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; JonsContractRadar/5.0; public listings)','Accept':'text/html,application/rss+xml,application/xml,application/pdf;q=0.8,*/*;q=0.4'})
 with ur.build_opener(RobotsAwareRedirect()).open(req,timeout=14) as r:
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
 url=notice_identity.canonical_url(url)
 if not cat or not eligible(text,source) or not eligible(norm(title+' '+description),source) or not url:return
 uid=notice_identity.notice_id(url)
 lead={'id':uid,'title':norm(title)[:220] or 'Possible tree-service contract','summary':norm(description)[:550], 'url':url,'source':source,'location':'NY/PA target area — driving time from Elmira unverified','category':cat,'deadline':deadline(text),'published':'','status':'unverified','lead_type':kind,'deadline_status':'date extracted; confirm time and amendments' if deadline(text) else 'unknown — verify original posting'}
 if uid not in out or len(lead['summary'])>len(out[uid]['summary']):out[uid]=lead

def annotate_explicit_closing(out, url, text):
 """Preserve an observed submission time, never a questions/site-visit time."""
 uid = notice_identity.notice_id(url)
 if uid not in out:
  return
 date, clock = submission_deadline_details(text)
 if date and clock:
  out[uid]['deadline'] = date
  out[uid]['deadline_time'] = clock
  out[uid]['deadline_timezone'] = 'America/New_York (NY/PA agency-local assumption)'
  out[uid]['deadline_status'] = 'explicit submission date/time; timezone assumed from issuing authority'


def excluded_url(url):
 return bool(re.search(r'archive|bid[-_ ]?results|bid[-_ ]?recordings|award|\.mp4(?:$|\?)|/projects(?:$|\?)|project-showcase',url,re.I))

def allowed_link(url,base):
 host=up.urlparse(url).hostname or ''
 if up.urlparse(url).scheme not in ('http','https'):return False
 return host==up.urlparse(base).hostname or any(host==x or host.endswith('.'+x) for x in ('bonfirehub.com','bidnetdirect.com','pennbid.net','publicpurchase.com'))

def safe_detail_url(origin, href):
 """Reject malformed, off-host, credentialed and non-web detail links before fetch.

 A malformed URL should not consume the bounded detail budget or turn a
 public-source scan into an accidental request to an unrelated host.
 """
 if not isinstance(href, str) or not href or any(ord(c) < 33 or ord(c) == 127 or c == '\\' for c in href):
  return ''
 if re.search(r'%(?:0[0-9a-f]|1[0-9a-f]|7f)', href, re.I):
  return ''
 try:
  url = up.urljoin(origin, href)
  parsed = up.urlsplit(url)
  if parsed.scheme not in ('http', 'https') or not parsed.hostname:
   return ''
  if parsed.username is not None or parsed.password is not None:
   return ''
  if parsed.port not in (None, 80, 443):
   return ''
  return url if allowed_link(url, origin) else ''
 except ValueError:
  return ''

def is_individual_notice_link(url):
 """A bid-detail shaped link, not a procurement index or PDF attachment.

 This is only a *listing detection* hint. It never establishes that a
 solicitation is real, open, or permitted to fetch.
 """
 try:
  parsed = up.urlparse(url)
  if parsed.path.lower().endswith('.pdf'):
   return False
  if any(key.lower() == 'bidid' for key in up.parse_qs(parsed.query)):
   return True
  return bool(re.search(
   r'/(?:bids?|rfp|rfq|solicitations?|tenders?|opportunities?)/[^/]+/?$',
   parsed.path, re.I))
 except ValueError:
  return False


def scan_civicplus(src, listing_pages, page_errors):
 """Only individual public bidID notices; never treat the whole listing as a bid."""
 name = src['name']
 records = {}
 for page, origin in listing_pages:
  for row in civicplus_bids.listing_records(page, origin):
   records.setdefault(row['url'], row)
 found = {}
 checked = 0
 individual_details_fetched = 0
 errors = []
 closed_count = 0
 expired_count = 0
 # Prioritize listing matches, but also inspect generic bid titles: the tree-work
 # scope may exist only on the individual detail page. Keep the 36-detail cap.
 prioritized = sorted(records.values(), key=lambda row:
                      0 if category(row['title'] + ' ' + row['description']) else 1)
 for row in prioritized:
  if row['open_status'] in civicplus_bids.CLOSED:
   closed_count += 1
   continue
  # The county listing is not the worksite; routing remains unverified.
  if checked >= civicplus_bids.MAX_DETAILS:
   break
  checked += 1
  detail_status = 'unknown'
  detail_due = ''
  detail_time = ''
  detail_scope = ''
  detail_worksite = ''
  try:
   blob, kind, final = fetch(row['url'], binary=True)
   # Never publish a listing-only candidate when the individual notice could
   # not be read. A failed fetch or redirect to a homepage is not evidence.
   if 'html' not in kind and not blob.lstrip().startswith(b'<'):
    errors.append('unsupported detail content')
    continue
   resolved = civicplus_bids.individual_url(final, row['url'])
   expected_id = next((v[0] for k, v in up.parse_qs(up.urlparse(row['url']).query).items()
                       if k.lower() == 'bidid' and v), '')
   actual_id = next((v[0] for k, v in up.parse_qs(up.urlparse(final).query).items()
                     if k.lower() == 'bidid' and v), '')
   if not resolved or actual_id != expected_id:
    errors.append('detail redirected away from original bid')
    continue
   detail = parse_html(blob.decode('utf-8', 'replace'))
   body = ' '.join(detail.parts)
   if not body:
    errors.append('empty detail content')
    continue
   # A server can retain ?bidID= in the URL while serving its generic
   # homepage. Require at least one bid-specific detail label as well.
   if not re.search(r'\b(?:Bid\s+(?:Number|Title)|Closing\s+Date/Time|Description|Status)\s*:', body, re.I):
    errors.append('missing individual bid fields')
    continue
   # Count only a successfully fetched, non-empty notice whose bidID still
   # matches the listing. Attempts and homepage reads are not bid details.
   individual_details_fetched += 1
   detail_status = civicplus_bids.status_of(body)
   detail_due, detail_time = civicplus_bids.detail_closing_of(body)
   detail_scope = civicplus_bids.detail_description(body)
   detail_worksite = civicplus_bids.detail_worksite(body)
  except Exception as e:
   errors.append(error_label(e))
   continue
  if detail_status in civicplus_bids.CLOSED:
   closed_count += 1
   continue
  # The individual notice takes precedence over a stale listing date.
  due = detail_due or row['deadline']
  due_time = detail_time if detail_due else row['deadline_time']
  if civicplus_bids.closing_passed(due, due_time, NOW):
   expired_count += 1
   continue
  scope = detail_scope or row['description']
  # A fetched individual notice takes precedence over a misleading listing
  # title. Never publish an unrelated notice merely because its title matched.
  if not category(detail_scope if detail_scope else row['title'] + ' ' + scope):
   continue
  evidence = row['title'] + ' bid ' + scope + (' Due date: ' + due if due else '')
  summary = ('Bid No. ' + row['bid_number'] + '. ' if row['bid_number'] else '') + scope
  if due:
   summary += ' Due date: ' + due
  add_lead(found, name, row['title'], row['url'], summary, 'individual county bid candidate', evidence=evidence)
  uid = notice_identity.notice_id(row['url'])
  if uid in found:
   found[uid].update({
    'agency': name.replace(' bids', '') + ' (issuing authority)',
    'scope': detail_scope or row['title'],
    'bid_number': row['bid_number'],
    'location': detail_worksite or 'Worksite unverified; county issuing authority is not a worksite',
    'location_verified': False,
    'open_status': 'detail_listed_open' if detail_status == 'open' else
                   'listing_open' if row['open_status'] == 'open' else 'unknown',
    'deadline_time': due_time,
    'deadline_timezone': 'unverified',
    'deadline_source': 'individual notice' if detail_due else 'listing' if due else 'unknown',
    'travel_verified': False,
    'travel_category': 'unverified',
   })
 status = (f'direct fetched; {len(listing_pages)} listing pages; '
           f'{len(records)} individual bid records; {checked} relevant details checked; '
           f'{individual_details_fetched} individual bid details fetched; '
           f'{len(found)} unverified candidates; {closed_count} closed; {expired_count} expired')
 if errors:
  status += f'; {len(errors)} detail errors: ' + ','.join(sorted(set(errors)))
 if page_errors:
  status += f'; {len(page_errors)} pagination errors: ' + ','.join(sorted(set(page_errors)))
 return list(found.values()), status


def individual_metadata_notice(body, url):
 """Require bid-specific fields before treating a metadata table as one notice.

 A table of many solicitations, a homepage, or a navigation menu must not
 become an individual bid merely because it mentions tree removal.
 """
 return (is_individual_notice_link(url)
         and bool(re.search(r'\b(?:Bid\s+(?:Number|No\.?)|Solicitation\s+(?:Number|ID))\s*:', body, re.I))
         and bool(re.search(r'\bDescription\s*:', body, re.I)))


def metadata_description(body):
 """Isolate the solicitation description from subsequent metadata fields."""
 match = re.search(
  r'\bDescription\s*:\s*(.+?)(?=\b(?:Closing\s+Date(?:/Time)?|'
  r'Bid\s+(?:Number|No\.?|Title)|Solicitation\s+(?:Number|ID)|'
  r'Status|Contact|Related\s+Documents|Publication\s+Date)\s*:|$)',
  body, re.I | re.S)
 return norm(match.group(1))[:1200] if match else ''


def scan_direct(src):
 base=src['url'];name=src['name'];found={};visited=set();errors=[];pdfs=0;nested_listing_pages=0;metadata_details=0
 html,ctype,final=fetch(base)
 if 'html' not in ctype and not html.lstrip().startswith('<'):return [],'unsupported content type'
 page=parse_html(html)
 listing_pages=[(page,final)]
 page_errors=[]
 if name in public_pages.PUBLIC_LISTINGS:
  seen_pages={final};cursor=0
  while cursor<len(listing_pages) and len(listing_pages)<public_pages.MAX_PAGES:
   current,origin=listing_pages[cursor];cursor+=1
   for next_url in public_pages.next_pages(current.links,origin,seen_pages):
    if len(listing_pages)>=public_pages.MAX_PAGES:break
    seen_pages.add(next_url)
    try:
     extra,extra_type,extra_final=fetch(next_url)
     if 'html' not in extra_type and not extra.lstrip().startswith('<'):
      page_errors.append('unsupported pagination content');continue
     listing_pages.append((parse_html(extra),extra_final))
    except Exception as e:page_errors.append(error_label(e))
 if name in civicplus_bids.SOURCES and any(civicplus_bids.listing_records(p, origin) for p, origin in listing_pages):
  return scan_civicplus(src, listing_pages, page_errors)
 # Keep each table/list record isolated from neighboring bid scopes and dates.
 max_details=public_pages.MAX_PUBLIC_DETAILS if name in public_pages.PUBLIC_LISTINGS else MAX_DETAIL
 candidates=[]
 listing_links=[(title,href,pos,p.link_rows.get(href,title),origin)
                for p,origin in listing_pages for title,href,pos in p.links]
 for title,href,pos,context,origin in listing_links:
  url=safe_detail_url(origin,href)
  if not url:continue
  # Follow only same-host notices and explicitly permitted platform links.
  same_host=up.urlparse(url).hostname==up.urlparse(origin).hostname
  context=context[:1500]
  descriptor=title+' '+context
  # Listing rows stay isolated; detail pages supply missing scope and deadlines.
  # A listing row is discovery evidence only. Never publish its link until
  # the corresponding individual notice has actually been fetched and parsed.
  if not excluded_url(url) and (any(x in (title+' '+href).lower() for x in FOLLOW_HINTS) or (category(descriptor) and same_host)) and url!=origin:
   # A generic 'Details' label can still point directly to a bid notice.
   # Prioritize its URL shape before unrelated purchasing/navigation links.
   score=(6 if is_individual_notice_link(url) else 0)+(4 if category(title) else 0)+(3 if bidlike(title+' '+href) else 0)+(1 if category(context) else 0)
   candidates.append((score,url,title,context))
 # Row parsing is used to discover relevant detail URLs, not to invent bid links.
 candidates.sort(key=lambda x:-x[0])
 # Nested bid links must be examined before unrelated siblings exhaust the
 # bounded detail budget. Python's list iterator visits inserted entries next.
 for candidate_index, (_,url,title,context) in enumerate(candidates):
  if url in visited or len(visited)>=max_details:continue
  visited.add(url)
  try:
   blob,kind,final_url=fetch(url,binary=True)
   # Redirects must not turn a permitted source link into an untrusted host.
   if not safe_detail_url(url,final_url) or excluded_url(final_url):continue
   if 'pdf' in kind or url.lower().split('?')[0].endswith('.pdf'):
    if pdfs>=MAX_PDF:continue
    pdfs+=1;text=pdf_text(blob)
    if closed(text) or (deadline(text) and deadline(text)<NOW.astimezone(ZoneInfo('America/New_York')).date().isoformat()) or explicit_closing_passed(text,NOW):
     found.pop(notice_identity.notice_id(url),None);continue
    if category(text) and (bidlike(title+' '+url) or bidlike(text[:3000])):
     key=category(text);p=text.lower().find(next((t for t in CATEGORIES[key] if t in text.lower()),''))
     snippet=text[max(0,p-150):p+500]
     if eligible(text,name):
      add_lead(found,name,title if category(title) else snippet[:130],final_url,snippet+' '+('Deadline: '+deadline(text) if deadline(text) else ''),'PDF bid candidate',evidence=text)
      annotate_explicit_closing(found,final_url,text)
   elif 'html' in kind or blob.lstrip().startswith(b'<'):
    p=parse_html(blob.decode('utf-8','replace'));body=norm(' '.join(p.parts))[:20000]
    # A listing containing many bids must be handled as separate rows.
    records=p.rows if p.rows else [body]
    if (not p.rows or individual_metadata_notice(body, final_url)) and (closed(body) or (deadline(body) and deadline(body)<NOW.astimezone(ZoneInfo('America/New_York')).date().isoformat()) or explicit_closing_passed(body,NOW)):
     found.pop(notice_identity.notice_id(url),None);continue
    nested_notice_links = False
    nested_candidates = []
    for label,href,_ in p.links:
     row=p.link_rows.get(href,label)
     target=safe_detail_url(final_url,href)
     if target and not excluded_url(target):
      # A page linking to distinct individual bid URLs is a listing, even
      # when it uses divs rather than tr/article/li elements. Do not emit
      # the listing URL as an individual solicitation.
      if target != final_url and is_individual_notice_link(target):
       nested_notice_links = True
      # A nested listing row likewise only queues a detail URL. It cannot
      # establish that the bid is current, relevant, or even accessible.
      if len(nested_candidates)<max_details and target not in visited and (category(row) or bidlike(label+' '+href)):
       priority = 8 if is_individual_notice_link(target) else 0
       nested_candidates.append((priority,target,label,row))
    if nested_candidates:
     nested_candidates.sort(key=lambda item: -item[0])
     candidates[candidate_index+1:candidate_index+1] = nested_candidates
    if nested_notice_links and not p.rows:
     nested_listing_pages += 1
    metadata_notice = individual_metadata_notice(body, final_url) and not nested_notice_links
    if metadata_notice:
     metadata_details += 1
    # A single notice's metadata rows are not a listing of separate bids.
    # Only the Description field, never navigation text, establishes relevance.
    scope = metadata_description(body) if metadata_notice else body
    if (not p.rows or metadata_notice) and not nested_notice_links and category(scope) and eligible(scope + (' bid' if metadata_notice else '') + (' Due date: ' + deadline(body) if deadline(body) else ''), name) and not closed(body) and not explicit_closing_passed(body,NOW):
     key=category(scope);match=next((t for t in CATEGORIES[key] if t in scope.lower()),'')
     ix=scope.lower().find(match);snippet=scope[max(0,ix-160):ix+520]
     add_lead(found,name,title if category(title) else snippet[:130],final_url,('Bid description: ' if metadata_notice else '')+snippet+' '+('Deadline: '+deadline(body) if deadline(body) else ''),'individual metadata bid candidate' if metadata_notice else 'direct detail candidate',evidence=body)
     annotate_explicit_closing(found,final_url,body)
  except Exception as e:errors.append(type(e).__name__)

 rendering='; dynamic/login portal: extraction incomplete' if not page.rows and any(x in html.lower() for x in ('enable javascript','ng-app','id="app"','id="root"','sign in','log in')) else ''
 return list(found.values()),f'direct fetched; {len(listing_pages)} listing pages; {len(visited)} details checked; {metadata_details} individual bid details fetched; {pdfs} PDFs checked; {len(found)} candidates; {nested_listing_pages} nested listing pages excluded as notices'+(f'; {len(errors)} detail errors: '+','.join(sorted(set(errors))) if errors else '')+(f'; {len(page_errors)} pagination errors: '+','.join(sorted(set(page_errors))) if page_errors else '')+rendering

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
   uid=notice_identity.notice_id((item.findtext('link') or '').strip())
   if uid in found: found[uid]['published']=date.isoformat()
 return list(found.values())

def error_label(error):
 return type(error).__name__ + (' HTTP '+str(error.code) if hasattr(error,'code') else '')

def run(src):
 statuses=[];leads=[]
 if src.get('url') and src.get('mode')=='direct_page':
  try:
   items,st=scan_direct(src);leads.extend(items);statuses.append(st)
  except robots_policy.RobotsDenied as e:statuses.append('direct blocked by robots policy: '+str(e))
  except Exception as e:statuses.append('direct error: '+error_label(e))
 if src['name']=='Elmira Next local bids':
  try:
   xml,ctype,_=fetch(local_bid_rss.FEED_URL)
   records=local_bid_rss.parse(xml,now=NOW)
   vetted={}
   for item in records:
    # Discovery only; published candidates still require source verification.
    item_leads={}
    add_lead(item_leads,src['name'],item['title'],item['url'],item['description'],'public bid RSS candidate')
    for uid,lead in item_leads.items():
     lead['published']=item['published']
     vetted[uid]=lead
   leads.extend(vetted.values())
   statuses.append(f'local bid RSS fetched; {len(records)} notices; {len(vetted)} unverified tree-service candidates')
  except Exception as e:
   statuses.append('local bid RSS error: '+error_label(e))
 try:
  items=scan_news(src);leads.extend(items);statuses.append(f'indirect RSS ok; {len(items)} candidates')
 except Exception as e:statuses.append('indirect RSS error: '+error_label(e))
 if src['name'] in ('BidNet NY platform','PennBid platform'):
  statuses.append('individual listing ingestion not connected; provider-approved feed/access not established')
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
 local_today=NOW.astimezone(ZoneInfo('America/New_York')).date()
 for uid,lead in found.items():
  lead.update(opportunity_triage.review_assessment(lead, local_today))
  old=historical.get(uid,{})
  old.pop('excluded_reason',None)
  historical[uid]={**old,**lead,'first_seen':old.get('first_seen',NOW.isoformat(timespec='seconds')),'last_seen':NOW.isoformat(timespec='seconds')}
 # Cap history to keep repository commits manageable.
 historical=dict(sorted(historical.items(),key=lambda x:x[1].get('last_seen',''),reverse=True)[:1000])
 history_path.parent.mkdir(parents=True,exist_ok=True)
 history_path.write_text(json.dumps({'updated':NOW.isoformat(timespec='seconds'),'opportunities':historical},indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 # A missed expired notice may remain in history for audit, never in active feed.
 published_leads=sorted((lead for lead in found.values() if lead['review_priority']!='expired_check'),
                        key=lambda x:(x['review_score'], x.get('published','')),reverse=True)[:300]
 direct=sum('direct fetched' in x for x in status.values());indirect=sum('indirect RSS ok' in x for x in status.values())
 # Configuration, page fetch, and individual-bid extraction are distinct states.
 direct_names={s['name'] for s in sources if s.get('mode')=='direct_page' and s.get('verified_url') is True and s.get('url')}
 coverage={
  'total_targets':len(sources),
  'direct_configured':len(direct_names),
  'pending_direct':len(sources)-len(direct_names),
  'direct_fetched':sum('direct fetched' in status.get(name,'') for name in direct_names),
  'direct_not_fetched':sum('direct fetched' not in status.get(name,'') for name in direct_names),
  'indirect_rss_succeeded':indirect,
  'verified_open_contracts':sum(x.get('status')=='verified' and x.get('open_status')=='verified_open' for x in published_leads),
  'warning':'A fetched listing page is not proof that all individual bids were extracted or that any bid is open.'
 }
 integration_status={
  'NYS Contract Reporter':'blocked: terms prohibit bulk automated access without explicit permission; authorized export parser only',
  'BidNet Direct':'not connected: individual bid listing interface/permission not established',
  'PennBid':'not connected: individual bid listing interface/permission not established',
 }
 data={'integration_status':integration_status,'source_coverage':coverage,'source_health':source_health.summarize(sources,status),'updated':NOW.isoformat(timespec='seconds'),'opportunities':published_leads,'source_status':status,'coverage_note':f'{len(sources)} named targets; {direct} direct public home pages fetched, with bounded detail/PDF checks; {indirect} indirect news searches succeeded. Direct page access does not guarantee complete extraction. Explicitly closed/expired and unrelated notices are filtered. Unknown deadlines and driving times remain unverified. {coverage['pending_direct']} targets do not have verified direct integrations. SAM.gov deferred.'}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 print(f'Targets {len(sources)}, direct fetched {direct}, indirect successful {indirect}, candidates {len(found)}')
if __name__=='__main__':main()
