"""Real HTTP/MySQL STEP07 verification against a fresh, isolated database only."""
import concurrent.futures, datetime, hashlib, json, os, re, subprocess, sys, threading, time
from pathlib import Path
from decimal import Decimal
import requests
from bs4 import BeautifulSoup

REPO = Path('D:/severlt/实验1/CSUCampusCraft')
OUT = Path(os.environ['STEP07_OUT'])
OUT.mkdir(parents=True, exist_ok=False)
MYSQL = os.environ['STEP07_MYSQL']
PORT = os.environ['STEP07_DB_PORT']
DB = os.environ['STEP07_DB_NAME']
BASE = os.environ.get('STEP07_BASE', 'http://127.0.0.1:18080')
TABLES = ['store_user', 'category', 'product', 'product_image', 'cart_item', 'sales_order', 'sales_order_item']
checks, http = [], []
PASSWORD = re.search(r'教学密码为\s*`([^`]+)`', (REPO/'README.md').read_text(encoding='utf-8')).group(1)

def sql(query):
    r = subprocess.run([MYSQL, '--no-defaults', '--protocol=TCP', '-h127.0.0.1', '-P'+PORT,
                        '-uroot', '--default-character-set=utf8mb4', '-N', '-B', '-r', DB, '-e', query],
                       capture_output=True, timeout=20, creationflags=subprocess.CREATE_NO_WINDOW)
    if r.returncode: raise RuntimeError(r.stderr.decode('utf-8', errors='replace'))
    return r.stdout.decode('utf-8').strip()

def check(name, ok, detail=None):
    checks.append({'name': name, 'passed': bool(ok), 'detail': detail})
    print(('PASS ' if ok else 'FAIL ')+name, flush=True)
    if not ok: raise AssertionError(name)

def snapshot():
    return {t: hashlib.sha256(sql('SELECT * FROM '+t+' ORDER BY id').encode()).hexdigest() for t in TABLES}

def rows(uid):
    raw = sql(f'SELECT id,product_id,quantity,version FROM cart_item WHERE user_id={uid} ORDER BY id')
    return [tuple(map(int, line.split('\t'))) for line in raw.splitlines()] if raw else []

def state():
    return {'cart':sql('SELECT id,user_id,product_id,quantity,version FROM cart_item ORDER BY id').splitlines(),
            'products':sql('SELECT id,status,price,stock,version FROM product ORDER BY id').splitlines()}

def session():
    s = requests.Session(); s.trust_env = False
    return s

def get(s, path):
    r = s.get(BASE+path, timeout=20, allow_redirects=False)
    check('GET '+path, r.status_code == 200)
    return r

def token(s, path='/cart'):
    node = BeautifulSoup(get(s, path).text, 'html.parser').select_one('input[name="_csrf"]')
    if node is None: raise AssertionError('Missing CSRF in '+path)
    return node['value']

def login(name):
    s = session(); csrf = token(s, '/login')
    r = s.post(BASE+'/login', data={'_csrf': csrf, 'username': name, 'password': PASSWORD}, allow_redirects=False, timeout=20)
    check('login '+name, r.status_code == 303)
    return s

def post(s, path, form, expected, label, csrf=True, unchanged=False):
    before = snapshot(); before_state = state()
    data = dict(form) if isinstance(form, dict) else list(form)
    if csrf:
        t = token(s)
        if isinstance(data, dict): data['_csrf'] = t
        else: data.append(('_csrf', t))
    start = time.monotonic()
    r = s.post(BASE+path, data=data, timeout=30, allow_redirects=False)
    after = snapshot()
    http.append({'label': label, 'path': path, 'status': r.status_code,
                 'location': r.headers.get('Location'), 'elapsed': round(time.monotonic()-start, 4),
                 'before': before, 'after': after, 'sql_before':before_state, 'sql_after':state()})
    check(label+' status', r.status_code == expected, {'expected': expected, 'actual': r.status_code})
    check(label+' inventory and unrelated tables', all(before[t] == after[t] for t in TABLES if t != 'cart_item'))
    if unchanged: check(label+' no database mutation', before == after)
    if expected == 303: check(label+' fixed redirect', r.headers.get('Location') == '/cart')
    check(label+' no session URL', ';CSUCAMPUSCRAFT_' not in r.text and ';CSUCAMPUSCRAFT_' not in r.headers.get('Location',''))
    check(label+' no password leakage', PASSWORD not in r.text and '$2a$10$' not in r.text)
    if expected in (400, 409):
        safe = re.sub(r'(name="_csrf"[^>]*value=")[^"]*', r'\1[REDACTED]', r.text)
        (OUT/(str(len(http)).zfill(3)+'-'+str(expected)+'.html')).write_text(safe, encoding='utf-8')
    return r

