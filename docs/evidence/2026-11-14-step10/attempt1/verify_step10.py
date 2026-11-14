"""STEP10 isolated verification; external tools only, no repository business mutation."""
from pathlib import Path
from html.parser import HTMLParser
import os,sys,re,json,time,socket,secrets,hashlib,subprocess,datetime,traceback,urllib.request,urllib.error,urllib.parse,http.cookiejar,zipfile,struct,gzip
REPO=Path('D:/Github Projects/CSUCampusCraft')
HERE=Path(__file__).resolve().parent
RUNTIME=Path('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies')
GIT=Path('C:/Program Files/Git/cmd/git.exe')
JAVA=Path('C:/Users/Starmetor/.jdks/ms-21.0.12.1/bin/java.exe')
MYSQL=Path('D:/MySQL/bin')
BASELINE='dc2033da0ee52eb478999031c4f6838d6434d70b'
TESTED=os.environ.get('STEP10_TESTED_CODE_SHA','')
if not re.fullmatch(r'[0-9a-f]{40}',TESTED):raise SystemExit('STEP10_TESTED_CODE_SHA must be exact 40-character implementation SHA')
RUN=sys.argv[1] if len(sys.argv)>1 else ''
if not re.fullmatch(r'attempt[1-9][0-9]*',RUN):raise SystemExit('Use a fresh attemptN')
BASE=HERE/'runtime'/RUN;EV=HERE/'evidence'/RUN
BASE.mkdir(parents=True,exist_ok=False);EV.mkdir(parents=True,exist_ok=False)
FLAG=subprocess.CREATE_NO_WINDOW
result={'date':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'baseline_git_sha':BASELINE,'tested_code_sha':TESTED,'requested_evidence_batch':'2026-11-14-step10','timestamp_policy':'actual system clock in Asia/Shanghai','checks':{},'scope':'STEP10 simulated payments and pending cancellation; no real payment, shipment, concurrency or injected failure'}
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
        audited=method=='POST' or path=='/checkout' or path.startswith('/orders')
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
    query="".join("SELECT '__STEP10_"+t+"__';SELECT COUNT(*) FROM "+t+";SELECT * FROM "+t+" ORDER BY id;" for t in TABLES)
    data=sql(query,'csucampuscraft').stdout;out={}
    for i,t in enumerate(TABLES):
        marker=('__STEP10_'+t+'__').encode();start=data.index(marker)+len(marker)
        start+=2 if data[start:start+2]==b'\r\n' else 1
        end=data.index(('__STEP10_'+TABLES[i+1]+'__').encode(),start) if i+1<len(TABLES) else len(data)
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

def action(cl,order_no,kind,name,status=303,result_value='SUCCESS',expected='NOOP',uid=1,csrf='valid',extra=None):
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

