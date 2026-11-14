"""STEP07 isolated verification; external tools only, no repository business mutation."""
from pathlib import Path
from html.parser import HTMLParser
import os,sys,re,json,time,socket,secrets,hashlib,subprocess,datetime,traceback,urllib.request,urllib.error,urllib.parse,http.cookiejar,zipfile,struct,gzip
REPO=Path('D:/Github Projects/CSUCampusCraft')
HERE=Path(__file__).resolve().parent
RUNTIME=Path('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies')
GIT=Path('C:/Program Files/Git/cmd/git.exe')
JAVA=Path('C:/Users/Starmetor/.jdks/ms-21.0.12.1/bin/java.exe')
MYSQL=Path('D:/MySQL/bin')
BASELINE='a1d4f3523f557af63fc77ea883986c099edcd93e'
TESTED=os.environ.get('STEP07_TESTED_CODE_SHA','')
if not re.fullmatch(r'[0-9a-f]{40}',TESTED):raise SystemExit('STEP07_TESTED_CODE_SHA must be exact 40-character implementation SHA')
RUN=sys.argv[1] if len(sys.argv)>1 else ''
if not re.fullmatch(r'attempt[1-9][0-9]*',RUN):raise SystemExit('Use a fresh attemptN')
BASE=HERE/'runtime'/RUN;EV=HERE/'evidence'/RUN
BASE.mkdir(parents=True,exist_ok=False);EV.mkdir(parents=True,exist_ok=False)
FLAG=subprocess.CREATE_NO_WINDOW
result={'date':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'baseline_git_sha':BASELINE,'tested_code_sha':TESTED,'ours_parent_tip':'dda8f8254eec3f63e9c3bede397131cbe55c6179','member_parent_tip':'221dfb6dfa4fe93d69ffe1eecda97e98705406e1','requested_evidence_batch':'2026-11-15-step07-merged','timestamp_policy':'actual system clock; batch directory date is user requested','checks':{},'scope':'Merged STEP07 cart; new full matrix, real guest journey, bounded actor-lock/disable interleaving; no cart/order concurrency or injected fault'}
match=re.search(r'教学密码为\s*\x60([^\x60]+)\x60',(REPO/'README.md').read_text(encoding='utf-8'))
if not match:raise SystemExit('Teaching password unavailable; do not fabricate credential')
PASSWORD=match.group(1)
rootpass,apppass=secrets.token_urlsafe(28),secrets.token_urlsafe(28)
wrongpass=secrets.token_urlsafe(24)
secret_values=[rootpass,apppass,PASSWORD,wrongpass]
handles=[];processes=[];server=None;http_no=0;command_no=0;private_files=[];restore_actions=[]
TABLES=['store_user','category','product','product_image','cart_item','sales_order','sales_order_item']
COOKIE_NAMES={8080:'CSUCAMPUSCRAFT_USER_SESSION',8081:'CSUCAMPUSCRAFT_ADMIN_SESSION'}

def scrub(s):
    for v in sorted(set(secret_values),key=len,reverse=True):
        if len(v)>=8:s=s.replace(v,'[REDACTED]')
    s=re.sub(r'(?i)(name=["\']_csrf["\'][^>]*value=["\'])[^"\']*(["\'])',r'\1[REDACTED]\2',s)
    s=re.sub(r'(?i)(value=["\'])[^"\']*(["\'][^>]*name=["\']_csrf["\'])',r'\1[REDACTED]\2',s)
    s=re.sub(r'(?i)(;CSUCAMPUSCRAFT_(?:USER|ADMIN)_SESSION=)[A-Za-z0-9.-]+',r'\1[REDACTED]',s)
    s=re.sub(r'(?im)^(Set-Cookie|Cookie):.*$',r'\1: [REDACTED]',s)
    s=re.sub(r'\$2[aby]\$\d\d\$[./A-Za-z0-9]{53}','[REDACTED-HASH]',s)
    return s
def save(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(scrub(text),encoding='utf-8',newline='\n')
def record(name,obj):
    with (EV/name).open('a',encoding='utf-8') as f:f.write(scrub(json.dumps(obj,ensure_ascii=False))+'\n')
def check(name,ok,detail=''):
    key=name;n=2
    while key in result['checks']:key=name+' ['+str(n)+']';n+=1
    result['checks'][key]={'passed':bool(ok),'detail':scrub(str(detail))}
    print(name+': '+('PASS' if ok else 'FAIL'),flush=True)
    if not ok:raise AssertionError(name)
def command(argv,**kw):
    global command_no
    command_no+=1;t=time.monotonic()
    p=subprocess.run([str(x) for x in argv],capture_output=True,creationflags=FLAG,**kw)
    record('commands.jsonl',{'sequence':command_no,'argv':[str(x) for x in argv],'exit_code':p.returncode,'elapsed_seconds':round(time.monotonic()-t,3)})
    return p
def git(*args):
    p=command([GIT,'-C',REPO,'-c','core.quotepath=false',*args],timeout=25)
    if p.returncode:raise RuntimeError('Read-only git failed')
    return p.stdout
def freeport():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
def stop(p):
    if p.poll() is None:
        p.terminate()
        try:p.wait(timeout=10)
        except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
class Node:
    def __init__(self,tag='',attrs=None,parent=None):self.tag=tag;self.a=dict(attrs or []);self.parent=parent;self.children=[]
    def nodes(self):
        yield self
        for x in self.children:
            if isinstance(x,Node):yield from x.nodes()
    def find(self,p):return next((n for n in self.nodes() if p(n)),None)
    def all(self,p):return [n for n in self.nodes() if p(n)]
    def text(self):return ''.join(x.text() if isinstance(x,Node) else x for x in self.children)
class Parser(HTMLParser):
    VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
    def __init__(self,text):super().__init__(convert_charrefs=True);self.root=Node();self.stack=[self.root];self.feed(text)
    def handle_starttag(self,tag,attrs):
        node=Node(tag,attrs,self.stack[-1]);self.stack[-1].children.append(node)
        if tag not in self.VOID:self.stack.append(node)
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==tag:self.stack=self.stack[:i];return
    def handle_data(self,data):self.stack[-1].children.append(data)
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*a):return None
class Client:
    def __init__(self):self.jar=http.cookiejar.CookieJar();self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(self.jar),NoRedirect())
    def cookie(self,port):return next((c.value for c in self.jar if c.name==COOKIE_NAMES[port]),None)
    def request(self,path='/',port=8080,method='GET',form=None,data=None,content_type=None,recorded=True):
        global http_no
        if form is not None:data=urllib.parse.urlencode(form,doseq=True).encode('utf-8');content_type='application/x-www-form-urlencoded'
        headers={'Accept':'text/html'}
        if content_type:headers['Content-Type']=content_type
        req=urllib.request.Request(f'http://127.0.0.1:{port}'+path,data=data,method=method,headers=headers)
        post_before=snapshot() if method=='POST' else None
        post_state=state() if method=='POST' else None
        try:r=self.opener.open(req,timeout=12)
        except urllib.error.HTTPError as e:r=e
        body=r.read();h=dict(r.headers.items());text=body.decode('utf-8',errors='replace');dom=Parser(text).root
        for c in self.jar:
            if c.value:secret_values.append(c.value)
        for n in dom.all(lambda x:x.tag=='input' and x.a.get('name')=='_csrf'):
            if n.a.get('value'):secret_values.append(n.a['value'])
        for set_cookie in r.headers.get_all('Set-Cookie',[]):
            value=set_cookie.split(';',1)[0].partition('=')[2]
            if value:secret_values.append(value)
        if recorded:
            http_no+=1
            redacted=scrub(text).encode('utf-8');digest=hashlib.sha256(redacted).hexdigest()
            filename='bodies/'+digest[:24]+'.body.gz'
            if not (EV/filename).exists():
                (EV/filename).parent.mkdir(exist_ok=True)
                (EV/filename).write_bytes(gzip.compress(redacted,mtime=0))
            record('http.jsonl',{'sequence':http_no,'method':method,'path':path,'port':port,'status':r.code,'content_type':h.get('Content-Type'),'location':h.get('Location'),'cookie_names':[c.name for c in self.jar],'cookie_values_recorded':False,'set_cookie_present':bool(r.headers.get_all('Set-Cookie',[])),'form_fields':sorted(form.keys()) if isinstance(form,dict) else None,'body_file':filename,'body_encoding':'gzip','redacted_body_sha256':digest,'redacted':True})
        check('no-session-url-rewriting-'+str(http_no),';CSUCAMPUSCRAFT_USER_SESSION=' not in text and ';CSUCAMPUSCRAFT_ADMIN_SESSION=' not in text and ';CSUCAMPUSCRAFT_' not in h.get('Location',''))
        if method=='POST':snapshot_pair('http-post-'+str(http_no),post_before,post_state,snapshot(),state(),http_sequence=http_no,path=path,status=r.code,automatic_all_posts=True)
        return r.code,h,body,dom
    def get(self,path='/',port=8080,recorded=True):return self.request(path,port,recorded=recorded)
    def post(self,path,form,port=8080):return self.request(path,port,method='POST',form=form)