def badge(s, value):
    for path in ['/', '/products', '/products/'+str(P1), '/cart']:
        node = BeautifulSoup(get(s, path).text, 'html.parser').select_one('#cart-quantity')
        check('badge '+path, node is not None and node.get('data-cart-quantity') == str(value), value)
        if path=='/cart':
            page=BeautifulSoup(get(s,path).text,'html.parser').select_one('[data-page-id="U05"]')
            expected=sql(f"SELECT COALESCE(SUM(c.quantity*p.price),0.00) FROM cart_item c JOIN product p ON p.id=c.product_id WHERE c.user_id={ALICE if s is not b else BOB} AND p.status='ON_SALE' AND p.stock>=c.quantity AND p.stock>0")
            check('cart total equals current valid SQL subtotal',Decimal(page['data-cart-total'])==Decimal(expected))

def clear(uid): sql(f'DELETE FROM cart_item WHERE user_id={uid}')

def add(s, pid, amount=1, expected=303, label='add'):
    return post(s, '/cart/items', {'productId':pid, 'quantity':amount}, expected, label, unchanged=expected != 303)

def parallel(a, b, path, forms, expected, label):
    tokens = [token(a), token(b)]; gate = threading.Barrier(2)
    before = snapshot(); before_state = state()
    def run(i, client):
        data = dict(forms[i]); data['_csrf'] = tokens[i]
        gate.wait(timeout=10); started = time.monotonic()
        r = client.post(BASE+path[i] if isinstance(path,list) else BASE+path, data=data, allow_redirects=False, timeout=30)
        return {'status':r.status_code, 'start':started, 'end':time.monotonic()}
    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        fa = pool.submit(run,0,a); fb = pool.submit(run,1,b)
        result = [fa.result(),fb.result()]
    after = snapshot()
    check(label+' responses', sorted(x['status'] for x in result) == sorted(expected), result)
    check(label+' inventory and unrelated tables', all(before[t]==after[t] for t in TABLES if t!='cart_item'))
    http.append({'label':label, 'concurrent':result, 'before':before, 'after':after,
                 'sql_before':before_state,'sql_after':state()})

result = {'date':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
          'scope':'STEP07; STEP08 checkout and order writes excluded', 'checks':checks, 'http':http}
