"""STEP08 isolated verification; external tools only, no repository business mutation."""
from pathlib import Path
from html.parser import HTMLParser
import os,sys,re,json,time,socket,secrets,hashlib,subprocess,datetime,traceback,urllib.request,urllib.error,urllib.parse,http.cookiejar,zipfile,struct,gzip
REPO=Path('D:/Github Projects/CSUCampusCraft')
HERE=Path(__file__).resolve().parent
RUNTIME=Path('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies')
GIT=Path('C:/Program Files/Git/cmd/git.exe')
JAVA=Path('C:/Users/Starmetor/.jdks/ms-21.0.12.1/bin/java.exe')
MYSQL=Path('D:/MySQL/bin')
BASELINE='993b2ee184a1a05af40a1943970276ffb14cfac0'
TESTED=os.environ.get('STEP08_TESTED_CODE_SHA','')
if not re.fullmatch(r'[0-9a-f]{40}',TESTED):raise SystemExit('STEP08_TESTED_CODE_SHA must be exact 40-character implementation SHA')
RUN=sys.argv[1] if len(sys.argv)>1 else ''
if not re.fullmatch(r'attempt[1-9][0-9]*',RUN):raise SystemExit('Use a fresh attemptN')
BASE=HERE/'runtime'/RUN;EV=HERE/'evidence'/RUN
BASE.mkdir(parents=True,exist_ok=False);EV.mkdir(parents=True,exist_ok=False)
FLAG=subprocess.CREATE_NO_WINDOW
result={'date':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'baseline_git_sha':BASELINE,'tested_code_sha':TESTED,'requested_evidence_batch':'2026-11-14-step08','timestamp_policy':'actual system clock in Asia/Shanghai','checks':{},'scope':'STEP08 whole-cart confirmation and validation-only POST /orders; no order writes, stock reservation or business row locks'}
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
        audited=method=='POST' or path=='/checkout'
        post_before=snapshot() if audited else None
        post_state=state() if audited else None
        try:r=self.opener.open(req,timeout=12)
        except urllib.error.HTTPError as e:r=e
        body=r.read();h=dict(r.headers.items());text=body.decode('utf-8',errors='replace');dom=Parser(text).root
        for c in self.jar:
            if c.value:secret_values.append(c.value)
        for n in dom.all(lambda x:x.tag=='input' and x.a.get('name') in ('_csrf','confirmationToken')):
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
        if audited:
            after=snapshot();snapshot_pair('http-'+method.lower()+'-'+str(http_no),post_before,post_state,after,state(),http_sequence=http_no,path=path,status=r.code,automatic_audit=True)
            if (method=='POST' and path=='/orders') or path=='/checkout':check('checkout-zero-write-http-'+str(http_no),post_before==after)
        return r.code,h,body,dom
    def get(self,path='/',port=8080,recorded=True):return self.request(path,port,recorded=recorded)
    def post(self,path,form,port=8080):return self.request(path,port,method='POST',form=form)
def token(r):
    n=r[3].find(lambda x:x.tag=='input' and x.a.get('name') in ('_csrf','confirmationToken'))
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
    query="".join("SELECT '__STEP08_"+t+"__';SELECT COUNT(*) FROM "+t+";SELECT * FROM "+t+" ORDER BY id;" for t in TABLES)
    data=sql(query,'csucampuscraft').stdout;out={}
    for i,t in enumerate(TABLES):
        marker=('__STEP08_'+t+'__').encode();start=data.index(marker)+len(marker)
        start+=2 if data[start:start+2]==b'\r\n' else 1
        end=data.index(('__STEP08_'+TABLES[i+1]+'__').encode(),start) if i+1<len(TABLES) else len(data)
        payload=data[start:end];count,raw=payload.split(b'\n',1)
        out[t]={'rows':int(count),'sha256':hashlib.sha256(raw).hexdigest()}
    return out


