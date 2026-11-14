"""Independent replay of saved STEP09 responses and privacy-safe SQL states; no live requests."""
from pathlib import Path
from html.parser import HTMLParser
from decimal import Decimal
from urllib.parse import urlsplit,parse_qs
import gzip,hashlib,json,re,sys

EV=Path(sys.argv[1]).resolve()
TABLES={'store_user','category','product','product_image','cart_item','sales_order','sales_order_item'}
checks=[]
def check(name,value):
    checks.append(dict(name=name,passed=bool(value)))
    if not value:raise AssertionError(name)
def read_records(name):
    path=EV/name
    raw=path.read_bytes() if path.exists() else gzip.decompress((EV/(name+'.gz')).read_bytes())
    return [json.loads(x) for x in raw.decode('utf-8-sig').splitlines() if x.strip()]
class Dom(HTMLParser):
    def __init__(self,text):
        super().__init__(convert_charrefs=True);self.nodes=[];self.sensitive=[];self.current=None;self.feed(text)
    def handle_starttag(self,tag,attrs):
        node=dict(attrs);node['_tag']=tag;self.nodes.append(node)
        if tag=='textarea' or 'data-shipping-value' in node:self.current=[tag,node,'']
    def handle_data(self,text):
        if self.current is not None:self.current[2]+=text
    def handle_endtag(self,tag):
        if self.current is not None and tag==self.current[0]:self.sensitive.append(self.current);self.current=None
def changes(row,table):
    a=row[table+'_before'];b=row[table+'_after']
    return {key:(a.get(key),b.get(key)) for key in a.keys()|b.keys() if a.get(key)!=b.get(key)}

def success(row,label):
    check(label+' unrelated tables',all(row['before'][t]==row['after'][t] for t in ['store_user','category','product_image']))
    order_change=changes(row,'sales_order')
    check(label+' one added master',len(order_change)==1 and all(a is None and b is not None for a,b in order_change.values()))
    order=next(iter(order_change.values()))[1];uid=order['userId']
    check(label+' safe order no',bool(re.fullmatch('[A-Za-z0-9_-]{1,40}',order['orderNo'])))
    check(label+' pending and null lifecycle fields',order['status']=='PENDING_PAYMENT' and all(order[k] is None for k in ['paymentMethod','paymentNo','paidAt','cancelledAt','shippedAt','completedAt']))
    check(label+' case insensitive uniqueness',sum(x['orderNo'].lower()==order['orderNo'].lower() for x in row['sales_order_after'].values())==1)
    for k in ['receiverNameSha256','receiverPhoneSha256','receiverAddressSha256']:
        check(label+' privacy hash '+k,bool(re.fullmatch('[0-9a-f]{64}',order[k])))
    cart=sorted((x for x in row['cart_item_before'].values() if x['userId']==uid),key=lambda x:x['id'])
    deleted=changes(row,'cart_item')
    check(label+' exact confirmed cart deletion',set(deleted)=={str(x['id']) for x in cart} and all(a is not None and b is None for a,b in deleted.values()))
    line_change=changes(row,'sales_order_item')
    check(label+' only new lines',len(line_change)==len(cart) and all(a is None and b is not None for a,b in line_change.values()))
    lines=[b for a,b in line_change.values()]
    check(label+' line master ownership',all(x['orderId']==order['id'] for x in lines))
    check(label+' exact product set',set(changes(row,'product'))=={str(x['productId']) for x in cart})
    total=Decimal('0.00')
    for item in cart:
        key=str(item['productId']);old=row['product_before'][key];new=row['product_after'][key]
        line=next(x for x in lines if x['productId']==item['productId'])
        value=Decimal(old['price'])*item['quantity'];total+=value
        check(label+' stock/version '+key,new['stock']==old['stock']-item['quantity'] and new['version']==old['version']+1)
        check(label+' other product fields '+key,all(new[k]==old[k] for k in old if k not in {'stock','version','updatedAt'}))
        check(label+' line snapshot '+key,line['skuSnapshot']==old['sku'] and line['productNameSnapshot']==old['name'] and line['coverImageSnapshot']==old['coverImage'] and Decimal(line['unitPrice'])==Decimal(old['price']) and line['quantity']==item['quantity'] and Decimal(line['lineAmount'])==value)
    check(label+' exact BigDecimal total',Decimal(order['totalAmount'])==total)
    return order['orderNo']

result=json.loads((EV/'result.json').read_text(encoding='utf-8'))
check('run PASS',result['overall']=='PASS')
check('runtime assertions all pass',all(x['passed'] for x in result['checks'].values()))
http=read_records('http.jsonl');db=read_records('database-writes.jsonl')
automatic={};native_rows=[]
for row in db:
    check('seven table summaries '+row['name'],set(row['before'])==TABLES and set(row['after'])==TABLES)
    if row.get('automatic_audit'):
        seq=row['http_sequence'];check('one automatic audit '+str(seq),seq not in automatic);automatic[seq]=row
    if row.get('transport')=='actual Service native probe, not HTTP':native_rows.append(row)
