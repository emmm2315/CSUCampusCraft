"""Replay saved STEP10 HTTP and SQL states independently; never starts services."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit
from collections import Counter
import gzip,hashlib,json,re,sys

EV=Path(sys.argv[1]).resolve(); checks=[]
TABLES={'store_user','category','product','product_image','cart_item','sales_order','sales_order_item'}
def check(name,value):
    checks.append(dict(name=name,passed=bool(value)))
    if not value:raise AssertionError(name)
def records(name):
    p=EV/name;b=p.read_bytes() if p.exists() else gzip.decompress((EV/(name+'.gz')).read_bytes())
    return [json.loads(x) for x in b.decode('utf-8-sig').splitlines() if x.strip()]
class Dom(HTMLParser):
    def __init__(self,text):
        super().__init__(convert_charrefs=True);self.nodes=[];self.values=[];self.current=None;self.feed(text)
    def handle_starttag(self,tag,attrs):
        n=dict(attrs);n['_tag']=tag;self.nodes.append(n)
        if tag=='textarea' or 'data-shipping-value' in n or 'data-payment-no' in n:self.current=[tag,n,'']
    def handle_data(self,data):
        if self.current:self.current[2]+=data
    def handle_endtag(self,tag):
        if self.current and self.current[0]==tag:self.values.append(self.current);self.current=None
def changed(row,table):
    a=row[table+'_before'];b=row[table+'_after']
    return {k:(a.get(k),b.get(k)) for k in a.keys()|b.keys() if a.get(k)!=b.get(k)}
def transition(row,key,label,kind):
    a=row['sales_order_before'][key];b=row['sales_order_after'][key]
    check(label+' existing order',a is not None and b is not None)
    if a==b:return 'NOOP'
    if kind=='payment':
        check(label+' payment transition',a['status']=='PENDING_PAYMENT' and b['status']=='PAID')
        allowed={'status','paymentMethod','paymentNo','paidAt','updatedAt'}
        check(label+' payment fields',b['paymentMethod']=='MOCK' and bool(re.fullmatch('[A-Za-z0-9_-]{1,40}',b['paymentNo'] or '')) and b['paidAt'] is not None and b['paidAt']>=b['createdAt'])
        check(label+' unique CI receipt',sum(bool(x['paymentNo']) and x['paymentNo'].lower()==b['paymentNo'].lower() for x in row['sales_order_after'].values())==1)
        result='PAID'
    else:
        check(label+' cancellation transition',a['status']=='PENDING_PAYMENT' and b['status']=='CANCELLED')
        allowed={'status','cancelledAt','updatedAt'}
        check(label+' cancellation fields',b['cancelledAt'] is not None and b['cancelledAt']>=b['createdAt'] and all(b[k] is None for k in ['paymentMethod','paymentNo','paidAt']))
        result='CANCELLED'
    check(label+' immutable order data',all(a[k]==b[k] for k in a if k not in allowed))
    return result
def refunds(row,order_id,label):
    quantities={x['productId']:x['quantity'] for x in row['sales_order_item_before'].values() if x['orderId']==order_id}
    check(label+' exact product set',set(changed(row,'product'))=={str(x) for x in quantities})
    for pid,q in quantities.items():
        a=row['product_before'][str(pid)];b=row['product_after'][str(pid)]
        check(label+' exact refund '+str(pid),b['stock']==a['stock']+q and b['version']==a['version']+1)
        check(label+' preserve product status/data '+str(pid),all(a[k]==b[k] for k in a if k not in {'stock','version','updatedAt'}))

run=json.loads((EV/'result.json').read_text(encoding='utf-8'))
check('run PASS',run['overall']=='PASS')
check('all runtime assertions PASS',all(x['passed'] for x in run['checks'].values()))
http=records('http.jsonl');db=records('database-writes.jsonl');auto={};native=[]
for row in db:
    check('seven tables '+row['name'],set(row['before'])==TABLES and set(row['after'])==TABLES)
    if row.get('automatic_audit'):
        seq=row['http_sequence'];check('unique automatic audit '+str(seq),seq not in auto);auto[seq]=row
    if row.get('transport')=='native actual Service, not HTTP':native.append(row)
stats=Counter();receipts=[];unavailable=0;u09=0
for h in http:
    seq=h['sequence'];path=urlsplit(h['path']).path
    body=gzip.decompress((EV/h['body_file']).read_bytes())
    check('body SHA '+str(seq),hashlib.sha256(body).hexdigest()==h['redacted_body_sha256'])
    if h.get('body_available') is False:
        unavailable+=1;check('unavailable redirect body '+str(seq),h['status'] in [302,303])
    dom=Dom(body.decode('utf-8'))
    for n in dom.nodes:
        if n['_tag']=='input' and n.get('name') in {'_csrf','confirmationToken','receiverName','receiverPhone','receiverAddress'}:
            check('sensitive input redacted '+str(seq),n.get('value','') in {'','[REDACTED]'})
    for tag,n,value in dom.values:
        if 'data-shipping-value' in n or n.get('name') in {'receiverName','receiverPhone','receiverAddress'}:
            check('shipping redacted '+str(seq),value in {'','[REDACTED]'})
    m=re.fullmatch('/orders/([^/]+)/(payment|cancel)',path)
    if h['method']=='POST' or path.startswith('/orders') or path=='/checkout':
        check('automatic audit exists '+str(seq),seq in auto)
    if h['method']=='GET' and seq in auto:
        check('read zero write '+str(seq),auto[seq]['before']==auto[seq]['after'])
    if h['method']=='POST' and m:
        row=auto[seq];kind=m[2];label='HTTP '+str(seq)
        if h['status']!=303:
            stats['rejected']+=1;check(label+' rejected seven-table zero write',row['before']==row['after']);continue
        check(label+' snapshots/cart/users/categories/images unchanged',all(row['before'][t]==row['after'][t] for t in ['store_user','category','product_image','cart_item','sales_order_item']))
        target=next(x for x in row['sales_order_before'].values() if x['orderNo'].lower()==m[1].lower());key=str(target['id'])
        outcome=transition(row,key,label,kind);stats[kind+'_'+outcome]+=1
        if outcome=='NOOP':check(label+' all-seven no-op',row['before']==row['after'])
        else:check(label+' only own order changed',set(changed(row,'sales_order'))=={key})
        if outcome=='PAID':
            check(label+' every product field unchanged',row['before']['product']==row['after']['product'] and row['product_before']==row['product_after'])
            receipts.append(row['sales_order_after'][key]['paymentNo'])
        if outcome=='CANCELLED':refunds(row,target['id'],label)
        location=urlsplit(h['location']);check(label+' safe detail 303',not location.netloc and location.path.lower()=='/orders/'+m[1].lower() and not location.query)
    root=next((x for x in dom.nodes if x.get('data-page-id')=='U09'),None)
    if root and h['status']==200:
        order=auto[seq]['sales_order_before'][root['data-order-id']]
        check('U09 original order '+str(seq),root['data-order-no']==order['orderNo'] and root['data-order-total']==order['totalAmount'] and order['status']=='PENDING_PAYMENT')
        check('U09 two canonical results '+str(seq),sorted(x.get('value') for x in dom.nodes if x['_tag']=='button' and x.get('name')=='result')==['FAILURE','SUCCESS'])
        u09+=1
    for tag,n,value in dom.values:
        if 'data-payment-no' in n:
            root=next(x for x in dom.nodes if x.get('data-page-id')=='U08')
            check('U08 first receipt '+str(seq),value==auto[seq]['sales_order_before'][root['data-order-id']]['paymentNo'])
check('one native combined audit',len(native)==1)
row=native[0];changes=changed(row,'sales_order')
check('native exactly two existing orders',len(changes)==2 and all(a is not None and b is not None for a,b in changes.values()))
check('native snapshots/cart/unrelated unchanged',all(row['before'][t]==row['after'][t] for t in ['store_user','category','product_image','cart_item','sales_order_item']))
for key,(a,b) in changes.items():
    kind='payment' if b['status']=='PAID' else 'cancel'
    result=transition(row,key,'native '+key,kind)
    check('native action '+key,result in {'PAID','CANCELLED'})
    if result=='CANCELLED':refunds(row,a['id'],'native refund')
br=json.loads((EV/'browser/result.json').read_text(encoding='utf-8'))
check('browser completed PASS',br['overall']=='PASS' and br['completed'])
check('browser all checks',all(x['passed'] for x in br['checks']))
check('24 actual screenshots',len(br['screenshots'])==24)
for shot in br['screenshots']:
    check('PNG SHA '+shot['path'],hashlib.sha256((EV/'browser'/shot['path']).read_bytes()).hexdigest()==shot['sha256'])
    check('PNG sensitive masks '+shot['path'],shot['shippingFieldsMasked'])
report=dict(overall='PASS',tested_code_sha=run['tested_code_sha'],checks=checks,http_records=len(http),automatic_audits=len(auto),
            http_action_counts=dict(stats),new_http_payment_receipts=receipts,successful_u09_pages=u09,
            native_combined_actions=2,unavailable_redirect_bodies=unavailable,screenshots=24,
            limits='Saved HTTP, full-field ordered SQL digests/safe row states and PNGs independently replayed; no concurrent payment/cancel or injected rollback claim.')
(EV.parent/'independent-observation-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='checks'}))
