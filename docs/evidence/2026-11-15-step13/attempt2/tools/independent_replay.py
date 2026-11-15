"""Read-only independent replay of new STEP13 files; no product or old generator invocation."""
import pathlib,json,gzip,hashlib,sys,datetime,re
from decimal import Decimal

TABLES={'store_user','category','product','product_image','cart_item','sales_order','sales_order_item'}
def sha(b):return hashlib.sha256(b).hexdigest()
def readlines(p):
    if not p.exists() and p.with_name(p.name+'.gz').exists():p=p.with_name(p.name+'.gz')
    b=p.read_bytes();b=gzip.decompress(b) if p.suffix=='.gz' else b
    return [json.loads(x) for x in b.splitlines() if x.strip()]
def run(attempt):
    p=pathlib.Path(attempt);rows=[]
    def check(name,yes,details=None):
        rows.append(dict(name=name,passed=bool(yes),details=details))
        if not yes:print('FAIL '+name,flush=True)
    result=json.loads((p/'result.json').read_text(encoding='utf-8-sig'))
    matrix=json.loads((p/'p0-matrix.json').read_text(encoding='utf-8-sig'))
    checks=readlines(p/'checks.jsonl');http=readlines(p/'http.jsonl');writes=readlines(p/'db-writes.jsonl')
    expected={f'TST-{n:02}' for n in range(1,41) if n!=36}
    check('exactly39 distinct required P0 identifiers',{x['id'] for x in matrix}==expected and len(matrix)==39)
    check('P0 matrix all PASS',all(x['result']=='PASS' for x in matrix))
    check('all P0 tied to tested SHA',len(result['tested_sha'])==40 and all(x['tested_sha']==result['tested_sha'] for x in matrix))
    check('all assertions observed and passing',len(checks)==result['checks'] and all(x['passed'] for x in checks),dict(recorded=len(checks),summary=result['checks']))
    for row in matrix:
        for segment in row['required_segments']:
            observations=[c for c in checks if c['case']==row['id'] and c['segment']==segment]
            check(row['id']+' '+segment+' contains own assertions',bool(observations) and all(x['passed'] for x in observations),len(observations))
    ids=[x['sequence'] for x in http];check('HTTP unique sequence',len(ids)==len(set(ids)))
    by_http={x['http_sequence']:x for x in writes if 'http_sequence' in x}
    standard=concurrent=readonly=rejected=0
    for h in http:
        body=p/h['body_file'];check('HTTP '+str(h['sequence'])+' actual archived bytes',body.exists() and sha(body.read_bytes())==h['stored_file_sha256'])
        plain=gzip.decompress(body.read_bytes()) if body.suffix=='.gz' else body.read_bytes()
        check('HTTP '+str(h['sequence'])+' decompressed text hash',sha(plain)==h['redacted_content_sha256'])
        audit=by_http.get(h['sequence']);check('HTTP '+str(h['sequence'])+' real audit linked',audit is not None)
        if audit is None:continue
        if audit.get('observation')=='CONCURRENT_WINDOW':
            concurrent+=1;check('concurrent request no false isolated before/after',audit.get('before') is None and audit.get('after') is None and audit.get('per_request_isolation_not_claimed') is True)
            continue
        standard+=1
        check('HTTP '+str(h['sequence'])+' seven-table whole field envelope',set(audit['before'])==TABLES and set(audit['after'])==TABLES and all(len(audit[w][t]['sha256'])==64 for w in ['before','after'] for t in TABLES))
        if h['method']=='GET':
            readonly+=1;check('HTTP '+str(h['sequence'])+' GET zero DB writes',audit['before']==audit['after'])
        elif h['status'] in [302,400,403,404,409,500]:
            rejected+=1;check('HTTP '+str(h['sequence'])+' serial rejection seven-table equality',audit['before']==audit['after'])
        elif h['method']=='POST' and h['status']==303:
            path=h['path'].split('?',1)[0];d=audit['deltas'];changed={t for t,x in d.items() if x};name='HTTP '+str(h['sequence'])+' successful '+path
            allowed=(set() if path in ['/login','/logout'] else {'cart_item'} if path.startswith('/cart/') else {'sales_order','sales_order_item','product','cart_item'} if path=='/orders' else {'sales_order','product'} if path.endswith('/cancel') else {'sales_order'} if path.startswith('/orders/') else {'store_user'} if path.startswith('/customers/') else {'category'} if path.startswith('/categories') else {'product','product_image'} if '/images' in path else {'product'} if path.startswith('/products') else None)
            check(name+' modifies only allowed tables',allowed is not None and changed<=allowed,sorted(changed))
            if path=='/orders':
                masters=d['sales_order'];items=d['sales_order_item'];products=d['product'];carts=d['cart_item']
                check(name+' exactly one new pending master',len(masters)==1 and masters[0]['before'] is None and masters[0]['after']['status']=='PENDING_PAYMENT')
                if len(masters)==1:
                    master=masters[0]['after'];newitems=[x['after'] for x in items if x['before'] is None and x['after'] is not None]
                    check(name+' lines amount and parent match',bool(newitems) and len(newitems)==len(items) and all(x['orderId']==master['id'] and Decimal(x['lineAmount'])==Decimal(x['unitPrice'])*x['quantity'] for x in newitems) and sum(Decimal(x['lineAmount']) for x in newitems)==Decimal(master['totalAmount']))
                    qty={x['productId']:x['quantity'] for x in newitems}
                    check(name+' exact ordered stock/version deductions',len(products)==len(qty) and all(x['after']['stock']==x['before']['stock']-qty[x['before']['id']] and x['after']['version']==x['before']['version']+1 and x['after']['status']==x['before']['status'] for x in products))
                    check(name+' clears only matching purchased user cart rows',len(carts)==len(qty) and all(x['after'] is None and x['before']['userId']==master['userId'] and qty.get(x['before']['productId'])==x['before']['quantity'] for x in carts))
            elif re.fullmatch('/orders/[^/]+/cancel',path) and d['sales_order']:
                a=d['sales_order'][0]['before'];b=d['sales_order'][0]['after'];orderitems=[x for x in audit['sales_order_item_before'].values() if x['orderId']==a['id']];qty={x['productId']:x['quantity'] for x in orderitems}
                check(name+' pending cancellation fields',len(d['sales_order'])==1 and a['status']=='PENDING_PAYMENT' and b['status']=='CANCELLED' and b['cancelledAt'] is not None and all(b[x] is None for x in ['paymentMethod','paymentNo','paidAt']))
                check(name+' exact single refund per SKU preserving availability',len(d['product'])==len(qty) and all(x['after']['stock']==x['before']['stock']+qty[x['before']['id']] and x['after']['version']==x['before']['version']+1 and x['after']['status']==x['before']['status'] for x in d['product']))
            elif re.fullmatch('/orders/[^/]+/payment',path) and d['sales_order']:
                a=d['sales_order'][0]['before'];b=d['sales_order'][0]['after']
                check(name+' first payment only changes allowed fields',len(d['sales_order'])==1 and a['status']=='PENDING_PAYMENT' and b['status']=='PAID' and b['paymentMethod']=='MOCK' and b['paidAt'] is not None and 0<len(b['paymentNo'])<=40 and all(a[k]==b[k] for k in a if k not in ['status','paymentMethod','paymentNo','paidAt','updatedAt']))
            elif re.fullmatch('/orders/[^/]+/ship',path) and d['sales_order']:
                a=d['sales_order'][0]['before'];b=d['sales_order'][0]['after']
                check(name+' paid shipment preserves receipt snapshot',len(d['sales_order'])==1 and a['status']=='PAID' and b['status']=='SHIPPED' and b['shippedAt']>=b['paidAt'] and all(a[k]==b[k] for k in a if k not in ['status','shippedAt','updatedAt']))
            elif path.startswith('/customers/') and d['store_user']:
                a=d['store_user'][0]['before'];b=d['store_user'][0]['after']
                check(name+' only CUSTOMER status and monotonic stamp',len(d['store_user'])==1 and a['role']==b['role']=='CUSTOMER' and a['status']!=b['status'] and b['updatedAt']>a['updatedAt'] and all(a[k]==b[k] for k in a if k not in ['status','updatedAt']))
            elif '/images' in path and changed:
                check(name+' image change increments parent only',len(d['product'])==1 and bool(d['product_image']) and all(x['after']['version']==x['before']['version']+1 and all(x['after'][k]==x['before'][k] for k in x['before'] if k not in ['version','updatedAt']) for x in d['product']))
    windows=[w for w in writes if w.get('observation')=='CONCURRENT_WINDOW' and w.get('before') is not None]
    check('eight distinct concurrency windows',len({w['name'] for w in windows})>=8,sorted({w['name'] for w in windows}))
    check('processes stopped',result['tracked_processes_stopped'])
    check('input stability independently repeated by orchestrator',result['runtime_inputs_stable'])
    scan=json.loads((p/'sensitive-scan.json').read_text(encoding='utf-8-sig'));check('attempt sensitive scan PASS',scan.get('overall')=='PASS')
    output=dict(overall='PASS' if all(x['passed'] for x in rows) else 'FAIL',reviewer='independent Codex saved-observation replay; not human signature',observed_at_utc=datetime.datetime.now(datetime.UTC).isoformat(),tested_sha=result['tested_sha'],checks=len(rows),failed=sum(not x['passed'] for x in rows),http_records=len(http),serial_http_audits=standard,concurrent_http_records=concurrent,serial_readonly_gets=readonly,serial_rejected_posts=rejected,observations=rows)
    (p/'independent-replay.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in output.items() if k!='observations'},ensure_ascii=False));return output
if __name__=='__main__':sys.exit(0 if run(sys.argv[1])['overall']=='PASS' else 1)
