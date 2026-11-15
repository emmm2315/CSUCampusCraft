"""Fresh before/after UI regression. Writes only private artifacts and isolated DB fixtures."""
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from decimal import Decimal
import base64,json,os,secrets,sys,threading,traceback
from ui_harness import UIHarness,TABLES,RUNTIME,scanner_regression,digest

HERE=Path(__file__).resolve().parent
REPO=Path('D:/Github Projects/CSUCampusCraft')


def functional(h):
    with h.case('UI-REGRESSION','functional'):
        original=h.snapshot();h.check('fresh SQL02 exact original seven counts',[original[t]['rows'] for t in TABLES]==[4,15,60,100,10,10,20]);h.save('seed-before.json',json.dumps(original,indent=2))
        user,_=h.login(username='alice');admin,_=h.login(end='a',username='admin')
        note=h.pid('CSU-LMK-NOTE-01');gift=h.pid('CSU-GRAD-BOX-01');a=h.product(note);b=h.product(gift)
        h.check('85 fixture originals',a['stock']==10 and b['stock']==12 and Decimal(a['price'])==18 and Decimal(b['price'])==49)
        order=h.new_order85(user)
        h.check('85 stock/version deduction',h.product(note)['stock']==8 and h.product(gift)['stock']==11 and h.product(note)['version']==a['version']+1 and h.product(gift)['version']==b['version']+1)
        h.check('85 two immutable lines',len([r for r in h.state()['sales_order_item'].values() if r['orderId']==order['id']])==2)
        h.check('85 cart cleared and badge0',not h.cartrows(1))
        h.post(user,'/orders/'+order['orderNo']+'/payment',{'result':'SUCCESS'})
        h.post(admin,'/orders/'+order['orderNo']+'/ship',{},end='a')
        order=h.order(order['orderNo']);h.check('85 paid/shipped state and monotonic chain',order['status']=='SHIPPED' and order['paymentMethod']=='MOCK' and order['paidAt'] and order['shippedAt']>=order['paidAt'])
        detail=user.get('/orders/'+order['orderNo'],expected=200);admin.get('/orders/'+order['orderNo'],end='a',expected=200)
        badge=detail.dom.find(lambda n:n.a.get('id')=='cart-quantity')
        h.check('rendered order target badge0 after clear',badge is not None and badge.a.get('data-cart-quantity')=='0' and badge.text().strip()=='0')
        bob,_=h.login(username='bob');bob.get('/orders/'+order['orderNo'],expected=404)
        guest=h.Client('guest');guest.get('/cart',expected=302);guest.post('/cart/items',{'productId':note,'quantity':1},expected=302,zero=True)
        h.post(user,'/cart/items',{'productId':note,'quantity':1},csrf=False,expected=403,zero=True)
        h.post(user,'/cart/items',{'productId':note,'quantity':'bad'},expected=400,zero=True)
        h.post(admin,f'/products/{note}/images',{'imagePath':'images/catalog-placeholder.svg','altText':'UI regression'},end='a',expected=409,zero=True)
        stale,_=h.login(username='alice');h.post(admin,'/customers/1/status',{'targetStatus':'DISABLED'},end='a');stale.get('/orders',expected=302)
        h.post(admin,'/customers/1/status',{'targetStatus':'ENABLED'},end='a');stale.get('/cart',expected=302);user,_=h.login(username='alice')
        dash=admin.get('/',end='a',expected=200);expected=json.loads(h.rows("SELECT JSON_OBJECT('onSale',(SELECT COUNT(*) FROM product WHERE status='ON_SALE'),'draft',(SELECT COUNT(*) FROM product WHERE status='DRAFT'),'paid',(SELECT COUNT(*) FROM sales_order WHERE status='PAID'),'enabled',(SELECT COUNT(*) FROM store_user WHERE role='CUSTOMER' AND status='ENABLED'),'disabled',(SELECT COUNT(*) FROM store_user WHERE role='CUSTOMER' AND status='DISABLED'))"))
        node=dash.dom.find(lambda n:n.a.get('data-page-id')=='A02');keys={'onSale':'data-on-sale-count','draft':'data-draft-count','paid':'data-paid-order-count','enabled':'data-enabled-customer-count','disabled':'data-disabled-customer-count'}
        h.check('A02 five current independent SQL counts',node is not None and all(node.a[k]==str(expected[v]) for v,k in keys.items()))
        pending=json.loads(h.rows("SELECT JSON_OBJECT('no',order_no) FROM sales_order WHERE user_id=1 AND status='PENDING_PAYMENT' ORDER BY id LIMIT 1"))['no']
        graduation=int(h.rows("SELECT id FROM category WHERE parent_id IS NULL AND code='GRADUATION'"))
        h.save('business-order-public.json',json.dumps(dict(mainOrderNo=order['orderNo'],paymentOrderNo=pending,graduationCategoryId=graduation,noteProductId=note,giftProductId=gift),ensure_ascii=False,indent=2))
        return dict(user=user,admin=admin,order=order,note=note,gift=gift,graduation=graduation,pending=pending,dashboard=expected)