try:
    instance = json.loads(Path(os.environ['STEP07_INSTANCE']).read_text(encoding='utf-8'))
    check('isolated database only', Path(instance['datadir']).resolve().is_relative_to(Path('D:/severlt/tmp/step07-validation/runtime'))
          and str(instance['port']) == PORT and instance['schema'] == DB
          and sql('SELECT @@server_uuid') == instance['uuid'])
    result['database_version'] = sql('SELECT VERSION()')
    ids = dict(line.split('\t') for line in sql("SELECT username,id FROM store_user WHERE username IN ('alice','bob')").splitlines())
    ALICE, BOB = int(ids['alice']), int(ids['bob'])
    products = [int(x) for x in sql("SELECT id FROM product WHERE status='ON_SALE' AND stock>0 ORDER BY id").splitlines()]
    P1, P2, P3 = products[:3]
    DRAFT = int(sql("SELECT id FROM product WHERE status='DRAFT' ORDER BY id LIMIT 1"))
    ZERO = int(sql("SELECT id FROM product WHERE status='ON_SALE' AND stock=0 ORDER BY id LIMIT 1"))
    sql(f'UPDATE product SET stock=150 WHERE id IN ({",".join(map(str,products[:23]))})')
    clear(ALICE); clear(BOB)
    a, b, a2 = login('alice'), login('bob'), login('alice')
    badge(a,0)
    post(session(), '/cart/items', {'productId':'bad','quantity':'bad'},302,'guest before parsing',csrf=False,unchanged=True)
    post(a,'/cart/items',{'productId':P1,'quantity':1},403,'missing CSRF',csrf=False,unchanged=True)
    post(a,'/cart/items',{'productId':P1,'quantity':1,'_csrf':'invalid'},403,'wrong CSRF',csrf=False,unchanged=True)
    for value in ['', '0', '-1', '1.5', '100', 'NaN', '9223372036854775808']:
        post(a,'/cart/items',{'productId':P1,'quantity':value},400,'quantity '+repr(value),unchanged=True)
    post(a,'/cart/items',{'quantity':1},400,'missing productId',unchanged=True)
    post(a,'/cart/items',{'productId':P1},400,'missing quantity',unchanged=True)
    for value in ['0','-1','1.0','abc','9223372036854775808']:
        post(a,'/cart/items',{'productId':value,'quantity':1},400,'productId '+value,unchanged=True)
    post(a,'/cart/items',[('productId',P1),('quantity',1),('quantity',2)],400,'duplicate quantity',unchanged=True)
    add(a,9223372036854775807,expected=404,label='missing product')
    add(a,DRAFT,expected=404,label='draft product')
    add(a,ZERO,expected=409,label='sold out product')
    sql(f'UPDATE product SET stock=1 WHERE id={P1}')
    add(a,P1,2,409,'over stock'); sql(f'UPDATE product SET stock=150 WHERE id={P1}')
    add(a,P1,1,label='first add'); add(a,P1,1,label='merge add')
    r = rows(ALICE); check('same SKU one row',len(r)==1 and r[0][2:]==(2,1),r)
    old_price=sql(f'SELECT price FROM product WHERE id={P1}')
    sql(f'UPDATE product SET price=price+0.01,version=version+1 WHERE id={P1}')
    badge(a,2)
    sql(f'UPDATE product SET price={old_price},version=version+1 WHERE id={P1}')
    item,_,amount,version = r[0]
    post(a,f'/cart/items/{item}/quantity',{'quantity':2,'version':version},303,'same quantity',unchanged=True)
    post(a,f'/cart/items/{item}/quantity',{'quantity':3,'version':version},303,'change quantity')
    post(a,f'/cart/items/{item}/quantity',{'quantity':4,'version':version},409,'old quantity version',unchanged=True)
    post(a,f'/cart/items/{item}/remove',{'version':version},409,'old remove version',unchanged=True)
    post(b,f'/cart/items/{item}/quantity',{'quantity':2,'version':version+1},403,'foreign quantity',unchanged=True)
    post(b,f'/cart/items/{item}/remove',{'version':version+1},403,'foreign remove',unchanged=True)
    post(a,'/cart/items/9223372036854775807/remove',{'version':0},404,'missing item',unchanged=True)
    missing = post(a,'/cart/items/9223372036854775807/quantity',{'quantity':0,'version':0},400,'missing row malformed quantity',unchanged=True)
    check('no broken error summary anchor',not BeautifulSoup(missing.text,'html.parser').select('.error-summary a'))
    for value in [None,'-1','1.2','9223372036854775808']:
        form={} if value is None else {'version':value}
        post(a,f'/cart/items/{item}/remove',form,400,'bad version '+str(value),unchanged=True)
    badge(a,3); badge(b,0)
    add(a,P1,96,label='merge to 99'); add(a,P1,1,409,'merge over 99')
    clear(ALICE)
    for pid in products[:20]: add(a,pid,label='SKU '+str(pid))
    add(a,products[20],1,409,'21st SKU'); add(a,products[0],label='merge allowed at 20 SKU')
    check('20 SKU retained',len(rows(ALICE))==20)
    clear(ALICE)
    parallel(a,a2,'/cart/items',[{'productId':P1,'quantity':1}]*2,[303,303],'same SKU concurrent add')
    check('concurrent unique row',len(rows(ALICE))==1 and rows(ALICE)[0][2:]==(2,1),rows(ALICE))
    clear(ALICE); add(a,P1,98,label='prepare 98')
    parallel(a,a2,'/cart/items',[{'productId':P1,'quantity':1}]*2,[303,409],'99 boundary concurrent add')
    check('quantity capped 99',rows(ALICE)[0][2:]==(99,1),rows(ALICE))
    clear(ALICE)
    sql(f'INSERT INTO cart_item(user_id,product_id,quantity) SELECT {ALICE},id,1 FROM product WHERE id IN ({",".join(map(str,products[:19]))})')
    parallel(a,a2,'/cart/items',[{'productId':products[19],'quantity':1},{'productId':products[20],'quantity':1}],[303,409],'20 SKU concurrent boundary')
    check('concurrent SKU cap',len(rows(ALICE))==20)
    clear(ALICE); add(a,P1,label='prepare version race')
    item,_,_,version=rows(ALICE)[0]
    parallel(a,a2,f'/cart/items/{item}/quantity',[{'quantity':2,'version':version},{'quantity':3,'version':version}],[303,409],'same version concurrent update')
    check('version increments once',rows(ALICE)[0][3]==version+1)
    clear(ALICE)
    add(a,P1,3,label='invalid draft fixture'); add(a,P2,2,label='invalid zero fixture'); add(a,P3,4,label='invalid stock fixture')
    sql(f"UPDATE product SET status='DRAFT' WHERE id={P1}; UPDATE product SET stock=0 WHERE id={P2}; UPDATE product SET stock=1 WHERE id={P3}")
    # Use another public product for cross-page badge checks after P1 becomes unavailable.
    oldP1=P1; P1=products[3]
    badge(a,9)
    page=get(a,'/cart'); soup=BeautifulSoup(page.text,'html.parser')
    check('all invalid reasons',all(x in page.text for x in ['下架','售罄','库存']))
    check('invalid checkout blocked',bool(soup.select('[data-checkout-allowed="false"]')))
    for item,pid,quantity,version in list(rows(ALICE)):
        post(a,f'/cart/items/{item}/quantity',{'quantity':quantity,'version':version},409,'invalid item change',unchanged=True)
        post(a,f'/cart/items/{item}/remove',{'version':version},303,'invalid item removable')
    badge(a,0)
    add(a,P1,2,label='persistent cart'); badge(a,2)
    csrf=token(a); response=a.post(BASE+'/logout',data={'_csrf':csrf},timeout=20,allow_redirects=False)
    check('logout success',response.status_code==303)
    visitor=BeautifulSoup(get(a,'/').text,'html.parser').select_one('#cart-quantity')
    check('logout badge is zero',visitor.get('data-cart-quantity')=='0')
    a=login('alice'); badge(a,2); badge(b,0)
    sql(f"UPDATE store_user SET status='DISABLED' WHERE id={ALICE}")
    post(a,'/cart/items',{'productId':P1,'quantity':1},302,'disabled identity before CSRF',csrf=False,unchanged=True)
    sql(f"UPDATE store_user SET status='ENABLED' WHERE id={ALICE}")
    a=login('alice'); badge(a,2)
    before_restart = snapshot()
    appdir=Path(instance['private_directory'])/'application'
    lifecycle=appdir/'lifecycle.json'
    events_before=json.loads(lifecycle.read_text(encoding='utf-8'))
    (appdir/'RESTART').touch()
    deadline=time.monotonic()+45
    while time.monotonic()<deadline:
        try:
            events=json.loads(lifecycle.read_text(encoding='utf-8'))
            if len(events)>len(events_before) and events[-1]['event']=='restarted': break
        except (OSError,json.JSONDecodeError): pass
        time.sleep(.2)
    else: raise AssertionError('Application restart did not complete')
    check('restart preserved seven tables',snapshot()==before_restart)
    old=a.get(BASE+'/cart',timeout=20,allow_redirects=False)
    check('restart requires fresh session',old.status_code==302)
    a=login('alice'); badge(a,2)
    result['restart_events']=events
    result['completed']=True
except Exception as failure:
    result['completed']=False; result['failure']=str(failure)
    raise
finally:
    (OUT/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