def native_probe(pay_no,cancel_no):
    extracted=BASE/'native-probe';classes=extracted/'classes';libs=extracted/'lib';classes.mkdir(parents=True);libs.mkdir()
    with zipfile.ZipFile(REPO/'csucampuscraft-user/target/csucampuscraft-user-0.0.1-SNAPSHOT.jar') as z:
        for n in z.namelist():
            if n.startswith('BOOT-INF/classes/') and not n.endswith('/'):
                p=classes/n[len('BOOT-INF/classes/'):];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
            elif n.startswith('BOOT-INF/lib/') and n.endswith('.jar'):(libs/Path(n).name).write_bytes(z.read(n))
    cp=str(classes)+';'+str(libs/'*')+';'+str(extracted)
    p=command([JAVA.parent/'javac.exe','-cp',cp,'-d',extracted,HERE/'NativePaymentProbe.java'],timeout=45)
    save(EV/'native-compile.log',p.stdout.decode('utf-8',errors='replace')+p.stderr.decode('utf-8',errors='replace'));check('native-compile',p.returncode==0)
    e=start_env();e.update(STEP10_NATIVE_USER_ID='2',STEP10_NATIVE_PAY_ORDER_NO=pay_no,STEP10_NATIVE_CANCEL_ORDER_NO=cancel_no)
    before=snapshot();a=state();p=command([JAVA,'-cp',cp,'org.csucampuscraft.storefront.payment.NativePaymentProbe','--live'],env=e,timeout=100);after=snapshot();b=state()
    text=p.stdout.decode('utf-8',errors='replace');save(EV/'native-probe.log',text+p.stderr.decode('utf-8',errors='replace'));check('native-exit',p.returncode==0)
    native=json.loads(text.strip().splitlines()[-1]);check('native-PASS',native['overall']=='PASS');result['native_checks']=native['checks']
    snapshot_pair('native-payment-and-cancel',before,a,after,b,transport='native actual Service, not HTTP',native_pay_no=pay_no,native_cancel_no=cancel_no)
    check('native-only-two-orders-changed',{int(x['id']) for x in deltas(a,b)['sales_order']}=={own_order(pay_no,a)['id'],own_order(cancel_no,a)['id']})
    check('native-snapshots-cart-unrelated-tables-unchanged',all(before[t]==after[t] for t in ['store_user','category','product_image','cart_item','sales_order_item']))
    pay=own_order(pay_no,b);cancelled=own_order(cancel_no,b)
    check('native-paid-and-cancelled',pay['status']=='PAID' and pay['paymentMethod']=='MOCK' and cancelled['status']=='CANCELLED')
    quantities={x['productId']:x['quantity'] for x in a['sales_order_item'].values() if x['orderId']==cancelled['id']}
    check('native-only-cancel-products-changed',{int(x['id']) for x in deltas(a,b)['product']}==set(quantities))
    for pid,q in quantities.items():
        old=a['product'][str(pid)];now=b['product'][str(pid)]
        check('native-refund-stock-version-'+str(pid),now['stock']==old['stock']+q and now['version']==old['version']+1 and all(now[k]==old[k] for k in old if k not in {'stock','version','updatedAt'}))
    record('native-action-observations.jsonl',dict(pay_order=pay,cancel_order=cancelled,native_not_http=True,shipping_raw_recorded=False))