def scenes(f,empty=False):
    if empty:return [dict(id='U05-empty',end='u',path='/cart',status=200),dict(id='U06-empty-conflict',end='u',path='/checkout',status=409),dict(id='U02-empty-results',end='u',path='/products?q=UI_NO_MATCH_937421',status=200),dict(id='A04-empty-results',end='a',path='/products?q=UI_NO_MATCH_937421',status=200)]
    rows=[('U01-home','u','/',True),('U02-products','u','/products',True),('U02-graduation','u',f"/products?categoryId={f['graduation']}&type=ALL",True),('U03-product','u',f"/products/{f['gift']}",True),('U04-login','u','/login',False),('U05-cart','u','/cart',True),('U06-checkout','u','/checkout',True),('U07-orders','u','/orders',False),('U08-order','u','/orders/'+f['order']['orderNo'],True),('U09-payment','u','/orders/'+f['pending']+'/payment',False),('A01-login','a','/login',False),('A02-dashboard','a','/',True),('A03-categories','a','/categories',False),('A03-category-form','a','/categories/new',False),('A04-products','a','/products',True),('A05-product-form','a',f"/products/{f['note']}/edit",False),('A05-product-new','a','/products/new',False),('A06-orders','a','/orders',False),('A07-order','a','/orders/'+f['order']['orderNo'],False),('A08-customers','a','/customers',False),('A09-customer','a','/customers/1',False),('A10-images','a',f"/products/{f['note']}/images",True)]
    output=[dict(id=i,end=e,path=p,status=200,mobile=m,auth='guest' if i in ['U04-login','A01-login'] else e) for i,e,p,m in rows]
    for end in ['u','a']:
        for status in [400,403,404,409,500]:output.append(dict(id=end+'-error-'+str(status),end=end,path='/__verification/errors/'+str(status),status=status))
    return output