list_observations={x['http_sequence']:x for x in read_records('list-observations.jsonl')}
detail_observations={x['http_sequence']:x for x in read_records('detail-observations.jsonl')}
created=[];rejected=order_gets=lists=details=0
for h in http:
    seq=h['sequence'];method=h['method'];path=urlsplit(h['path']).path
    body=gzip.decompress((EV/h['body_file']).read_bytes())
    check('HTTP body digest '+str(seq),hashlib.sha256(body).hexdigest()==h['redacted_body_sha256'])
    dom=Dom(body.decode('utf-8'))
    for node in dom.nodes:
        if node['_tag']=='input' and node.get('name') in {'_csrf','confirmationToken','receiverName','receiverPhone','receiverAddress'}:
            check('input redaction '+str(seq)+' '+node['name'],node.get('value','') in {'','[REDACTED]'})
    for tag,node,value in dom.sensitive:
        if 'data-shipping-value' in node or node.get('name') in {'receiverName','receiverPhone','receiverAddress'}:
            check('shipping redaction '+str(seq),value in {'','[REDACTED]'})
    needs_audit=method=='POST' or path.startswith('/orders') or path=='/checkout'
    if needs_audit:
        check('automatic SQL audit exists '+str(seq),seq in automatic)
        row=automatic[seq]
        if method=='POST' and path=='/orders':
            if h['status']==303:
                number=success(row,'HTTP '+str(seq));created.append(number)
                check('303 safe canonical target '+str(seq),h['location']=='/orders/'+number)
            else:
                rejected+=1;check('rejected order seven-table zero write '+str(seq),row['before']==row['after'])
        elif method=='GET':
            check('order/checkout GET zero write '+str(seq),row['before']==row['after'])
            if path.startswith('/orders'):order_gets+=1
    root=next((x for x in dom.nodes if x.get('data-page-id') in {'U07','U08'}),None)
    if root is None:continue
    row=automatic[seq]
    if root['data-page-id']=='U07':
        query=parse_qs(urlsplit(h['path']).query,keep_blank_values=True)
        no=query.get('orderNo',[''])[0].strip();status=query.get('status',['ALL'])[0].strip()
        page=max(1,int(query.get('page',['1'])[0]));size=int(query.get('size',['10'])[0])
        displayed=[x for x in dom.nodes if x['_tag']=='tr' and 'data-order-id' in x]
        saved=list_observations.get(seq)
        if saved is not None:uid=saved['user_id']
        elif displayed:uid=row['sales_order_before'][displayed[0]['data-order-id']]['userId']
        else:uid=1 # All browser U07 test cases in the saved registry are alice; guests redirect to U04.
        expected=sorted((x for x in row['sales_order_before'].values() if x['userId']==uid and (not no or x['orderNo'].lower()==no.lower()) and (status=='ALL' or x['status']==status)),key=lambda x:(x['createdAt'],x['id']),reverse=True)
        shown=expected[(page-1)*size:page*size]
        check('U07 owner/filter/order '+str(seq),[int(x['data-order-id']) for x in displayed]==[x['id'] for x in shown])
        check('U07 same count and pagination '+str(seq),int(root['data-order-count'])==len(expected) and int(root['data-page'])==page and int(root['data-size'])==size)
        lists+=1
    else:
        order=row['sales_order_before'][root['data-order-id']]
        saved=detail_observations.get(seq)
        if saved:check('U08 owner '+str(seq),order['userId']==saved['owner'])
        check('U08 header '+str(seq),root['data-order-no']==order['orderNo'] and root['data-order-status']==order['status'] and Decimal(root['data-order-total'])==Decimal(order['totalAmount']))
        expected=sorted((x for x in row['sales_order_item_before'].values() if x['orderId']==order['id']),key=lambda x:x['id'])
        displayed=[x for x in dom.nodes if x['_tag']=='tr' and 'data-order-item-id' in x]
        check('U08 all snapshot lines '+str(seq),[int(x['data-order-item-id']) for x in displayed]==[x['id'] for x in expected])
        for node,line in zip(displayed,expected):
            check('U08 stored snapshot '+str(seq)+' '+str(line['id']),node['data-snapshot-sku']==line['skuSnapshot'] and node['data-snapshot-name']==line['productNameSnapshot'] and node['data-snapshot-cover']==line['coverImageSnapshot'] and Decimal(node['data-unit-price'])==Decimal(line['unitPrice']) and int(node['data-quantity'])==line['quantity'] and Decimal(node['data-line-amount'])==Decimal(line['lineAmount']))
        check('U08 shipping wrappers redacted '+str(seq),sum('data-shipping-value' in x for x in dom.nodes)==3)
        details+=1
check('three independent HTTP orders',len(created)==3 and len(set(created))==3)
check('one native Service order audit',len(native_rows)==1)
native_no=success(native_rows[0],'native Service')
check('native separate from HTTP',native_no not in created)
for item in read_records('snapshot-immutability.jsonl'):
    check('historical master snapshot digest',item['before_order_table']==item['after_order_table'])
    check('historical line snapshot digest',item['before_line_table']==item['after_line_table'])
br=json.loads((EV/'browser/result.json').read_text(encoding='utf-8'))
check('browser completed',br['overall']=='PASS' and br['completed'])
check('browser checks',all(x['passed'] for x in br['checks']))
check('24 screenshots',len(br['screenshots'])==24)
for shot in br['screenshots']:
    png=(EV/'browser'/shot['path']).read_bytes()
    check('screenshot SHA '+shot['path'],hashlib.sha256(png).hexdigest()==shot['sha256'])
    check('screenshot masks '+shot['path'],shot['shippingFieldsMasked'])
report=dict(overall='PASS',tested_code_sha=result['tested_code_sha'],checks=checks,http_records=len(http),
            automatic_database_audits=len(automatic),http_created_orders=created,native_created_orders=[native_no],
            rejected_order_posts_zero_write=rejected,order_gets_zero_write=order_gets,
            list_pages_replayed=lists,detail_pages_replayed=details,screenshots=24,
            boundary='Saved redacted HTTP, SQL summaries/safe row states and PNG bytes only; native Service creation counted separately; no admin order HTTP, concurrency or injected-failure claim.')
(EV.parent/'independent-observation-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='checks'},ensure_ascii=False))