def browser(cookies,browser_orders,fixed):
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
                    for node in dom.all(lambda n:n.tag=='input' and n.a.get('name') in ['_csrf','confirmationToken']):
                        if node.a.get('value'):secret_values.append(node.a['value'])
                    http_no+=1;redacted=scrub(text).encode();digest=hashlib.sha256(redacted).hexdigest();filename='bodies/'+digest[:24]+'.body.gz'
                    if not (EV/filename).exists():(EV/filename).parent.mkdir(exist_ok=True);(EV/filename).write_bytes(gzip.compress(redacted,mtime=0))
                    record('http.jsonl',dict(sequence=http_no,request_id=obj['id'],method=meta['method'],path=meta['path'],port=8080,status=obj['status'],content_type=obj['content_type'],location=obj.get('location'),cookie_values_recorded=False,form_fields=meta.get('form_fields'),result_value=meta.get('result_value'),body_file=filename,body_encoding='gzip',body_available=obj['body_available'],redacted_body_sha256=digest,redacted=True,transport='Actual browser request, continued after before-snapshot; response separately captured'))
                    after=snapshot();b=state()
                    snapshot_pair('browser-'+obj['id'],meta['before'],meta['state'],after,b,http_sequence=http_no,path=meta['path'],status=obj['status'],automatic_audit=True,transport='real browser')
                    if meta['method']=='GET' or obj['status']!=303:check('browser-read-or-reject-zero-write-'+obj['id'],meta['before']==after)
                    else:
                        match=re.fullmatch('/orders/([^/]+)/(payment|cancel)',meta['path']);check('browser-action-route-'+obj['id'],match is not None)
                        no,kind=match.groups();old=own_order(no,meta['state'])
                        expected='PAID' if kind=='payment' and meta.get('result_value')=='SUCCESS' and old['status']=='PENDING_PAYMENT' else 'CANCELLED' if kind=='cancel' and old['status']=='PENDING_PAYMENT' else 'NOOP'
                        verify_action(obj['id'],meta['before'],meta['state'],after,b,no,expected,transport='real browser',http_sequence=http_no)
                    completed.append(obj['id'])
                else:raise RuntimeError('Unknown audit operation')
                self.send_response(200);self.end_headers();self.wfile.write(b'{}')
            except Exception as error:
                failures.append(scrub(str(error)));self.send_response(500);self.end_headers();self.wfile.write(b'{"error":"audit failure"}')
    service=HTTPServer(('127.0.0.1',0),Control);thread=Thread(target=service.serve_forever,daemon=True);thread.start()
    e=start_env();e.update(STEP10_BROWSER_OUT=str(EV/'browser'),STEP10_BROWSER_COOKIES=json.dumps(cookies),STEP10_BROWSER_ORDERS=json.dumps(browser_orders),STEP10_BROWSER_FIXED=json.dumps(fixed),STEP10_BROWSER_CONTROL='http://127.0.0.1:'+str(service.server_port),STEP10_BROWSER_CONTROL_TOKEN=control_token)
    try:
        p=command([RUNTIME/'node/bin/node.exe',HERE/'verify_browser.cjs'],env=e,timeout=240)
        save(EV/'browser.log',p.stdout.decode('utf-8',errors='replace')+p.stderr.decode('utf-8',errors='replace'));check('browser-exit',p.returncode==0)
        check('browser-audit-complete',not pending and not failures and len(completed)>0)
        br=json.loads((EV/'browser/result.json').read_text(encoding='utf-8'));check('browser-PASS',br['completed'] and br['overall']=='PASS')
        result['browser_checks']=len(br['checks']);result['screenshots']=len(br['screenshots']);result['browser_http_audits']=len(completed)
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
    report={'overall':'PASS' if not findings else 'FAIL','files_scanned':files,'gzip_decompressed_files':decompressed,'known_values_checked':len(tokens),'secret_values_recorded':False,'findings':findings,'shipping_redaction':'Receiver input/textarea and U08 data-shipping-value contents structurally redacted; SQL order state contains only per-field SHA; screenshots mask shipping; no request form values recorded.'}
    save(EV/'sensitive-scan.json',json.dumps(report,ensure_ascii=False,indent=2))
    if findings:result['overall']='FAIL';result['sensitive_scan_failed']=True