def token(r):
    n=r[3].find(lambda x:x.tag=='input' and x.a.get('name')=='_csrf')
    return n.a.get('value') if n else None
def assert_page(r,status,name):
    check(name+'-status',r[0]==status,str(status))
    if status in (302,303):return
    check(name+'-html',r[1].get('Content-Type','').startswith('text/html'))
    text=r[2].decode('utf-8')
    check(name+'-no-secrets',PASSWORD not in text and not re.search(r'\\$2[aby]\\$\\d\\d\\$[./A-Za-z0-9]{53}',text))
    if status>=400:
        feedback=r[3].find(lambda n:n.a.get('role')=='alert' or 'field-error' in n.a.get('class',''))
        check(name+'-error-feedback',feedback is not None or str(status) in r[3].text())
        check(name+'-no-technical-leak','java.lang.' not in text and 'jdbc:mysql:' not in text and 'SELECT ' not in text)


def login_page(cl,port,name='login',return_url=None):
    path='/login'+('?' + urllib.parse.urlencode({'returnUrl':return_url}) if return_url is not None else '')
    r=cl.get(path,port);assert_page(r,200,name)
    p=r[3].find(lambda n:n.tag=='input' and n.a.get('name')=='password')
    check(name+'-password-empty',p is not None and p.a.get('type')=='password' and not p.a.get('value'))
    check(name+'-csrf',bool(token(r)) and bool(re.fullmatch('[0-9a-f]{64}',token(r) or '')))
    return r
def login(cl,port,username=None,password=None,return_url='/',name='success'):
    r=login_page(cl,port,name+'-form',return_url)
    old=cl.cookie(port);t=token(r)
    resp=cl.post('/login',{'username':username or ('alice' if port==8080 else 'admin'),'password':PASSWORD if password is None else password,'_csrf':t,'returnUrl':return_url},port)
    return resp,old,t
def logged_in(cl,port,name):
    r=cl.get('/cart' if port==8080 else '/',port)
    assert_page(r,200,name)
    return r
def is_login_redirect(r,name,expected_return=None):
    check(name+'-302',r[0]==302)
    u=urllib.parse.urlsplit(r[1].get('Location',''))
    check(name+'-same-end-login',not u.netloc and u.path=='/login')
    q=urllib.parse.parse_qs(u.query)
    check(name+'-return-url-present',bool(q.get('returnUrl')))
    if expected_return is not None:check(name+'-return-url',q.get('returnUrl')==[expected_return])
def has_logout(r):return bool(r[3].find(lambda n:n.tag=='form' and urllib.parse.urlsplit(n.a.get('action','')).path=='/logout'))

mysqlport=freeport();env=os.environ.copy();env['MYSQL_PWD']=rootpass
MYSQLARGS=[MYSQL/'mysql.exe','--no-defaults','--no-login-paths','--protocol=TCP','--host=127.0.0.1',f'--port={mysqlport}','--user=root','--connect-timeout=2','--default-character-set=utf8mb4','--batch','--raw','--skip-column-names','--unbuffered']
def sql(q,db=None,fail_ok=False):
    p=command(MYSQLARGS+([f'--database={db}'] if db else []),input=("SET SESSION time_zone='+00:00';"+q).encode('utf-8'),env=env,timeout=40)
    if p.returncode and not fail_ok:
        save(EV/('sql-error-'+str(command_no)+'.json'),json.dumps({'query':q,'exit_code':p.returncode,'stderr':p.stderr.decode('utf-8',errors='replace')},ensure_ascii=False,indent=2))
        raise RuntimeError('Isolated SQL command failed')
    return p
def rows(q,db='csucampuscraft'):return sql(q,db).stdout.decode('utf-8').strip()
def literal(text):return "(CONVERT(0x"+text.encode('utf-8').hex()+" USING utf8mb4) COLLATE utf8mb4_0900_as_ci)"
def snapshot():
    query="".join("SELECT '__STEP07_"+t+"__';SELECT COUNT(*) FROM "+t+";SELECT * FROM "+t+" ORDER BY id;" for t in TABLES)
    data=sql(query,'csucampuscraft').stdout;out={}
    for i,t in enumerate(TABLES):
        marker=('__STEP07_'+t+'__').encode();start=data.index(marker)+len(marker)
        start+=2 if data[start:start+2]==b'\r\n' else 1
        end=data.index(('__STEP07_'+TABLES[i+1]+'__').encode(),start) if i+1<len(TABLES) else len(data)
        payload=data[start:end];count,raw=payload.split(b'\n',1)
        out[t]={'rows':int(count),'sha256':hashlib.sha256(raw).hexdigest()}
    return out


def start_env():
    e=os.environ.copy()
    for k in ['SPRING_APPLICATION_JSON','SPRING_CONFIG_LOCATION','SPRING_CONFIG_ADDITIONAL_LOCATION','JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVA_OPTIONS']:e.pop(k,None)
    url=f'jdbc:mysql://127.0.0.1:{mysqlport}/csucampuscraft'
    e.update(CSUCAMPUSCRAFT_DB_URL=url,CSUCAMPUSCRAFT_DB_USER='csucampuscraft',CSUCAMPUSCRAFT_DB_PASSWORD=apppass,SPRING_DATASOURCE_URL=url,SPRING_DATASOURCE_USERNAME='csucampuscraft',SPRING_DATASOURCE_PASSWORD=apppass,SPRING_PROFILES_ACTIVE='default',SPRING_SQL_INIT_MODE='never')
    return e
