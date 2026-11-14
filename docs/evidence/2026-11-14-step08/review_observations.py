"""Independently replay saved STEP08 HTTP/DB observations; never starts an app."""
from pathlib import Path
from html.parser import HTMLParser
from decimal import Decimal
import gzip, hashlib, json, sys

ev = Path(sys.argv[1]).resolve()
tables = {'store_user','category','product','product_image','cart_item','sales_order','sales_order_item'}
checks = []
def check(name, value):
    checks.append(dict(name=name, passed=bool(value)))
    if not value: raise AssertionError(name)
def records(name):
    path = ev/name
    raw = path.read_bytes() if path.exists() else gzip.decompress((ev/(name+'.gz')).read_bytes())
    return [json.loads(line) for line in raw.decode('utf-8-sig').splitlines() if line.strip()]

class Dom(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.elements=[]; self.textareas=[]; self.current=None
        self.feed(text)
    def handle_starttag(self, tag, attrs):
        node=dict(attrs); node['_tag']=tag; self.elements.append(node)
        if tag=='textarea': self.current=[node, '']
    def handle_data(self, data):
        if self.current is not None: self.current[1]+=data
    def handle_endtag(self, tag):
        if tag=='textarea' and self.current is not None:
            self.textareas.append(self.current); self.current=None

http=records('http.jsonl'); db=records('database-writes.jsonl')
result=json.loads((ev/'result.json').read_text(encoding='utf-8-sig'))
check('run PASS', result['overall']=='PASS')
check('all runtime assertions passed', all(x['passed'] for x in result['checks'].values()))
check('full tested SHA', len(result['tested_code_sha'])==40)
check('HTTP sequence unique', len({x['sequence'] for x in http})==len(http))
automatic={}
for row in db:
    check('seven tables in before '+row['name'], set(row['before'])==tables)
    check('seven tables in after '+row['name'], set(row['after'])==tables)
    if row.get('automatic_audit'):
        sequence=row['http_sequence']
        check('one automatic DB audit '+str(sequence), sequence not in automatic)
        automatic[sequence]=row

checkout_gets=order_posts=amount_pages=browser_responses=0
status_counts={}
for h in http:
    sequence=h['sequence']; method=h['method']; path=h['path'].split('?')[0]
    raw=(ev/h['body_file']).read_bytes()
    body=gzip.decompress(raw) if h.get('body_encoding')=='gzip' else raw
    check('body SHA '+str(sequence), hashlib.sha256(body).hexdigest()==h['redacted_body_sha256'])
    text=body.decode('utf-8'); dom=Dom(text)
    for node in dom.elements:
        name=node.get('name')
        if node['_tag']=='input' and name in {'_csrf','confirmationToken','receiverName','receiverPhone','receiverAddress'}:
            check('sensitive input redacted '+str(sequence)+' '+name, node.get('value','') in {'','[REDACTED]'})
    for node,value in dom.textareas:
        if node.get('name') in {'receiverName','receiverPhone','receiverAddress'}:
            check('sensitive textarea redacted '+str(sequence), value in {'','[REDACTED]'})
    requested=h.get('requested_path',h['path']).split('?')[0]
    relevant=(method=='POST' and path=='/orders') or (method=='GET' and (path=='/checkout' or requested=='/checkout'))
    if relevant:
        check('checkout audit exists '+str(sequence), sequence in automatic)
        row=automatic[sequence]
        check('checkout all-seven zero-write '+str(sequence), row['before']==row['after'])
        check('checkout product values unchanged '+str(sequence), row['product_before']==row['product_after'])
        check('checkout cart values unchanged '+str(sequence), row['cart_before']==row['cart_after'])
        status_counts[str(h['status'])]=status_counts.get(str(h['status']),0)+1
        if method=='POST': order_posts+=1
        else: checkout_gets+=1
    if h.get('transport')=='real Playwright navigation':
        browser_responses+=1
        if requested=='/checkout' and path=='/login':
            check('guest redirect retained '+str(sequence), any(x.get('status')==302 for x in h.get('redirect_chain',[])))
    root=next((n for n in dom.elements if 'data-checkout-total' in n),None)
    if root is not None:
        check('amount page DB audit exists '+str(sequence), sequence in automatic)
        row=automatic[sequence]
        lines=[n for n in dom.elements if n['_tag']=='tr' and 'data-checkout-item-id' in n]
        displayed_ids=[int(n['data-checkout-item-id']) for n in lines]
        owners={row['cart_before'][str(i)]['userId'] for i in displayed_ids}
        check('U06 one actual owner '+str(sequence), len(owners)==1)
        owner=next(iter(owners))
        own=sorted((x for x in row['cart_before'].values() if x['userId']==owner), key=lambda x:x['id'])
        total=sum((Decimal(row['product_before'][str(x['productId'])]['price'])*x['quantity'] for x in own),Decimal('0.00'))
        check('U06 exact total '+str(sequence), Decimal(root['data-checkout-total'])==total)
        check('U06 exact count '+str(sequence), int(root['data-checkout-item-count'])==len(own)==len(lines))
        check('U06 exact quantity '+str(sequence), int(root['data-checkout-quantity'])==sum(x['quantity'] for x in own))
        for cart,line in zip(own,lines):
            price=Decimal(row['product_before'][str(cart['productId'])]['price'])
            check('U06 line '+str(sequence)+' '+str(cart['id']),
                  int(line['data-checkout-item-id'])==cart['id'] and int(line['data-product-id'])==cart['productId']
                  and int(line['data-quantity'])==cart['quantity'] and int(line['data-item-version'])==cart['version']
                  and Decimal(line['data-unit-price'])==price and Decimal(line['data-line-subtotal'])==price*cart['quantity'])
        amount_pages+=1

br=json.loads((ev/'browser/result.json').read_text(encoding='utf-8'))
check('browser completed PASS', br['completed'] and br['overall']=='PASS')
check('browser assertions', all(x['passed'] for x in br['checks']))
check('24 screenshots', len(br['screenshots'])==24)
for shot in br['screenshots']:
    png=(ev/'browser'/shot['path']).read_bytes()
    check('screenshot raw SHA '+shot['path'], hashlib.sha256(png).hexdigest()==shot['sha256'])
    check('shipping screenshot masked '+shot['path'], shot['shippingFieldsMasked'])
check('both requested viewports', {x['viewport']['width'] for x in br['screenshots']}=={1366,1920})
report=dict(overall='PASS',tested_code_sha=result['tested_code_sha'],checks=checks,
            http_records=len(http),automatic_database_audits=len(automatic),checkout_get_audits=checkout_gets,
            order_post_audits=order_posts,checkout_status_counts=status_counts,exact_amount_pages=amount_pages,
            browser_responses=browser_responses,screenshots=len(br['screenshots']),
            limits='Saved redacted responses, raw screenshot bytes, and recorded independent SQL summaries replayed; no new live requests or order-write/concurrency claim.')
out=ev.parent/'independent-observation-review.json'
out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='checks'},ensure_ascii=False))