def start_env():
    e=os.environ.copy()
    for k in ['CSUCAMPUSCRAFT_CHECKOUT_CONFIRMATION_TTL','SPRING_APPLICATION_JSON','SPRING_CONFIG_LOCATION','SPRING_CONFIG_ADDITIONAL_LOCATION','JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVA_OPTIONS']:e.pop(k,None)
    url=f'jdbc:mysql://127.0.0.1:{mysqlport}/csucampuscraft'
    e.update(CSUCAMPUSCRAFT_DB_URL=url,CSUCAMPUSCRAFT_DB_USER='csucampuscraft',CSUCAMPUSCRAFT_DB_PASSWORD=apppass,SPRING_DATASOURCE_URL=url,SPRING_DATASOURCE_USERNAME='csucampuscraft',SPRING_DATASOURCE_PASSWORD=apppass,SPRING_PROFILES_ACTIVE='default',SPRING_SQL_INIT_MODE='never')
    return e
launch_counts={}
def launch(app,port,profile='default',ttl=None):
    launch_counts[app]=launch_counts.get(app,0)+1
    log=BASE/(app+'-'+profile+'-'+str(launch_counts[app])+'.log');h=log.open('wb');handles.append(h)
    argv=[JAVA,'-jar',REPO/app/'target'/f'{app}-0.0.1-SNAPSHOT.jar',f'--server.port={port}','--server.address=127.0.0.1','--spring.profiles.active='+profile]
    launch_env=start_env()
    if ttl:launch_env['CSUCAMPUSCRAFT_CHECKOUT_CONFIRMATION_TTL']=ttl
    p=subprocess.Popen([str(x) for x in argv],env=launch_env,stdout=h,stderr=subprocess.STDOUT,creationflags=FLAG);processes.append(p)
    record('launches.jsonl',{'app':app,'port':port,'database':'csucampuscraft','database_port':mysqlport,'database_user':'csucampuscraft','password_supplied':True,'profile':profile,'confirmation_ttl':ttl or 'PT10M (default)','argv':[str(x) for x in argv]})
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

from decimal import Decimal

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
# Shipping fields exist only in transient client memory and are redacted before evidence.
_basic_scrub=scrub
def scrub(s):
    s=_basic_scrub(s)
    def hide_input(m):
        tag=m.group(0)
        if re.search(r'''\bname=["'](?:receiverName|receiverPhone|receiverAddress|confirmationToken)["']''',tag,re.I):
            tag=re.sub(r'''(\bvalue=["'])[^"']*(["'])''',r'\1[REDACTED]\2',tag,flags=re.I)
        return tag
    s=re.sub(r'<input\b[^>]*>',hide_input,s,flags=re.I)
    s=re.sub(r'''(<textarea\b[^>]*\bname=["'](?:receiverName|receiverPhone|receiverAddress)["'][^>]*>)[\s\S]*?(</textarea>)''',r'\1[REDACTED]\2',s,flags=re.I)
    return s

def confirmation(r):
    n=r[3].find(lambda x:x.tag=='input' and x.a.get('name')=='confirmationToken')
    return n.a.get('value') if n else None

def shipping(**overrides):
    data=dict(receiverName='测试收货人',receiverPhone='1',receiverAddress='仅用于验证的模拟地址')
    data.update(overrides)
    return data

def checkout(cl,name='confirmation',status=200,total=None,uid=1):
    r=cl.get('/checkout');assert_page(r,status,name);badge(r,uid,name)
    if status!=200:
        check(name+'-back-cart',r[3].find(lambda n:n.tag=='a' and n.a.get('href')=='/cart') is not None)
        return r
    root=r[3].find(lambda n:n.a.get('data-page-id')=='U06');check(name+'-U06',root is not None)
    t=confirmation(r);check(name+'-opaque-token',bool(t) and len(t)>=43)
    check(name+'-token-not-in-url',t not in r[1].get('Location','') and not root.find(lambda n:t in n.a.get('href','')))
    own=cartrows(uid)
    expected=sum(Decimal(product(x['productId'])['price'])*x['quantity'] for x in own)
    if total is not None:check(name+'-expected-fixture-total',expected==Decimal(total))
    check(name+'-amount-readable',format(expected,'.2f') in root.text())
    check(name+'-total-marker',root.a.get('data-checkout-total')==format(expected,'.2f'))
    check(name+'-count-marker',root.a.get('data-checkout-item-count')==str(len(own)))
    check(name+'-quantity-marker',root.a.get('data-checkout-quantity')==str(sum(x['quantity'] for x in own)))
    actual=root.all(lambda n:n.tag=='tr' and 'data-checkout-item-id' in n.a)
    check(name+'-complete-own-items',[int(n.a['data-checkout-item-id']) for n in actual]==[x['id'] for x in own])
    for n,x in zip(actual,own):
        price=Decimal(product(x['productId'])['price'])
        check(name+'-item-'+str(x['id']),n.a.get('data-product-id')==str(x['productId']) and n.a.get('data-quantity')==str(x['quantity']) and n.a.get('data-item-version')==str(x['version']) and Decimal(n.a['data-unit-price'])==price and Decimal(n.a['data-line-subtotal'])==price*x['quantity'])
    record('confirmation-observations.jsonl',{'name':name,'http_sequence':http_no,'user_id':uid,'token_redacted_alias':hashlib.sha256(t.encode()).hexdigest()[:12],'ordered_cart':own,'expected_total':format(expected,'.2f'),'shipping_recorded':False})
    return r

