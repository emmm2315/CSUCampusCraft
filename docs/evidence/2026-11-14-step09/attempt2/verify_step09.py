"""STEP09 isolated verification; external tools only, no repository business mutation."""
from pathlib import Path
from html.parser import HTMLParser
import os,sys,re,json,time,socket,secrets,hashlib,subprocess,datetime,traceback,urllib.request,urllib.error,urllib.parse,http.cookiejar,zipfile,struct,gzip
REPO=Path('D:/Github Projects/CSUCampusCraft')
HERE=Path(__file__).resolve().parent
RUNTIME=Path('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies')
GIT=Path('C:/Program Files/Git/cmd/git.exe')
JAVA=Path('C:/Users/Starmetor/.jdks/ms-21.0.12.1/bin/java.exe')
MYSQL=Path('D:/MySQL/bin')
BASELINE='e3bfb2fe0c1087f915d838d0dff50ae0be3db0bf'
TESTED=os.environ.get('STEP09_TESTED_CODE_SHA','')
if not re.fullmatch(r'[0-9a-f]{40}',TESTED):raise SystemExit('STEP09_TESTED_CODE_SHA must be exact 40-character implementation SHA')
RUN=sys.argv[1] if len(sys.argv)>1 else ''
if not re.fullmatch(r'attempt[1-9][0-9]*',RUN):raise SystemExit('Use a fresh attemptN')
BASE=HERE/'runtime'/RUN;EV=HERE/'evidence'/RUN
BASE.mkdir(parents=True,exist_ok=False);EV.mkdir(parents=True,exist_ok=False)
FLAG=subprocess.CREATE_NO_WINDOW
result={'date':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'baseline_git_sha':BASELINE,'tested_code_sha':TESTED,'requested_evidence_batch':'2026-11-14-step09','timestamp_policy':'actual system clock in Asia/Shanghai','checks':{},'scope':'STEP09 atomic orders and own-order reads; payment/cancel/shipping STEP10/11, concurrent and injected-failure acceptance STEP13'}
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
    query="".join("SELECT '__STEP09_"+t+"__';SELECT COUNT(*) FROM "+t+";SELECT * FROM "+t+" ORDER BY id;" for t in TABLES)
    data=sql(query,'csucampuscraft').stdout;out={}
    for i,t in enumerate(TABLES):
        marker=('__STEP09_'+t+'__').encode();start=data.index(marker)+len(marker)
        start+=2 if data[start:start+2]==b'\r\n' else 1
        end=data.index(('__STEP09_'+TABLES[i+1]+'__').encode(),start) if i+1<len(TABLES) else len(data)
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
      'product':"SELECT JSON_OBJECT('id',id,'categoryId',category_id,'sku',sku,'name',name,'coverImage',cover_image,'summary',summary,'description',description,'price',CAST(price AS CHAR),'stock',stock,'status',status,'sortOrder',sort_order,'version',version,'createdAt',created_at,'updatedAt',updated_at) FROM product ORDER BY id;",
      'sales_order':"SELECT JSON_OBJECT('id',id,'orderNo',order_no,'userId',user_id,'status',status,'totalAmount',CAST(total_amount AS CHAR),'receiverNameSha256',SHA2(receiver_name,256),'receiverPhoneSha256',SHA2(receiver_phone,256),'receiverAddressSha256',SHA2(receiver_address,256),'createdAt',created_at,'updatedAt',updated_at,'paymentMethod',payment_method,'paymentNo',payment_no,'paidAt',paid_at,'cancelledAt',cancelled_at,'shippedAt',shipped_at,'completedAt',completed_at) FROM sales_order ORDER BY id;",
      'sales_order_item':"SELECT JSON_OBJECT('id',id,'orderId',order_id,'productId',product_id,'skuSnapshot',sku_snapshot,'productNameSnapshot',product_name_snapshot,'coverImageSnapshot',cover_image_snapshot,'unitPrice',CAST(unit_price AS CHAR),'quantity',quantity,'lineAmount',CAST(line_amount AS CHAR)) FROM sales_order_item ORDER BY id;"}
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
def static_manifest():
    out={}
    for p in sorted((REPO/'assets').rglob('*')):
        if p.is_file():out['assets/'+p.relative_to(REPO/'assets').as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    for app in ['csucampuscraft-user','csucampuscraft-admin']:
        with zipfile.ZipFile(REPO/app/'target'/f'{app}-0.0.1-SNAPSHOT.jar') as z:
            for n in z.namelist():
                if n.startswith('BOOT-INF/classes/static/images/') and not n.endswith('/'):out[app+'/'+n]=hashlib.sha256(z.read(n)).hexdigest()
    return out

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
    check(name+'-no-payment-cancel-actions',not root.find(lambda n:n.tag in ['a','form'] and re.search('/(?:payment|cancel)(?:$|[/?])',n.a.get('href','')+n.a.get('action',''))))
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

def native_probe():
    extracted=BASE/'native-probe';classes=extracted/'classes';libs=extracted/'lib';classes.mkdir(parents=True);libs.mkdir()
    with zipfile.ZipFile(REPO/'csucampuscraft-user/target/csucampuscraft-user-0.0.1-SNAPSHOT.jar') as z:
        for n in z.namelist():
            if n.startswith('BOOT-INF/classes/') and not n.endswith('/'):
                p=classes/n[len('BOOT-INF/classes/'):];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
            elif n.startswith('BOOT-INF/lib/') and n.endswith('.jar'):(libs/Path(n).name).write_bytes(z.read(n))
    cp=str(classes)+';'+str(libs/'*')+';'+str(extracted)
    p=command([JAVA.parent/'javac.exe','-cp',cp,'-d',extracted,HERE/'NativeOrderWriteProbe.java'],timeout=45)
    save(EV/'native-compile.log',p.stdout.decode('utf-8',errors='replace')+p.stderr.decode('utf-8',errors='replace'));check('native-probe-compile',p.returncode==0)
    native_env=start_env();native_env['STEP09_NATIVE_USER_ID']='2'
    before=snapshot();a=state();p=command([JAVA,'-cp',cp,'org.csucampuscraft.storefront.checkout.NativeOrderWriteProbe','--live'],env=native_env,timeout=100);after=snapshot();b=state()
    output=p.stdout.decode('utf-8',errors='replace');save(EV/'native-probe.log',output+p.stderr.decode('utf-8',errors='replace'))
    check('native-probe',p.returncode==0 and '"overall":"PASS"' in output)
    native=json.loads(output.strip().splitlines()[-1]);result['native_checks']=native['checks']
    snapshot_pair('native-real-service-submit',before,a,after,b,transport='actual Service native probe, not HTTP')
    verify_order_write('native-real-service-submit',before,a,after,b,2,order_no=native['orderNo'])

def browser(cookies,cases):
    from http.server import BaseHTTPRequestHandler,HTTPServer
    from threading import Thread
    import base64
    db=state()
    for case in cases:
        if case['kind']=='U07':
            q=urllib.parse.parse_qs(urllib.parse.urlsplit(case['path']).query)
            no=q.get('orderNo',[''])[0].strip();wanted=q.get('status',['ALL'])[0];page=max(1,int(q.get('page',[1])[0]));size=int(q.get('size',[10])[0])
            matches=sorted((x for x in db['sales_order'].values() if x['userId']==case['uid'] and (not no or x['orderNo'].lower()==no.lower()) and (wanted=='ALL' or x['status']==wanted)),key=lambda x:(x['createdAt'],x['id']),reverse=True)
            case['expectedList']={'total':len(matches),'page':page,'size':size,'ids':[x['id'] for x in matches[(page-1)*size:page*size]]}
        elif case['kind']=='U08':
            order=next(x for x in db['sales_order'].values() if x['orderNo']==case['orderNo'] and x['userId']==case['uid'])
            case['expectedOrder']=order
            case['expectedItems']=sorted((x for x in db['sales_order_item'].values() if x['orderId']==order['id']),key=lambda x:x['id'])
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
                    if not (EV/filename).exists():(EV/filename).parent.mkdir(exist_ok=True);(EV/filename).write_bytes(gzip.compress(redacted,mtime=0))
                    record('http.jsonl',dict(sequence=http_no,method=meta['method'],path=obj.get('response_path',meta['path']),requested_path=meta['path'],redirect_chain=obj.get('redirect_chain',[]),port=8080,status=obj['status'],content_type=obj['content_type'],location=obj.get('location'),cookie_values_recorded=False,form_fields=meta.get('form_fields'),body_file=filename,body_encoding='gzip',redacted_body_sha256=digest,redacted=True,transport='real Playwright navigation'))
                    after=snapshot();snapshot_pair('browser-'+obj['id'],meta['before'],meta['state'],after,state(),http_sequence=http_no,path=meta['path'],status=obj['status'],automatic_audit=True)
                    check('browser-read-or-reject-zero-write-'+obj['id'],meta['before']==after);completed.append(obj['id'])
                else:raise RuntimeError('Unknown browser audit operation')
                self.send_response(200);self.end_headers();self.wfile.write(b'{}')
            except Exception as ex:
                failures.append(scrub(str(ex)));self.send_response(500);self.end_headers();self.wfile.write(b'{"error":"audit failure"}')
    service=HTTPServer(('127.0.0.1',0),Control);thread=Thread(target=service.serve_forever,daemon=True);thread.start()
    e=start_env();e.update(STEP09_BROWSER_OUT=str(EV/'browser'),STEP09_BROWSER_CASES=json.dumps(cases,ensure_ascii=False),STEP09_BROWSER_COOKIES=json.dumps(cookies),STEP09_BROWSER_CONTROL='http://127.0.0.1:'+str(service.server_port),STEP09_BROWSER_CONTROL_TOKEN=control_token)
    try:
        p=command([RUNTIME/'node/bin/node.exe',HERE/'verify_browser.cjs'],env=e,timeout=180)
        save(EV/'browser.log',p.stdout.decode('utf-8',errors='replace')+p.stderr.decode('utf-8',errors='replace'));check('browser-exit',p.returncode==0)
        check('browser-audit-complete',not pending and not failures and completed)
        br=json.loads((EV/'browser/result.json').read_text(encoding='utf-8'));check('browser-result',br.get('completed') and br['overall']=='PASS')
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
    result['branch']=git('branch','--show-current').decode().strip();check('feature-branch',result['branch']=='feat/step09-orders')
    status=git('status','--short','--untracked-files=all').decode();save(EV/'git-input-status.txt',status);check('tested-worktree-clean',not status.strip())
    save(EV/'implementation-diff.patch',git('diff',BASELINE+'..'+TESTED,'--','csucampuscraft-user').decode('utf-8'))
    inputs=[]
    for app in ['csucampuscraft-user','csucampuscraft-admin']:
        inputs.append(REPO/app/'pom.xml');inputs.extend(p for p in (REPO/app/'src').rglob('*') if p.is_file())
    inputs.extend(p for d in ['database','assets','.mvn'] for p in (REPO/d).rglob('*') if p.is_file());inputs.extend([REPO/'mvnw',REPO/'mvnw.cmd'])
    manifest=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(REPO).as_posix()+'\n' for p in sorted(inputs,key=lambda x:x.relative_to(REPO).as_posix()))
    save(EV/'runtime-inputs.sha256',manifest);result['runtime_manifest_sha256']=hashlib.sha256(manifest.encode()).hexdigest();result['runtime_file_count']=len(inputs)
    for name in ['verify_step09.py','verify_browser.cjs','NativeOrderWriteProbe.java']:save(EV/name,(HERE/name).read_text(encoding='utf-8-sig'))
    builddir=Path(os.environ.get('STEP09_BUILD_LOG_DIR',HERE.parent));exits=json.loads((builddir/'build-exits.json').read_text(encoding='utf-8-sig'))
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
    sql("GRANT INSERT ON csucampuscraft.sales_order TO 'csucampuscraft'@'127.0.0.1';")
    sql("GRANT INSERT ON csucampuscraft.sales_order_item TO 'csucampuscraft'@'127.0.0.1';")
    save(EV/'application-grants.txt',rows("SHOW GRANTS FOR 'csucampuscraft'@'127.0.0.1';",None))
    original=snapshot();save(EV/'database-original.json',json.dumps(original,indent=2));check('seed-counts',[original[t]['rows'] for t in TABLES]==[4,15,60,100,10,10,20])
    for port in [8080,8081]:
        with socket.socket() as s:s.bind(('127.0.0.1',port))
    user_process=launch('csucampuscraft-user',8080);launch('csucampuscraft-admin',8081)
    note=pid_by_sku('CSU-LMK-NOTE-01');gift=pid_by_sku('CSU-GRAD-BOX-01')
    cl=Client();second=Client();bob=Client();admin=Client();guest=Client()
    is_login_redirect(guest.get('/orders'),'guest-order-list','/orders')
    is_login_redirect(guest.get('/checkout'),'guest-checkout','/checkout')
    is_login_redirect(guest.post('/orders',{}),'guest-order-post-before-csrf')
    for client,user,port in [(cl,'alice',8080),(second,'alice',8080),(bob,'bob',8080),(admin,'admin',8081)]:
        out,_,_=login(client,port,username=user,name='initial-'+user+'-'+str(port));assert_page(out,303,'login-'+user)
    assert_page(admin.get('/products',8081),200,'admin-shared-database-ready')
    assert_page(admin.get('/orders',8081),404,'admin-order-page-not-yet-implemented')
    record('scope-boundaries.jsonl',dict(name='historical snapshots on admin',admin_order_detail_implemented=False,admin_code_changed=False,current_proof='user U08 plus independent SQL snapshots',deferred_step='STEP11',both_sides_http_claimed=False))
    checkout(cl,'invalid-seed-cart',409)
    clear_cart(cl,1,'clear-alice-seed-via-http');clear_cart(bob,2,'clear-bob-seed-via-http')
    checkout(cl,'empty-cart',409)
    prepare_eighty_five(cl,'main-85-cart')
    check('main-initial-stock-10-12',product(note)['stock']==10 and product(gift)['stock']==12)
    r=checkout(cl,'main-85-confirm',total='85.00')
    # Invalid shipping never consumes the valid confirmation or creates any part of an order.
    for field,limit in [('receiverName',50),('receiverPhone',30),('receiverAddress',255)]:
        for label,value in [('missing',None),('empty',''),('blank',' \u3000\t '),('too-long','测'*(limit+1)),('astral-too-long','😀'*(limit+1))]:
            fields=shipping();fields.pop(field)
            if value is not None:fields[field]=value
            out,_=submit(cl,r,'invalid-'+field+'-'+label,400,fields=fields)
            check(field+'-'+label+'-same-token-retained',confirmation(out)==confirmation(r))
            check(field+'-'+label+'-field-feedback',out[3].find(lambda n:n.a.get('id')==field+'-error') is not None)
    payload='<script>alert(1)</script>'
    out,_=submit(cl,r,'script-fields-text-only',400,fields=shipping(receiverName=payload,receiverPhone='',receiverAddress=payload))
    check('script-input-literal',out[3].find(lambda n:n.a.get('id')=='receiverName').a.get('value')==payload)
    check('script-textarea-literal',out[3].find(lambda n:n.a.get('id')=='receiverAddress').text()==payload)
    check('script-does-not-create-inline-element',not out[3].find(lambda n:n.tag=='script' and not n.a.get('src')))
    record('field-boundaries.jsonl',dict(name='three shipping limits and script text',limits=[50,30,255],missing_empty_blank_max_plus_one_astral_max_plus_one_status=400,token_retained=True,input_and_textarea_literal=True,inline_script_injected=False,raw_shipping_recorded=False))
    submit(cl,r,'missing-csrf-first',403,csrf='missing',submitted_token='bad-confirmation')
    submit(cl,r,'wrong-csrf-first',403,csrf='wrong',fields={})
    main_fields=shipping(receiverName=' \u3000'+shipping()['receiverName']+'\u3000 ')
    success,main_order=submit(cl,r,'main-real-85-submit',303,fields=main_fields,extra={'total':'0.01','amount':'0.01','unitPrice':'0.01','userId':'2','productId':'999999'})
    check('main-stock-8-11',product(note)['stock']==8 and product(gift)['stock']==11)
    check('main-two-items-and-85',len([x for x in state()['sales_order_item'].values() if x['orderId']==main_order['id']])==2 and main_order['totalAmount']=='85.00')
    main_no=main_order['orderNo'];detail(cl,main_no,'main-303-destination',uid=1)
    check('main-cleared-cart-and-badge-zero',not cartrows(1));badge(cl.get('/'),1,'main-home-badge-zero')
    submit(cl,r,'repeat-used-confirmation-no-second-order',409)
    checkout(cl,'empty-after-success',409)

    # Owner-only reads, exact case-insensitive number matching, state and stable pagination.
    for label,params in [('default',{}),('size-one',{'size':1}),('second-page',{'size':1,'page':2}),('size-max',{'size':50}),('page-zero',{'page':0}),('page-negative',{'page':-3}),('beyond',{'page':10000,'size':1}),('overflow-safe-empty',{'page':9223372036854775807,'size':50}),('exact',{'orderNo':main_no}),('case-insensitive',{'orderNo':main_no.lower()}),('trim-number',{'orderNo':' '+main_no+' '}),('partial-not-match',{'orderNo':main_no[:-1]}),('unknown-no-results',{'orderNo':'UNKNOWN_STEP09_ORDER'}),('literal-wildcards',{'orderNo':"%_\\'"})]:
        order_list(cl,'list-'+label,params)
    for status in ['ALL','PENDING_PAYMENT','PAID','SHIPPED','COMPLETED','CANCELLED']:
        order_list(cl,'list-status-'+status,{'status':status,'size':1})
    order_list(bob,'bob-own-list',uid=2)
    for label,params in [('long-number',{'orderNo':'X'*41}),('invalid-status',{'status':'UNKNOWN'}),('empty-status',{'status':''}),('size-zero',{'size':0}),('size-51',{'size':51}),('size-text',{'size':'x'}),('page-text',{'page':'x'}),('page-decimal',{'page':'1.5'}),('page-overlong',{'page':'9'*30}),('duplicate-status',{'status':['ALL','PAID']})]:
        order_list(cl,'list-invalid-'+label,params,status=400)
    detail(cl,main_no.lower(),'detail-case-insensitive',uid=1)
    detail(bob,main_no,'foreign-order-hidden-404',status=404,uid=2)
    detail(cl,'UNKNOWN_STEP09_ORDER','unknown-order-hidden-404',status=404)
    paid_seed=next(x for x in state()['sales_order'].values() if x['userId']==1 and x['status']=='PAID')
    detail(cl,paid_seed['orderNo'],'historical-paid-read-only')

    # Product edits after purchase must not alter persisted or rendered transaction snapshots.
    saved=state()['product'];before_history=snapshot();safe_before=state()
    fixture("UPDATE product SET name='STEP09后续商品名称',price=19.25,cover_image='images/step09-missing-cover.svg',status='DRAFT',version=version+1 WHERE id="+str(note)+';','after-order-product-name-price-cover-status')
    changed=snapshot();safe_after=state()
    check('historical-order-and-line-full-table-unchanged',before_history['sales_order']==changed['sales_order'] and before_history['sales_order_item']==changed['sales_order_item'])
    check('historical-safe-snapshots-unchanged',safe_before['sales_order']==safe_after['sales_order'] and safe_before['sales_order_item']==safe_after['sales_order_item'])
    detail(cl,main_no,'immutable-user-detail-after-product-change')
    record('snapshot-immutability.jsonl',dict(order_no=main_no,before_order_table=before_history['sales_order'],after_order_table=changed['sales_order'],before_line_table=before_history['sales_order_item'],after_line_table=changed['sales_order_item'],user_detail_unchanged=True,product_fixture='root SQL name/price/cover/status change',admin_http_deferred='STEP11'))
    restore_products(saved)

    # Every stale/refused submission is checked against all seven tables.
    prepare_eighty_five(cl,'rejection-matrix-cart')
    a=checkout(cl,'replace-A');b=checkout(cl,'replace-B')
    check('fresh-token-different',confirmation(a)!=confirmation(b))
    submit(cl,a,'replaced-A-rejected',409);submit(cl,b,'old-A-invalidates-current-B-policy',409)
    for label,submitted in [('missing',False),('bad','not-a-confirmation')]:
        r=checkout(cl,'before-'+label+'-token');submit(cl,r,label+'-confirmation',409,submitted_token=submitted)
    a=checkout(cl,'owner-session-confirm');b=checkout(second,'other-session-confirm')
    submit(second,b,'same-user-foreign-session-token',409,submitted_token=confirmation(a))
    out,_=submit(cl,a,'owner-confirmation-survives-other-session',400,fields=shipping(receiverPhone=''))
    check('other-session-does-not-consume-owner-token',confirmation(out)==confirmation(a))
    add(bob,gift,1,'bob-own-gift',uid=2);b=checkout(bob,'bob-confirmation',uid=2)
    submit(bob,b,'other-user-token-rejected',409,submitted_token=confirmation(a),uid=2)
    clear_cart(bob,2,'clear-bob-after-token-matrix')
    r=checkout(cl,'before-quantity-change');change(second,item_for(note),3,'second-session-quantity-change')
    submit(cl,r,'old-quantity-rejected',409);check('changed-quantity-remains',item_for(note)['quantity']==3)
    change(second,item_for(note),2,'restore-quantity')
    r=checkout(cl,'before-quantity-version-roundtrip');change(second,item_for(note),3,'roundtrip-up');change(second,item_for(note),2,'roundtrip-down')
    submit(cl,r,'item-version-changed-even-same-quantity',409)
    r=checkout(cl,'before-same-value-change');change(second,item_for(note),2,'same-value-change')
    out,_=submit(cl,r,'same-value-does-not-stale-confirmation',400,fields=shipping(receiverName=''));check('same-value-keeps-token',confirmation(out)==confirmation(r))
    extra=int(rows("SELECT id FROM product WHERE status='ON_SALE' AND stock>1 AND id NOT IN ("+str(note)+','+str(gift)+') ORDER BY id LIMIT 1;'))
    r=checkout(cl,'before-extra-line');add(second,extra,1,'second-session-add-line');submit(cl,r,'new-line-stales-confirmation',409)
    check('new-unconfirmed-line-remains',item_for(extra) is not None);remove(second,item_for(extra),'remove-extra-line')
    r=checkout(cl,'before-removed-line');remove(second,item_for(gift),'second-session-remove-line');submit(cl,r,'removed-line-stales-confirmation',409);add(second,gift,1,'restore-gift-line')
    for label,update in [('price','price=19.25'),('draft',"status='DRAFT'"),('sold-out','stock=0'),('over-stock','stock=1'),('max-product-version','version=9223372036854775807')]:
        saved=state()['product'];r=checkout(cl,'before-'+label)
        fixture('UPDATE product SET '+update+',updated_at=updated_at WHERE id='+str(note)+';','root-'+label)
        submit(cl,r,'reject-'+label,409)
        check(label+'-cart-remains',len(cartrows())==2)
        restore_products(saved)
    for label,update in [('line-overflow','price=9999999999.99'),('aggregate-overflow','price=6000000000.00')]:
        saved=state()['product'];r=checkout(cl,'before-'+label)
        if label=='aggregate-overflow':
            fixture('UPDATE product SET '+update+',updated_at=updated_at WHERE id IN ('+str(note)+','+str(gift)+');','root-'+label)
        else:fixture('UPDATE product SET '+update+',updated_at=updated_at WHERE id='+str(note)+';','root-'+label)
        submit(cl,r,'reject-'+label,409);checkout(cl,label+'-cannot-create-confirmation',409)
        restore_products(saved)

    # Existing identity and TTL rules remain effective around the new write entry.
    r=checkout(cl,'before-disable');stamp=rows('SELECT CAST(updated_at AS CHAR) FROM store_user WHERE id=1;')
    fixture("UPDATE store_user SET status='DISABLED',updated_at=GREATEST(CURRENT_TIMESTAMP(6),updated_at+INTERVAL 1 MICROSECOND) WHERE id=1;",'disable-confirmation-owner')
    is_login_redirect(cl.post('/orders',{}),'disabled-before-csrf-token')
    fixture("UPDATE store_user SET status='ENABLED',updated_at=GREATEST(CURRENT_TIMESTAMP(6),updated_at+INTERVAL 1 MICROSECOND) WHERE id=1;",'reenable-confirmation-owner')
    is_login_redirect(cl.get('/orders'),'reenabled-old-session-not-revived','/orders')
    fixture('UPDATE store_user SET updated_at='+literal(stamp)+' WHERE id=1;','restore-controlled-auth-stamp')
    out,_,_=login(cl,8080,name='fresh-after-disable');assert_page(out,303,'fresh-after-disable')
    submit(cl,cl.get('/cart'),'disabled-old-confirmation-gone',409,submitted_token=confirmation(r))
    before=snapshot();stop(user_process);user_process=launch('csucampuscraft-user',8080,ttl='PT1S')
    cl=Client();out,_,_=login(cl,8080,name='short-ttl-login');assert_page(out,303,'short-ttl-login')
    r=checkout(cl,'short-ttl-confirm');time.sleep(1.2);submit(cl,r,'expired-real-service-confirmation',409)
    check('short-ttl-rejection-phase-zero-write',before==snapshot())
    stop(user_process);user_process=launch('csucampuscraft-user',8080)
    cl=Client();second=Client();bob=Client()
    for client,user in [(cl,'alice'),(second,'alice'),(bob,'bob')]:
        out,_,_=login(client,8080,username=user,name='default-'+user);assert_page(out,303,'default-login-'+user)
    # Real accepted all-field Unicode maxima, with server trimming and client price ignored.
    r=checkout(cl,'unicode-max-confirm',total='85.00')
    max_fields=shipping(receiverName=' \u3000'+'😀'*50+'\u3000 ',receiverPhone=' \u3000'+'😀'*30+'\u3000 ',receiverAddress=' \u3000'+'😀'*255+'\u3000 ')
    out,max_order=submit(cl,r,'all-three-codepoint-maxima-create-order',303,fields=max_fields,extra={'total':'9999999999.99'})
    detail(cl,max_order['orderNo'],'max-fields-persisted-safely')
    clear_cart(cl,1,'gift-only-clean-cart');add(cl,gift,2,'two-independent-gift-boxes')
    r=checkout(cl,'gift-only-98-confirm',total='98.00');out,gift_order=submit(cl,r,'gift-independent-sku-purchase',303)
    check('gift-only-has-one-independent-line',len([x for x in state()['sales_order_item'].values() if x['orderId']==gift_order['id']])==1)
    detail(cl,gift_order['orderNo'],'gift-only-order-detail')

    # New browser captures read the real orders; two actual failed form POSTs are independently audited.
    prepare_eighty_five(cl,'browser-cart')
    browser({'alice':cl.cookie(8080),'bob':bob.cookie(8080)},[
      {'name':'u07-own-orders','path':'/orders','account':'alice','kind':'U07','status':200,'uid':1,'badge':3},
      {'name':'u07-pending-filter','path':'/orders?status=PENDING_PAYMENT&size=1','account':'alice','kind':'U07','status':200,'uid':1,'badge':3},
      {'name':'u07-exact-number-ci','path':'/orders?orderNo='+main_no.lower(),'account':'alice','kind':'U07','status':200,'uid':1,'badge':3},
      {'name':'u07-empty-result','path':'/orders?orderNo=UNKNOWN_STEP09_ORDER','account':'alice','kind':'U07','status':200,'uid':1,'badge':3},
      {'name':'u07-outofrange','path':'/orders?page=10000&size=1','account':'alice','kind':'U07','status':200,'uid':1,'badge':3},
      {'name':'u08-created-85','path':'/orders/'+main_no,'account':'alice','kind':'U08','status':200,'uid':1,'badge':3,'orderNo':main_no},
      {'name':'u08-historical-paid-readonly','path':'/orders/'+paid_seed['orderNo'],'account':'alice','kind':'U08','status':200,'uid':1,'badge':3,'orderNo':paid_seed['orderNo']},
      {'name':'u08-foreign-404','path':'/orders/'+main_no,'account':'bob','kind':'error','status':404,'uid':2,'badge':0},
      {'name':'u08-unknown-404','path':'/orders/UNKNOWN_STEP09_ORDER','account':'alice','kind':'error','status':404,'uid':1,'badge':3},
      {'name':'u06-script-fields-400','path':'/checkout','account':'alice','kind':'U06','status':400,'uid':1,'badge':3,'action':'script'},
      {'name':'u06-csrf-403','path':'/checkout','account':'alice','kind':'error','status':403,'uid':1,'badge':3,'action':'csrf'},
      {'name':'u07-guest-login','path':'/orders','account':'guest','kind':'U04','status':200,'uid':None,'badge':0}])
    check('exact-24-browser-screenshots',result['screenshots']==24)
    # Separate native actual Service creation, not counted as an HTTP-created order.
    clear_cart(bob,2,'native-bob-clean-cart');add(bob,gift,1,'native-bob-gift-first',uid=2);add(bob,note,2,'native-bob-two-notes-second',uid=2)
    check('native-input-cart-order-opposes-product-lock-order',[x['productId'] for x in cartrows(2)]==[gift,note] and gift>note)
    native_probe()
    final=snapshot();save(EV/'database-final.json',json.dumps(final,indent=2))
    check('unrelated-three-table-digests-unchanged',all(original[t]==final[t] for t in ['store_user','category','product_image']))
    check('runtime-inputs-stable',all(hashlib.sha256((REPO/line.split('  ',1)[1]).read_bytes()).hexdigest()==line.split('  ',1)[0] for line in manifest.splitlines()))
    check('static-images-and-assets-unchanged',static_manifest()==statics)
    check('order-pending-placeholder-removed',all('ORDER_SUBMISSION_PENDING' not in p.read_text(encoding='utf-8') for p in (REPO/'csucampuscraft-user/src/main').rglob('*') if p.suffix in ['.java','.html']))
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