def browser_batch(h,f,phase,kind,rows):
    tickets={};errors=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*a):pass
        def do_POST(self):
            try:
                if self.headers.get('Authorization')!='Bearer '+control_secret:raise RuntimeError('Unauthorized control')
                data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                if self.path=='/before':
                    ticket=secrets.token_hex(12);tickets[ticket]=(h.snapshot(),h.state(),data);response={'ticket':ticket}
                elif self.path=='/after':
                    before,a,request=tickets.pop(data['ticket']);after,b=h.snapshot(),h.state()
                    r=h.observe_http(request['method'],request['path'],request['end'],data['status'],data['headers'],base64.b64decode(data['body']),transport='Actual Playwright navigation',scene=request['scene'],viewport=request['viewport'])
                    h.db_pair('browser-'+request['scene'],before,a,after,b,http_sequence=r.sequence,automatic_audit=True,observation='Real per-navigation full seven-table before/after')
                    h.check('browser GET seven-table no write '+request['scene'],before==after);response={'ok':True}
                else:raise RuntimeError('Unknown control path')
                raw=json.dumps(response).encode();self.send_response(200);self.end_headers();self.wfile.write(raw)
            except BaseException as exc:
                errors.append(type(exc).__name__);self.send_response(500);self.end_headers();self.wfile.write(b'{}')
    control_secret=secrets.token_urlsafe(30);h.secret(control_secret)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    fixture=dict(phase=phase,sourceSha=h.tested_sha,bases={'u':h.base('u'),'a':h.base('a')},scenes=rows,extraAudits=kind=='main')
    filename='browser-fixture-'+kind+'.json';h.save(filename,json.dumps(fixture,ensure_ascii=False,indent=2));source=HERE/'browser_ui.cjs';h.save('browser_ui.cjs',source.read_bytes())
    env=os.environ.copy();env.update(UI_FIXTURE=str(h.evidence/filename),UI_OUT=str(h.evidence/'browser'/kind),UI_USER_COOKIE=f['user'].cookie('u'),UI_ADMIN_COOKIE=f['admin'].cookie('a'),UI_PLAYWRIGHT=str(RUNTIME/'node/node_modules/playwright'),UI_CONTROL='http://127.0.0.1:'+str(server.server_port),UI_CONTROL_SECRET=control_secret)
    before=h.snapshot();a=h.state()
    try:p=h.command([RUNTIME/'node/bin/node.exe',source],env=env,timeout=900)
    finally:server.shutdown();server.server_close();thread.join()
    h.save('browser-'+kind+'-stdout.log',p.stdout.decode('utf-8',errors='replace'));h.save('browser-'+kind+'-stderr.log',p.stderr.decode('utf-8',errors='replace'));after,b=h.snapshot(),h.state();h.db_pair('browser-'+kind+'-batch',before,a,after,b)
    h.check('browser '+kind+' helper success',p.returncode==0 and not errors and not tickets)
    result=json.loads((h.evidence/'browser'/kind/'result.json').read_text(encoding='utf-8'));h.check('browser '+kind+' batch no writes',before==after);h.check('no external browser network '+kind,not result['externalRequests']);return result


def after_gates(h,observations,main_result,norm):
    relevant=[x for x in observations if 'scene' in x]
    h.check('after all144 normal/error/empty viewport navigations recorded',len(relevant)==144)
    h.check('after every document within both desktop and mobile viewport widths',not any(x['overflow'] for x in relevant))
    h.check('after all visible fields have labels',not any(x['unlabeled'] for x in relevant))
    h.check('after no dangling aria labels or descriptions',not any(x['unresolved'] for x in relevant))
    h.check('after every table retains a caption',all(t['caption'] for x in relevant for t in x['tables']))
    h.check('after each normal page keeps its expected page identity',all(x['pageId']==x['scene'].split('-')[0] for x in relevant if x['scene'][0] in ['U','A']))
    media=main_result['observations'][-1]
    h.check('after dark media changes actual body background',media['dark']['background']!=media['light'])
    h.check('after reduced motion has no long transition or animation',media['dark']['motion']==0)
    h.check('after keyboard focus is visible with at least2px outline',media['focus']['visible'] and float(media['focus']['outlineWidth'].replace('px',''))>=2 and media['focus']['outlineStyle']!='none')
    before=json.loads((HERE/'evidence/attempt2/normalized-business.json').read_text(encoding='utf-8'))
    h.save('before-after-business-comparison.json',json.dumps(dict(overall='PASS' if before==norm else 'FAIL',normalization='Random order numbers, payment numbers, timestamps and private shipping values omitted; all state/money/stock/version/cart/snapshot/catalog/card fields retained',before=before,after=norm),ensure_ascii=False,indent=2))
    h.check('before and after normalized business outcomes exactly match',before==norm)
    source=HERE/'nojs.cjs';h.save('nojs.cjs',source.read_bytes())
    env=os.environ.copy();env.update(UI_PLAYWRIGHT=str(RUNTIME/'node/node_modules/playwright'),CSU_UI_USER_BASE=h.base('u'),CSU_UI_USERNAME='alice',CSU_UI_PASSWORD=h.password,UI_NOJS_OUT=str(h.evidence/'nojs'))
    a=h.snapshot();sa=h.state();p=h.command([RUNTIME/'node/bin/node.exe',source],env=env,timeout=180);b=h.snapshot();sb=h.state()
    h.db_pair('no-JavaScript-native-login-and-quantity-noop-batch',a,sa,b,sb,observation='Real whole batch before/after, browser POST303 metadata separately recorded; raw POST bodies are not claimed available')
    h.save('nojs-stdout.log',p.stdout.decode('utf-8',errors='replace'));h.save('nojs-stderr.log',p.stderr.decode('utf-8',errors='replace'))
    h.check('actual disabled-JavaScript native form helper succeeds',p.returncode==0)
    result=json.loads((h.evidence/'nojs/result.json').read_text(encoding='utf-8'));h.check('noJS actual native login/cart303 checks pass',result['overall']=='PASS')
    h.check('noJS login and same-quantity post have no database writes',a==b)


