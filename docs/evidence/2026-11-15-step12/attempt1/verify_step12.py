"""STEP12 isolated verification; external tools only, no repository business mutation."""
from pathlib import Path
from privacy_checks import contains_bcrypt,run_regression
from html.parser import HTMLParser
import os,sys,re,json,time,socket,secrets,hashlib,subprocess,datetime,traceback,urllib.request,urllib.error,urllib.parse,http.cookiejar,zipfile,struct,gzip
REPO=Path('D:/Github Projects/CSUCampusCraft')
HERE=Path(__file__).resolve().parent
RUNTIME=Path('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies')
GIT=Path('C:/Program Files/Git/cmd/git.exe')
JAVA=Path('C:/Users/Starmetor/.jdks/ms-21.0.12.1/bin/java.exe')
MYSQL=Path('D:/MySQL/bin')
BASELINE='a899cce263526926292afec8ed55d6757aed0597'
TESTED=os.environ.get('STEP12_TESTED_CODE_SHA','')
if not re.fullmatch(r'[0-9a-f]{40}',TESTED):raise SystemExit('STEP12_TESTED_CODE_SHA must be exact 40-character implementation SHA')
BATCH=os.environ.get('STEP12_EVIDENCE_BATCH','')
if not re.fullmatch(r'2026-11-\d{2}-step12',BATCH):raise SystemExit('Set STEP12_EVIDENCE_BATCH to the authorized actual local date batch')
DATABASE='csucampuscraft';APP_USERNAME='csucampuscraft'
RUN=sys.argv[1] if len(sys.argv)>1 else ''
if not re.fullmatch(r'attempt[1-9][0-9]*',RUN):raise SystemExit('Use a fresh attemptN')
BASE=HERE/'runtime'/RUN;EV=HERE/'evidence'/RUN
BASE.mkdir(parents=True,exist_ok=False);EV.mkdir(parents=True,exist_ok=False)
FLAG=subprocess.CREATE_NO_WINDOW
result={'date':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'baseline_git_sha':BASELINE,'tested_code_sha':TESTED,'requested_evidence_batch':BATCH,'timestamp_policy':'actual system clock in Asia/Shanghai','checks':{},'scope':'STEP12 customer status and real dashboard; sequential checks only; no concurrency, injected failure, account creation route or user-source changes'}
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
        audited=recorded
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
            check('raw-response-no-bcrypt-'+str(http_no+1),not contains_bcrypt(text))
            check('raw-response-no-password-'+str(http_no+1),PASSWORD not in text)
            http_no+=1
            redacted=scrub(text).encode('utf-8');digest=hashlib.sha256(redacted).hexdigest()
            filename='bodies/'+digest[:24]+'.body.gz'
            if not (EV/filename).exists():
                (EV/filename).parent.mkdir(exist_ok=True)
                (EV/filename).write_bytes(gzip.compress(redacted,mtime=0))
            record('http.jsonl',{'sequence':http_no,'method':method,'path':path,'port':port,'status':r.code,'content_type':h.get('Content-Type'),'location':h.get('Location'),'cookie_names':[c.name for c in self.jar],'cookie_values_recorded':False,'set_cookie_present':bool(r.headers.get_all('Set-Cookie',[])),'database':DATABASE,'application_db_user':APP_USERNAME,'form_fields':sorted(form.keys()) if isinstance(form,dict) else None,'body_file':filename,'body_encoding':'gzip','redacted_body_sha256':digest,'redacted':True,'raw_bcrypt_scan_passed':not contains_bcrypt(text),'raw_response_scan_before_redaction':True})
        check('no-session-url-rewriting-'+str(http_no),';CSUCAMPUSCRAFT_USER_SESSION=' not in text and ';CSUCAMPUSCRAFT_ADMIN_SESSION=' not in text and ';CSUCAMPUSCRAFT_' not in h.get('Location',''))
        if audited:
            after=snapshot();snapshot_pair('http-'+method.lower()+'-'+str(http_no),post_before,post_state,after,state(),http_sequence=http_no,path=path,status=r.code,database=DATABASE,application_db_user=APP_USERNAME,automatic_audit=True)
            if method=='GET' or (method=='POST' and path=='/orders' and r.code!=303):check('read-or-rejected-order-zero-write-http-'+str(http_no),post_before==after)
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
    check(name+'-no-secrets',PASSWORD not in text and not contains_bcrypt(text))
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
def rows(q,db=None):return sql(q,db or DATABASE).stdout.decode('utf-8').strip()
def literal(text):return "(CONVERT(0x"+text.encode('utf-8').hex()+" USING utf8mb4) COLLATE utf8mb4_0900_as_ci)"
def snapshot():
    query="".join("SELECT '__STEP12_"+t+"__';SELECT COUNT(*) FROM "+t+";SELECT * FROM "+t+" ORDER BY id;" for t in TABLES)
    data=sql(query,DATABASE).stdout;out={}
    for i,t in enumerate(TABLES):
        marker=('__STEP12_'+t+'__').encode();start=data.index(marker)+len(marker)
        start+=2 if data[start:start+2]==b'\r\n' else 1
        end=data.index(('__STEP12_'+TABLES[i+1]+'__').encode(),start) if i+1<len(TABLES) else len(data)
        payload=data[start:end];count,raw=payload.split(b'\n',1)
        out[t]={'rows':int(count),'sha256':hashlib.sha256(raw).hexdigest()}
    return out


def start_env():
    e=os.environ.copy()
    for k in ['CSUCAMPUSCRAFT_CHECKOUT_CONFIRMATION_TTL','SPRING_APPLICATION_JSON','SPRING_CONFIG_LOCATION','SPRING_CONFIG_ADDITIONAL_LOCATION','JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVA_OPTIONS']:e.pop(k,None)
    url=f'jdbc:mysql://127.0.0.1:{mysqlport}/{DATABASE}'
    e.update(CSUCAMPUSCRAFT_DB_URL=url,CSUCAMPUSCRAFT_DB_USER=APP_USERNAME,CSUCAMPUSCRAFT_DB_PASSWORD=apppass,SPRING_DATASOURCE_URL=url,SPRING_DATASOURCE_USERNAME=APP_USERNAME,SPRING_DATASOURCE_PASSWORD=apppass,SPRING_PROFILES_ACTIVE='default',SPRING_SQL_INIT_MODE='never')
    return e
launch_counts={}
def launch(app,port,profile='default',ttl=None):
    launch_counts[app]=launch_counts.get(app,0)+1
    log=BASE/(app+'-'+profile+'-'+str(launch_counts[app])+'.log');h=log.open('wb');handles.append(h)
    argv=[JAVA,'-jar',REPO/app/'target'/f'{app}-0.0.1-SNAPSHOT.jar',f'--server.port={port}','--server.address=127.0.0.1','--spring.profiles.active='+profile]
    launch_env=start_env()
    if ttl:launch_env['CSUCAMPUSCRAFT_CHECKOUT_CONFIRMATION_TTL']=ttl
    p=subprocess.Popen([str(x) for x in argv],env=launch_env,stdout=h,stderr=subprocess.STDOUT,creationflags=FLAG);processes.append(p)
    record('launches.jsonl',{'app':app,'port':port,'database':DATABASE,'database_port':mysqlport,'database_user':APP_USERNAME,'password_supplied':True,'profile':profile,'confirmation_ttl':ttl or 'PT10M (default)','argv':[str(x) for x in argv]})
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
    before=snapshot();a=state();sql(q,DATABASE);after=snapshot();b=state()
    record('fixtures.jsonl',{'name':name,'database':DATABASE,'controlled_root_fixture':True,'query':q,'before':before,'after':after,'deltas':deltas(a,b)})
