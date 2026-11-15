"""Read-only independent replay of new STEP13 files; no product or old generator invocation."""
import pathlib,json,gzip,lzma,hashlib,sys,datetime,re
from decimal import Decimal

TABLES={'store_user','category','product','product_image','cart_item','sales_order','sales_order_item'}
def sha(b):return hashlib.sha256(b).hexdigest()
def readlines(p):
    if not p.exists():
        for suffix in ['.gz','.xz']:
            if p.with_name(p.name+suffix).exists():p=p.with_name(p.name+suffix);break
    b=p.read_bytes();b=gzip.decompress(b) if p.suffix=='.gz' else lzma.decompress(b) if p.suffix=='.xz' else b
    return [json.loads(x) for x in b.splitlines() if x.strip()]
def run(attempt,mode='full'):
    p=pathlib.Path(attempt);rows=[]
    def check(name,yes,details=None):
        rows.append(dict(name=name,passed=bool(yes),details=details))
        if not yes:print('FAIL '+name,flush=True)
    result=json.loads((p/'result.json').read_text(encoding='utf-8-sig'))
    matrix=json.loads((p/'p0-matrix.json').read_text(encoding='utf-8-sig'))
    checks=readlines(p/'checks.jsonl');http=readlines(p/'http.jsonl');writes=readlines(p/'db-writes.jsonl')
    expected={f'TST-{n:02}' for n in range(1,41) if n!=36} if mode in ['full','serial'] else {'TST-16','TST-17','TST-20','TST-23','TST-24','TST-28','TST-29','TST-35','TST-39','TST-40'} if mode=='cd' else {'TST-13','TST-20','TST-21','TST-29'} if mode=='state' else {'TST-02','TST-03','TST-09'}
    check('exactly expected distinct P0 identifiers',{x['id'] for x in matrix}==expected and len(matrix)==len(expected))
    if mode!='serial':check('scoped P0 matrix all PASS',all(x['result']=='PASS' for x in matrix))
    check('all P0 tied to tested SHA',len(result['tested_sha'])==40 and all(x['tested_sha']==result['tested_sha'] for x in matrix))
    check('all assertions observed and passing',len(checks)==result['checks'] and all(x['passed'] for x in checks),dict(recorded=len(checks),summary=result['checks']))
    for row in matrix:
        for segment in row['required_segments']:
            if mode=='serial' and re.fullmatch('[CD][0-9]+',segment):continue
            check(row['id']+' '+segment+' scoped matrix PASS',row['observed_segments'].get(segment,{}).get('passed') is True)
            observations=[c for c in checks if c['case']==row['id'] and c['segment']==segment]
            if segment=='browser':
                browser=json.loads((p/'browser/result.json').read_text(encoding='utf-8-sig'))
                observations=[c for c in browser['checks'] if re.search('fallback|gallery|missing|cover',c['name'],re.I)]
                check('external browser component and original image observations PASS',browser['overall']=='PASS' and len(observations)>=4)
            check(row['id']+' '+segment+' contains own assertions',bool(observations) and all(x['passed'] for x in observations),len(observations))
    ids=[x['sequence'] for x in http];check('HTTP unique sequence',len(ids)==len(set(ids)))
    by_http={x['http_sequence']:x for x in writes if 'http_sequence' in x}
    standard=concurrent=readonly=rejected=timezone_observations=0
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
            html=plain.decode('utf-8',errors='replace')
            if h['status']==200 and re.search(r'data-page-id="(?:U08|A07)"',html):
                order_id=re.search(r'data-order-id="([0-9]+)"',html)
                order=audit['sales_order_after'].get(order_id[1]) if order_id else None
                check('HTTP '+str(h['sequence'])+' displayed order links to SQL UTC row',order is not None)
                if order:
                    for field,attr in [('createdAt',None),('paidAt','data-payment-time'),('shippedAt','data-shipped-time'),('cancelledAt','data-cancelled-time')]:
                        if order.get(field) is None:continue
                        parsed=datetime.datetime.fromisoformat(order[field]).replace(tzinfo=datetime.UTC)
                        expected_time=parsed.astimezone(datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
                        displayed=(re.search(attr+r'[^>]*>([^<]*)<',html) if attr else None)
                        if attr and displayed is None:
                            label={'shippedAt':'模拟发货','cancelledAt':'取消订单'}.get(field)
                            if label:displayed=re.search(r'<dt[^>]*>'+label+r'</dt>\s*<dd[^>]*>([^<]*)</dd>',html)
                        matched=(displayed is not None and displayed[1]==expected_time) if attr else expected_time in re.findall(r'<time(?:\s[^>]*)?>([^<]+)</time>',html)
                        check('HTTP '+str(h['sequence'])+' UTC SQL to current Asia Shanghai '+field,matched,dict(sql_utc=order[field],displayed=displayed[1] if displayed else expected_time,offset_hours=8))
                        timezone_observations+=1
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
    if mode in ['full','cd']:check('eight distinct concurrency windows',len({w['name'] for w in windows})>=8,sorted({w['name'] for w in windows}))
    elif mode!='serial':check('supplement does not impersonate concurrency',not windows)
    check('processes stopped',result['tracked_processes_stopped'])
    check('input stability independently repeated by orchestrator',result['runtime_inputs_stable'])
    scan=json.loads((p/'sensitive-scan.json').read_text(encoding='utf-8-sig'));check('attempt sensitive scan PASS',scan.get('overall')=='PASS')
    if mode=='state':
        cleanup=json.loads((p.parents[1]/'cleanup-retry.json').read_text(encoding='utf-8-sig'))
        check('retained cleanup-tool FAIL resolved by independent scoped retry',result['overall']=='FAIL' and cleanup['passed'] and cleanup['private_runtime_removed'] and cleanup['production_or_main5_instances_touched'] is False)
    output=dict(overall='PASS' if all(x['passed'] for x in rows) else 'FAIL',scope=mode,original_attempt_overall=result['overall'],reviewer='independent Codex saved-observation replay; not human signature',observed_at_utc=datetime.datetime.now(datetime.UTC).isoformat(),tested_sha=result['tested_sha'],checks=len(rows),failed=sum(not x['passed'] for x in rows),http_records=len(http),serial_http_audits=standard,concurrent_http_records=concurrent,serial_readonly_gets=readonly,serial_rejected_posts=rejected,timezone_observations=timezone_observations,observations=rows)
    (p/'independent-replay.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in output.items() if k!='observations'},ensure_ascii=False));return output
if __name__=='__main__':sys.exit(0 if run(sys.argv[1],sys.argv[2] if len(sys.argv)>2 else 'full')['overall']=='PASS' else 1)