def main():
    phase,sha,attempt=sys.argv[1:4];h=UIHarness(HERE,REPO,sha,attempt);error=None;h.result['phase']=phase
    try:
        h.save('scanner-self-test.json',json.dumps(scanner_regression(),indent=2))
        for p in HERE.glob('*'):
            if p.is_file() and p.suffix in ['.py','.json','.cjs']:h.save('tools/'+p.name,p.read_bytes())
        h.initialize();h.app_overrides['SPRING_PROFILES_ACTIVE']='verification';h.create_schema('csucampuscraft','demo');h.start_apps();f=functional(h)
        with h.case('UI-REGRESSION','browser'):
            empty=browser_batch(h,f,phase,'empty',scenes(f,True));h.add(f['user'],f['note'],2);h.add(f['user'],f['gift'],1)
            main_result=browser_batch(h,f,phase,'main',scenes(f))
            observations=empty['observations']+main_result['observations'];screens=empty['screenshots']+main_result['screenshots']
            h.save('browser-summary.json',json.dumps(dict(screenshots=len(screens),navigations=sum('scene' in x for x in observations),overflow_observations=[x for x in observations if x.get('overflow')],a11y_observations=[dict(scene=x.get('scene'),viewport=x.get('viewport'),unlabeled=x.get('unlabeled'),unresolved=x.get('unresolved'),tables=x.get('tables')) for x in observations],baseline_findings_are_observations_not_functional_failures=True),ensure_ascii=False,indent=2))
            order=h.order(f['order']['orderNo']);items=[{k:v for k,v in r.items() if k not in ['id','orderId']} for r in h.state()['sales_order_item'].values() if r['orderId']==order['id']]
            norm=dict(status=order['status'],amount=order['totalAmount'],paymentMethod=order['paymentMethod'],items=items,products={str(pid):{k:h.product(pid)[k] for k in ['sku','stock','version','price','status']} for pid in [f['note'],f['gift']]},cart=[{k:r[k] for k in ['userId','productId','quantity','version']} for r in h.cartrows(1)],dashboard=f['dashboard'],finalSevenCounts=[h.snapshot()[t]['rows'] for t in TABLES])
            h.save('normalized-business.json',json.dumps(norm,ensure_ascii=False,indent=2));h.result['screenshots']=len(screens);h.result['browser_navigation_count']=sum('scene' in x for x in observations)
            if phase=='after':after_gates(h,observations,main_result,norm)
    except BaseException as exc:error=exc;h.save('failure.txt',traceback.format_exc());print(type(exc).__name__+': '+str(exc),flush=True)
    finally:result=h.finish(error);print('UI_RESULT '+str(h.evidence/'result.json')+' '+result['overall'],flush=True)
    return 0 if result['overall']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