def static_manifest():
    out={}
    for p in sorted((REPO/'assets').rglob('*')):
        if p.is_file():out['assets/'+p.relative_to(REPO/'assets').as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    for app in ['csucampuscraft-user','csucampuscraft-admin']:
        with zipfile.ZipFile(REPO/app/'target'/f'{app}-0.0.1-SNAPSHOT.jar') as z:
            for n in z.namelist():
                if n.startswith('BOOT-INF/classes/static/images/') and not n.endswith('/'):out[app+'/'+n]=hashlib.sha256(z.read(n)).hexdigest()
    return out


def state():
    queries={
      'cart_item':"SELECT JSON_OBJECT('id',id,'userId',user_id,'productId',product_id,'quantity',quantity,'version',version,'createdAt',created_at,'updatedAt',updated_at) FROM cart_item ORDER BY id;",
      'product':"SELECT JSON_OBJECT('id',id,'categoryId',category_id,'sku',sku,'name',name,'coverImage',cover_image,'summary',summary,'description',description,'price',CAST(price AS CHAR),'stock',stock,'status',status,'sortOrder',sort_order,'version',version,'createdAt',created_at,'updatedAt',updated_at) FROM product ORDER BY id;",
      'sales_order':"SELECT JSON_OBJECT('id',id,'orderNo',order_no,'userId',user_id,'status',status,'totalAmount',CAST(total_amount AS CHAR),'receiverNameSha256',SHA2(receiver_name,256),'receiverPhoneSha256',SHA2(receiver_phone,256),'receiverAddressSha256',SHA2(receiver_address,256),'createdAt',created_at,'updatedAt',updated_at,'paymentMethod',payment_method,'paymentNo',payment_no,'paidAt',paid_at,'cancelledAt',cancelled_at,'shippedAt',shipped_at,'completedAt',completed_at) FROM sales_order ORDER BY id;",
      'sales_order_item':"SELECT JSON_OBJECT('id',id,'orderId',order_id,'productId',product_id,'skuSnapshot',sku_snapshot,'productNameSnapshot',product_name_snapshot,'coverImageSnapshot',cover_image_snapshot,'unitPrice',CAST(unit_price AS CHAR),'quantity',quantity,'lineAmount',CAST(line_amount AS CHAR)) FROM sales_order_item ORDER BY id;"}
    return {t:{str(x['id']):x for x in map(json.loads,rows(q).splitlines())} for t,q in queries.items()}


# Override the common delta recorder with full, privacy-safe order/line state.
def snapshot_pair(name,before,a,after,b,**extra):
    record('database-writes.jsonl',dict(name=name,before=before,after=after,
        **{t+'_before':a[t] for t in a},**{t+'_after':b[t] for t in b},deltas=deltas(a,b),**extra))

def restore_products(original):
    fields={'name':'name','coverImage':'cover_image','price':'price','stock':'stock','status':'status','version':'version','updatedAt':'updated_at'}
    for x in original.values():
        if product(x['id'])!=x:
            values=[]
            for key,column in fields.items():
                value=x[key]
                values.append(column+'='+ (str(value) if key in ['price','stock','version'] else literal(value)))
            fixture('UPDATE product SET '+','.join(values)+' WHERE id='+str(x['id'])+';','restore-product-'+str(x['id']))
    check('root-product-fixtures-fully-restored',state()['product']==original)

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
    s=re.sub(r'''(<([a-z][a-z0-9]*)\b[^>]*\bdata-shipping-value(?:=["'][^"']*["'])?[^>]*>)[\s\S]*?(</\2>)''',r'\1[REDACTED]\3',s,flags=re.I)
    return s

def confirmation(r):
    n=r[3].find(lambda x:x.tag=='input' and x.a.get('name')=='confirmationToken')
    return n.a.get('value') if n else None

def shipping(**overrides):
    data=dict(receiverName='验证收货人'+secrets.token_hex(4),receiverPhone='1',receiverAddress='仅用于验证 '+secrets.token_hex(8))
    data.update(overrides)
    # Dynamic personal fixtures are checked in process; constants in tool source remain public test definitions.
    for value in data.values():
        if len(value)>=8 and ('仅用于验证 ' in value or value.startswith('验证收货人')):secret_values.append(value)
    return data

def shipping_hashes(data):
    return {key+'Sha256':hashlib.sha256(value.strip().encode('utf-8')).hexdigest() for key,value in data.items() if key in ['receiverName','receiverPhone','receiverAddress']}

def checkout(cl,name='confirmation',status=200,total=None,uid=1):
    r=cl.get('/checkout');assert_page(r,status,name);badge(r,uid,name)
    if status!=200:
        check(name+'-back-cart',r[3].find(lambda n:n.tag=='a' and n.a.get('href')=='/cart') is not None)
        return r
    root=r[3].find(lambda n:n.a.get('data-page-id')=='U06');check(name+'-U06',root is not None)
    t=confirmation(r);check(name+'-opaque-token',bool(t) and len(t)==43)
    own=cartrows(uid);products=state()['product']
    expected=sum(Decimal(products[str(x['productId'])]['price'])*x['quantity'] for x in own)
    if total is not None:check(name+'-fixture-total',expected==Decimal(total))
    check(name+'-amount-marker',root.a.get('data-checkout-total')==format(expected,'.2f'))
    check(name+'-complete-own-cart',root.a.get('data-checkout-item-count')==str(len(own)) and root.a.get('data-checkout-quantity')==str(sum(x['quantity'] for x in own)))
    record('confirmation-observations.jsonl',dict(name=name,http_sequence=http_no,user_id=uid,token_redacted_alias=hashlib.sha256(t.encode()).hexdigest()[:12],ordered_cart=own,expected_total=format(expected,'.2f')))
    return r

def verify_order_write(name,before,a,after,b,uid,fields=None,order_no=None,http_sequence=None):
    check(name+'-nonorder-business-tables-unchanged',all(before[t]==after[t] for t in ['store_user','category','product_image']))
    changes=deltas(a,b)
    neworders=[x['after'] for x in changes['sales_order'] if x['before'] is None]
    check(name+'-exactly-one-new-order',len(changes['sales_order'])==1 and len(neworders)==1)
    order=neworders[0]
    if order_no is not None:check(name+'-correct-order-number',order['orderNo']==order_no)
    check(name+'-order-number-safe',bool(re.fullmatch(r'[A-Za-z0-9_-]{1,40}',order['orderNo'])))
    check(name+'-number-unique-CI',sum(x['orderNo'].lower()==order['orderNo'].lower() for x in b['sales_order'].values())==1)
    check(name+'-owner-pending-null-payment',order['userId']==uid and order['status']=='PENDING_PAYMENT' and all(order[k] is None for k in ['paymentMethod','paymentNo','paidAt','cancelledAt','shippedAt','completedAt']))
    own=sorted((x for x in a['cart_item'].values() if x['userId']==uid),key=lambda x:x['id'])
    removed=changes['cart_item']
    check(name+'-only-confirmed-own-cart-deleted',len(removed)==len(own) and all(x['after'] is None and x['before'] in own for x in removed))
    check(name+'-no-own-cart-left',not any(x['userId']==uid for x in b['cart_item'].values()))
    newlines=[x['after'] for x in changes['sales_order_item'] if x['before'] is None]
    check(name+'-one-line-per-confirmed-sku',len(changes['sales_order_item'])==len(newlines)==len(own) and all(x['orderId']==order['id'] for x in newlines))
    expected=Decimal('0.00')
    for cart in own:
        p=a['product'][str(cart['productId'])];now=b['product'][str(cart['productId'])]
        line=next((x for x in newlines if x['productId']==cart['productId']),None)
        line_total=Decimal(p['price'])*cart['quantity'];expected+=line_total
        check(name+'-stock-version-'+str(p['id']),now['stock']==p['stock']-cart['quantity'] and now['version']==p['version']+1)
        check(name+'-locked-product-snapshot-'+str(p['id']),line is not None and line['skuSnapshot']==p['sku'] and line['productNameSnapshot']==p['name'] and line['coverImageSnapshot']==p['coverImage'] and Decimal(line['unitPrice'])==Decimal(p['price']) and line['quantity']==cart['quantity'] and Decimal(line['lineAmount'])==line_total)
        check(name+'-product-only-stock-version-time-'+str(p['id']),all(now[k]==p[k] for k in p if k not in ['stock','version','updatedAt']))
    check(name+'-only-confirmed-products-changed',{int(x['id']) for x in changes['product']}=={x['productId'] for x in own})
    check(name+'-server-total',Decimal(order['totalAmount'])==expected)
    if fields is not None:check(name+'-shipping-hashes-server-trim',all(order[k]==v for k,v in shipping_hashes(fields).items()))
    record('order-observations.jsonl',dict(name=name,http_sequence=http_sequence,order_no=order['orderNo'],order=order,items=newlines,confirmed_cart=own,expected_total=format(expected,'.2f'),raw_shipping_recorded=False))
    return order

def submit(cl,r,name,status,fields=None,submitted_token=None,csrf='valid',uid=1,extra=None):
    fields=shipping() if fields is None else dict(fields)
    data=dict(fields)
    if submitted_token is not False:data['confirmationToken']=confirmation(r) if submitted_token is None else submitted_token
    if csrf=='valid':data['_csrf']=token(r)
    elif csrf=='wrong':data['_csrf']='wrong-token'
    if extra:data.update(extra)
    before=snapshot();a=state();out=cl.post('/orders',data);seq=http_no;after=snapshot();b=state()
    assert_page(out,status,name)
    snapshot_pair(name,before,a,after,b,http_sequence=seq,path='/orders',status=status,expected_status=status,actor_user_id=uid,form_fields=sorted(data),semantic_order_check=True)
    if status==303:
        location=urllib.parse.urlsplit(out[1].get('Location',''))
        check(name+'-safe-detail-303',not location.netloc and not location.query and re.fullmatch(r'/orders/[A-Za-z0-9_-]{1,40}',location.path) is not None)
        order=verify_order_write(name,before,a,after,b,uid,fields,location.path.rsplit('/',1)[1],seq)
        return out,order
    check(name+'-all-seven-zero-write',before==after)
    if status!=302:badge(out,uid,name)
    return out,None

def detail(cl,order_no,name,status=200,uid=1):
    r=cl.get('/orders/'+order_no);assert_page(r,status,name)
    if status!=200:
        check(name+'-no-order-data-leak',order_no not in r[3].text() and not r[3].find(lambda n:'data-shipping-value' in n.a))
        return r
    badge(r,uid,name)
    data=state();order=next(x for x in data['sales_order'].values() if x['orderNo'].lower()==order_no.lower() and x['userId']==uid)
    root=r[3].find(lambda n:n.a.get('data-page-id')=='U08');check(name+'-U08',root is not None)
    check(name+'-order-data',root.a.get('data-order-no')==order['orderNo'] and root.a.get('data-order-status')==order['status'] and Decimal(root.a.get('data-order-total'))==Decimal(order['totalAmount']))
    lines=sorted((x for x in data['sales_order_item'].values() if x['orderId']==order['id']),key=lambda x:x['id'])
    dom=root.all(lambda n:n.tag=='tr' and 'data-order-item-id' in n.a)
    check(name+'-all-snapshot-lines',[int(n.a['data-order-item-id']) for n in dom]==[x['id'] for x in lines])
    for n,x in zip(dom,lines):
        check(name+'-snapshot-'+str(x['id']),n.a.get('data-snapshot-sku')==x['skuSnapshot'] and n.a.get('data-snapshot-name')==x['productNameSnapshot'] and n.a.get('data-snapshot-cover')==x['coverImageSnapshot'] and Decimal(n.a['data-unit-price'])==Decimal(x['unitPrice']) and int(n.a['data-quantity'])==x['quantity'] and Decimal(n.a['data-line-amount'])==Decimal(x['lineAmount']))
    for key in ['receiverName','receiverPhone','receiverAddress']:
        n=root.find(lambda n:n.a.get('data-shipping-value')==key)
        check(name+'-shipping-snapshot-'+key,n is not None and hashlib.sha256(n.text().encode('utf-8')).hexdigest()==order[key+'Sha256'])

    record('detail-observations.jsonl',dict(name=name,http_sequence=http_no,order_no=order['orderNo'],owner=uid,snapshot_lines=lines,shipping_values_recorded=False))
    return r

def order_list(cl,name,params=None,uid=1,status=200):
    params=dict(params or {});path='/orders'+('?' + urllib.parse.urlencode(params,doseq=True) if params else '')
    r=cl.get(path);assert_page(r,status,name)
    if status!=200:return r
    badge(r,uid,name);root=r[3].find(lambda n:n.a.get('data-page-id')=='U07');check(name+'-U07',root is not None)
    no=params.get('orderNo','').strip();wanted=params.get('status','ALL') or 'ALL';page=max(1,int(params.get('page',1)));size=int(params.get('size',10))
    matches=sorted((x for x in state()['sales_order'].values() if x['userId']==uid and (not no or x['orderNo'].lower()==no.lower()) and (wanted=='ALL' or x['status']==wanted)),key=lambda x:(x['createdAt'],x['id']),reverse=True)
    shown=matches[(page-1)*size:page*size]
    actual=root.all(lambda n:n.tag=='tr' and 'data-order-id' in n.a)
    check(name+'-same-where-count',int(root.a['data-order-count'])==len(matches))
    check(name+'-page-size',int(root.a['data-page'])==page and int(root.a['data-size'])==size)
    check(name+'-own-filter-and-stable-order',[int(n.a['data-order-id']) for n in actual]==[x['id'] for x in shown])
    for n,x in zip(actual,shown):check(name+'-row-'+str(x['id']),n.a.get('data-order-no')==x['orderNo'] and n.a.get('data-order-status')==x['status'] and Decimal(n.a['data-order-total'])==Decimal(x['totalAmount']))
    if page>1 and not shown:check(name+'-outofrange-recovery-link',root.find(lambda n:n.tag=='a' and '/orders?' in n.a.get('href','') and 'page=' in n.a['href']) is not None)
    for n in root.all(lambda n:n.tag=='a' and 'data-page-link' in n.a and n.a.get('href','').startswith('/orders?') and 'page=' in n.a['href']):
        query=urllib.parse.parse_qs(urllib.parse.urlsplit(n.a['href']).query,keep_blank_values=True)
        check(name+'-pagination-retains-size',query.get('size')==[str(size)])
        if no:check(name+'-pagination-retains-number',query.get('orderNo')==[no])
        if wanted!='ALL':check(name+'-pagination-retains-status',query.get('status')==[wanted])
    record('list-observations.jsonl',dict(name=name,http_sequence=http_no,user_id=uid,parameters=params,total=len(matches),ordered_ids=[x['id'] for x in shown],page=page,size=size))
    return r

def prepare_eighty_five(cl,name='prepare-85'):
    clear_cart(cl,1,name+'-empty');add(cl,note,2,name+'-two-note');add(cl,gift,1,name+'-one-gift')

def own_order(order_no,db=None):
    db=db or state()
    return next((x for x in db['sales_order'].values() if x['orderNo'].lower()==order_no.lower()),None)

def new_order(cl,name,uid=1,lines=None):
    clear_cart(cl,uid,name+'-clear')
    for pid,qty in (lines or [(note,2),(gift,1)]):add(cl,pid,qty,name+'-add-'+str(pid),uid=uid)
    r=checkout(cl,name+'-confirm',uid=uid)
    response,order=submit(cl,r,name+'-create',303,uid=uid)
    detail(cl,order['orderNo'],name+'-created-detail',uid=uid)
    return order

def verify_action(name,before,a,after,b,order_no,expected,transport='HTTP',http_sequence=None):
    old=own_order(order_no,a);current=own_order(order_no,b)
    check(name+'-order-present',old is not None and current is not None)
    check(name+'-unchanged-users-categories-images-cart-lines',all(before[t]==after[t] for t in ['store_user','category','product_image','cart_item','sales_order_item']))
    delta=deltas(a,b)
    if expected=='NOOP':
        check(name+'-all-seven-noop',before==after)
    elif expected=='PAID':
        check(name+'-only-own-order-row',len(delta['sales_order'])==1 and delta['sales_order'][0]['id']==str(old['id']))
        check(name+'-pending-to-paid',old['status']=='PENDING_PAYMENT' and current['status']=='PAID')
        check(name+'-method-first-voucher-time',current['paymentMethod']=='MOCK' and bool(re.fullmatch('[A-Za-z0-9_-]{1,40}',current['paymentNo'] or '')) and current['paidAt'] is not None and current['paidAt']>=current['createdAt'])
        check(name+'-voucher-case-insensitive-unique',sum(bool(x['paymentNo']) and x['paymentNo'].lower()==current['paymentNo'].lower() for x in b['sales_order'].values())==1)
        permitted={'status','paymentMethod','paymentNo','paidAt','updatedAt'}
        check(name+'-all-snapshots-and-other-order-fields-unchanged',all(old[k]==current[k] for k in old if k not in permitted))
        check(name+'-all-product-fields-unchanged',before['product']==after['product'] and a['product']==b['product'])
    elif expected=='CANCELLED':
        check(name+'-only-own-order-row',len(delta['sales_order'])==1 and delta['sales_order'][0]['id']==str(old['id']))
        check(name+'-pending-to-cancelled',old['status']=='PENDING_PAYMENT' and current['status']=='CANCELLED')
        check(name+'-first-cancel-time-valid',current['cancelledAt'] is not None and current['cancelledAt']>=current['createdAt'])
        check(name+'-payment-fields-null',all(current[k] is None for k in ['paymentMethod','paymentNo','paidAt']))
        check(name+'-snapshots-and-other-order-fields-unchanged',all(old[k]==current[k] for k in old if k not in {'status','cancelledAt','updatedAt'}))
        lines=[x for x in a['sales_order_item'].values() if x['orderId']==old['id']]
        quantities={x['productId']:x['quantity'] for x in lines}
        check(name+'-only-order-products-refunded',{int(x['id']) for x in delta['product']}==set(quantities))
        for pid,qty in quantities.items():
            previous=a['product'][str(pid)];now=b['product'][str(pid)]
            check(name+'-exact-stock-version-'+str(pid),now['stock']==previous['stock']+qty and now['version']==previous['version']+1)
            check(name+'-all-other-product-fields-including-status-preserved-'+str(pid),all(now[k]==previous[k] for k in previous if k not in {'stock','version','updatedAt'}))
    else:raise RuntimeError('Unknown action assertion scope')
    record('action-observations.jsonl',dict(name=name,http_sequence=http_sequence,transport=transport,order_no=current['orderNo'],expected_transition=expected,before_order=old,after_order=current,payment_fields_recorded=True,shipping_raw_recorded=False))
    return current

def user_action(cl,order_no,kind,name,status=303,result_value='SUCCESS',expected='NOOP',uid=1,csrf='valid',extra=None):
    form=dict(extra or {})
    if kind=='payment' and result_value is not False:form['result']=result_value
    if csrf=='valid':
        page=cl.get('/orders');assert_page(page,200,name+'-form');form['_csrf']=token(page)
    elif csrf=='wrong':form['_csrf']='wrong-csrf'
    before=snapshot();a=state();out=cl.post('/orders/'+order_no+'/'+kind,form);seq=http_no;after=snapshot();b=state()
    assert_page(out,status,name)
    snapshot_pair(name,before,a,after,b,http_sequence=seq,path='/orders/'+order_no+'/'+kind,status=status,expected_status=status,actor_user_id=uid,action_kind=kind,expected_transition=expected,semantic_action_check=True)
    if status==303:
        u=urllib.parse.urlsplit(out[1].get('Location',''))
        check(name+'-safe-detail-303',not u.netloc and not u.query and u.path.lower()=='/orders/'+order_no.lower())
        current=verify_action(name,before,a,after,b,order_no,expected,http_sequence=seq)
        page=detail(cl,current['orderNo'],name+'-303-detail',uid=uid)
        if kind=='payment' and result_value=='FAILURE':
            check(name+'-failed-flash-retry-cancel',('失败' in page[3].text() or '未完成' in page[3].text()) and '待支付' in page[3].text() and '取消' in page[3].text())
        elif kind=='payment':
            check(name+'-first-receipt-visible',current['paymentNo'] in page[3].text())
        else:check(name+'-cancelled-flash-visible','已取消' in page[3].text())
        return current,page
    check(name+'-all-seven-rejected-zero-write',before==after)
    if status not in [302]:badge(out,uid,name)
    return None,out

def payment_page(cl,no,name,status=200,uid=1):
    before=snapshot();r=cl.get('/orders/'+no+'/payment');assert_page(r,status,name);check(name+'-GET-zero-write',snapshot()==before)
    if status==200:
        badge(r,uid,name);order=own_order(no)
        root=r[3].find(lambda n:n.a.get('data-page-id')=='U09')
        check(name+'-U09-original-amount',root is not None and root.a.get('data-order-no')==order['orderNo'] and Decimal(root.a.get('data-order-total'))==Decimal(order['totalAmount']))
        check(name+'-teaching-simulation','模拟' in r[3].text() and ('教学' in r[3].text() or '真实支付' in r[3].text()))
        buttons=root.all(lambda n:n.tag=='button' and n.a.get('name')=='result')
        check(name+'-two-results',sorted(n.a.get('value') for n in buttons)==['FAILURE','SUCCESS'])
        check(name+'-no-card-or-bank-fields',not root.find(lambda n:n.tag=='input' and n.a.get('name') not in ['_csrf']))
    elif status==404:
        check(name+'-no-order-or-shipping-leak',no not in r[3].text() and not r[3].find(lambda n:'data-shipping-value' in n.a))
    return r

def admin_list(cl,name,params=None,status=200):
    params=dict(params or {});path='/orders'+('?' + urllib.parse.urlencode(params,doseq=True) if params else '')
    r=cl.get(path,8081);assert_page(r,status,name)
    if status!=200:return r
    root=r[3].find(lambda n:n.a.get('data-page-id')=='A06');check(name+'-A06',root is not None)
    no=params.get('orderNo','').strip();wanted=params.get('status','ALL') or 'ALL';uid=str(params.get('userId','')).strip();page=max(1,int(params.get('page',1)));size=int(params.get('size',10))
    matches=sorted((x for x in state()['sales_order'].values() if (not uid or x['userId']==int(uid)) and (not no or x['orderNo'].lower()==no.lower()) and (wanted=='ALL' or x['status']==wanted)),key=lambda x:(x['createdAt'],x['id']),reverse=True)
    shown=matches[(page-1)*size:page*size];actual=root.all(lambda n:n.tag=='tr' and 'data-order-id' in n.a)
    check(name+'-same-where-count',int(root.a['data-order-count'])==len(matches))
    check(name+'-page-size',int(root.a['data-page'])==page and int(root.a['data-size'])==size)
    check(name+'-allsite-AND-stable-order',[int(n.a['data-order-id']) for n in actual]==[x['id'] for x in shown])
    for n,x in zip(actual,shown):
        check(name+'-row-'+str(x['id']),n.a.get('data-order-no')==x['orderNo'] and n.a.get('data-order-status')==x['status'] and Decimal(n.a['data-order-total'])==Decimal(x['totalAmount']) and int(n.a['data-user-id'])==x['userId'])
    if page>1 and not shown:check(name+'-outofrange-recovery',root.find(lambda n:n.tag=='a' and 'data-page-link' in n.a and 'page=' in n.a.get('href','')) is not None)
    for n in root.all(lambda n:n.tag=='a' and 'data-page-link' in n.a):
        query=urllib.parse.parse_qs(urllib.parse.urlsplit(n.a['href']).query,keep_blank_values=True)
        check(name+'-page-retains-size',query.get('size')==[str(size)])
        if no:check(name+'-page-retains-number',query.get('orderNo')==[no])
        if wanted!='ALL':check(name+'-page-retains-status',query.get('status')==[wanted])
        if uid:check(name+'-page-retains-customer',query.get('userId')==[uid])
    record('admin-list-observations.jsonl',dict(name=name,http_sequence=http_no,parameters=params,total=len(matches),ordered_ids=[x['id'] for x in shown],page=page,size=size))
    return r

def admin_detail(cl,no,name,status=200):
    r=cl.get('/orders/'+no,8081);assert_page(r,status,name)
    if status!=200:
        check(name+'-no-private-detail',not r[3].find(lambda n:'data-shipping-value' in n.a))
        return r
    data=state();order=own_order(no,data);root=r[3].find(lambda n:n.a.get('data-page-id')=='A07');check(name+'-A07',root is not None)
    check(name+'-current-order',root.a.get('data-order-no')==order['orderNo'] and root.a.get('data-order-status')==order['status'] and Decimal(root.a['data-order-total'])==Decimal(order['totalAmount']))
    lines=sorted((x for x in data['sales_order_item'].values() if x['orderId']==order['id']),key=lambda x:x['id'])
    shown=root.all(lambda n:n.tag=='tr' and 'data-order-item-id' in n.a)
    check(name+'-all-snapshot-lines',[int(n.a['data-order-item-id']) for n in shown]==[x['id'] for x in lines])
    for n,x in zip(shown,lines):
        check(name+'-snapshot-'+str(x['id']),n.a.get('data-snapshot-sku')==x['skuSnapshot'] and n.a.get('data-snapshot-name')==x['productNameSnapshot'] and n.a.get('data-snapshot-cover')==x['coverImageSnapshot'] and Decimal(n.a['data-unit-price'])==Decimal(x['unitPrice']) and int(n.a['data-quantity'])==x['quantity'] and Decimal(n.a['data-line-amount'])==Decimal(x['lineAmount']))
    for k in ['receiverName','receiverPhone','receiverAddress']:
        n=root.find(lambda n:n.a.get('data-shipping-value')==k);check(name+'-shipping-snapshot-'+k,n is not None and hashlib.sha256(n.text().encode()).hexdigest()==order[k+'Sha256'])
    forms=root.all(lambda n:n.tag=='form' and re.fullmatch('/orders/[^/]+/ship',n.a.get('action','')) is not None)
    check(name+'-only-PAID-ship-form',len(forms)==(1 if order['status']=='PAID' else 0))
    if forms:
        check(name+'-csrf-one',len(forms[0].all(lambda n:n.tag=='input' and n.a.get('name')=='_csrf'))==1)
        check(name+'-visible-order-confirmation',order['orderNo'] in forms[0].text() or order['orderNo'] in root.text())
    if order['paymentNo']:
        receipt=root.find(lambda n:'data-payment-no' in n.a);check(name+'-first-payment-receipt',receipt is not None and receipt.text().strip()==order['paymentNo'])
    for k in ['createdAt','paidAt','cancelledAt','shippedAt','completedAt']:
        if order[k] is not None:
            expected=(datetime.datetime.fromisoformat(order[k])+datetime.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
            check(name+'-timeline-'+k,expected in root.text())
    check(name+'-linked-customer-detail',root.find(lambda n:n.tag=='a' and n.a.get('href')=='/customers/'+str(order['userId'])) is not None)
    record('admin-detail-observations.jsonl',dict(name=name,http_sequence=http_no,order_no=order['orderNo'],snapshot_lines=lines,first_payment_no=order['paymentNo'],first_times={k:order[k] for k in ['createdAt','paidAt','cancelledAt','shippedAt','completedAt']},shipping_values_recorded=False))
    return r

def verify_ship(name,before,a,after,b,no,expected,transport='HTTP',http_sequence=None):
    old=own_order(no,a);current=own_order(no,b);check(name+'-order-present',old is not None and current is not None)
    check(name+'-six-nonorder-tables-entirely-unchanged',all(before[t]==after[t] for t in TABLES if t!='sales_order'))
    check(name+'-all-product-fields-cart-and-snapshots-unchanged',all(a[t]==b[t] for t in ['product','cart_item','sales_order_item']))
    if expected=='NOOP':check(name+'-all-seven-noop',before==after)
    elif expected=='SHIPPED':
        delta=deltas(a,b)['sales_order'];check(name+'-only-target-order',len(delta)==1 and delta[0]['id']==str(old['id']))
        check(name+'-PAID-to-SHIPPED',old['status']=='PAID' and current['status']=='SHIPPED')
        check(name+'-first-shipped-time-valid',old['shippedAt'] is None and current['shippedAt'] is not None and current['shippedAt']>=old['paidAt'])
        check(name+'-receipt-amount-shipping-and-all-other-fields-preserved',all(current[k]==old[k] for k in old if k not in {'status','shippedAt','updatedAt'}))
    else:raise RuntimeError('Unknown shipment assertion scope')
    record('ship-observations.jsonl',dict(name=name,http_sequence=http_sequence,transport=transport,order_no=current['orderNo'],expected_transition=expected,before_order=old,after_order=current,shipping_raw_recorded=False))
    return current

def ship(cl,no,name,status=303,expected='NOOP',csrf='valid',extra=None):
    form=dict(extra or {})
    if csrf=='valid':
        page=cl.get('/orders',8081);assert_page(page,200,name+'-csrf-page');form['_csrf']=token(page)
    elif csrf=='wrong':form['_csrf']='wrong-step11-csrf'
    before=snapshot();a=state();out=cl.post('/orders/'+no+'/ship',form,8081);seq=http_no;after=snapshot();b=state();assert_page(out,status,name)
    snapshot_pair(name,before,a,after,b,http_sequence=seq,path='/orders/'+no+'/ship',status=status,expected_status=status,action_kind='ship',expected_transition=expected,semantic_action_check=True)
    if status==303:
        target=urllib.parse.urlsplit(out[1].get('Location',''));check(name+'-safe-detail-303',not target.netloc and not target.query and target.path.lower()=='/orders/'+no.lower())
        current=verify_ship(name,before,a,after,b,no,expected,http_sequence=seq)
        page=admin_detail(cl,target.path.rsplit('/',1)[1],name+'-303-detail')
        expected_message='模拟发货已登记，请核对首次发货时间。本操作不涉及真实物流。' if expected=='SHIPPED' else '该订单已发货或已完成，保留首次发货结果，未重复改写时间。'
        statuses=page[3].all(lambda n:n.a.get('role')=='status')
        check(name+'-exact-global-shipment-result-flash',any(n.text().strip()==expected_message for n in statuses))
        record('shipment-feedback-observations.jsonl',dict(name=name,http_sequence=http_no,followed_exact_location=out[1]['Location'],expected_message=expected_message,observed_status_messages=[n.text().strip() for n in statuses],matched=True))
        return current,page
    check(name+'-rejected-all-seven-zero-write',before==after)
    if status==404:check(name+'-unknown-no-detail-leak',not out[3].find(lambda n:'data-shipping-value' in n.a))
    return None,out

# Extend safe evidence with public fixture profiles and hashed private credential/contact values.
_orders_state=state
def state():
    data=_orders_state()
    q="SELECT JSON_OBJECT('id',id,'username',username,'displayName',display_name,'role',role,'status',status,'emailSha256',SHA2(email,256),'phoneSha256',SHA2(phone,256),'emailBlank',email IS NULL OR TRIM(email)='','phoneBlank',phone IS NULL OR TRIM(phone)='','passwordHashSha256',SHA2(password_hash,256),'createdAt',created_at,'updatedAt',updated_at) FROM store_user ORDER BY id;"
    data['store_user']={str(x['id']):x for x in map(json.loads,rows(q).splitlines())}
    return data

_shipping_scrub=scrub
def scrub(text):
    text=_shipping_scrub(text)
    return re.sub(r'''(<([a-z][a-z0-9]*)\b[^>]*\bdata-customer-contact=["'][^"']*["'][^>]*>)[\s\S]*?(</\2>)''',r'\1[REDACTED-CONTACT]\3',text,flags=re.I)

def customer_row(uid,data=None):return (data or state())['store_user'].get(str(uid))
def customer_list(cl,name,params=None,status=200):
    params=dict(params or {});r=cl.get('/customers'+('?' + urllib.parse.urlencode(params,doseq=True) if params else ''),8081);assert_page(r,status,name)
    if status!=200:return r
    root=r[3].find(lambda n:n.a.get('data-page-id')=='A08');check(name+'-A08',root is not None)
    q=params.get('q','').strip();wanted=params.get('status','ALL') or 'ALL';page=max(1,int(params.get('page',1)));size=int(params.get('size',10))
    matches=sorted((x for x in state()['store_user'].values() if x['role']=='CUSTOMER' and q.casefold() in x['username'].casefold() and (wanted=='ALL' or x['status']==wanted)),key=lambda x:x['id'])
    shown=matches[(page-1)*size:page*size];actual=root.all(lambda n:n.tag=='tr' and 'data-customer-id' in n.a)
    check(name+'-same-where-total',int(root.a['data-customer-count'])==len(matches))
    check(name+'-canonical-page-size',int(root.a['data-page'])==page and int(root.a['data-size'])==size)
    check(name+'-literal-username-AND-status-id-order',[int(n.a['data-customer-id']) for n in actual]==[x['id'] for x in shown])
    for n,x in zip(actual,shown):check(name+'-safe-row-'+str(x['id']),n.a.get('data-customer-username')==x['username'] and n.a.get('data-customer-status')==x['status'] and x['role']=='CUSTOMER')
    if page>1 and not shown:check(name+'-outofrange-recovery',root.find(lambda n:n.tag=='a' and 'data-page-link' in n.a) is not None)
    for n in root.all(lambda n:n.tag=='a' and 'data-page-link' in n.a):
        query=urllib.parse.parse_qs(urllib.parse.urlsplit(n.a.get('href','')).query,keep_blank_values=True)
        check(name+'-page-keeps-size',query.get('size')==[str(size)])
        if q:check(name+'-page-keeps-q',query.get('q')==[q])
        if wanted!='ALL':check(name+'-page-keeps-status',query.get('status')==[wanted])
    check(name+'-no-bcrypt-in-raw-response',not contains_bcrypt(r[2].decode('utf-8')))
    check(name+'-no-injected-script-node',not root.find(lambda n:n.tag=='script' and 'step12' in n.text()))
    record('customer-list-observations.jsonl',dict(name=name,http_sequence=http_no,database=DATABASE,parameters=params,total=len(matches),ordered_ids=[x['id'] for x in shown],page=page,size=size,ADMIN_excluded=True))
    return r

def customer_detail(cl,uid,name,status=200):
    r=cl.get('/customers/'+str(uid),8081);assert_page(r,status,name)
    if status!=200:
        check(name+'-no-profile-leak',not r[3].find(lambda n:n.a.get('data-page-id')=='A09'))
        return r
    row=customer_row(uid);root=r[3].find(lambda n:n.a.get('data-page-id')=='A09');check(name+'-A09',root is not None)
    check(name+'-CUSTOMER-only',row is not None and row['role']=='CUSTOMER' and root.a.get('data-customer-id')==str(int(str(uid).strip())) and root.a.get('data-customer-status')==row['status'])
    for key,attr in [('username','data-customer-username'),('displayName','data-customer-display-name')]:
        node=root.find(lambda n:attr in n.a);check(name+'-profile-'+key,node is not None and node.text().strip()==row[key])
    for key in ['email','phone']:
        node=root.find(lambda n:n.a.get('data-customer-contact')==key);check(name+'-contact-node-'+key,node is not None)
        if row[key+'Blank']:check(name+'-blank-contact-fallback-'+key,node.text().strip()=='未填写')
        else:check(name+'-contact-hash-'+key,hashlib.sha256(node.text().encode()).hexdigest()==row[key+'Sha256'])
    orders_link=root.find(lambda n:n.tag=='a' and 'data-customer-orders-link' in n.a)
    check(name+'-orders-filter-link',orders_link is not None and urllib.parse.urlsplit(orders_link.a['href']).path=='/orders' and urllib.parse.parse_qs(urllib.parse.urlsplit(orders_link.a['href']).query).get('userId')==[str(uid)])
    forms=root.all(lambda n:n.tag=='form' and 'data-customer-status-form' in n.a);check(name+'-one-status-form',len(forms)==1)
    targets=forms[0].all(lambda n:n.tag=='input' and n.a.get('name')=='targetStatus');check(name+'-opposite-only-target',len(targets)==1 and targets[0].a.get('value')==('DISABLED' if row['status']=='ENABLED' else 'ENABLED'))
    check(name+'-one-csrf',len(forms[0].all(lambda n:n.tag=='input' and n.a.get('name')=='_csrf'))==1)
    check(name+'-no-extra-profile-inputs',not root.find(lambda n:n.tag in ['input','textarea','select'] and n.a.get('name') not in ['_csrf','targetStatus']))
    check(name+'-raw-hash-not-exposed',not contains_bcrypt(r[2].decode()))
    record('customer-detail-observations.jsonl',dict(name=name,http_sequence=http_no,database=DATABASE,customer_id=int(uid),safe_profile=row,orders_href=orders_link.a['href'],raw_contacts_recorded=False))
    return r

def verify_customer_change(name,before,a,after,b,uid,wanted,transport='HTTP',http_sequence=None):
    old=customer_row(uid,a);now=customer_row(uid,b);check(name+'-target-present',old is not None and now is not None and old['role']=='CUSTOMER')
    check(name+'-six-business-tables-entirely-unchanged',all(before[t]==after[t] for t in TABLES if t!='store_user'))
    if old['status']==wanted:
        check(name+'-same-state-seven-tables-and-stamp-noop',before==after and a['store_user']==b['store_user']);changed=False
    else:
        changed=True;delta=deltas(a,b)['store_user'];check(name+'-only-target-user-row',len(delta)==1 and delta[0]['id']==str(uid))
        check(name+'-only-status-and-stamp-fields-change',now['status']==wanted and all(now[k]==old[k] for k in old if k not in {'status','updatedAt'}))
        previous=datetime.datetime.fromisoformat(old['updatedAt']);current=datetime.datetime.fromisoformat(now['updatedAt'])
        check(name+'-stamp-monotonic-microsecond-lower-bound',current>=previous+datetime.timedelta(microseconds=1))
        if previous>datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None):check(name+'-future-stamp-exact-plus-one-microsecond',current==previous+datetime.timedelta(microseconds=1))
    record('customer-status-observations.jsonl',dict(name=name,http_sequence=http_sequence,transport=transport,customer_id=uid,target_status=wanted,changed=changed,before_user=old,after_user=now,six_business_tables_preserved=True,raw_password_or_contacts_recorded=False))
    return now,changed

def status_action(cl,uid,wanted,name,status=303,csrf='valid',extra=None):
    form=dict(extra or {})
    if wanted is not False:form['targetStatus']=wanted
    if csrf=='valid':
        formpage=cl.get('/customers',8081);assert_page(formpage,200,name+'-csrf-page');form['_csrf']=token(formpage)
    elif csrf=='wrong':form['_csrf']='wrong-step12-csrf'
    before=snapshot();a=state();out=cl.post('/customers/'+str(uid)+'/status',form,8081);seq=http_no;after=snapshot();b=state();assert_page(out,status,name)
    snapshot_pair(name,before,a,after,b,http_sequence=seq,database=DATABASE,path='/customers/'+str(uid)+'/status',status=status,expected_status=status,action_kind='customer-status',target_status=wanted,semantic_action_check=True)
    if status==303:
        location=out[1].get('Location','');target=urllib.parse.urlsplit(location);check(name+'-safe-exact-detail-303',not target.netloc and target.path=='/customers/'+str(int(str(uid).strip())) and not target.query)
        now,changed=verify_customer_change(name,before,a,after,b,int(uid),str(wanted).strip(),http_sequence=seq)
        page=customer_detail(cl,target.path.rsplit('/',1)[1],name+'-303-detail')
        messages=[n.text().strip() for n in page[3].all(lambda n:n.a.get('role')=='status')]
        expected=status_feedback(str(wanted).strip(),changed)
        check(name+'-exact-global-result',expected in messages)
        record('customer-feedback-observations.jsonl',dict(name=name,http_sequence=http_no,followed_exact_location=location,expected_message=expected,observed_status_messages=messages,matched=True))
        return now,page
    check(name+'-rejected-all-seven-zero-write',before==after)
    return None,out

def status_feedback(wanted,changed):
    # Exact strings must be aligned to the published controller before the formal source is frozen.
    return CUSTOMER_FEEDBACK[(wanted,changed)]

CUSTOMER_FEEDBACK={(wanted,changed):('顾客状态已更新。真实切换后的既有会话需重新登录，购物车与历史订单保留。' if changed else '顾客已处于目标状态，未重复更新状态或时间。') for wanted in ['ENABLED','DISABLED'] for changed in [True,False]}

def dashboard_counts():
    r=rows("SELECT JSON_OBJECT('on-sale-products',(SELECT COUNT(*) FROM product WHERE status='ON_SALE'),'draft-products',(SELECT COUNT(*) FROM product WHERE status='DRAFT'),'paid-orders',(SELECT COUNT(*) FROM sales_order WHERE status='PAID'),'enabled-customers',(SELECT COUNT(*) FROM store_user WHERE role='CUSTOMER' AND status='ENABLED'),'disabled-customers',(SELECT COUNT(*) FROM store_user WHERE role='CUSTOMER' AND status='DISABLED'));")
    return json.loads(r)

DASHBOARD_LINKS={'on-sale-products':('/products','ON_SALE'),'draft-products':('/products','DRAFT'),'paid-orders':('/orders','PAID'),'enabled-customers':('/customers','ENABLED'),'disabled-customers':('/customers','DISABLED')}
def dashboard(cl,name,status=200,follow_links=True):
    r=cl.get('/',8081);seq=http_no;assert_page(r,status,name)
    if status!=200:
        check(name+'-no-fabricated-counts',not r[3].find(lambda n:'data-dashboard-count' in n.a))
        check(name+'-retry-root-link',r[3].find(lambda n:n.tag=='a' and n.a.get('href')=='/') is not None)
        record('dashboard-error-observations.jsonl',dict(name=name,http_sequence=seq,database=DATABASE,application_db_user=APP_USERNAME,status=status,no_numeric_fallback=True,retry_root=True,natural_permission_failure=True))
        return r
    root=r[3].find(lambda n:n.a.get('data-page-id')=='A02');check(name+'-A02',root is not None)
    expected=dashboard_counts();cards=root.all(lambda n:'data-dashboard-card' in n.a);check(name+'-five-independent-cards',len(cards)==5 and {n.a['data-dashboard-card'] for n in cards}==set(expected))
    for card in cards:
        key=card.a['data-dashboard-card'];value=card.find(lambda n:'data-dashboard-count' in n.a);check(name+'-count-'+key,value is not None and value.text().strip()==str(expected[key]))
        link=card if card.tag=='a' else card.find(lambda n:n.tag=='a');path,wanted=DASHBOARD_LINKS[key];check(name+'-link-'+key,link is not None and urllib.parse.urlsplit(link.a.get('href','')).path==path and urllib.parse.parse_qs(urllib.parse.urlsplit(link.a['href']).query).get('status')==[wanted])
        if follow_links:
            page=cl.get(link.a['href'],8081);assert_page(page,200,name+'-linked-'+key)
            attr='data-product-count' if path=='/products' else 'data-order-count' if path=='/orders' else 'data-customer-count'
            node=page[3].find(lambda n:attr in n.a);check(name+'-linked-count-'+key,node is not None and int(node.a[attr])==expected[key])
    record('dashboard-observations.jsonl',dict(name=name,http_sequence=seq,database=DATABASE,counts=expected,ADMIN_excluded=True,source='one HTTP page compared to five independent SQL count conditions',card_lists_followed=follow_links))
    return r

def fixture_accounts():
    names=['step12%literal','step12_literal','step12\\literal','step12literal','step12Alpha','step12Beta','界'*50,'😀'*50,'<script>step12</script>']
    before=snapshot();a=state()
    for i,name in enumerate(names):
        fixture("INSERT INTO store_user(username,password_hash,display_name,role,status,email,phone) SELECT "+literal(name)+",password_hash,"+literal('验证顾客'+str(i))+",'CUSTOMER',"+literal('DISABLED' if i%3==0 else 'ENABLED')+",NULL,NULL FROM store_user WHERE id=2;",'root-special-username-fixture-'+str(i))
    after=snapshot();b=state();check('root-account-fixtures-only-user-table',all(before[t]==after[t] for t in TABLES if t!='store_user'))
    created=[x['after'] for x in deltas(a,b)['store_user'] if x['before'] is None]
    check('root-nine-account-fixtures',len(created)==9 and all(x['role']=='CUSTOMER' for x in created))
    save(EV/'controlled-account-fixtures.json',json.dumps(dict(original_seed_users=4,fixture_CUSTOMERs=9,current_total_users=after['store_user']['rows'],fixture_ids=[x['id'] for x in created],fixture_usernames=names,no_business_account_create_route=True),ensure_ascii=False,indent=2))
    return created

def product_publication(cl,pid,kind,name):
    row=product(pid);formpage=cl.get('/products/'+str(pid)+'/edit',8081);assert_page(formpage,200,name+'-form')
    before=snapshot();a=state();out=cl.post('/products/'+str(pid)+'/'+kind,{'version':row['version'],'_csrf':token(formpage)},8081);seq=http_no;after=snapshot();b=state();assert_page(out,303,name)
    snapshot_pair(name,before,a,after,b,http_sequence=seq,path='/products/'+str(pid)+'/'+kind,status=303,setup_action='existing-product-publication')
    check(name+'-only-product-table',all(before[t]==after[t] for t in TABLES if t!='product'))
    delta=deltas(a,b)['product'];now=product(pid);check(name+'-target-status-version-only',len(delta)==1 and delta[0]['id']==str(pid) and now['status']==('ON_SALE' if kind=='publish' else 'DRAFT') and now['version']==row['version']+1 and all(now[k]==row[k] for k in row if k not in {'status','version','updatedAt'}))
    return out

def native_probe():
    extracted=BASE/'native-probe';classes=extracted/'classes';libs=extracted/'lib';classes.mkdir(parents=True);libs.mkdir()
    with zipfile.ZipFile(REPO/'csucampuscraft-admin/target/csucampuscraft-admin-0.0.1-SNAPSHOT.jar') as z:
        for n in z.namelist():
            if n.startswith('BOOT-INF/classes/') and not n.endswith('/'):
                p=classes/n[len('BOOT-INF/classes/'):];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
            elif n.startswith('BOOT-INF/lib/') and n.endswith('.jar'):(libs/Path(n).name).write_bytes(z.read(n))
    cp=str(classes)+';'+str(libs/'*')+';'+str(extracted)
    p=command([JAVA.parent/'javac.exe','-cp',cp,'-d',extracted,HERE/'NativeCustomerDashboardProbe.java'],timeout=45)
    save(EV/'native-compile.log',p.stdout.decode('utf-8',errors='replace')+p.stderr.decode('utf-8',errors='replace'));check('native-compile',p.returncode==0)
    p=command([JAVA,'-cp',cp,'org.csucampuscraft.admin.customer.NativeCustomerDashboardProbe','--structural'],timeout=45)
    save(EV/'native-structural.log',p.stdout.decode('utf-8',errors='replace')+p.stderr.decode('utf-8',errors='replace'));check('native-structural-regression',p.returncode==0)
    e=start_env();e.update(STEP12_NATIVE_ADMIN_ID='4',STEP12_NATIVE_CUSTOMER_ID='2',STEP12_NATIVE_TARGET_ID='3')
    before=snapshot();a=state();p=command([JAVA,'-cp',cp,'org.csucampuscraft.admin.customer.NativeCustomerDashboardProbe','--live'],env=e,timeout=110);after=snapshot();b=state()
    text=p.stdout.decode('utf-8',errors='replace');save(EV/'native-probe.log',text+p.stderr.decode('utf-8',errors='replace'))
    snapshot_pair('native-customer-status-and-dashboard',before,a,after,b,transport='native actual Service; not HTTP',native_target_id=3,native_exit_code=p.returncode)
    check('native-exit',p.returncode==0);native=json.loads(text.strip().splitlines()[-1]);check('native-PASS',native['overall']=='PASS');result['native_checks']=native['checks']
    check('native-only-target-user-changed',len(deltas(a,b)['store_user'])==1 and deltas(a,b)['store_user'][0]['id']=='3')
    old=customer_row(3,a);now=customer_row(3,b);check('native-target-back-disabled-and-profile-preserved',old['status']==now['status']=='DISABLED' and all(old[k]==now[k] for k in old if k!='updatedAt'))
    check('native-target-exact-plus-two-microseconds',datetime.datetime.fromisoformat(now['updatedAt'])==datetime.datetime.fromisoformat(old['updatedAt'])+datetime.timedelta(microseconds=2))
    check('native-all-six-business-tables-unchanged',all(before[t]==after[t] for t in TABLES if t!='store_user'))

def alternate_dashboard_scenarios(main_admin_process):
    global DATABASE,APP_USERNAME
    stop(main_admin_process)
    empty_name='csucampuscraft_empty'
    sql('CREATE DATABASE '+empty_name+' CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_ci;')
    sql((REPO/'database/01-schema.sql').read_text(encoding='utf-8-sig'),empty_name)
    sql('INSERT INTO '+empty_name+'.store_user(id,username,password_hash,display_name,role,status,email,phone,created_at,updated_at) SELECT id,username,password_hash,display_name,role,status,email,phone,created_at,updated_at FROM csucampuscraft.store_user WHERE id=4;')
    sql("GRANT SELECT ON "+empty_name+".* TO 'csucampuscraft'@'127.0.0.1';")
    DATABASE=empty_name;APP_USERNAME='csucampuscraft'
    before=snapshot();a=state();check('empty-business-keeps-only-ADMIN-fixture',[before[t]['rows'] for t in TABLES]==[1,0,0,0,0,0,0] and customer_row(4)['role']=='ADMIN')
    save(EV/'empty-business-identity.json',json.dumps(dict(database=DATABASE,mysql_port=mysqlport,kept_ADMIN_id=4,store_user_rows=1,all_other_tables_empty=True,no_CUSTOMER=True,not_a_literal_seven_table_zero_login=True),indent=2))
    empty_process=launch('csucampuscraft-admin',8081);empty_admin=Client();out,_,_=login(empty_admin,8081,name='empty-business-admin');assert_page(out,303,'empty-business-admin-login')
    dashboard(empty_admin,'empty-business-dashboard-zero',follow_links=False)
    check('empty-business-all-five-zero',all(v==0 for v in dashboard_counts().values()))
    browser('empty',{'admin':empty_admin.cookie(8081)})
    after=snapshot();snapshot_pair('empty-business-read-only',before,a,after,state(),database=DATABASE,scenario='ADMIN fixture plus empty business tables')
    check('empty-business-all-reads-zero-write',before==after);stop(empty_process)
    DATABASE='csucampuscraft';APP_USERNAME='csucampuscraft_dashboard_denied'
    sql("CREATE USER 'csucampuscraft_dashboard_denied'@'127.0.0.1' IDENTIFIED BY '"+apppass+"';")
    sql("GRANT SELECT ON csucampuscraft.store_user TO 'csucampuscraft_dashboard_denied'@'127.0.0.1';")
    save(EV/'dashboard-denied-grants.txt',rows("SHOW GRANTS FOR 'csucampuscraft_dashboard_denied'@'127.0.0.1';",None))
    before=snapshot();a=state();denied_process=launch('csucampuscraft-admin',8081);denied_admin=Client();out,_,_=login(denied_admin,8081,name='denied-summary-admin');assert_page(out,303,'denied-summary-login-still-success')
    dashboard(denied_admin,'natural-summary-permission-error',500,follow_links=False)
    dashboard(denied_admin,'natural-summary-retry-still-error',500,follow_links=False)
    browser('error',{'admin':denied_admin.cookie(8081)})
    after=snapshot();snapshot_pair('natural-dashboard-permission-error-zero-write',before,a,after,state(),database=DATABASE,application_db_user=APP_USERNAME,scenario='natural SELECT denial; same JAR; login allowed')
    check('natural-dashboard-error-seven-zero-write',before==after);stop(denied_process)
    APP_USERNAME='csucampuscraft'

def browser(phase,cookies,fixed=None):
    from http.server import BaseHTTPRequestHandler,HTTPServer
    from threading import Thread
    import base64
    control_token=secrets.token_urlsafe(32);secret_values.append(control_token);fixed=dict(fixed or {})
    pending={};completed=[];failures=[];after_only=[]
    class Control(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            global http_no
            try:
                if self.headers.get('Authorization')!='Bearer '+control_token:raise RuntimeError('Unauthorized browser audit')
                obj=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                if self.path=='/register-private':
                    for value in obj['values']:
                        if value:secret_values.append(value)
                elif self.path=='/before':pending[obj['id']]={'before':snapshot(),'state':state(),**obj}
                elif self.path in ['/after','/after-only']:
                    readonly=self.path=='/after-only'
                    meta=obj if readonly else pending.pop(obj['id'])
                    check('browser-unrouted-response-is-read-only-'+obj['id'],not readonly or meta['method']=='GET')
                    text=base64.b64decode(obj['body_base64']).decode('utf-8',errors='replace');dom=Parser(text).root
                    if obj['body_available']:
                        check('browser-raw-no-bcrypt-'+obj['id'],not contains_bcrypt(text));check('browser-raw-no-password-'+obj['id'],PASSWORD not in text)
                    for n in dom.all(lambda n:n.tag=='input' and n.a.get('name') in ['_csrf','confirmationToken']):
                        if n.a.get('value'):secret_values.append(n.a['value'])
                    http_no+=1;redacted=scrub(text).encode();digest=hashlib.sha256(redacted).hexdigest();filename='bodies/'+digest[:24]+'.body.gz'
                    if not (EV/filename).exists():(EV/filename).parent.mkdir(exist_ok=True);(EV/filename).write_bytes(gzip.compress(redacted,mtime=0))
                    record('http.jsonl',dict(sequence=http_no,request_id=obj['id'],method=meta['method'],path=meta['path'],port=meta['port'],database=DATABASE,application_db_user=APP_USERNAME,status=obj['status'],content_type=obj['content_type'],location=obj.get('location'),cookie_values_recorded=False,form_fields=meta.get('form_fields'),target_status=meta.get('target_status'),body_file=filename,body_encoding='gzip',body_available=obj['body_available'],redacted_body_sha256=digest,redacted=True,raw_bcrypt_scan_passed=not contains_bcrypt(text) if obj['body_available'] else None,raw_response_scan_before_redaction=obj['body_available'],database_observation='AFTER_ONLY; no invented before snapshot' if readonly else 'Genuine before route.continue and after response',redirected_from=meta.get('redirected_from'),transport='Actual browser response, redirect GET after-only' if readonly else 'Actual browser request continued after seven-table before snapshot'))
                    after=snapshot();b=state()
                    if readonly:
                        record('database-writes.jsonl',dict(name='browser-'+obj['id'],http_sequence=http_no,path=meta['path'],port=meta['port'],database=DATABASE,status=obj['status'],before=None,after=after,**{t+'_after':b[t] for t in b},automatic_audit=False,database_observation='AFTER_ONLY',read_only_response=True,no_before_snapshot_claimed=True));after_only.append(obj['id'])
                    else:
                        snapshot_pair('browser-'+obj['id'],meta['before'],meta['state'],after,b,http_sequence=http_no,path=meta['path'],port=meta['port'],database=DATABASE,status=obj['status'],automatic_audit=True,transport='real browser')
                        if meta['method']=='GET' or obj['status']!=303 or meta['path']=='/login':check('browser-read-session-or-reject-zero-write-'+obj['id'],meta['before']==after)
                        else:
                            match=re.fullmatch('/customers/([0-9]+)/status',meta['path']);check('browser-status-route-'+obj['id'],match is not None and meta['port']==8081)
                            verify_customer_change(obj['id'],meta['before'],meta['state'],after,b,int(match.group(1)),meta['target_status'],transport='real browser',http_sequence=http_no)
                    completed.append(obj['id'])
                else:raise RuntimeError('Unknown audit operation')
                self.send_response(200);self.end_headers();self.wfile.write(b'{}')
            except Exception as error:
                failures.append(scrub(str(error)));self.send_response(500);self.end_headers();self.wfile.write(b'{"error":"audit failure"}')
    service=HTTPServer(('127.0.0.1',0),Control);thread=Thread(target=service.serve_forever,daemon=True);thread.start()
    e=start_env();e.update(STEP12_BROWSER_OUT=str(EV/'browser'/phase),STEP12_BROWSER_PHASE=phase,STEP12_BROWSER_COOKIES=json.dumps(cookies),STEP12_BROWSER_FIXED=json.dumps(fixed),STEP12_BROWSER_PASSWORD=PASSWORD,STEP12_BROWSER_CONTROL='http://127.0.0.1:'+str(service.server_port),STEP12_BROWSER_CONTROL_TOKEN=control_token)
    try:
        p=command([RUNTIME/'node/bin/node.exe',HERE/'verify_browser.cjs'],env=e,timeout=300)
        save(EV/('browser-'+phase+'.log'),p.stdout.decode('utf-8',errors='replace')+p.stderr.decode('utf-8',errors='replace'));check('browser-'+phase+'-exit',p.returncode==0)
        check('browser-'+phase+'-audits-complete',not pending and not failures and len(completed)>0)
        br=json.loads((EV/'browser'/phase/'result.json').read_text(encoding='utf-8'));check('browser-'+phase+'-PASS',br['completed'] and br['overall']=='PASS')
        result.setdefault('browser',{})[phase]=dict(checks=len(br['checks']),screenshots=len(br['screenshots']),captured_responses=len(completed),redirect_GET_after_only=len(after_only),all_POST_have_genuine_before_after=True)
    finally:service.shutdown();thread.join(timeout=5);service.server_close()

def aggregate_browser():
    aggregated=dict(overall='PASS',completed=True,checks=[],screenshots=[],phase_results={},browser='Microsoft Edge via Playwright',database_boundaries='main=csucampuscraft; empty=csucampuscraft_empty with ADMIN fixture; error=main schema with restricted SELECT application account',redirect_GET_boundary='Fallback GET response capture is after-only, not an invented before snapshot; every POST requires genuine before/after.')
    for phase in ['main','empty','error']:
        data=json.loads((EV/'browser'/phase/'result.json').read_text(encoding='utf-8'));check('browser-aggregate-'+phase,data['overall']=='PASS' and data['completed'])
        aggregated['phase_results'][phase]=dict(result_file=phase+'/result.json',**result['browser'][phase])
        aggregated['checks'].extend(dict(item,phase=phase,name=phase+'/'+item['name']) for item in data['checks'])
        for shot in data['screenshots']:
            name=shot['path'];check('browser-safe-relative-PNG-'+phase+'-'+name,'/' not in name and '\\' not in name and '..' not in name)
            p=EV/'browser'/phase/name;check('browser-PNG-archive-byte-identity-'+phase+'-'+name,hashlib.sha256(p.read_bytes()).hexdigest()==shot['sha256'])
            aggregated['screenshots'].append(dict(shot,path=phase+'/'+name,phase=phase))
    check('browser-exact24-total-PNG',len(aggregated['screenshots'])==24)
    check('browser-aggregate-new-file',not (EV/'browser/result.json').exists())
    save(EV/'browser/result.json',json.dumps(aggregated,ensure_ascii=False,indent=2));result['screenshots']=24;result['browser_checks']=len(aggregated['checks'])

def sensitive_scan():
    findings=[];files=0;decompressed=0
    tokens={x for x in secret_values if len(x)>=8}
    for p in EV.rglob('*'):
        if not p.is_file() or p.suffix=='.png':continue
        files+=1;data=p.read_bytes()
        if p.suffix=='.gz':data=gzip.decompress(data);decompressed+=1
        for value in tokens:
            if value.encode('utf-8') in data:findings.append({'file':p.relative_to(EV).as_posix(),'type':'known-private-value'})
    report={'overall':'PASS' if not findings else 'FAIL','files_scanned':files,'gzip_decompressed_files':decompressed,'known_values_checked':len(tokens),'secret_values_recorded':False,'findings':findings,'shipping_redaction':'Receiver input/textarea and U08 data-shipping-value contents structurally redacted; SQL order state contains only per-field SHA; screenshots mask shipping; no request form values recorded.'}
    save(EV/'sensitive-scan.json',json.dumps(report,ensure_ascii=False,indent=2))
    if findings:result['overall']='FAIL';result['sensitive_scan_failed']=True

try:
    regression=run_regression();save(EV/'raw-response-scanner-regression.json',json.dumps(regression,indent=2));check('raw-response-scanner-offline-regression',regression['overall']=='PASS')
    check('tested-code-head',git('rev-parse','HEAD').decode().strip()==TESTED)
    result['branch']=git('branch','--show-current').decode().strip();check('feature-branch',result['branch']=='feat/step12-admin-customers')
    status=git('status','--short','--untracked-files=all').decode();save(EV/'git-input-status.txt',status);check('tested-worktree-clean',not status.strip())
    save(EV/'implementation-diff.patch',git('diff',BASELINE+'..'+TESTED,'--','csucampuscraft-admin').decode('utf-8'))
    inputs=[]
    for app in ['csucampuscraft-user','csucampuscraft-admin']:
        inputs.append(REPO/app/'pom.xml');inputs.extend(p for p in (REPO/app/'src').rglob('*') if p.is_file())
    inputs.extend(p for d in ['database','assets','.mvn'] for p in (REPO/d).rglob('*') if p.is_file());inputs.extend([REPO/'mvnw',REPO/'mvnw.cmd'])
    manifest=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(REPO).as_posix()+'\n' for p in sorted(inputs,key=lambda x:x.relative_to(REPO).as_posix()))
    save(EV/'runtime-inputs.sha256',manifest);result['runtime_manifest_sha256']=hashlib.sha256(manifest.encode()).hexdigest();result['runtime_file_count']=len(inputs)
    tools=[]
    for name in ['verify_step12.py','verify_browser.cjs','NativeCustomerDashboardProbe.java','privacy_checks.py']:
        save(EV/name,(HERE/name).read_text(encoding='utf-8-sig'));tools.append(dict(path=name,actual_source_sha256=hashlib.sha256((HERE/name).read_bytes()).hexdigest(),saved_source_sha256=hashlib.sha256((EV/name).read_bytes()).hexdigest()))
    save(EV/'tool-identity.json',json.dumps(dict(captured_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),timing='Before private database initialization',files=tools,privacy_import='from privacy_checks import contains_bcrypt,run_regression'),indent=2))
    builddir=Path(os.environ.get('STEP12_BUILD_LOG_DIR',HERE.parent));exits=json.loads((builddir/'build-exits.json').read_text(encoding='utf-8-sig'))
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
    sql("GRANT UPDATE ON csucampuscraft.store_user TO 'csucampuscraft'@'127.0.0.1';")
    sql("GRANT UPDATE ON csucampuscraft.product TO 'csucampuscraft'@'127.0.0.1';")
    sql("GRANT INSERT,UPDATE ON csucampuscraft.sales_order TO 'csucampuscraft'@'127.0.0.1';")
    sql("GRANT INSERT ON csucampuscraft.sales_order_item TO 'csucampuscraft'@'127.0.0.1';")
    save(EV/'application-grants.txt',rows("SHOW GRANTS FOR 'csucampuscraft'@'127.0.0.1';",None))
    original=snapshot();save(EV/'database-original.json',json.dumps(original,indent=2));check('seed-counts',[original[t]['rows'] for t in TABLES]==[4,15,60,100,10,10,20])
    for port in [8080,8081]:
        with socket.socket() as s:s.bind(('127.0.0.1',port))
    user_process=launch('csucampuscraft-user',8080);admin_process=launch('csucampuscraft-admin',8081)
    note=pid_by_sku('CSU-LMK-NOTE-01');gift=pid_by_sku('CSU-GRAD-BOX-01')
    cl=Client();admin=Client();guest=Client()
    for client,user,port in [(cl,'alice',8080),(admin,'admin',8081)]:
        out,_,_=login(client,port,username=user,name='initial-'+user);assert_page(out,303,'login-'+user)
    for protected in ['csucampuscraft-user','database','mvnw','mvnw.cmd','.mvn','csucampuscraft-admin/pom.xml']:
        check('protected-source-unchanged-'+protected,not git('diff','--name-only',BASELINE+'..'+TESTED,'--',protected).strip())
    dashboard(admin,'original-demo-dashboard')
    zero_sale=product(pid_by_sku('CSU-SPT-STAND-01'));check('sold-out-still-ON_SALE',zero_sale['status']=='ON_SALE' and zero_sale['stock']==0)
    created=fixture_accounts();empty_customer=created[0]['id']
    dashboard(admin,'fixture-accounts-dashboard-not-original-seed-count')
    for params,label in [({},'all'),({'status':'ENABLED'},'enabled'),({'status':'DISABLED'},'disabled'),({'page':2,'size':2},'second-page'),({'page':0},'page-zero'),({'page':-2},'page-negative'),({'page':9223372036854775807,'size':50},'huge-offset'),({'size':1},'size-min'),({'size':50},'size-max'),({'q':'  step12  ','status':'ENABLED','size':2,'page':2},'joint-filter-page2'),({'q':'ADMIN'},'ADMIN-name-excluded'),({'q':'no-such-customer'},'empty')]:customer_list(admin,'A08-'+label,params)
    for i,q in enumerate(['%','_','\\','step12%literal','step12_literal','step12\\literal','界'*50,'😀'*50,'<script>step12</script>']):customer_list(admin,'A08-literal-q-'+str(i),{'q':q,'size':50})
    for key,values in {'q':['a'*51,'😀'*51],'status':['UNKNOWN','enabled','1'],'page':['x','1.1','9223372036854775808'],'size':['x','0','-1','51','1.5']}.items():
        for i,value in enumerate(values):customer_list(admin,'A08-invalid-'+key+'-'+str(i),{key:value},400)
    for key in ['q','status','page','size']:customer_list(admin,'A08-duplicate-'+key,{key:['1','2']},400)
    for uid in [1,2,3,empty_customer]:customer_detail(admin,uid,'A09-valid-'+str(uid))
    for uid in [4,999999]:customer_detail(admin,uid,'A09-unknown-or-ADMIN-'+str(uid),404)
    for uid in ['0','-1','x','1.1','9223372036854775808']:customer_detail(admin,uid,'A09-invalid-'+uid,400)
    admin_list(admin,'A09-no-order-customer-valid',{'userId':empty_customer})
    alice_seed=next(x for x in state()['sales_order'].values() if x['userId']==1)
    admin_list(admin,'A09-order-AND-CI',{'userId':1,'status':alice_seed['status'],'orderNo':alice_seed['orderNo'].lower(),'size':1})
    admin_list(admin,'A09-order-other-customer-intersection',{'userId':2,'orderNo':alice_seed['orderNo']})
    admin_detail(admin,alice_seed['orderNo'],'A07-back-customer-link')
    draft=next(x for x in state()['product'].values() if x['status']=='DRAFT')
    product_publication(admin,draft['id'],'publish','dashboard-publish-existing');dashboard(admin,'dashboard-after-publish')
    product_publication(admin,draft['id'],'unpublish','dashboard-unpublish-existing');dashboard(admin,'dashboard-after-unpublish')
    pending=next(x for x in state()['sales_order'].values() if x['userId']==1 and x['status']=='PENDING_PAYMENT')
    user_action(cl,pending['orderNo'],'payment','dashboard-payment-existing-order',303,expected='PAID');dashboard(admin,'dashboard-after-real-payment')
    status_action(admin,1,'DISABLED','disable-owner-before-existing-PAID-shipment')
    check('PAID-owner-disabled-before-admin-shipment',customer_row(1)['status']=='DISABLED')
    ship(admin,pending['orderNo'],'dashboard-shipment-existing-order',303,expected='SHIPPED');dashboard(admin,'dashboard-after-real-shipment')
    check('disabled-owner-does-not-block-legal-shipment',customer_row(1)['status']=='DISABLED' and own_order(pending['orderNo'])['status']=='SHIPPED')
    status_action(admin,1,'ENABLED','reenable-owner-after-admin-shipment')
    # Actual timestamp lower-bound fixture, not a changed system clock or same-wall-clock claim.
    fixture('UPDATE store_user SET updated_at=DATE_ADD(CURRENT_TIMESTAMP(6),INTERVAL 1 HOUR) WHERE id=1;','root-alice-future-auth-stamp')
    out,_,_=login(cl,8080,name='fresh-alice-future-stamp');assert_page(out,303,'fresh-alice-future-stamp')
    prepare_eighty_five(cl,'valid-alice-cart-for-old-confirmations')
    baseline_business=snapshot();business_state=state()
    for uid in [4,999999]:status_action(admin,uid,'DISABLED','status-ADMIN-or-unknown-'+str(uid),404)
    for uid in ['0','-1','x','1.1','9223372036854775808']:status_action(admin,uid,'DISABLED','status-invalid-id-'+uid,400)
    for i,wanted in enumerate([False,'','UNKNOWN','disabled',['ENABLED','DISABLED']]):status_action(admin,1,wanted,'status-invalid-target-'+str(i),400)
    for csrf in ['missing','wrong']:status_action(admin,1,'DISABLED','status-'+csrf+'-csrf',403,csrf=csrf)
    is_login_redirect(guest.get('/customers',8081),'guest-customers','/customers')
    is_login_redirect(guest.get('/customers/1',8081),'guest-customer-detail','/customers/1')
    is_login_redirect(guest.post('/customers/1/status',{'targetStatus':'DISABLED'},8081),'guest-status-before-csrf')
    is_login_redirect(cl.post('/customers/1/status',{'targetStatus':'DISABLED'},8081),'user-cookie-not-admin')
    # Four distinct old sessions cover protected reads, a checkout token, orders, and a POST.
    olds=[]
    for i in range(4):
        old=Client();out,_,_=login(old,8080,name='old-alice-'+str(i));assert_page(out,303,'old-alice-'+str(i));olds.append(old)
    old_confirmation=checkout(olds[1],'old-alice-confirmation-before-disable',total='85.00')
    old_token=confirmation(old_confirmation)
    status_action(admin,1,'DISABLED','first-disable-alice',extra={'role':'ADMIN','password':'CLIENT_FAKE','password_hash':'CLIENT_FAKE','displayName':'CLIENT_FAKE','updated_at':'2000-01-01'})
    status_action(admin,1,'DISABLED','repeat-disable-no-write');dashboard(admin,'dashboard-after-disable')
    admin_list(admin,'disabled-CUSTOMER-orders-still-queryable',{'userId':1})
    is_login_redirect(olds[0].get('/cart'),'disabled-next-cart','/cart')
    is_login_redirect(olds[1].post('/orders',{'confirmationToken':old_token}),'disabled-next-submit-before-csrf')
    is_login_redirect(olds[2].get('/orders'),'disabled-next-orders','/orders')
    is_login_redirect(olds[3].post('/cart/items',{'productId':'x','quantity':'x'}),'disabled-next-write-before-format-csrf')
    public=cl.get('/products');assert_page(public,200,'disabled-public-catalog');badge(public,None,'disabled-public-badge0')
    status_action(admin,1,'ENABLED','first-enable-alice');status_action(admin,1,'ENABLED','repeat-enable-no-write');dashboard(admin,'dashboard-after-enable')
    for i,old in enumerate(olds):is_login_redirect(old.get('/cart'),'re-enabled-old-session-'+str(i),'/cart')
    out,_,_=login(olds[1],8080,name='fresh-after-reenable');assert_page(out,303,'fresh-after-reenable')
    fresh_csrf_page=olds[1].get('/cart');assert_page(fresh_csrf_page,200,'fresh-current-CSRF-without-new-confirmation')
    submit(olds[1],fresh_csrf_page,'old-confirmation-does-not-revive',409,submitted_token=old_token,fields=shipping(),csrf='valid')
    current=olds[1].get('/cart');assert_page(current,200,'fresh-login-recovers-cart');badge(current,1,'fresh-login-cart-badge');order_list(olds[1],'fresh-login-recovers-original-orders')
    # Two additional old sessions do not access anything between disable and immediate enable.
    silent=[]
    for i in range(2):
        old=Client();out,_,_=login(old,8080,name='silent-old-'+str(i));assert_page(out,303,'silent-old-'+str(i));silent.append(old)
    status_action(admin,1,'DISABLED','silent-disable');status_action(admin,1,'ENABLED','silent-immediate-enable')
    is_login_redirect(silent[0].get('/checkout'),'silent-old-checkout-stale','/checkout')
    is_login_redirect(silent[1].post('/cart/items',{}),'silent-old-write-stale-before-csrf')
    check('all-status-actions-preserve-original-business-data',all(baseline_business[t]==snapshot()[t] for t in TABLES if t!='store_user'))
    out,_,_=login(cl,8080,name='fresh-final-alice');assert_page(out,303,'fresh-final-alice');order_list(cl,'final-alice-orders-preserved')
    browser('main',{'admin':admin.cookie(8081)},dict(alice_order=alice_seed['orderNo'],empty_customer=empty_customer))
    fixture('UPDATE store_user SET updated_at=DATE_ADD(CURRENT_TIMESTAMP(6),INTERVAL 1 HOUR) WHERE id=3;','root-native-disabled-target-future-stamp')
    native_probe()
    dashboard(admin,'final-main-dashboard')
    final=snapshot();save(EV/'database-main-final.json',json.dumps(final,indent=2))
    check('final-status-only-phase-preserves-six-business-tables',all(baseline_business[t]==final[t] for t in TABLES if t!='store_user'))
    alternate_dashboard_scenarios(admin_process)
    aggregate_browser()
    check('alternate-scenarios-preserve-main-data',snapshot()==final)
    check('runtime-inputs-stable',all(hashlib.sha256((REPO/line.split('  ',1)[1]).read_bytes()).hexdigest()==line.split('  ',1)[0] for line in manifest.splitlines()))
    check('assets-and-packaged-images-unchanged',static_manifest()==statics)
    check('protected-user-and-sql-still-unmodified',not git('diff','--name-only',BASELINE+'..'+TESTED,'--','csucampuscraft-user','database').strip())
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
    result['finished_at_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();result['finished_at_local']=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
    save(EV/'result.json',json.dumps(result,ensure_ascii=False,indent=2))
    print('RESULT '+str(EV/'result.json'),flush=True)
if result['overall']!='PASS':raise SystemExit(1)
