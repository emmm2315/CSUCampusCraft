"""Independently replay recorded STEP11 HTTP/SQL evidence; no database or service calls."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,parse_qs
from collections import Counter
import gzip,hashlib,json,re,sys

EV=Path(sys.argv[1]).resolve();checks=[]
TABLES={'store_user','category','product','product_image','cart_item','sales_order','sales_order_item'}
def check(name,value):
    checks.append(dict(name=name,passed=bool(value)))
    if not value:raise AssertionError(name)
def records(name):
    p=EV/name;raw=p.read_bytes() if p.exists() else gzip.decompress((EV/(name+'.gz')).read_bytes())
    return [json.loads(x) for x in raw.decode('utf-8-sig').splitlines() if x.strip()]
class Dom(HTMLParser):
    def __init__(self,text):
        super().__init__(convert_charrefs=True);self.nodes=[];self.values=[];self.current=None;self.feed(text)
    def handle_starttag(self,tag,attrs):
        n=dict(attrs);n['_tag']=tag;self.nodes.append(n)
        if tag=='textarea' or 'data-shipping-value' in n or 'data-payment-no' in n or n.get('role')=='status':self.current=[tag,n,'']
    def handle_data(self,data):
        if self.current:self.current[2]+=data
    def handle_endtag(self,tag):
        if self.current and self.current[0]==tag:self.values.append(self.current);self.current=None
def changed(row,table):
    a=row[table+'_before'];b=row[table+'_after']
    return {k:(a.get(k),b.get(k)) for k in a.keys()|b.keys() if a.get(k)!=b.get(k)}
def shipment(row,key,label):
    a=row['sales_order_before'][key];b=row['sales_order_after'][key]
    check(label+' pending shipment transition',a['status']=='PAID' and b['status']=='SHIPPED')
    check(label+' shipped time at least first paid time',b['shippedAt'] is not None and b['shippedAt']>=a['paidAt'])
    check(label+' only shipment order fields',all(a[k]==b[k] for k in a if k not in {'status','shippedAt','updatedAt'}))
    check(label+' other six tables unchanged',all(row['before'][t]==row['after'][t] for t in TABLES-{'sales_order'}))

run=json.loads((EV/'result.json').read_text(encoding='utf-8'))
check('completed run PASS',run['overall']=='PASS')
http=records('http.jsonl');db=records('database-writes.jsonl');auto={};native=[]
for row in db:
    check('seven tables '+row['name'],set(row['before'])==TABLES and set(row['after'])==TABLES)
    if row.get('automatic_audit'):
        seq=row['http_sequence'];check('unique automatic audit '+str(seq),seq not in auto);auto[seq]=row
    if row.get('transport') in {'native actual Service, not HTTP','native actual Service; not HTTP'}:native.append(row)
br=json.loads((EV/'browser/result.json').read_text(encoding='utf-8'))
stats=Counter();list_pages=0;detail_pages=0;unavailable=0;network_flashes=0;browser_dom_flashes=0
for http_index,h in enumerate(http):
    seq=h['sequence'];url=urlsplit(h['path']);path=url.path
    raw=gzip.decompress((EV/h['body_file']).read_bytes())
    check('HTTP body SHA '+str(seq),hashlib.sha256(raw).hexdigest()==h['redacted_body_sha256'])
    if h.get('body_available') is False:
        unavailable+=1;check('unavailable body honestly marked '+str(seq),h['status'] in [302,303])
    dom=Dom(raw.decode('utf-8'))
    for n in dom.nodes:
        if n['_tag']=='input' and n.get('name') in {'_csrf','confirmationToken','receiverName','receiverPhone','receiverAddress'}:
            check('secret input redacted '+str(seq),n.get('value','') in {'','[REDACTED]'})
    for tag,n,value in dom.values:
        if 'data-shipping-value' in n or n.get('name') in {'receiverName','receiverPhone','receiverAddress'}:
            check('shipping text redacted '+str(seq),value in {'','[REDACTED]'})
    if h['method']=='POST' or path.startswith('/orders') or path=='/checkout':
        check('automatic database audit '+str(seq),seq in auto)
    if h['method']=='GET' and seq in auto:
        check('GET no database write '+str(seq),auto[seq]['before']==auto[seq]['after'])
    match=re.fullmatch('/orders/([^/]+)/ship',path)
    if h['method']=='POST' and match:
        row=auto[seq];label='ship POST '+str(seq)
        if h['status']!=303:
            stats['rejected']+=1;check(label+' rejected seven-table zero write',row['before']==row['after'])
        else:
            differences=changed(row,'sales_order')
            if not differences:
                stats['replay']+=1;check(label+' replay all seven tables unchanged',row['before']==row['after'])
            else:
                stats['first_shipment']+=1;check(label+' exactly one existing order',len(differences)==1)
                key=next(iter(differences));a,b=differences[key]
                check(label+' requested order only',a['orderNo'].lower()==match[1].lower())
                shipment(row,key,label)
            location=urlsplit(h['location'])
            check(label+' safe 303 detail',not location.netloc and location.path.lower()=='/orders/'+match[1].lower() and not location.query)
            if h.get('transport','').startswith('Actual browser'):
                # Playwright route did not assign an ID to redirect GETs. The next captured same
                # path is U08 on 8080, not the missing A07 on 8081: never substitute that body.
                width=h['request_id'].split('-')[1]
                check(label+' exact actual browser DOM flash assertion',any(x.get('name')=='exact-shipment-global-flash-'+width and x['passed'] for x in br['checks']))
                shot=next(x for x in br['screenshots']if x['path']=='journey-admin-first-shipped-'+width+'.png')
                check(label+' actual A07 screenshot same shipped order',shot['observation']['orderNo']==match[1] and shot['observation']['orderStatus']=='SHIPPED' and shot['observation']['port']==8081)
                browser_dom_flashes+=1
            else:
                following=next((x for x in http[http_index+1:]if x['method']=='GET'),None)
                check(label+' follows actual Location with same case and port',following is not None and following['port']==8081 and urlsplit(following['path']).path==location.path)
                feedback=Dom(gzip.decompress((EV/following['body_file']).read_bytes()).decode('utf-8'))
                expected_message=('模拟发货已登记，请核对首次发货时间。本操作不涉及真实物流。' if differences else '该订单已发货或已完成，保留首次发货结果，未重复改写时间。')
                check(label+' complete success flash in captured status region',any(n.get('role')=='status' and 'alert-success' in n.get('class','') and expected_message in text for tag,n,text in feedback.values))
                network_flashes+=1
    root=next((n for n in dom.nodes if n.get('data-page-id') in {'A06','A07'}),None)
    if not root or h['status']!=200:continue
    check('page database observation '+str(seq),seq in auto)
    row=auto[seq]
    if root['data-page-id']=='A06':
        query=parse_qs(url.query,keep_blank_values=True)
        value=lambda k,default:query.get(k,[default])[0].strip()
        number=value('orderNo','');state=value('status','ALL');uid=value('userId','')
        page=max(1,int(value('page','1')));size=int(value('size','10'))
        expected=[x for x in row['sales_order_before'].values() if (not number or x['orderNo'].lower()==number.lower()) and (state=='ALL' or x['status']==state) and (not uid or x['userId']==int(uid))]
        expected.sort(key=lambda x:(x['createdAt'],x['id']),reverse=True)
        check('A06 total count '+str(seq),int(root['data-order-count'])==len(expected))
        check('A06 page/size '+str(seq),int(root['data-page'])==page and int(root['data-size'])==size)
        expected=expected[(page-1)*size:page*size]
        actual=[n for n in dom.nodes if n['_tag']=='tr' and 'data-order-id' in n]
        check('A06 SQL ordered rows '+str(seq),[int(n['data-order-id']) for n in actual]==[x['id'] for x in expected])
        for node,order in zip(actual,expected):
            check('A06 order values '+str(seq)+' '+str(order['id']),node['data-order-no']==order['orderNo'] and node['data-order-status']==order['status'] and int(node['data-user-id'])==order['userId'] and node['data-order-total']==order['totalAmount'])
        for node in dom.nodes:
            if 'data-page-link' in node:
                target=parse_qs(urlsplit(node['href']).query,keep_blank_values=True)
                check('A06 pagination conditions '+str(seq),all(target.get(k,[''])[0]==v for k,v in [('orderNo',number),('status',state),('userId',uid),('size',str(size))] if v!=''))
        list_pages+=1
    else:
        order=row['sales_order_before'][root['data-order-id']]
        check('A07 order identity/state/amount '+str(seq),root['data-order-no']==order['orderNo'] and root['data-order-status']==order['status'] and root['data-order-total']==order['totalAmount'])
        forms=[n for n in dom.nodes if n['_tag']=='form' and 'data-ship-order-form' in n]
        check('A07 only PAID has shipment form '+str(seq),len(forms)==(1 if order['status']=='PAID' else 0))
        expected=sorted([x for x in row['sales_order_item_before'].values() if x['orderId']==order['id']],key=lambda x:x['id'])
        actual=[n for n in dom.nodes if n['_tag']=='tr' and 'data-order-item-id' in n]
        check('A07 ordered snapshot lines '+str(seq),[int(n['data-order-item-id']) for n in actual]==[x['id'] for x in expected])
        for node,line in zip(actual,expected):
            check('A07 immutable snapshot '+str(seq)+' '+str(line['id']),node['data-snapshot-sku']==line['skuSnapshot'] and node['data-snapshot-name']==line['productNameSnapshot'] and node['data-snapshot-cover']==line['coverImageSnapshot'] and int(node['data-quantity'])==line['quantity'] and node['data-unit-price']==line['unitPrice'] and node['data-line-amount']==line['lineAmount'])
        for tag,node,value in dom.values:
            if 'data-payment-no' in node:check('A07 first payment receipt '+str(seq),value==order['paymentNo'])
        detail_pages+=1
check('one native combined seven-table audit',len(native)==1)
for row in native:
    changes=changed(row,'sales_order')
    check('native exactly two existing HTTP-created paid targets',len(changes)==2)
    for key in changes:shipment(row,key,'native '+key)
    check('native unrelated tables remain unchanged',all(row['before'][t]==row['after'][t] for t in TABLES-{'sales_order'}))
check('browser PASS',br['overall']=='PASS' and br['completed'])
check('20 to 30 fresh screenshots',20<=len(br['screenshots'])<=30)
for shot in br['screenshots']:
    check('PNG original SHA '+shot['path'],hashlib.sha256((EV/'browser'/shot['path']).read_bytes()).hexdigest()==shot['sha256'])
    check('PNG shipping mask '+shot['path'],shot['shippingFieldsMasked'])
report=dict(overall='PASS',tested_code_sha=run['tested_code_sha'],checks=checks,http_records=len(http),automatic_audits=len(auto),http_shipment_counts=dict(stats),successful_a06_pages=list_pages,successful_a07_pages=detail_pages,native_observations=len(native),unavailable_redirect_bodies=unavailable,captured_complete_network_flash_chains=network_flashes,browser_dom_and_png_flash_chains=browser_dom_flashes,uncaptured_browser_admin_redirect_gets=browser_dom_flashes,screenshots=len(br['screenshots']),limits='Replayed saved HTTP/SQL full-field summaries and privacy-masked PNGs only. Two browser A07 redirect GETs were not captured; actual DOM assertions/PNG prove their flash, not a saved network body. U08 on port8080 never substitutes A07 on8081. No new requests, concurrency or injected rollback proof.')
(EV.parent/'independent-observation-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='checks'}))
