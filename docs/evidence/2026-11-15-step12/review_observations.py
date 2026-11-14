"""Independently replay saved STEP12 evidence without starting apps or databases."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,parse_qs
from collections import Counter
import datetime,gzip,hashlib,json,re,sys
EV=Path(sys.argv[1]).resolve();checks=[]
TABLES={'store_user','category','product','product_image','cart_item','sales_order','sales_order_item'}
def check(name,value):
    checks.append(dict(name=name,passed=bool(value)))
    if not value:raise AssertionError(name)
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def records(name):
    p=EV/name;raw=p.read_bytes() if p.exists() else gzip.decompress((EV/(name+'.gz')).read_bytes())
    return [json.loads(x)for x in raw.decode('utf-8-sig').splitlines()if x.strip()]
class Node:
    def __init__(self,tag='',attrs=None):self.tag=tag;self.a=dict(attrs or []);self.children=[]
    def nodes(self):
        yield self
        for x in self.children:
            if isinstance(x,Node):yield from x.nodes()
    def find(self,p):return next((x for x in self.nodes()if p(x)),None)
    def all(self,p):return [x for x in self.nodes()if p(x)]
    def text(self):return ''.join(x.text()if isinstance(x,Node)else x for x in self.children)
class Dom(HTMLParser):
    VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
    def __init__(self,text):super().__init__(convert_charrefs=True);self.root=Node();self.stack=[self.root];self.feed(text)
    def handle_starttag(self,tag,attrs):
        n=Node(tag,attrs);self.stack[-1].children.append(n)
        if tag not in self.VOID:self.stack.append(n)
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==tag:self.stack=self.stack[:i];break
    def handle_data(self,text):self.stack[-1].children.append(text)
def changes(row,table):
    a=row[table+'_before'];b=row[table+'_after']
    return {k:(a.get(k),b.get(k))for k in a.keys()|b.keys()if a.get(k)!=b.get(k)}

run=read(EV/'result.json');check('completed run PASS',run['overall']=='PASS')
http=records('http.jsonl');database=records('database-writes.jsonl');auto={};after_only={};native=[]
for row in database:
    if row.get('before') is None:
        check('after-only explicitly scoped '+row['name'],row.get('no_before_snapshot_claimed') and row.get('read_only_response') and set(row['after'])==TABLES)
        seq=row['http_sequence'];check('unique after-only sequence '+str(seq),seq not in auto and seq not in after_only);after_only[seq]=row
    else:
        check('seven real before/after tables '+row['name'],set(row['before'])==TABLES and set(row['after'])==TABLES)
        if row.get('automatic_audit'):
            seq=row['http_sequence'];check('unique full audit sequence '+str(seq),seq not in auto and seq not in after_only);auto[seq]=row
        if str(row.get('transport','')).startswith('native actual'):native.append(row)
stats=Counter();list_pages=0;detail_pages=0;dashboards=0;unavailable=0;scanned=0;flash_chains=0;contexts=set()
for i,h in enumerate(http):
    seq=h['sequence'];u=urlsplit(h['path']);path=u.path;raw=gzip.decompress((EV/h['body_file']).read_bytes())
    check('saved redacted response hash '+str(seq),hashlib.sha256(raw).hexdigest()==h['redacted_body_sha256'])
    if h.get('body_available') is False:
        unavailable+=1;check('unavailable redirect body labelled '+str(seq),h['status']in[302,303] and not h.get('raw_response_scan_before_redaction'))
    else:
        scanned+=1;check('actual raw scanner recorded before redaction '+str(seq),h.get('raw_bcrypt_scan_passed') is True and h.get('raw_response_scan_before_redaction') is True)
    dom=Dom(raw.decode('utf-8')).root
    for n in dom.all(lambda x:x.tag=='input'and x.a.get('name')in{'_csrf','confirmationToken','receiverName','receiverPhone','receiverAddress'}):
        check('sensitive form value redacted '+str(seq),n.a.get('value','')in{'','[REDACTED]'})
    for n in dom.all(lambda x:'data-shipping-value'in x.a):check('shipping masked '+str(seq),n.text()in{'','[REDACTED]'})
    for n in dom.all(lambda x:'data-customer-contact'in x.a):check('contact structurally redacted '+str(seq),n.text()=='[REDACTED-CONTACT]')
    if h['method']=='POST':check('every POST has genuine before/after '+str(seq),seq in auto)
    if seq in after_only:
        check('after-only only GET '+str(seq),h['method']=='GET')
        observed=after_only[seq];state_suffix='_after'
    elif seq in auto:
        observed=auto[seq];state_suffix='_before'
        if h['method']=='GET':check('captured read zero write '+str(seq),observed['before']==observed['after'])
    else:observed=None;state_suffix=None
    if observed and h.get('database'):
        check('database context matches HTTP '+str(seq),observed.get('database',h['database'])==h['database']);contexts.add(h['database'])
    m=re.fullmatch('/customers/([^/]+)/status',path)
    if h['method']=='POST'and m:
        row=auto[seq];label='status POST '+str(seq)
        if h['status']!=303:
            stats['rejected']+=1;check(label+' rejected all seven unchanged',row['before']==row['after']);continue
        delta=changes(row,'store_user')
        if not delta:
            stats['same_state']+=1;check(label+' entire seven-table no-op',row['before']==row['after'])
        else:
            stats['changed']+=1;check(label+' one target only',len(delta)==1 and next(iter(delta))==str(int(m[1])))
            before,after=next(iter(delta.values()))
            check(label+' only CUSTOMER state changes',before['role']=='CUSTOMER' and before['status']!=after['status'] and after['status']in{'ENABLED','DISABLED'})
            check(label+' all other account fields preserved',all(before[k]==after[k]for k in before if k not in{'status','updatedAt'}))
            old=datetime.datetime.fromisoformat(before['updatedAt']);new=datetime.datetime.fromisoformat(after['updatedAt'])
            check(label+' at least one microsecond advance',new>=old+datetime.timedelta(microseconds=1))
            check(label+' six other tables unchanged',all(row['before'][t]==row['after'][t]for t in TABLES-{'store_user'}))
        loc=urlsplit(h['location']);check(label+' canonical safe 303 detail',not loc.netloc and loc.path=='/customers/'+str(int(m[1]))and not loc.query)
        following=next((x for x in http[i+1:]if x['method']=='GET'),None)
        check(label+' actual following location and port',following is not None and following['port']==8081 and urlsplit(following['path']).path==loc.path)
        next_dom=Dom(gzip.decompress((EV/following['body_file']).read_bytes()).decode('utf-8')).root
        message='顾客状态已更新。真实切换后的既有会话需重新登录，购物车与历史订单保留。'if delta else'顾客已处于目标状态，未重复更新状态或时间。'
        check(label+' complete global feedback',any(n.a.get('role')=='status'and message==n.text().strip()for n in next_dom.nodes()));flash_chains+=1
    root=dom.find(lambda n:n.a.get('data-page-id')in{'A02','A08','A09'})
    if not root or h['status']!=200:continue
    check('page has actual database observation '+str(seq),observed is not None)
    users=observed['store_user'+state_suffix]
    if root.a['data-page-id']=='A08':
        q=parse_qs(u.query,keep_blank_values=True);get=lambda k,d:q.get(k,[d])[0].strip()
        text=get('q','');status=get('status','ALL');page=max(1,int(get('page','1')));size=int(get('size','10'))
        expected=sorted([x for x in users.values()if x['role']=='CUSTOMER'and text.casefold()in x['username'].casefold()and(status=='ALL'or x['status']==status)],key=lambda x:x['id'])
        check('A08 count and page '+str(seq),int(root.a['data-customer-count'])==len(expected)and int(root.a['data-page'])==page and int(root.a['data-size'])==size)
        shown=expected[(page-1)*size:page*size];actual=root.all(lambda n:n.tag=='tr'and'data-customer-id'in n.a)
        check('A08 SQL condition/order rows '+str(seq),[int(n.a['data-customer-id'])for n in actual]==[x['id']for x in shown])
        for node,x in zip(actual,shown):check('A08 safe fields '+str(seq)+' '+str(x['id']),node.a['data-customer-username']==x['username']and node.a['data-customer-status']==x['status'])
        list_pages+=1
    elif root.a['data-page-id']=='A09':
        x=users[root.a['data-customer-id']];check('A09 CUSTOMER identity/status '+str(seq),x['role']=='CUSTOMER'and root.a['data-customer-status']==x['status'])
        for key,attr in [('username','data-customer-username'),('displayName','data-customer-display-name')]:
            node=root.find(lambda n:attr in n.a);check('A09 profile '+key+' '+str(seq),node is not None and node.text().strip()==x[key])
        link=root.find(lambda n:'data-customer-orders-link'in n.a)
        check('A09 associated userId '+str(seq),link is not None and urlsplit(link.a['href']).path=='/orders'and parse_qs(urlsplit(link.a['href']).query).get('userId')==[str(x['id'])])
        detail_pages+=1
    else:
        products=observed['product'+state_suffix];orders=observed['sales_order'+state_suffix]
        expected={'on-sale-products':sum(x['status']=='ON_SALE'for x in products.values()),'draft-products':sum(x['status']=='DRAFT'for x in products.values()),'paid-orders':sum(x['status']=='PAID'for x in orders.values()),'enabled-customers':sum(x['role']=='CUSTOMER'and x['status']=='ENABLED'for x in users.values()),'disabled-customers':sum(x['role']=='CUSTOMER'and x['status']=='DISABLED'for x in users.values())}
        cards=root.all(lambda n:'data-dashboard-card'in n.a);check('A02 five exact cards '+str(seq),{n.a['data-dashboard-card']for n in cards}==set(expected))
        for n in cards:
            value=n.find(lambda x:'data-dashboard-count'in x.a);check('A02 count from independent stored SQL '+str(seq)+' '+n.a['data-dashboard-card'],value is not None and int(value.text().strip())==expected[n.a['data-dashboard-card']])
        dashboards+=1
check('one native combined audit',len(native)==1)
for row in native:
    delta=changes(row,'store_user');check('native exactly target3 timestamp changes',set(delta)=={'3'})
    a,b=delta['3'];check('native roundtrip preserves status and all other user data',all(a[k]==b[k]for k in a if k!='updatedAt'))
    check('native two real microsecond advances',datetime.datetime.fromisoformat(b['updatedAt'])==datetime.datetime.fromisoformat(a['updatedAt'])+datetime.timedelta(microseconds=2))
    check('native all six business tables unchanged',all(row['before'][t]==row['after'][t]for t in TABLES-{'store_user'}))
br=read(EV/'browser/result.json');check('browser aggregate PASS',br['overall']=='PASS'and br['completed'])
check('20 to 26 new screenshots',20<=len(br['screenshots'])<=26)
for shot in br['screenshots']:
    check('original PNG byte SHA '+shot['path'],hashlib.sha256((EV/'browser'/shot['path']).read_bytes()).hexdigest()==shot['sha256'])
report=dict(overall='PASS',tested_code_sha=run['tested_code_sha'],checks=checks,http_records=len(http),genuine_automatic_audits=len(auto),explicit_after_only_gets=len(after_only),captured_raw_body_scans=scanned,unavailable_redirect_bodies=unavailable,http_status_actions=dict(stats),successful_a08_pages=list_pages,successful_a09_pages=detail_pages,successful_dashboard_pages=dashboards,complete_feedback_chains=flash_chains,native_combined_audits=len(native),database_contexts=sorted(contexts),screenshots=len(br['screenshots']),limits='Independent saved-observation replay only; after-only GETs have no before or zero-write claim. Contacts redacted; original raw contact/hash checks remain primary tool assertions. No concurrency or fault-injection claim.')
(EV.parent/'independent-observation-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items()if k!='checks'}))