def submit(cl,r,name,status,fields=None,submitted_token=None,csrf='valid',code=None,extra=None):
    data=shipping() if fields is None else dict(fields)
    if submitted_token is not False:data['confirmationToken']=confirmation(r) if submitted_token is None else submitted_token
    if csrf=='valid':data['_csrf']=token(r)
    elif csrf=='wrong':data['_csrf']='wrong-token'
    if extra:data.update(extra)
    before=snapshot();out=cl.post('/orders',data);assert_page(out,status,name)
    check(name+'-all-seven-zero-write',snapshot()==before)
    if code:check(name+'-stable-code',code in out[3].text() or out[3].find(lambda n:n.a.get('data-error-code')==code or n.a.get('data-checkout-code')==code) is not None)
    if status not in [302]:badge(out,1,name)
    return out

def native_probe():
    extracted=BASE/'native-probe';classes=extracted/'classes';libs=extracted/'lib';classes.mkdir(parents=True);libs.mkdir()
    with zipfile.ZipFile(REPO/'csucampuscraft-user/target/csucampuscraft-user-0.0.1-SNAPSHOT.jar') as z:
        for n in z.namelist():
            if n.startswith('BOOT-INF/classes/') and not n.endswith('/'):
                p=classes/n[len('BOOT-INF/classes/'):];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
            elif n.startswith('BOOT-INF/lib/') and n.endswith('.jar'):(libs/Path(n).name).write_bytes(z.read(n))
    cp=str(classes)+';'+str(libs/'*')+';'+str(extracted)
    p=command([JAVA.parent/'javac.exe','-cp',cp,'-d',extracted,HERE/'NativeCheckoutProbe.java'],timeout=45)
    save(EV/'native-compile.log',p.stdout.decode('utf-8',errors='replace')+p.stderr.decode('utf-8',errors='replace'));check('native-probe-compile',p.returncode==0)
    before=snapshot();p=command([JAVA,'-cp',cp,'org.csucampuscraft.storefront.checkout.NativeCheckoutProbe','--live'],env=start_env(),timeout=100);after=snapshot()
    save(EV/'native-probe.log',p.stdout.decode('utf-8',errors='replace')+p.stderr.decode('utf-8',errors='replace'))
    check('native-probe',p.returncode==0 and '"overall":"PASS"' in p.stdout.decode('utf-8',errors='replace'))
    check('native-probe-all-seven-zero-write',before==after)