launch_counts={}
def launch(app,port,profile='default'):
    launch_counts[app]=launch_counts.get(app,0)+1
    log=BASE/(app+'-'+profile+'-'+str(launch_counts[app])+'.log');h=log.open('wb');handles.append(h)
    argv=[JAVA,'-jar',REPO/app/'target'/f'{app}-0.0.1-SNAPSHOT.jar',f'--server.port={port}','--server.address=127.0.0.1','--spring.profiles.active='+profile]
    p=subprocess.Popen([str(x) for x in argv],env=start_env(),stdout=h,stderr=subprocess.STDOUT,creationflags=FLAG);processes.append(p)
    record('launches.jsonl',{'app':app,'port':port,'database':'csucampuscraft','database_port':mysqlport,'database_user':'csucampuscraft','password_supplied':True,'profile':profile,'argv':[str(x) for x in argv]})
    until=time.monotonic()+55;cl=Client()
    while time.monotonic()<until:
        if p.poll() is not None:raise RuntimeError(app+' exited at startup')
        try:
            if cl.get('/login',port,recorded=False)[0]==200 and 'Started CSUCampusCraft' in log.read_text(encoding='utf-8',errors='replace'):
                owner=command([Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe','-NoLogo','-NoProfile','-Command',f"Get-NetTCPConnection -LocalPort {port} -State Listen | Select-Object -ExpandProperty OwningProcess"],timeout=20)
                pids=[int(x) for x in owner.stdout.decode(errors='replace').split() if x.isdigit()]
                check(app+'-listener-owned-by-created-process',owner.returncode==0 and pids and all(x==p.pid for x in pids))
                record('listener-ownership.jsonl',{'app':app,'port':port,'created_pid':p.pid,'observed_pids':pids,'passed':True})
                return p
        except (OSError,urllib.error.URLError):pass
        time.sleep(.2)
    raise RuntimeError(app+' initialization timeout')

# Merged STEP07 verification helpers follow.

def state():
    queries={
      'cart_item':"SELECT JSON_OBJECT('id',id,'userId',user_id,'productId',product_id,'quantity',quantity,'version',version,'createdAt',created_at,'updatedAt',updated_at) FROM cart_item ORDER BY id;",
      'product':"SELECT JSON_OBJECT('id',id,'sku',sku,'name',name,'price',CAST(price AS CHAR),'stock',stock,'status',status,'version',version,'updatedAt',updated_at) FROM product ORDER BY id;"}
    return {t:{str(x['id']):x for x in map(json.loads,rows(q).splitlines())} for t,q in queries.items()}

def deltas(a,b):
    return {t:[{'id':k,'before':a[t].get(k),'after':b[t].get(k)} for k in sorted(set(a[t])|set(b[t]),key=int) if a[t].get(k)!=b[t].get(k)] for t in a}
def cartrows(uid=1):return sorted((x for x in state()['cart_item'].values() if x['userId']==uid),key=lambda x:x['id'])
def item(iid):return state()['cart_item'].get(str(iid))
def item_for(pid,uid=1):return next((x for x in cartrows(uid) if x['productId']==pid),None)
def product(pid):return state()['product'][str(pid)]
def pid_by_sku(sku):return int(rows('SELECT id FROM product WHERE sku='+literal(sku)))
def quantity(uid=1):return int(rows('SELECT COALESCE(SUM(quantity),0) FROM cart_item WHERE user_id='+str(uid)))
def unchanged_other(a,b):return all(a[t]==b[t] for t in TABLES if t!='cart_item')
def snapshot_pair(name,before,a,after,b,**extra):
    record('database-writes.jsonl',dict(name=name,before=before,after=after,cart_before=a['cart_item'],cart_after=b['cart_item'],product_before=a['product'],product_after=b['product'],deltas=deltas(a,b),**extra))
def badge(r,uid,name):
    n=r[3].find(lambda x:x.a.get('id')=='cart-quantity')
    expected=quantity(uid) if uid is not None else 0
    check(name+'-badge-present',n is not None)
    check(name+'-badge-sum',n.a.get('data-cart-quantity')==str(expected) and n.text().strip()==str(expected),{'expected':expected})
    record('badge-observations.jsonl',{'name':name,'http_sequence':http_no,'user_id':uid,'expected_sum_all_rows':expected,'displayed':n.text().strip(),'data_value':n.a.get('data-cart-quantity'),'includes_invalid_rows':True})
    return r
def cart(cl,uid,name):
    r=cl.get('/cart');assert_page(r,200,name);badge(r,uid,name)
    root=r[3].find(lambda x:x.a.get('data-page-id')=='U05');check(name+'-root',root is not None)
    expected=cartrows(uid);actual=root.all(lambda x:x.tag=='tr' and 'data-cart-item-id' in x.a)
    check(name+'-own-rows-only',[int(x.a['data-cart-item-id']) for x in actual]==[x['id'] for x in expected])
    invalid=0;total=Decimal('0.00')
    for n,x in zip(actual,expected):
        p=product(x['productId']);valid=p['status']=='ON_SALE' and p['stock']>0 and x['quantity']<=p['stock']
        check(name+'-row-'+str(x['id']),n.a.get('data-product-id')==str(x['productId']) and n.a.get('data-quantity')==str(x['quantity']) and n.a.get('data-version')==str(x['version']))
        check(name+'-validity-'+str(x['id']),n.a.get('data-cart-valid')==str(valid).lower())
        unit=n.find(lambda z:z.tag=='td' and 'cart-money' in z.a.get('class','').split())
        check(name+'-unit-price-'+str(x['id']),unit is not None and unit.text().strip()=='¥'+format(Decimal(p['price']),'.2f'))
        if valid:
            line_amount=Decimal(p['price'])*x['quantity'];total+=line_amount
            amount=n.find(lambda z:'data-line-subtotal' in z.a)
            check(name+'-line-money-'+str(x['id']),amount is not None and Decimal(amount.a['data-line-subtotal'])==line_amount and amount.text().strip()=='¥'+format(line_amount,'.2f'))
        else:
            invalid+=1;reason='DRAFT' if p['status']!='ON_SALE' else 'SOLD_OUT' if p['stock']==0 else 'OVER_STOCK'
            check(name+'-invalid-reason-'+str(x['id']),n.a.get('data-invalid-reason')==reason)
            check(name+'-visible-reason-'+str(x['id']),{'DRAFT':'下架','SOLD_OUT':'售罄','OVER_STOCK':'超过当前库存'}[reason] in n.text())
            amount=n.find(lambda z:'data-line-subtotal' in z.a)
            check(name+'-invalid-no-numeric-subtotal-'+str(x['id']),amount is None or not amount.a.get('data-line-subtotal'))
        forms=n.all(lambda z:z.tag=='form')
        check(name+'-row-forms-'+str(x['id']),{f.a.get('data-cart-action') for f in forms}=={'quantity','remove'})
        for f in forms:
            check(name+'-csrf-'+str(x['id']),len(f.all(lambda z:z.tag=='input' and z.a.get('name')=='_csrf'))==1)
            version=f.find(lambda z:z.tag=='input' and z.a.get('name')=='version')
            check(name+'-form-version-'+str(x['id']),version is not None and version.a.get('value')==str(x['version']))
    amount=root.find(lambda x:'data-cart-total' in x.a)
    check(name+'-valid-total',amount is not None and Decimal(amount.a['data-cart-total'])==total)
    check(name+'-invalid-count',root.a.get('data-cart-invalid-count')==str(invalid))
    checkout=root.find(lambda x:'data-checkout-unavailable' in x.a)
    check(name+'-checkout-unavailable',checkout is not None and 'disabled' in checkout.a)
    check(name+'-no-checkout-link',not root.find(lambda x:x.a.get('href')=='/checkout' or x.a.get('action')=='/orders'))
    if not expected:check(name+'-empty-state','去逛逛' in root.text() or '购物车' in root.text())
    record('cart-observations.jsonl',{'name':name,'http_sequence':http_no,'user_id':uid,'ordered_cart_rows':expected,'invalid_count':invalid,'valid_total':str(total),'quantity_sum':quantity(uid)})
    return r
def write(cl,path,form,status,name,csrf=True,uid=1,back='/cart'):
    data=dict(form)
    if csrf:
        r=cl.get(back);assert_page(r,200,name+'-form');data['_csrf']=token(r);check(name+'-token',bool(data['_csrf']))
    before=snapshot();a=state();r=cl.post(path,data);after=snapshot();b=state()
    snapshot_pair(name,before,a,after,b,path=path,status=r[0],expected_status=status,csrf_supplied=csrf,actor_user_id=uid,form_fields=sorted(data))
    assert_page(r,status,name)
    check(name+'-other-six-tables-unchanged',unchanged_other(before,after))
    if status!=303:
        check(name+'-rejected-zero-write',before==after)
        if status not in [302] and uid is not None:badge(r,uid,name)
    else:
        u=urllib.parse.urlsplit(r[1].get('Location',''))
        check(name+'-fixed-cart-redirect',not u.netloc and u.path=='/cart' and not u.query)
        changes=deltas(a,b)['cart_item'];check(name+'-own-cart-only',all((x['before'] or x['after'])['userId']==uid for x in changes))
        check(name+'-at-most-one-cart-row',len(changes)<=1)
    return r,a,b
def add(cl,pid,qty,name,uid=1,**extra):
    old=item_for(pid,uid);r,a,b=write(cl,'/cart/items',dict(productId=str(pid),quantity=str(qty),**extra),303,name,uid=uid,back='/products/'+str(pid))
    current=item_for(pid,uid);check(name+'-one-sku-row',current is not None and len([x for x in cartrows(uid) if x['productId']==pid])==1)
    check(name+'-quantity',current['quantity']==(old['quantity'] if old else 0)+int(qty))
    check(name+'-version',current['version']==(old['version']+1 if old else 0))
    return current
def change(cl,row,qty,name,status=303,version=None,uid=1):
    form={'quantity':str(qty),'version':str(row['version'] if version is None else version)}
    return write(cl,'/cart/items/'+str(row['id'])+'/quantity',form,status,name,uid=uid)
def remove(cl,row,name,status=303,version=None,uid=1):
    return write(cl,'/cart/items/'+str(row['id'])+'/remove',{'version':str(row['version'] if version is None else version)},status,name,uid=uid)
def clear_cart(cl,uid,name):
    for i,row in enumerate(cartrows(uid)):remove(cl,row,name+'-'+str(i),uid=uid)
    check(name+'-empty',not cartrows(uid))
def fixture(q,name):
    before=snapshot();a=state();sql(q,'csucampuscraft');after=snapshot();b=state()
    record('fixtures.jsonl',{'name':name,'controlled_root_fixture':True,'query':q,'before':before,'after':after,'deltas':deltas(a,b)})
def restore_products(original):
    for x in original.values():
        now=product(x['id'])
        if now!=x:
            fixture("UPDATE product SET price="+x['price']+",stock="+str(x['stock'])+",status="+literal(x['status'])+",version="+str(x['version'])+",updated_at="+literal(x['updatedAt'])+" WHERE id="+str(x['id'])+';','restore-product-'+str(x['id']))
def static_manifest():
    out={}
    for p in sorted((REPO/'assets').rglob('*')):
        if p.is_file():out['assets/'+p.relative_to(REPO/'assets').as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    for app in ['csucampuscraft-user','csucampuscraft-admin']:
        with zipfile.ZipFile(REPO/app/'target'/f'{app}-0.0.1-SNAPSHOT.jar') as z:
            for n in z.namelist():
                if n.startswith('BOOT-INF/classes/static/images/') and not n.endswith('/'):out[app+'/'+n]=hashlib.sha256(z.read(n)).hexdigest()
    return out
def native_probe():
    extracted=BASE/'native-probe';classes=extracted/'classes';libs=extracted/'lib';classes.mkdir(parents=True);libs.mkdir()
    with zipfile.ZipFile(REPO/'csucampuscraft-user/target/csucampuscraft-user-0.0.1-SNAPSHOT.jar') as z:
        for n in z.namelist():
            if n.startswith('BOOT-INF/classes/') and not n.endswith('/'):
                p=classes/n[len('BOOT-INF/classes/'):];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
            elif n.startswith('BOOT-INF/lib/') and n.endswith('.jar'):(libs/Path(n).name).write_bytes(z.read(n))
    cp=str(classes)+';'+str(libs/'*')+';'+str(extracted)
    p=command([JAVA.parent/'javac.exe','-cp',cp,'-d',extracted,HERE/'CartWriteProbe.java'],timeout=45)
    save(EV/'native-compile.log',p.stdout.decode('utf-8',errors='replace')+p.stderr.decode('utf-8',errors='replace'));check('native-probe-compile',p.returncode==0)
    e=start_env();e.update(STEP07_ROOT_PASSWORD=rootpass,STEP07_MYSQL_PORT=str(mysqlport))
    before=snapshot();a=state();p=command([JAVA,'-cp',cp,'CartWriteProbe'],env=e,timeout=110);after=snapshot();b=state()
    save(EV/'native-probe.log',p.stdout.decode('utf-8',errors='replace')+p.stderr.decode('utf-8',errors='replace'))
    snapshot_pair('native-cart-service-probe',before,a,after,b)
    check('native-probe',p.returncode==0 and '"overall":"PASS"' in p.stdout.decode('utf-8',errors='replace'))
    check('native-other-six-tables-stable',unchanged_other(before,after))
def browser(cookies,cases):
    e=start_env();e.update(STEP07_BROWSER_OUT=str(EV/'browser'),STEP07_BROWSER_CASES=json.dumps(cases,ensure_ascii=False),STEP07_BROWSER_COOKIES=json.dumps(cookies))
    before=snapshot();p=command([RUNTIME/'node/bin/node.exe',HERE/'verify_browser.cjs'],env=e,timeout=150)
    save(EV/('browser-'+str(len(cases))+'.log'),p.stdout.decode('utf-8',errors='replace')+p.stderr.decode('utf-8',errors='replace'));check('browser',p.returncode==0)
    br=json.loads((EV/'browser/result.json').read_text(encoding='utf-8'));check('browser-completed',br.get('completed') and br['overall']=='PASS')
    result['browser_checks']=len(br['checks'])+result.get('journey_checks',0);result['screenshots']=len(br['screenshots'])+result.get('journey_screenshots',0);check('browser-zero-write',snapshot()==before)

from decimal import Decimal

def guest_browser_journey(product_id):
    from http.server import BaseHTTPRequestHandler,HTTPServer
    from threading import Thread
    import base64
    check('journey-starts-with-empty-own-cart',not cartrows(1))
    control_token=secrets.token_urlsafe(32);secret_values.append(control_token)
    pending={};failures=[];completed=[]
    def actual_response(info):
        global http_no
        text=base64.b64decode(info['body_base64']).decode('utf-8',errors='replace')
        dom=Parser(text).root
        for n in dom.all(lambda x:x.tag=='input' and x.a.get('name')=='_csrf'):
            if n.a.get('value'):secret_values.append(n.a['value'])
        http_no+=1
        redacted=scrub(text).encode('utf-8');digest=hashlib.sha256(redacted).hexdigest()
        filename='bodies/'+digest[:24]+'.body.gz'
        if not (EV/filename).exists():
            (EV/filename).parent.mkdir(exist_ok=True);(EV/filename).write_bytes(gzip.compress(redacted,mtime=0))
        record('http.jsonl',{'sequence':http_no,'method':info['method'],'path':info['path'],'port':8080,'status':info['status'],'content_type':info['content_type'],'location':info['location'],'cookie_names':info['cookie_names'],'cookie_values_recorded':False,'set_cookie_present':info['set_cookie_present'],'form_fields':pending[info['id']]['fields'] if info['id'] in pending else None,'body_file':filename,'body_encoding':'gzip','redacted_body_sha256':digest,'redacted':True,'transport':'actual Playwright navigation','body_available':info['body_available']})
        check('journey-no-session-url-'+str(http_no),';CSUCAMPUSCRAFT_' not in text and ';CSUCAMPUSCRAFT_' not in (info['location'] or ''))
        if dom.find(lambda n:n.a.get('id')=='cart-quantity'):
            authenticated=dom.find(lambda n:n.tag=='body' and n.a.get('data-authenticated')=='true') is not None
            badge((info['status'],{'Content-Type':info['content_type']},text.encode('utf-8'),dom),1 if authenticated else None,'journey-badge-'+str(http_no))
        if info['method']=='POST':
            context=pending.pop(info['id'])
            check('journey-response-path-matches-before',info['path']==context['path'])
            after=snapshot();b=state()
            snapshot_pair('http-post-'+str(http_no),context['before'],context['state'],after,b,http_sequence=http_no,path=info['path'],status=info['status'],automatic_all_posts=True,transport='playwright-guest-journey')
            snapshot_pair('browser-journey-'+info['path'].strip('/').replace('/','-'),context['before'],context['state'],after,b,path=info['path'],status=info['status'],expected_status=303,actor_user_id=1,transport='playwright-guest-journey')
            check('journey-post-303-'+info['path'],info['status']==303)
            check('journey-post-other-six-unchanged-'+info['path'],unchanged_other(context['before'],after))
            if info['path']=='/login':check('journey-login-not-replayed-cart',context['before']==after)
            else:
                delta=deltas(context['state'],b)['cart_item']
                check('journey-manual-one-new-row',len(delta)==1 and delta[0]['before'] is None and delta[0]['after']['userId']==1 and delta[0]['after']['productId']==product_id and delta[0]['after']['quantity']==1 and delta[0]['after']['version']==0)
        return {'ok':True,'sequence':http_no}
    class Observer(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            try:
                if not secrets.compare_digest(self.headers.get('X-Audit-Token',''),control_token):raise ValueError('Observer authentication failed')
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<2_000_000:raise ValueError('Observer message length invalid')
                item=json.loads(self.rfile.read(length).decode('utf-8'))
                if self.path=='/before':
                    check('journey-only-expected-post-path',item['path'] in ['/login','/cart/items'])
                    check('journey-single-post-at-a-time',not pending)
                    ident=rows('SELECT @@server_uuid,@@port,@@datadir;',None).split('\t')
                    check('journey-private-db-identity',ident[0]==uuid and int(ident[1])==mysqlport and Path(ident[2]).resolve()==data.resolve())
                    owner=command([Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe','-NoProfile','-Command','Get-NetTCPConnection -LocalPort 8080 -State Listen | Select-Object -ExpandProperty OwningProcess'],timeout=20)
                    pids=[int(x) for x in owner.stdout.decode().split() if x.isdigit()]
                    check('journey-owned-user-listener',owner.returncode==0 and pids and all(x==user_process.pid for x in pids))
                    pending[item['id']]={'path':item['path'],'fields':item['form_fields'],'before':snapshot(),'state':state()}
                    result_body={'ok':True}
                elif self.path=='/response':result_body=actual_response(item)
                elif self.path=='/complete':
                    check('journey-all-posts-audited',not pending and item['posts']==2 and item['screenshots']==4)
                    completed.append(True);result_body={'ok':True}
                else:raise ValueError('Observer path invalid')
                encoded=json.dumps(result_body).encode('utf-8');self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(encoded)));self.end_headers();self.wfile.write(encoded)
            except Exception as failure:
                failures.append(type(failure).__name__+': '+scrub(str(failure)))
                self.send_response(500);self.send_header('Content-Length','0');self.end_headers()
    observer=HTTPServer(('127.0.0.1',0),Observer)
    thread=Thread(target=observer.serve_forever,daemon=True);thread.start()
    try:
        e=start_env();e.update(STEP07_JOURNEY_OUT=str(EV/'journey'),STEP07_JOURNEY_PRODUCT=str(product_id),STEP07_JOURNEY_CONTROL=str(observer.server_port),STEP07_JOURNEY_CONTROL_TOKEN=control_token,STEP07_JOURNEY_PASSWORD=PASSWORD)
        p=command([RUNTIME/'node/bin/node.exe',HERE/'verify_guest_journey.cjs'],env=e,timeout=150)
        save(EV/'journey.log',p.stdout.decode('utf-8',errors='replace')+p.stderr.decode('utf-8',errors='replace'))
        if failures:save(EV/'journey-observer-errors.json',json.dumps(failures,ensure_ascii=False,indent=2))
        check('guest-real-browser-journey',p.returncode==0 and not failures and completed and not pending)
        jr=json.loads((EV/'journey/result.json').read_text(encoding='utf-8'))
        check('guest-real-browser-completed',jr['overall']=='PASS' and jr['completed'])
        result['journey_checks']=len(jr['checks']);result['journey_screenshots']=len(jr['screenshots']);result['journey_posts']=len(jr['posts'])
        check('guest-journey-four-screens-two-posts',result['journey_screenshots']==4 and result['journey_posts']==2)
        check('guest-journey-one-manual-cart-item',len(cartrows(1))==1 and item_for(product_id)['quantity']==1)
    finally:
        observer.shutdown();observer.server_close();thread.join(timeout=3)


try:
    check('tested-code-head',git('rev-parse','HEAD').decode().strip()==TESTED)
    result['branch']=git('branch','--show-current').decode().strip();check('feature-branch',result['branch']=='feat/step07-cart-merged')
    status=git('status','--short','--untracked-files=all').decode();save(EV/'git-input-status.txt',status);check('tested-worktree-clean',not status.strip())
    save(EV/'implementation-diff.patch',git('diff',BASELINE+'..'+TESTED,'--','csucampuscraft-user').decode('utf-8'))
    inputs=[]
    for app in ['csucampuscraft-user','csucampuscraft-admin']:
        inputs.append(REPO/app/'pom.xml');inputs.extend(p for p in (REPO/app/'src').rglob('*') if p.is_file())
    inputs.extend(p for d in ['database','assets','.mvn'] for p in (REPO/d).rglob('*') if p.is_file());inputs.extend([REPO/'mvnw',REPO/'mvnw.cmd'])
    manifest=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(REPO).as_posix()+'\n' for p in sorted(inputs,key=lambda x:x.relative_to(REPO).as_posix()))
    save(EV/'runtime-inputs.sha256',manifest);result['runtime_manifest_sha256']=hashlib.sha256(manifest.encode()).hexdigest();result['runtime_file_count']=len(inputs)
    for name in ['verify_step07.py','verify_browser.cjs','verify_guest_journey.cjs','CartWriteProbe.java']:save(EV/name,(HERE/name).read_text(encoding='utf-8-sig'))
    builddir=Path(os.environ.get('STEP07_BUILD_LOG_DIR',HERE.parent));exits=json.loads((builddir/'build-exits.json').read_text(encoding='utf-8-sig'))
    for app in ['user','admin']:
        text=(builddir/('build-'+app+'.log')).read_text(encoding='utf-8',errors='replace');check('wrapper-build-'+app,exits[app]==0 and 'BUILD SUCCESS' in text);save(EV/('build-'+app+'.log'),text)
    save(EV/'build-exits.json',json.dumps(exits))
    ve=os.environ.copy();ve['JAVA_HOME']=str(JAVA.parent.parent);ve['PATH']=str(JAVA.parent)+';'+os.environ['SystemRoot']+'/System32;'+os.environ['SystemRoot']+'/System32/WindowsPowerShell/v1.0'
    versions=[]
    for args in [[JAVA,'-version'],[REPO/'mvnw.cmd','-v'],[MYSQL/'mysqld.exe','--version']]:
        p=command(args,env=ve,timeout=60);check('tool-version-'+str(len(versions)),p.returncode==0);versions.append(p.stdout.decode(errors='replace')+p.stderr.decode(errors='replace'))
    save(EV/'versions.txt','\n'.join(versions));check('wrapper-pin','Apache Maven 3.9.16' in versions[1])
    for app in ['csucampuscraft-user','csucampuscraft-admin']:result[app+'_jar_sha256']=hashlib.sha256((REPO/app/'target'/f'{app}-0.0.1-SNAPSHOT.jar').read_bytes()).hexdigest()
    statics=static_manifest();save(EV/'static-before.json',json.dumps(statics,indent=2));result['static_files']=len(statics)
    data=BASE/'mysql-data';data.mkdir();init=BASE/'mysql-init-private.sql';private_files.append(init)
    init.write_text("ALTER USER 'root'@'localhost' IDENTIFIED BY '"+rootpass+"';",encoding='utf-8')
    p=command([MYSQL/'mysqld.exe','--no-defaults','--initialize-insecure','--basedir=D:/MySQL',f'--datadir={data}',f'--log-error={BASE/"mysql-initialize.log"}'],timeout=45);check('isolated-mysql-created',p.returncode==0)
    h=(BASE/'mysql-server.log').open('wb');handles.append(h)
    server=subprocess.Popen([str(MYSQL/'mysqld.exe'),'--no-defaults','--basedir=D:/MySQL',f'--datadir={data}',f'--port={mysqlport}','--bind-address=127.0.0.1','--mysqlx=OFF',f'--init-file={init}',f'--pid-file={BASE/"mysql.pid"}','--console'],stdout=h,stderr=subprocess.STDOUT,creationflags=FLAG)
    deadline=time.monotonic()+35
    while time.monotonic()<deadline:
        p=sql('SELECT @@version,@@server_uuid,@@port,@@datadir;',fail_ok=True)
        if p.returncode==0:break
        if server.poll() is not None:raise RuntimeError('Private MySQL exited')
        time.sleep(.2)
    else:raise RuntimeError('Private MySQL readiness timeout')
    ident=p.stdout.decode().strip().split('\t');uuid=re.search(r'server-uuid=(.+)',(data/'auto.cnf').read_text(encoding='utf-8')).group(1).strip()
    check('isolated-mysql-identity',ident[1]==uuid and int(ident[2])==mysqlport and Path(ident[3]).resolve()==data.resolve());result['mysql_version']=ident[0];result['mysql_port']=mysqlport;init.unlink()
    save(EV/'database-identity.json',json.dumps({'version':ident[0],'uuid':uuid,'port':mysqlport,'datadir_is_private':True,'every_connection_timezone':'UTC','collation':'utf8mb4_0900_as_ci'},indent=2))
    sql('CREATE DATABASE csucampuscraft CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_ci;')
    sql((REPO/'database/02-schema-with-demo.sql').read_text(encoding='utf-8-sig'),'csucampuscraft')
    sql("CREATE USER 'csucampuscraft'@'127.0.0.1' IDENTIFIED BY '"+apppass+"';")
    sql("GRANT SELECT,LOCK TABLES ON csucampuscraft.* TO 'csucampuscraft'@'127.0.0.1';")
    sql("GRANT INSERT,UPDATE,DELETE ON csucampuscraft.cart_item TO 'csucampuscraft'@'127.0.0.1';")
    save(EV/'application-grants.txt',rows("SHOW GRANTS FOR 'csucampuscraft'@'127.0.0.1';",None))
    original=snapshot();save(EV/'database-original.json',json.dumps(original,indent=2));check('seed-counts',[original[t]['rows'] for t in TABLES]==[4,15,60,100,10,10,20])
    for port in [8080,8081]:
        with socket.socket() as s:s.bind(('127.0.0.1',port))
    user_process=launch('csucampuscraft-user',8080);launch('csucampuscraft-admin',8081)
    originals=state()['product'];store_original=rows("SELECT CAST(updated_at AS CHAR) FROM store_user WHERE id=1;")
    note=pid_by_sku('CSU-LMK-NOTE-01');gift=pid_by_sku('CSU-GRAD-BOX-01');draft=pid_by_sku('CSU-CLB-FOLDER-02');sold=pid_by_sku('CSU-SPT-STAND-01')
    guest=Client();is_login_redirect(guest.get('/cart'),'guest-cart','/cart')
    guest_detail=guest.get('/products/'+str(gift));assert_page(guest_detail,200,'guest-detail-link-only')
    check('guest-detail-no-post-form',not guest_detail[3].find(lambda n:n.tag=='form' and n.a.get('method','').lower()=='post'))
    guest_link=guest_detail[3].find(lambda n:n.tag=='a' and 'data-login-to-add' in n.a)
    check('guest-detail-has-login-to-add',guest_link is not None and '登录后加购' in guest_link.text())
    guest_target=urllib.parse.urlsplit(guest_link.a['href'])
    check('guest-detail-login-return',guest_target.path=='/login' and urllib.parse.parse_qs(guest_target.query).get('returnUrl')==['/products/'+str(gift)])
    guest_sold=guest.get('/products/'+str(sold));assert_page(guest_sold,200,'guest-soldout-detail')
    check('guest-soldout-no-post-form',not guest_sold[3].find(lambda n:n.tag=='form' and n.a.get('method','').lower()=='post'))
    check('guest-soldout-no-login-purchase-link',not guest_sold[3].find(lambda n:'data-login-to-add' in n.a))
    check('guest-soldout-disabled-purchase',guest_sold[3].find(lambda n:n.tag=='button' and n.a.get('type')=='button' and 'disabled' in n.a and ('售罄' in n.text() or '加入购物车' in n.text())) is not None)
    r,_,_=write(guest,'/cart/items',{'productId':str(gift),'quantity':'abc'},302,'guest-before-format-csrf',csrf=False,uid=None)
    is_login_redirect(r,'guest-add-return-detail','/products/'+str(gift))
    for path in ['/cart/items/1/quantity','/cart/items/1/remove']:
        r,_,_=write(guest,path,{},302,'guest-'+path.split('/')[-1],csrf=False,uid=None);is_login_redirect(r,'guest-row-return-cart','/cart')
    r,_,_=login(guest,8080,return_url='/products/'+str(gift),name='guest-return-login');assert_page(r,303,'guest-login');check('guest-login-returns-GET',r[1].get('Location')=='/products/'+str(gift))
    check('login-did-not-replay-old-post',snapshot()==original)
    cl=guest;clbob=Client();r,_,_=login(clbob,8080,username='bob',name='bob');assert_page(r,303,'bob-login')
    admin=Client();r,_,_=login(admin,8081,name='admin');assert_page(r,303,'admin-login');assert_page(admin.get('/products',8081),200,'same-db-admin-read')
    cart(cl,1,'alice-seed-invalid-cart');cart(clbob,2,'bob-isolated-seed-cart')
    r=cl.get('/products/'+str(sold));assert_page(r,200,'soldout-detail-browsable');badge(r,1,'soldout-detail-badge')
    purchase=r[3].find(lambda n:n.tag=='form' and 'data-add-cart' in n.a)
    check('soldout-controls-disabled',purchase is not None and all('disabled' in n.a for n in purchase.all(lambda n:n.tag=='button' or n.tag=='input' and n.a.get('name')=='quantity')))
    for name,path in [('home','/'),('list','/products'),('detail','/products/'+str(gift)),('login','/login'),('400','/products?size=0'),('404','/step07-missing-page')]:
        r=cl.get(path);assert_page(r,400 if name=='400' else 404 if name=='404' else 200,'seed-badge-'+name);badge(r,1,'seed-badge-'+name)
    for path in ['/cart/items','/cart/items/1/quantity','/cart/items/1/remove']:
        write(cl,path,{},403,'missing-csrf-'+path.replace('/','-'),csrf=False)
        write(cl,path,{'_csrf':'not-a-session-token'},403,'wrong-csrf-'+path.replace('/','-'),csrf=False)
    # Preserve authentication timestamp so this deliberately wrong role is not confused with expiry.
    for cs in [False,True]:
        roleclient=Client();r,_,_=login(roleclient,8080,name='role-fixture-login');assert_page(r,303,'role-fixture-authenticated')
        role_token=token(roleclient.get('/products/'+str(gift)))
        fixture("UPDATE store_user SET role='ADMIN',updated_at=updated_at WHERE id=1;",'wrong-role-preserve-stamp')
        try:
            form={'productId':'bad-id','quantity':'bad-quantity','_csrf':role_token if cs else 'wrong-token'}
            r,_,_=write(roleclient,'/cart/items',form,403,'role-priority-'+str(cs),csrf=False,uid=None)
            check('csrf-before-role-'+str(cs),('CSRF_REJECTED' in r[3].text()) if not cs else ('AUTH_ROLE_FORBIDDEN' in r[3].text()))
        finally:fixture("UPDATE store_user SET role='CUSTOMER',updated_at=updated_at WHERE id=1;",'restore-customer-role')
    # All parameter failures use a valid CUSTOMER, valid CSRF and an otherwise available product.
    for index,value in enumerate([None,'','abc','1.0','1.2','1e0','0','-1','100','9223372036854775808']):
        form={'productId':str(gift)}
        if value is not None:form['quantity']=value
        write(cl,'/cart/items',form,400,'invalid-add-quantity-'+str(index))
    for index,value in enumerate([None,'','abc','1.0','1e0','0','-1','9223372036854775808']):
        form={'quantity':'1'}
        if value is not None:form['productId']=value
        write(cl,'/cart/items',form,400,'invalid-add-product-'+str(index))
    write(cl,'/cart/items',{'productId':str(gift),'quantity':['1','2']},400,'duplicate-quantity-field')
    for pid,name,status in [(999999999,'unknown-product',404),(draft,'draft-product',404),(sold,'sold-out-product',409)]:
        write(cl,'/cart/items',{'productId':str(pid),'quantity':'1'},status,'add-'+name)
    seedrow=cartrows(1)[0];foreign=cartrows(2)[0]
    for suffix,form in [('quantity',{'quantity':'1','version':str(foreign['version']+9)}),('remove',{'version':str(foreign['version']+9)})]:
        write(cl,'/cart/items/'+str(foreign['id'])+'/'+suffix,form,403,'foreign-'+suffix)
        write(cl,'/cart/items/999999999/'+suffix,form,404,'unknown-'+suffix)
    for suffix in ['quantity','remove']:
        for index,value in enumerate([None,'','abc','-1','1.0','9223372036854775808']):
            form={'quantity':'1'}
            if value is not None:form['version']=value
            write(cl,'/cart/items/'+str(seedrow['id'])+'/'+suffix,form,400,'invalid-'+suffix+'-version-'+str(index))
    for index,value in enumerate(['','abc','1.0','1e0','0','-1','100','9223372036854775808']):change(cl,seedrow,value,'invalid-change-quantity-'+str(index),400)
    clear_cart(cl,1,'clear-alice-seed-via-app');cart(cl,1,'empty-alice-after-removes')
    guest_browser_journey(gift)
    clear_cart(cl,1,'clear-real-browser-journey-via-app');cart(cl,1,'empty-after-real-browser-journey')
    row=add(cl,note,1,'add-new-sku-one',userId='2',role='ADMIN',price='0.01')
    row=add(cl,note,1,'duplicate-add-merges-in-one')
    cart(cl,1,'merged-quantity-two');check('forged-user-id-not-used',not item_for(note,2) or item_for(note,2)['id']!=row['id'])
    before=snapshot();change(cl,row,row['quantity'],'same-value-edit');check('same-value-no-write',snapshot()==before)
    change(cl,row,3,'actual-quantity-increments');new=item(row['id']);check('changed-version-plus-one',new['version']==row['version']+1)
    change(cl,new,2,'old-version-change',409,version=row['version']);remove(cl,new,'old-version-remove',409,version=row['version'])
    write(cl,'/cart/items',{'productId':str(note),'quantity':str(originals[str(note)]['stock'])},409,'merged-stock-shortage')
    fixture('UPDATE product SET stock=200,updated_at=updated_at WHERE id='+str(gift)+';','stock-for-99-boundary')
    large=add(cl,gift,99,'valid-single-99')
    write(cl,'/cart/items',{'productId':str(gift),'quantity':'1'},409,'merged-over-99-with-enough-stock')
    change(cl,large,98,'quantity-98');large=item(large['id']);check('change-98-version',large['version']==1)
    change(cl,large,99,'quantity-99');large=item(large['id']);remove(cl,large,'remove-valid-99')
    fixture('UPDATE cart_item SET version=9223372036854775807,updated_at=updated_at WHERE id='+str(new['id'])+';','max-cart-version')
    maxrow=item(new['id']);before=snapshot();change(cl,maxrow,maxrow['quantity'],'max-version-same-value');check('max-noop-all-tables-unchanged',snapshot()==before)
    change(cl,maxrow,2,'max-version-change-refused',409)
    write(cl,'/cart/items',{'productId':str(note),'quantity':'1'},409,'max-version-add-refused')
    remove(cl,maxrow,'max-version-remove-allowed');cart(cl,1,'empty-after-max-version-delete')
    # Every add/removal remains a real HTTP operation; root changes only stock/status fixture.
    candidates=[int(x) for x in rows("SELECT id FROM product WHERE status='ON_SALE' ORDER BY id LIMIT 21;").splitlines()]
    fixture('UPDATE product SET stock=200,updated_at=updated_at WHERE id IN ('+','.join(map(str,candidates))+');','stock-for-21-sku-matrix')
    for index,pid in enumerate(candidates[:20]):add(cl,pid,1,'fill-20-skus-'+str(index))
    fixture("UPDATE product SET status='DRAFT',updated_at=updated_at WHERE id="+str(candidates[0])+';','invalid-row-still-counts-toward-20')
    write(cl,'/cart/items',{'productId':str(candidates[20]),'quantity':'1'},409,'new-21st-sku-rejected-counts-invalid')
    add(cl,candidates[1],1,'existing-sku-can-merge-at-20')
    cart(cl,1,'twenty-types-including-invalid')
    clear_cart(cl,1,'clear-20-skus-via-app');restore_products(originals)
    # Independent scenario: exact 85.00 valid subtotal from current prices, without checkout/order routes.
    add(cl,note,2,'add-two-18-yuan-notebooks');add(cl,gift,1,'add-one-49-yuan-gift');r=cart(cl,1,'eighty-five-yuan-cart')
    check('85-yuan-total','85.00'==str(sum(Decimal(product(x['productId'])['price'])*x['quantity'] for x in cartrows(1))))
    stable_cart=cartrows(1);before=snapshot();stop(user_process);user_process=launch('csucampuscraft-user',8080)
    is_login_redirect(cl.get('/cart'),'old-session-after-restart','/cart')
    fresh=Client();r,_,_=login(fresh,8080,name='after-restart-login');assert_page(r,303,'restart-login');cl=fresh
    cart(cl,1,'restart-restores-cart');check('restart-did-not-write-any-table',snapshot()==before and cartrows(1)==stable_cart)
    # Logout redirects to / rather than cart, so validate via the raw HTTP audit path.
    before=snapshot();r=cl.post('/logout',{'_csrf':token(cl.get('/cart'))});assert_page(r,303,'logout');check('logout-return-home',r[1].get('Location')=='/');check('logout-preserves-database',snapshot()==before)
    badge(cl.get('/'),None,'after-logout-home');r,_,_=login(cl,8080,name='relogin');assert_page(r,303,'relogin');cart(cl,1,'relogin-restores-cart')
    other_browser=Client();r,_,_=login(other_browser,8080,name='new-browser');assert_page(r,303,'new-browser-login');cart(other_browser,1,'new-browser-same-account-cart')
    # Failed reauthentication cannot retain the old account's badge.
    bad=Client();r,_,_=login(bad,8080,name='reauth-start');assert_page(r,303,'reauth-start-login')
    r=bad.post('/login',{'username':'alice','password':wrongpass,'_csrf':token(bad.get('/login'))});assert_page(r,200,'failed-reauth');badge(r,None,'failed-reauth-clears-badge');is_login_redirect(bad.get('/cart'),'failed-reauth-clears-identity','/cart')
    bad2=Client();r,_,_=login(bad2,8080,name='invalid-reauth-start');assert_page(r,303,'invalid-reauth-login')
    r=bad2.post('/login',{'username':'','password':'','_csrf':token(bad2.get('/login'))});assert_page(r,400,'invalid-reauth');badge(r,None,'invalid-reauth-zero-badge')
    # Disable uses root SQL solely as a controlled authorization fixture. No admin enable route is added.
    fixture("UPDATE store_user SET status='DISABLED',updated_at=GREATEST(CURRENT_TIMESTAMP(6),updated_at+INTERVAL 1 MICROSECOND) WHERE id=1;",'disabled-customer')
    r,_,_=write(cl,'/cart/items',{'productId':'bad','quantity':'bad'},302,'disabled-before-csrf-format',csrf=False,uid=None);is_login_redirect(r,'disabled-login-redirect')
    badge(cl.get('/'),None,'disabled-public-home-as-guest')
    fixture("UPDATE store_user SET status='ENABLED',updated_at=GREATEST(CURRENT_TIMESTAMP(6),updated_at+INTERVAL 1 MICROSECOND) WHERE id=1;",'reenabled-requires-new-login')
    is_login_redirect(cl.get('/cart'),'reenabled-old-session-does-not-revive','/cart')
    fixture('UPDATE store_user SET status=\'ENABLED\',role=\'CUSTOMER\',updated_at='+literal(store_original)+' WHERE id=1;','restore-private-account-fixture-exact-stamp')
    cl=Client();r,_,_=login(cl,8080,name='after-disable-fresh-login');assert_page(r,303,'new-login-after-disable');cart(cl,1,'fresh-login-preserves-cart')
    # A current price changes preview only, with no cart version/update writes.
    fixture('UPDATE product SET price=19.25,updated_at=updated_at WHERE id='+str(note)+';','current-price-preview')
    before=snapshot();cart(cl,1,'current-price-cart-preview');check('price-preview-get-does-not-write-cart',snapshot()==before)
    restore_products(originals)
    assert_page(cl.get('/__verification/errors/500'),404,'verification-profile-default-inactive')
    # Existing foundation probes are enabled only in a later read-only profile phase.
    before=snapshot();stop(user_process);user_process=launch('csucampuscraft-user',8080,'verification')
    cl=Client();r,_,_=login(cl,8080,name='verification-phase-login');assert_page(r,303,'verification-phase-auth');clbob=Client();r,_,_=login(clbob,8080,username='bob',name='verification-phase-bob');assert_page(r,303,'verification-bob-auth')
    check('verification-restart-keeps-all-data',snapshot()==before)
    for code in [400,403,404,409,500]:
        r=cl.get('/__verification/errors/'+str(code));assert_page(r,code,'foundation-error-'+str(code));badge(r,1,'foundation-error-'+str(code))
    native_probe();cart(cl,1,'native-probe-kept-original-cart')
    browser({'alice':cl.cookie(8080),'bob':clbob.cookie(8080)},[{'name':'u05-valid-85','path':'/cart','kind':'U05','account':'alice','badge':quantity(1),'status':200,'total':'85.00'}])
    # Change current goods without touching cart rows, then show all three invalidity reasons.
    fixture("UPDATE product SET status='DRAFT',updated_at=updated_at WHERE id="+str(note)+';','cart-product-downlisted')
    fixture('UPDATE product SET stock=2,updated_at=updated_at WHERE id='+str(sold)+';','make-sold-product-addable-for-invalidation')
    row_sold=add(cl,sold,1,'prepare-cart-before-sold-out')
    extra=next(int(x) for x in rows("SELECT id FROM product WHERE status='ON_SALE' AND stock>=2 AND id NOT IN ("+','.join(map(str,[note,gift,sold]))+") ORDER BY id LIMIT 1;").splitlines())
    row_extra=add(cl,extra,2,'prepare-cart-before-shortage')
    fixture('UPDATE product SET stock=0,updated_at=updated_at WHERE id='+str(sold)+';','cart-product-sold-out')
    fixture('UPDATE product SET stock=1,updated_at=updated_at WHERE id='+str(extra)+';','cart-product-stock-reduced')
    r=cart(cl,1,'three-invalid-reasons-retained');check('all-invalid-reason-text','下架' in r[3].text() and '售罄' in r[3].text() and ('库存' in r[3].text()))
    before=snapshot();change(cl,item_for(note),item_for(note)['quantity'],'same-quantity-invalid-row-noop');check('invalid-row-noop-no-write',snapshot()==before)
    downlisted=change(cl,item_for(note),1,'downlisted-quantity-change',409)
    check('downlisted-change-removal-recovery','请移除该条目后继续选购' in downlisted[0][3].text())
    change(cl,row_sold,2,'soldout-quantity-change',409)
    change(cl,row_extra,3,'overstock-quantity-change',409)
    clear_cart(clbob,2,'bob-clears-own-cart');cart(clbob,2,'bob-empty-cart')
    cases=[
      {'name':'u05-invalid-live-status','path':'/cart','kind':'U05','account':'alice','badge':quantity(1),'status':200},
      {'name':'u05-empty-bob','path':'/cart','kind':'U05','account':'bob','badge':0,'status':200},
      {'name':'u01-live-badge','path':'/','kind':'U01','account':'alice','badge':quantity(1),'status':200},
      {'name':'u02-live-badge','path':'/products','kind':'U02','account':'alice','badge':quantity(1),'status':200},
      {'name':'u03-real-add-form','path':'/products/'+str(gift),'kind':'U03','account':'alice','badge':quantity(1),'status':200},
      {'name':'u03-guest-zero-badge','path':'/products/'+str(gift),'kind':'U03','account':'guest','badge':0,'status':200},
      *[{'name':'error-'+str(code)+'-badge','path':'/__verification/errors/'+str(code),'kind':'error','account':'alice','badge':quantity(1),'status':code} for code in [400,403,404,409,500]]]
    browser({'alice':cl.cookie(8080),'bob':clbob.cookie(8080)},cases)
    check('exact-28-screenshots',result['screenshots']==28)
    for row in list(cartrows(1)):
        if row['productId']!=gift:remove(cl,row,'remove-invalid-or-extra-'+str(row['id']))
    cart(cl,1,'invalid-removal-recomputes-badge')
    clear_cart(cl,1,'final-empty-cart');cart(cl,1,'final-empty-state-and-badge')
    restore_products(originals)
    final=snapshot();save(EV/'database-final.json',json.dumps(final,indent=2));check('final-other-six-tables-unchanged',unchanged_other(original,final))
    check('static-sources-and-dual-jar-images-unchanged',static_manifest()==statics);save(EV/'static-after.json',json.dumps(static_manifest(),indent=2))
    check('runtime-inputs-stable',all(hashlib.sha256((REPO/line.split('  ',1)[1]).read_bytes()).hexdigest()==line.split('  ',1)[0] for line in manifest.splitlines()))
    result['overall']='PASS'

except Exception as e:
    result['overall']='FAIL';result['error']=scrub(type(e).__name__+': '+str(e));save(EV/'failure.txt',traceback.format_exc());print(result['error'],flush=True)
finally:
    for p in reversed(processes):stop(p)
    if server is not None:
        if server.poll() is None:
            try:command([MYSQL/'mysqladmin.exe','--no-defaults','--no-login-paths','--protocol=TCP','--host=127.0.0.1',f'--port={mysqlport}','--user=root','shutdown'],env=env,timeout=15)
            except Exception:pass
        stop(server)
    for h in handles:h.close()
    for p in private_files:
        if p.exists():p.unlink()
    result['tracked_processes_stopped']=all(p.poll() is not None for p in processes) and (server is None or server.poll() is not None)
    save(EV/'result.json',json.dumps(result,ensure_ascii=False,indent=2))
    for log in BASE.glob('*.log'):save(EV/log.name,log.read_text(encoding='utf-8',errors='replace'))
    print('RESULT '+str(EV/'result.json'),flush=True)
if result['overall']!='PASS':raise SystemExit(1)