try:
    check('tested-code-head',git('rev-parse','HEAD').decode().strip()==TESTED)
    result['branch']=git('branch','--show-current').decode().strip();check('feature-branch',result['branch']=='feat/step10-payment')
    status=git('status','--short','--untracked-files=all').decode();save(EV/'git-input-status.txt',status);check('tested-worktree-clean',not status.strip())
    save(EV/'implementation-diff.patch',git('diff',BASELINE+'..'+TESTED,'--','csucampuscraft-user').decode('utf-8'))
    inputs=[]
    for app in ['csucampuscraft-user','csucampuscraft-admin']:
        inputs.append(REPO/app/'pom.xml');inputs.extend(p for p in (REPO/app/'src').rglob('*') if p.is_file())
    inputs.extend(p for d in ['database','assets','.mvn'] for p in (REPO/d).rglob('*') if p.is_file());inputs.extend([REPO/'mvnw',REPO/'mvnw.cmd'])
    manifest=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(REPO).as_posix()+'\n' for p in sorted(inputs,key=lambda x:x.relative_to(REPO).as_posix()))
    save(EV/'runtime-inputs.sha256',manifest);result['runtime_manifest_sha256']=hashlib.sha256(manifest.encode()).hexdigest();result['runtime_file_count']=len(inputs)
    for name in ['verify_step10.py','verify_browser.cjs','NativePaymentProbe.java']:save(EV/name,(HERE/name).read_text(encoding='utf-8-sig'))
    builddir=Path(os.environ.get('STEP10_BUILD_LOG_DIR',HERE.parent));exits=json.loads((builddir/'build-exits.json').read_text(encoding='utf-8-sig'))
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
    sql("GRANT UPDATE ON csucampuscraft.product TO 'csucampuscraft'@'127.0.0.1';")
    sql("GRANT INSERT,UPDATE ON csucampuscraft.sales_order TO 'csucampuscraft'@'127.0.0.1';")
    sql("GRANT INSERT ON csucampuscraft.sales_order_item TO 'csucampuscraft'@'127.0.0.1';")
    save(EV/'application-grants.txt',rows("SHOW GRANTS FOR 'csucampuscraft'@'127.0.0.1';",None))
    original=snapshot();save(EV/'database-original.json',json.dumps(original,indent=2));check('seed-counts',[original[t]['rows'] for t in TABLES]==[4,15,60,100,10,10,20])
    for port in [8080,8081]:
        with socket.socket() as s:s.bind(('127.0.0.1',port))
    user_process=launch('csucampuscraft-user',8080);launch('csucampuscraft-admin',8081)
    note=pid_by_sku('CSU-LMK-NOTE-01');gift=pid_by_sku('CSU-GRAD-BOX-01')
    cl=Client();bob=Client();admin=Client();guest=Client()
    for client,user,port in [(cl,'alice',8080),(bob,'bob',8080),(admin,'admin',8081)]:
        out,_,_=login(client,port,username=user,name='initial-'+user);assert_page(out,303,'login-'+user)
    assert_page(admin.get('/products',8081),200,'admin-same-private-db')
    clear_cart(cl,1,'clear-alice-seed');clear_cart(bob,2,'clear-bob-seed')
    pay=new_order(cl,'payment-85')
    no=pay['orderNo']
    is_login_redirect(guest.get('/orders/'+no+'/payment'),'guest-payment-page','/orders/'+no+'/payment')
    is_login_redirect(guest.post('/orders/'+no+'/payment',{'result':'SUCCESS'}),'guest-pay-before-csrf')
    is_login_redirect(guest.post('/orders/'+no+'/cancel',{}),'guest-cancel-before-csrf')
    payment_page(cl,no,'pending-payment-U09')
    for label,value in [('missing',False),('empty',''),('unknown','UNKNOWN'),('lowercase','success'),('duplicate',['SUCCESS','FAILURE'])]:
        action(cl,no,'payment','invalid-result-'+label,400,result_value=value)
    action(cl,no,'payment','missing-payment-csrf',403,csrf='missing',result_value='UNKNOWN')
    action(cl,no,'payment','wrong-payment-csrf',403,csrf='wrong')
    action(cl,no,'cancel','missing-cancel-csrf',403,csrf='missing')
    action(cl,no,'cancel','wrong-cancel-csrf',403,csrf='wrong')
    for kind in ['payment','cancel']:
        action(bob,no,kind,'foreign-'+kind,404,uid=2)
        action(cl,'UNKNOWN_STEP10_ORDER',kind,'unknown-'+kind,404)
    action(bob,no,'payment','foreign-invalid-result-still-404',404,result_value='UNKNOWN',uid=2)
    payment_page(bob,no,'foreign-U09-no-leak',404,uid=2)
    payment_page(cl,'UNKNOWN_STEP10_ORDER','unknown-U09-no-leak',404)
    # Price/name/cover/status changes are root fixtures, never claimed as admin business HTTP.
    saved=state()['product']
    fixture("UPDATE product SET name='STEP10当前商品变化',price=19.25,cover_image='images/step10-missing.svg',status='DRAFT',updated_at=updated_at WHERE id="+str(note)+';','root-after-order-current-product-changed')
    payment_page(cl,no,'U09-keeps-original-85-after-product-change')
    action(cl,no,'payment','pending-simulated-failure',303,result_value='FAILURE')
    paid,_=action(cl,no,'payment','first-success-uses-order-amount',303,expected='PAID',extra={'amount':'0.01','total':'0.01','payment_no':'CLIENT_FAKE','paid_at':'2000-01-01','user_id':'2'})
    receipt=(paid['paymentMethod'],paid['paymentNo'],paid['paidAt'])
    restore_products(saved)
    action(cl,no.lower(),'payment','paid-repeat-success-CI',303)
    current=own_order(no);check('first-receipt-and-time-retained',(current['paymentMethod'],current['paymentNo'],current['paidAt'])==receipt)
    action(cl,no,'payment','paid-failure-conflict',409,result_value='FAILURE')
    action(cl,no,'cancel','paid-cancel-conflict',409)
    payment_page(cl,no,'paid-payment-page-conflict',409)
    seeds={status:next(x for x in state()['sales_order'].values() if x['userId']==1 and x['status']==status) for status in ['SHIPPED','COMPLETED','CANCELLED']}
    for status in ['SHIPPED','COMPLETED']:
        seed=seeds[status];action(cl,seed['orderNo'],'payment',status+'-repeat-success-keeps-receipt',303)
        action(cl,seed['orderNo'],'payment',status+'-failure-conflict',409,result_value='FAILURE')
        action(cl,seed['orderNo'],'cancel',status+'-cancel-conflict',409)
    for value in ['SUCCESS','FAILURE']:action(cl,seeds['CANCELLED']['orderNo'],'payment','seed-cancelled-payment-'+value,409,result_value=value)
    # Cancellation never restores purchased items into a current cart, nor clears newly added items.
    cancel_order=new_order(cl,'cancel-two-lines')
    cancel_no=cancel_order['orderNo']
    extra=int(rows("SELECT id FROM product WHERE status='ON_SALE' AND stock>0 AND id NOT IN ("+str(note)+','+str(gift)+') ORDER BY id LIMIT 1;'))
    add(cl,extra,1,'new-unconfirmed-cart-before-cancel')
    before_cart=state()['cart_item']
    original_status=product(note)['status']
    fixture("UPDATE product SET status='DRAFT',updated_at=updated_at WHERE id="+str(note)+';','root-draft-before-refund')
    cancelled,_=action(cl,cancel_no,'cancel','cancel-two-lines-including-draft',303,expected='CANCELLED')
    check('draft-status-preserved-after-refund',product(note)['status']=='DRAFT')
    check('current-cart-quantity-and-version-preserved',state()['cart_item']==before_cart and quantity(1)==1)
    record('nonempty-cart-cancel.jsonl',dict(order_no=cancel_no,cart_before=before_cart,cart_after=state()['cart_item'],sum_quantity=1,no_purchased_items_added=True))
    fixture('UPDATE product SET status='+literal(original_status)+',updated_at=updated_at WHERE id='+str(note)+';','root-restore-only-controlled-status-after-refund')
    first_cancel=cancelled['cancelledAt'];action(cl,cancel_no.lower(),'cancel','repeat-cancel-no-second-refund',303)
    check('first-cancel-time-retained',own_order(cancel_no)['cancelledAt']==first_cancel)
    for value in ['SUCCESS','FAILURE']:action(cl,cancel_no,'payment','new-cancelled-payment-'+value,409,result_value=value)
    payment_page(cl,cancel_no,'cancelled-U09-conflict',409)
    gift_order=new_order(cl,'independent-two-gift-order',lines=[(gift,2)])
    gift_cancelled,_=action(cl,gift_order['orderNo'],'cancel','two-gift-independent-refund',303,expected='CANCELLED')
    action(cl,gift_order['orderNo'],'cancel','two-gift-repeat-no-extra-stock',303)
    # Boundaries reject before any refund; no mid-transaction fault injection is performed.
    overflow_order=new_order(cl,'overflow-refund-order')
    for label,pid,assignment in [('stock-max',note,'stock=2147483647'),('version-max',gift,'version=9223372036854775807')]:
        saved=state()['product']
        fixture('UPDATE product SET '+assignment+',updated_at=updated_at WHERE id='+str(pid)+';','root-refund-'+label)
        action(cl,overflow_order['orderNo'],'cancel','refund-'+label+'-zero-partial',409)
        restore_products(saved)
    action(cl,overflow_order['orderNo'],'cancel','refund-after-valid-boundary-restoration',303,expected='CANCELLED')
    # AuthFilter's invalidation remains ahead of CSRF and no-op actions.
    stamp=rows('SELECT CAST(updated_at AS CHAR) FROM store_user WHERE id=1;')
    fixture("UPDATE store_user SET status='DISABLED',updated_at=GREATEST(CURRENT_TIMESTAMP(6),updated_at+INTERVAL 1 MICROSECOND) WHERE id=1;",'disable-payment-owner')
    is_login_redirect(cl.post('/orders/'+no+'/payment',{'result':'SUCCESS'}),'disabled-before-csrf')
    fixture("UPDATE store_user SET status='ENABLED',updated_at=GREATEST(CURRENT_TIMESTAMP(6),updated_at+INTERVAL 1 MICROSECOND) WHERE id=1;",'reenable-payment-owner')
    is_login_redirect(cl.get('/orders/'+no),'old-session-does-not-revive','/orders/'+no)
    fixture('UPDATE store_user SET updated_at='+literal(stamp)+' WHERE id=1;','restore-controlled-auth-stamp')
    out,_,_=login(cl,8080,name='fresh-after-auth-change');assert_page(out,303,'fresh-after-auth-change')
    # Distinct browser orders per viewport; all clicks are real forms, captured before forwarding.
    browser_orders={}
    for width in [1366,1920]:
        browser_orders[str(width)]={'pay':new_order(cl,'browser-pay-'+str(width))['orderNo'],'cancel':new_order(cl,'browser-cancel-'+str(width))['orderNo']}
    add(cl,extra,1,'browser-current-cart-survives-actions')
    browser({'alice':cl.cookie(8080),'bob':bob.cookie(8080)},browser_orders,dict(paid=no,cancelled=cancel_no,shipped=seeds['SHIPPED']['orderNo']))
    # Native actions are separate from all HTTP action counts; both target orders were created by HTTP.
    native_pay=new_order(bob,'native-bob-pay',uid=2)
    native_cancel=new_order(bob,'native-bob-cancel',uid=2)
    native_probe(native_pay['orderNo'],native_cancel['orderNo'])
    final=snapshot();save(EV/'database-final.json',json.dumps(final,indent=2))
    check('users-categories-images-preserved',all(original[t]==final[t] for t in ['store_user','category','product_image']))
    check('runtime-inputs-stable',all(hashlib.sha256((REPO/line.split('  ',1)[1]).read_bytes()).hexdigest()==line.split('  ',1)[0] for line in manifest.splitlines()))
    check('assets-and-packaged-images-unchanged',static_manifest()==statics)
    # Preserve every STEP09 Java byte: this is checked against the exact source baseline, not old results.
    for line in git('ls-tree','-r','--name-only',BASELINE,'--','csucampuscraft-user/src/main/java/org/csucampuscraft/storefront/order','csucampuscraft-user/src/main/java/org/csucampuscraft/storefront/checkout').decode('utf-8').splitlines():
        old=git('show',BASELINE+':'+line).replace(b'\r\n',b'\n');now=(REPO/line).read_bytes().replace(b'\r\n',b'\n')
        check('step09-java-unchanged-'+Path(line).name,old==now)
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