def browser(cookies,cases):
    from http.server import BaseHTTPRequestHandler,HTTPServer
    from threading import Thread
    import base64
    control_token=secrets.token_urlsafe(32);secret_values.append(control_token)
    pending={};completed=[];failures=[]
    class Control(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            global http_no
            try:
                if self.headers.get('Authorization')!='Bearer '+control_token:raise RuntimeError('Unauthorized browser audit')
                obj=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                if self.path=='/before':pending[obj['id']]={'before':snapshot(),'state':state(),**obj}
                elif self.path=='/after':
                    meta=pending.pop(obj['id']);text=base64.b64decode(obj['body_base64']).decode('utf-8',errors='replace');dom=Parser(text).root
                    for n in dom.all(lambda x:x.tag=='input' and x.a.get('name') in ('_csrf','confirmationToken')):
                        if n.a.get('value'):secret_values.append(n.a['value'])
                    http_no+=1;redacted=scrub(text).encode();digest=hashlib.sha256(redacted).hexdigest();filename='bodies/'+digest[:24]+'.body.gz'
                    if not (EV/filename).exists():
                        (EV/filename).parent.mkdir(exist_ok=True);(EV/filename).write_bytes(gzip.compress(redacted,mtime=0))
                    record('http.jsonl',dict(sequence=http_no,method=meta['method'],path=obj.get('response_path',meta['path']),requested_path=meta['path'],redirect_chain=obj.get('redirect_chain',[]),port=8080,status=obj['status'],content_type=obj['content_type'],location=obj.get('location'),cookie_values_recorded=False,form_fields=meta.get('form_fields'),body_file=filename,body_encoding='gzip',redacted_body_sha256=digest,redacted=True,transport='real Playwright navigation'))
                    after=snapshot();snapshot_pair('browser-'+obj['id'],meta['before'],meta['state'],after,state(),http_sequence=http_no,path=meta['path'],status=obj['status'],automatic_audit=True)
                    check('browser-zero-write-'+obj['id'],meta['before']==after);completed.append(obj['id'])
                else:raise RuntimeError('Unknown audit operation')
                self.send_response(200);self.end_headers();self.wfile.write(b'{}')
            except Exception as ex:
                failures.append(scrub(str(ex)));self.send_response(500);self.end_headers();self.wfile.write(b'{"error":"audit failure"}')
    service=HTTPServer(('127.0.0.1',0),Control);thread=Thread(target=service.serve_forever,daemon=True);thread.start()
    e=start_env();e.update(STEP08_BROWSER_OUT=str(EV/'browser'),STEP08_BROWSER_CASES=json.dumps(cases,ensure_ascii=False),STEP08_BROWSER_COOKIES=json.dumps(cookies),STEP08_BROWSER_CONTROL='http://127.0.0.1:'+str(service.server_port),STEP08_BROWSER_CONTROL_TOKEN=control_token)
    try:
        p=command([RUNTIME/'node/bin/node.exe',HERE/'verify_browser.cjs'],env=e,timeout=180)
        save(EV/('browser-'+str(len(cases))+'.log'),p.stdout.decode('utf-8',errors='replace')+p.stderr.decode('utf-8',errors='replace'));check('browser-exit',p.returncode==0)
        check('browser-audit-complete',not pending and not failures and completed)
        br=json.loads((EV/'browser/result.json').read_text(encoding='utf-8'));check('browser-result',br.get('completed') and br['overall']=='PASS')
        result['browser_checks']=len(br['checks']);result['screenshots']=len(br['screenshots']);result['browser_http_audits']=len(completed)+result.get('browser_http_audits',0)
    finally:service.shutdown();thread.join(timeout=5);service.server_close()

def sensitive_scan():
    findings=[];files=0;decompressed=0
    tokens={x for x in secret_values if len(x)>=8}
    for p in EV.rglob('*'):
        if not p.is_file() or p.suffix=='.png':continue
        files+=1;data=p.read_bytes()
        if p.suffix=='.gz':data=gzip.decompress(data);decompressed+=1
        for value in tokens:
            if value.encode('utf-8') in data:findings.append({'file':p.relative_to(EV).as_posix(),'type':'known-private-value'})
    report={'overall':'PASS' if not findings else 'FAIL','files_scanned':files,'gzip_decompressed_files':decompressed,'known_values_checked':len(tokens),'secret_values_recorded':False,'findings':findings,'shipping_redaction':'All receiver input values and receiver textarea contents structurally redacted before writing HTML; screenshot fields masked; HTTP form values never recorded.'}
    save(EV/'sensitive-scan.json',json.dumps(report,ensure_ascii=False,indent=2))
    if findings:result['overall']='FAIL';result['sensitive_scan_failed']=True

try:
    check('tested-code-head',git('rev-parse','HEAD').decode().strip()==TESTED)
    result['branch']=git('branch','--show-current').decode().strip();check('feature-branch',result['branch']=='feat/step08-checkout')
    status=git('status','--short','--untracked-files=all').decode();save(EV/'git-input-status.txt',status);check('tested-worktree-clean',not status.strip())
    save(EV/'implementation-diff.patch',git('diff',BASELINE+'..'+TESTED,'--','csucampuscraft-user').decode('utf-8'))
    inputs=[]
    for app in ['csucampuscraft-user','csucampuscraft-admin']:
        inputs.append(REPO/app/'pom.xml');inputs.extend(p for p in (REPO/app/'src').rglob('*') if p.is_file())
    inputs.extend(p for d in ['database','assets','.mvn'] for p in (REPO/d).rglob('*') if p.is_file());inputs.extend([REPO/'mvnw',REPO/'mvnw.cmd'])
    manifest=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(REPO).as_posix()+'\n' for p in sorted(inputs,key=lambda x:x.relative_to(REPO).as_posix()))
    save(EV/'runtime-inputs.sha256',manifest);result['runtime_manifest_sha256']=hashlib.sha256(manifest.encode()).hexdigest();result['runtime_file_count']=len(inputs)
    for name in ['verify_step08.py','verify_browser.cjs','NativeCheckoutProbe.java']:save(EV/name,(HERE/name).read_text(encoding='utf-8-sig'))
    builddir=Path(os.environ.get('STEP08_BUILD_LOG_DIR',HERE.parent));exits=json.loads((builddir/'build-exits.json').read_text(encoding='utf-8-sig'))
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
    originals=state()['product']
    note=pid_by_sku('CSU-LMK-NOTE-01');gift=pid_by_sku('CSU-GRAD-BOX-01')
    cl=Client();second=Client();bob=Client();admin=Client();guest=Client()
    is_login_redirect(guest.get('/checkout'),'guest-checkout','/checkout')
    is_login_redirect(guest.post('/orders',{}),'guest-post-no-replay')
    for client,user,port in [(cl,'alice',8080),(second,'alice',8080),(bob,'bob',8080),(admin,'admin',8081)]:
        r,_,_=login(client,port,username=user,name='initial-'+user+'-'+str(port));assert_page(r,303,'initial-login-'+user)
    assert_page(admin.get('/products',8081),200,'admin-shared-db-products')
    checkout(cl,'invalid-seed-cart',409)
    clear_cart(cl,1,'clear-alice-seed-through-http');clear_cart(bob,2,'clear-bob-seed-through-http')
    checkout(cl,'empty-cart',409)
    add(cl,note,2,'two-current-18-notebooks');add(cl,gift,1,'one-current-49-gift')
    r=checkout(cl,'valid-eighty-five',total='85.00')
    u05=cl.get('/cart');assert_page(u05,200,'valid-cart-entry')
    check('valid-cart-enables-checkout',u05[3].find(lambda n:n.tag=='a' and n.a.get('href')=='/checkout' and 'data-checkout-link' in n.a) is not None)
    submit(cl,r,'validated-stub-only',409,code='ORDER_SUBMISSION_PENDING')
    submit(cl,r,'stub-is-not-success-keeps-valid-token',409,code='ORDER_SUBMISSION_PENDING')
    submit(cl,r,'missing-csrf-before-token',403,csrf='missing',submitted_token='bad-token')
    submit(cl,r,'wrong-csrf-before-fields',403,csrf='wrong',fields={})
    submit(cl,r,'csrf-rejection-keeps-confirmation',409,code='ORDER_SUBMISSION_PENDING')
    for name,kw in [('missing',{'submitted_token':False}),('unknown',{'submitted_token':'unknown-confirmation'})]:
        r=checkout(cl,'before-'+name+'-token');submit(cl,r,name+'-token-conflict',409,**kw)
        submit(cl,r,name+'-cleared-previous-token',409)
    a=checkout(cl,'token-A');b=checkout(cl,'token-B')
    check('reopening-replaces-token',confirmation(a)!=confirmation(b))
    submit(cl,a,'old-A-replaced',409)
    submit(cl,b,'invalid-token-clears-current-B-policy',409)
    # A token is stored server-side only within one user's one session.
    a=checkout(cl,'session-owner-A');b=checkout(second,'same-account-other-session-B')
    submit(second,b,'same-account-foreign-session-token',409,submitted_token=confirmation(a))
    submit(cl,a,'owner-session-A-not-affected-by-other-session',409,code='ORDER_SUBMISSION_PENDING')
    add(bob,gift,1,'bob-own-cart-one',uid=2)
    b=checkout(bob,'bob-own-confirmation',uid=2)
    foreign=bob.post('/orders',dict(shipping(),confirmationToken=confirmation(a),_csrf=token(b)))
    assert_page(foreign,409,'other-account-token');badge(foreign,2,'bob-token-conflict')
    # Field errors retain exactly the current still-valid token; the shipping data is never session state.
    for field,limit in [('receiverName',50),('receiverPhone',30),('receiverAddress',255)]:
        for label,value in [('missing',None),('empty',''),('blank',' \u3000\t '),('too-long','测'*(limit+1)),('astral-too-long','😀'*(limit+1))]:
            r=checkout(cl,'field-'+field+'-'+label+'-confirm')
            data=shipping();data.pop(field)
            if value is not None:data[field]=value
            out=submit(cl,r,'field-'+field+'-'+label,400,fields=data)
            check(field+'-'+label+'-token-retained',confirmation(out)==confirmation(r))
            n=out[3].find(lambda n:n.a.get('id')==field)
            check(field+'-'+label+'-field-anchor',n is not None)
            submit(cl,out,field+'-'+label+'-can-correct',409,code='ORDER_SUBMISSION_PENDING')
        for label,value in [('minimum','测'),('maximum','测'*limit),('astral-maximum','😀'*limit),('trim-maximum',' \u3000'+'测'*limit+'\u3000 ')]:
            r=checkout(cl,'valid-'+field+'-'+label+'-confirm')
            submit(cl,r,'valid-'+field+'-'+label,409,fields=shipping(**{field:value}),code='ORDER_SUBMISSION_PENDING')
    r=checkout(cl,'all-max-codepoint-boundaries')
    submit(cl,r,'all-max-codepoint-fields-accepted',409,fields=shipping(receiverName='😀'*50,receiverPhone='😀'*30,receiverAddress='😀'*255),code='ORDER_SUBMISSION_PENDING')
    r=checkout(cl,'script-text-confirm');payload='<script>alert(1)</script>'
    out=submit(cl,r,'script-fields-escaped',400,fields=shipping(receiverName=payload,receiverPhone='',receiverAddress=payload))
    name=out[3].find(lambda n:n.a.get('id')=='receiverName');address=out[3].find(lambda n:n.a.get('id')=='receiverAddress')
    check('script-name-is-input-text',name is not None and name.a.get('value')==payload)
    check('script-address-is-textarea-text',address is not None and address.text()==payload)
    check('script-cannot-be-element',not out[3].find(lambda n:n.tag=='script' and not n.a.get('src')))
    record('field-boundaries.jsonl',{'name':'script escaping','status':400,'input_literal_preserved':True,'textarea_literal_preserved':True,'script_element_count':0,'raw_shipping_recorded':False})
    submit(cl,r,'client-total-ignored',409,extra={'total':'0.01','amount':'0.01','unitPrice':'0.01','userId':'2','productId':'999999'},code='ORDER_SUBMISSION_PENDING')
    # The same cart is modified through another authenticated session, never by an untracked helper.
    r=checkout(cl,'before-other-session-quantity');row=item_for(note)
    change(second,row,3,'other-session-quantity-change')
    submit(cl,r,'stale-quantity-conflict',409);check('quantity-conflict-keeps-cart',item_for(note)['quantity']==3)
    change(second,item_for(note),2,'restore-quantity-through-http')
    r=checkout(cl,'before-same-value-quantity');before=snapshot();change(second,item_for(note),2,'same-value-cart-noop')
    check('same-value-change-did-not-write',snapshot()==before)
    submit(cl,r,'same-value-valid-confirmation',409,code='ORDER_SUBMISSION_PENDING')
    # Version changes matter even if quantity returns to its old value.
    r=checkout(cl,'before-quantity-roundtrip');change(second,item_for(note),3,'quantity-roundtrip-up');change(second,item_for(note),2,'quantity-roundtrip-down')
    submit(cl,r,'item-version-roundtrip-stale',409)
    extra=int(rows("SELECT id FROM product WHERE status='ON_SALE' AND stock>1 AND id NOT IN ("+str(note)+','+str(gift)+") ORDER BY id LIMIT 1;"))
    r=checkout(cl,'before-another-session-add');add(second,extra,1,'other-session-add')
    submit(cl,r,'stale-added-line-conflict',409);check('new-line-remains-in-cart',item_for(extra) is not None)
    remove(second,item_for(extra),'remove-added-line-through-http')
    r=checkout(cl,'before-another-session-removal');remove(second,item_for(gift),'other-session-remove')
    submit(cl,r,'stale-removed-line-conflict',409);add(second,gift,1,'restore-removed-gift')
    # Current price/state/stock changes are isolated root fixtures; product version alone is not a snapshot field.
    r=checkout(cl,'before-product-version-only')
    fixture('UPDATE product SET version=version+1,updated_at=updated_at WHERE id='+str(note)+';','product-version-only')
    submit(cl,r,'product-version-only-keeps-confirmation',409,code='ORDER_SUBMISSION_PENDING');restore_products(originals)
    r=checkout(cl,'before-current-price-change')
    fixture('UPDATE product SET price=19.25,version=version+1,updated_at=updated_at WHERE id='+str(note)+';','backend-price-change')
    submit(cl,r,'stale-current-price-conflict',409);check('price-conflict-cart-retained',len(cartrows())==2)
    restore_products(originals)
    for label,update in [('draft',"status='DRAFT'"),('sold-out','stock=0'),('over-stock','stock=1')]:
        r=checkout(cl,'before-'+label)
        fixture('UPDATE product SET '+update+',updated_at=updated_at WHERE id='+str(note)+';','make-'+label)
        submit(cl,r,label+'-after-confirmation',409);checkout(cl,label+'-cannot-open-confirmation',409)
        restore_products(originals)
    r=checkout(cl,'before-stock-change-still-sufficient');fixture('UPDATE product SET stock=stock+1,updated_at=updated_at WHERE id='+str(note)+';','stock-still-sufficient')
    submit(cl,r,'sufficient-stock-change-does-not-reserve-or-conflict',409,code='ORDER_SUBMISSION_PENDING');restore_products(originals)
    # DECIMAL(12,2): line overflow and aggregate-only overflow are both rejected without writes.
    fixture('UPDATE product SET price=9999999999.99,stock=100,updated_at=updated_at WHERE id='+str(note)+';','line-amount-overflow')
    checkout(cl,'line-amount-overflow-refused',409);restore_products(originals)
    change(second,item_for(note),1,'prepare-aggregate-overflow-one-note')
    fixture('UPDATE product SET price=6000000000.00,updated_at=updated_at WHERE id IN ('+str(note)+','+str(gift)+');','aggregate-only-overflow')
    checkout(cl,'aggregate-amount-overflow-refused',409);restore_products(originals)
    change(second,item_for(note),2,'restore-eighty-five-quantities')
    # Logout and reauthentication invalidate the session's old confirmation, with no cart/stock changes.
    r=checkout(cl,'before-logout');before=snapshot();out=cl.post('/logout',{'_csrf':token(r)})
    assert_page(out,303,'logout');check('logout-zero-write',snapshot()==before)
    is_login_redirect(cl.get('/checkout'),'checkout-after-logout','/checkout')
    out,_,_=login(cl,8080,name='relogin-after-logout');assert_page(out,303,'relogin-after-logout')
    submit(cl,cl.get('/cart'),'old-token-not-restored-after-relogin',409,submitted_token=confirmation(r))
    saved_stamp=rows("SELECT CAST(updated_at AS CHAR) FROM store_user WHERE id=1;")
    r=checkout(cl,'before-disable-confirmation')
    fixture("UPDATE store_user SET status='DISABLED',updated_at=GREATEST(CURRENT_TIMESTAMP(6),updated_at+INTERVAL 1 MICROSECOND) WHERE id=1;",'disabled-checkout-owner')
    is_login_redirect(cl.post('/orders',{}),'disabled-identity-before-csrf-token')
    fixture("UPDATE store_user SET status='ENABLED',updated_at=GREATEST(CURRENT_TIMESTAMP(6),updated_at+INTERVAL 1 MICROSECOND) WHERE id=1;",'reenabled-checkout-owner')
    is_login_redirect(cl.get('/checkout'),'reenabled-session-not-revived','/checkout')
    fixture("UPDATE store_user SET updated_at="+literal(saved_stamp)+" WHERE id=1;",'restore-isolated-owner-stamp')
    out,_,_=login(cl,8080,name='fresh-login-after-disable');assert_page(out,303,'fresh-login-after-disable')
    submit(cl,cl.get('/cart'),'disabled-confirmation-not-restored',409,submitted_token=confirmation(r))
    # Real short TTL: restart only our user JAR, same isolated database, then return to default.
    before=snapshot();stop(user_process);user_process=launch('csucampuscraft-user',8080,ttl='PT1S')
    cl=Client();out,_,_=login(cl,8080,name='short-ttl-login');assert_page(out,303,'short-ttl-login')
    r=checkout(cl,'short-ttl-confirmation');time.sleep(1.15)
    submit(cl,r,'expired-confirmation',409);submit(cl,r,'expired-confirmation-stays-invalid',409)
    check('short-ttl-phase-zero-write',snapshot()==before)
    stop(user_process);user_process=launch('csucampuscraft-user',8080)
    cl=Client();bob=Client()
    for client,user in [(cl,'alice'),(bob,'bob')]:
        out,_,_=login(client,8080,username=user,name='browser-'+user);assert_page(out,303,'browser-login-'+user)
    check('default-restored-no-db-write',snapshot()==before)
    r=checkout(cl,'default-ttl-restored',total='85.00')
    native_probe()
    # 24 screenshots: twelve representative real browser states at both requested resolutions.
    browser({'alice':cl.cookie(8080)},[
      {'name':'u06-valid-85','path':'/checkout','account':'alice','kind':'U06','status':200,'badge':3,'total':'85.00'},
      {'name':'u06-fields-400','path':'/checkout','account':'alice','kind':'U06','status':400,'badge':3,'total':'85.00','action':'fields'},
      {'name':'u06-script-literal-400','path':'/checkout','account':'alice','kind':'U06','status':400,'badge':3,'total':'85.00','action':'script'},
      {'name':'u06-validated-pending-409','path':'/checkout','account':'alice','kind':'U06','status':409,'badge':3,'action':'pending','code':'ORDER_SUBMISSION_PENDING'},
      {'name':'u06-replaced-token-409','path':'/checkout','account':'alice','kind':'U06','status':409,'badge':3,'action':'replaced'},
      {'name':'u06-csrf-403','path':'/checkout','account':'alice','kind':'error','status':403,'badge':3,'action':'csrf'},
      {'name':'u05-valid-checkout-entry','path':'/cart','account':'alice','kind':'U05','status':200,'badge':3,'cartLink':True},
      {'name':'u01-live-badge','path':'/','account':'alice','kind':'U01','status':200,'badge':3},
      {'name':'u03-live-badge','path':'/products/'+str(gift),'account':'alice','kind':'U03','status':200,'badge':3},
      {'name':'u06-guest-login','path':'/checkout','account':'guest','kind':'U04','status':200,'badge':0}])
    fixture("UPDATE product SET status='DRAFT',updated_at=updated_at WHERE id="+str(note)+';','browser-invalid-cart')
    browser({'alice':cl.cookie(8080)},[{'name':'u06-invalid-cart-409','path':'/checkout','account':'alice','kind':'U06','status':409,'badge':3}])
    restore_products(originals);clear_cart(bob,2,'empty-bob-for-browser')
    browser({'bob':bob.cookie(8080)},[{'name':'u06-empty-cart-409','path':'/checkout','account':'bob','kind':'U06','status':409,'badge':0}])
    check('exact-24-screenshots',result['screenshots']==24)
    final=snapshot();save(EV/'database-final.json',json.dumps(final,indent=2))
    check('final-other-six-tables-unchanged',unchanged_other(original,final))
    check('runtime-inputs-stable',all(hashlib.sha256((REPO/line.split('  ',1)[1]).read_bytes()).hexdigest()==line.split('  ',1)[0] for line in manifest.splitlines()))
    check('static-sources-and-jar-images-unchanged',static_manifest()==statics)
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
    for log in BASE.glob('*.log'):save(EV/log.name,log.read_text(encoding='utf-8',errors='replace'))
    sensitive_scan()
    save(EV/'result.json',json.dumps(result,ensure_ascii=False,indent=2))
    print('RESULT '+str(EV/'result.json'),flush=True)
if result['overall']!='PASS':raise SystemExit(1)
