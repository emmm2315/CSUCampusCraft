"""STEP05 isolated verification; external tools only, no repository business mutation."""
from pathlib import Path
from html.parser import HTMLParser
import os,sys,re,json,time,socket,secrets,hashlib,subprocess,datetime,traceback,urllib.request,urllib.error,urllib.parse,http.cookiejar,zipfile,struct,gzip
REPO=Path('D:/Github Projects/CSUCampusCraft')
HERE=Path(__file__).resolve().parent
RUNTIME=Path('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies')
GIT=Path('C:/Program Files/Git/cmd/git.exe')
JAVA=Path('C:/Users/Starmetor/.jdks/ms-21.0.12.1/bin/java.exe')
MYSQL=Path('D:/MySQL/bin')
BASELINE='a8438b72493fba108577e0ba4918e61b043b8916'
TESTED=os.environ.get('STEP05_TESTED_CODE_SHA','')
if not re.fullmatch(r'[0-9a-f]{40}',TESTED):raise SystemExit('STEP05_TESTED_CODE_SHA must be exact 40-character implementation SHA')
RUN=sys.argv[1] if len(sys.argv)>1 else ''
if RUN!='supplement-guest-rejections':raise SystemExit('Use fresh supplement-guest-rejections directory')
BASE=HERE/'runtime'/RUN;EV=HERE/'evidence'/RUN
BASE.mkdir(parents=True,exist_ok=False);EV.mkdir(parents=True,exist_ok=False)
FLAG=subprocess.CREATE_NO_WINDOW
result={'date':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'baseline_git_sha':BASELINE,'tested_code_sha':TESTED,'checks':{},'scope':'independent supplementary 3 anonymous POST observations; not replacement or retroactive evidence for attempt3'}
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
    assert_page(r,404 if port==8080 else 200,name)
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
    query="".join("SELECT '__STEP05_"+t+"__';SELECT COUNT(*) FROM "+t+";SELECT * FROM "+t+" ORDER BY id;" for t in TABLES)
    data=sql(query,'csucampuscraft').stdout;out={}
    for i,t in enumerate(TABLES):
        marker=('__STEP05_'+t+'__').encode();start=data.index(marker)+len(marker)
        start+=2 if data[start:start+2]==b'\r\n' else 1
        end=data.index(('__STEP05_'+TABLES[i+1]+'__').encode(),start) if i+1<len(TABLES) else len(data)
        payload=data[start:end];count,raw=payload.split(b'\n',1)
        out[t]={'rows':int(count),'sha256':hashlib.sha256(raw).hexdigest()}
    return out


def start_env():
    e=os.environ.copy()
    for k in ['SPRING_APPLICATION_JSON','SPRING_CONFIG_LOCATION','SPRING_CONFIG_ADDITIONAL_LOCATION','JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVA_OPTIONS']:e.pop(k,None)
    url=f'jdbc:mysql://127.0.0.1:{mysqlport}/csucampuscraft'
    e.update(CSUCAMPUSCRAFT_DB_URL=url,CSUCAMPUSCRAFT_DB_USER='csucampuscraft',CSUCAMPUSCRAFT_DB_PASSWORD=apppass,SPRING_DATASOURCE_URL=url,SPRING_DATASOURCE_USERNAME='csucampuscraft',SPRING_DATASOURCE_PASSWORD=apppass,SPRING_PROFILES_ACTIVE='default',SPRING_SQL_INIT_MODE='never')
    return e
def launch(app,port):
    log=BASE/(app+'.log');h=log.open('wb');handles.append(h)
    argv=[JAVA,'-jar',REPO/app/'target'/f'{app}-0.0.1-SNAPSHOT.jar',f'--server.port={port}','--server.address=127.0.0.1']
    p=subprocess.Popen([str(x) for x in argv],env=start_env(),stdout=h,stderr=subprocess.STDOUT,creationflags=FLAG);processes.append(p)
    record('launches.jsonl',{'app':app,'port':port,'database':'csucampuscraft','database_port':mysqlport,'database_user':'csucampuscraft','password_supplied':True,'argv':[str(x) for x in argv]})
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

def catalog_state():
    cat=rows("SELECT JSON_OBJECT('id',id,'code',code,'parentId',parent_id,'name',name,'sortOrder',sort_order,'createdAt',created_at,'updatedAt',updated_at) FROM category ORDER BY id;")
    prod=rows("SELECT JSON_OBJECT('id',id,'sku',sku,'categoryId',category_id,'name',name,'summaryChars',CHAR_LENGTH(COALESCE(summary,'')),'summarySha',SHA2(COALESCE(summary,''),256),'descriptionBytes',OCTET_LENGTH(COALESCE(description,'')),'descriptionSha',SHA2(COALESCE(description,''),256),'coverImage',cover_image,'price',CAST(price AS CHAR),'stock',stock,'status',status,'sortOrder',sort_order,'version',version,'createdAt',created_at,'updatedAt',updated_at) FROM product ORDER BY id;")
    return {'category':{str(x['id']):x for x in map(json.loads,cat.splitlines())},'product':{str(x['id']):x for x in map(json.loads,prod.splitlines())}}
def deltas(a,b):
    return {t:[{'id':k,'before':a[t].get(k),'after':b[t].get(k)} for k in sorted(set(a[t])|set(b[t]),key=int) if a[t].get(k)!=b[t].get(k)] for t in ['category','product']}
def unaffected(a,b):
    return all(a[t]==b[t] for t in TABLES if t not in ['category','product'])
def admin_token(cl,path='/categories/new'):
    r=cl.get(path,8081);assert_page(r,200,'write-form-'+path);t=token(r);check('write-form-token',bool(t))
    return t
def write(cl,path,form,status,name,csrf=True,back='/categories/new'):
    before=snapshot();a=catalog_state()
    data=dict(form)
    if csrf:data['_csrf']=admin_token(cl,back)
    r=cl.post(path,data,8081)
    after=snapshot();b=catalog_state()
    record('database-writes.jsonl',{'name':name,'path':path,'status':r[0],'expected_status':status,'before':before,'after':after,'catalog_deltas':deltas(a,b),'csrf_supplied':csrf,'form_fields':sorted(data)})
    assert_page(r,status,name)
    check(name+'-noncatalog-unchanged',unaffected(before,after))
    if status!=303:check(name+'-rejected-zero-write',before==after)
    else:
        dest=urllib.parse.urlsplit(r[1].get('Location',''))
        check(name+'-internal-readable-location',not dest.netloc and dest.path in ['/categories','/products'])
        check(name+'-location-no-public-model','csrfToken' not in dest.query and 'currentUser' not in dest.query)
    return r,a,b
def cid(r):
    values=urllib.parse.parse_qs(urllib.parse.urlsplit(r[1].get('Location','')).query)
    value=int(values['createdId'][0])
    check('auto-id-positive',value>0)
    check('auto-id-exists',rows('SELECT COUNT(*) FROM category WHERE id='+str(value))=='1')
    return value
def create_category(cl,code,name,parent=None,typ='STATIONERY',sort=''):
    form={'code':code,'name':name,'sortOrder':sort}
    if parent is not None:form.update(parentId=str(parent),type=typ)
    r,_,_=write(cl,'/categories',form,303,'create-category-'+name)
    return cid(r)
def product_form(**values):
    data={'sku':'CSU-QA-STEP05-01','categoryId':'101','name':'STEP05验收商品','price':'12.50','summary':'测试摘要','description':'<script>notExecutable()</script> 纯文本设计说明','coverImage':'','stock':'10','sortOrder':''}
    data.update(values);return data
def pid_by_sku(sku):return int(rows('SELECT id FROM product WHERE sku='+literal(sku)))
def product(pid):return catalog_state()['product'][str(pid)]
def category(cid):return catalog_state()['category'][str(cid)]
def public_detail(pid,status,name):
    r=Client().get('/products/'+str(pid),8080);assert_page(r,status,name)
    if status==200:
        node=r[3].find(lambda n:n.a.get('data-page-id')=='U03')
        p=product(pid)
        check(name+'-id',node is not None and node.a.get('data-product-id')==str(pid))
        check(name+'-stock',int(node.a['data-stock'])==p['stock'])
        check(name+'-price',node.a.get('data-price')==p['price'])
    return r
def verify_list(cl,params,name):
    r=cl.get('/products?'+urllib.parse.urlencode(params),8081);assert_page(r,200,name)
    node=r[3].find(lambda n:n.a.get('data-page-id')=='A04');check(name+'-page-marker',node is not None)
    where=['1=1'];cat=params.get('categoryId')
    if cat:
        exists=rows('SELECT COALESCE(parent_id,0) FROM category WHERE id='+str(cat))
        where.append('(p.category_id='+str(cat)+' OR c.parent_id='+str(cat)+')' if exists=='0' else 'p.category_id='+str(cat))
    status=params.get('status','ALL')
    if status!='ALL':where.append('p.status='+literal(status))
    q=str(params.get('q','')).strip()
    if q:where.append("p.name LIKE "+literal('%'+q.replace('!','!!').replace('%','!%').replace('_','!_')+'%')+" ESCAPE '!'")
    select=' FROM product p JOIN category c ON c.id=p.category_id WHERE '+' AND '.join(where)
    total=int(rows('SELECT COUNT(*)'+select));size=int(params.get('size',10));page=max(1,int(params.get('page',1)))
    exp=rows('SELECT p.id'+select+' ORDER BY p.sort_order ASC,p.id ASC LIMIT '+str(size)+' OFFSET '+str((page-1)*size)+';')
    expected=[int(x) for x in exp.splitlines()] if exp else []
    actual=[int(n.a['data-product-id']) for n in node.all(lambda n:'data-product-id' in n.a and n is not node)]
    check(name+'-count',int(node.a['data-product-count'])==total)
    check(name+'-ids',actual==expected,{'actual':actual,'expected':expected})
    check(name+'-page-size',int(node.a['data-page'])==page and int(node.a['data-size'])==size)
    record('sql-reference.jsonl',{'name':name,'params':params,'total':total,'ids':expected})
    return r
def fixture_product(pid,assignments,label):
    sql('UPDATE product SET '+assignments+' WHERE id='+str(pid)+';','csucampuscraft')
    record('fixtures.jsonl',{'name':label,'product_id':pid,'assignments':assignments,'source_sql_changed':False})
def actor_probe():
    extracted=BASE/'actor-probe';classes=extracted/'classes';libs=extracted/'lib';classes.mkdir(parents=True);libs.mkdir()
    jar=REPO/'csucampuscraft-admin/target/csucampuscraft-admin-0.0.1-SNAPSHOT.jar'
    with zipfile.ZipFile(jar) as z:
        for n in z.namelist():
            if n.startswith('BOOT-INF/classes/') and not n.endswith('/'):
                p=classes/n[len('BOOT-INF/classes/'):];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
            elif n.startswith('BOOT-INF/lib/') and n.endswith('.jar'):(libs/Path(n).name).write_bytes(z.read(n))
    cp=str(classes)+';'+str(libs/'*')+';'+str(extracted)
    p=command([JAVA.parent/'javac.exe','-cp',cp,'-d',extracted,HERE/'ActorWriteProbe.java'],timeout=45)
    save(EV/'actor-probe-compile.log',p.stdout.decode(errors='replace')+p.stderr.decode(errors='replace'));check('actor-probe-compile',p.returncode==0)
    e=start_env();e.update(STEP05_ROOT_PASSWORD=rootpass,STEP05_MYSQL_PORT=str(mysqlport))
    before=snapshot();a=catalog_state()
    p=command([JAVA,'-cp',cp,'ActorWriteProbe'],env=e,timeout=90)
    save(EV/'actor-probe.log',p.stdout.decode(errors='replace')+p.stderr.decode(errors='replace'))
    check('actor-probe',p.returncode==0 and '"overall":"PASS"' in p.stdout.decode(errors='replace'))
    after=snapshot();b=catalog_state();record('database-writes.jsonl',{'name':'native-actor-guard-probe','before':before,'after':after,'catalog_deltas':deltas(a,b)})
    check('actor-probe-noncatalog-stable',unaffected(before,after))
def browser(admin_cookie,cases):
    e=start_env();e['STEP05_BROWSER_OUT']=str(EV/'browser');e['STEP05_BROWSER_CASES']=json.dumps(cases,ensure_ascii=False)
    e['STEP05_ADMIN_COOKIE']=admin_cookie;e['STEP05_VALID_PASSWORD']=PASSWORD
    before=snapshot()
    p=command([RUNTIME/'node/bin/node.exe',HERE/'verify_browser.cjs'],env=e,timeout=150)
    save(EV/'browser.log',p.stdout.decode(errors='replace')+p.stderr.decode(errors='replace'));check('browser-critical-pages',p.returncode==0)
    br=json.loads((EV/'browser/result.json').read_text());check('browser-completed',br.get('completed') and br['overall']=='PASS')
    result['browser_checks']=len(br['checks']);result['screenshots']=len(br['screenshots'])
    check('browser-rejected-writes-zero-change',snapshot()==before)


try:
    check('tested-code-head',git('rev-parse','HEAD').decode().strip()==TESTED)
    result['branch']=git('branch','--show-current').decode().strip();check('feature-branch',result['branch']=='feat/step05-admin-catalog')
    state=git('status','--short','--untracked-files=all').decode();save(EV/'git-input-status.txt',state);check('worktree-clean',not state.strip())
    inputs=[]
    for app in ['csucampuscraft-user','csucampuscraft-admin']:
        inputs.append(REPO/app/'pom.xml');inputs.extend(p for p in (REPO/app/'src').rglob('*') if p.is_file())
    inputs.extend(p for d in ['database','assets','.mvn'] for p in (REPO/d).rglob('*') if p.is_file());inputs.extend([REPO/'mvnw',REPO/'mvnw.cmd'])
    manifest=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(REPO).as_posix()+'\n' for p in sorted(inputs,key=lambda x:x.relative_to(REPO).as_posix()))
    save(EV/'runtime-inputs.sha256',manifest);result['runtime_manifest_sha256']=hashlib.sha256(manifest.encode()).hexdigest();result['runtime_file_count']=len(inputs)
    save(EV/'verify_guest_supplement.py',Path(__file__).read_text(encoding='utf-8'))
    ve=os.environ.copy();ve['JAVA_HOME']=str(JAVA.parent.parent);ve['PATH']=str(JAVA.parent)+';'+os.environ['SystemRoot']+'/System32;'+os.environ['SystemRoot']+'/System32/WindowsPowerShell/v1.0'
    versions=[]
    for argv in [[JAVA,'-version'],[REPO/'mvnw.cmd','-v'],[MYSQL/'mysqld.exe','--version']]:
        q=command(argv,env=ve,timeout=60);check('tool-version-'+str(len(versions)),q.returncode==0);versions.append(q.stdout.decode(errors='replace')+q.stderr.decode(errors='replace'))
    save(EV/'versions.txt','\n'.join(versions));check('wrapper-maven-pin','Apache Maven 3.9.16' in versions[1])
    primary=json.loads((HERE/'evidence/attempt3/result.json').read_text(encoding='utf-8'))
    for app in ['csucampuscraft-user','csucampuscraft-admin']:
        digest=hashlib.sha256((REPO/app/'target'/f'{app}-0.0.1-SNAPSHOT.jar').read_bytes()).hexdigest()
        result[app+'_jar_sha256']=digest;check(app+'-same-jar-as-full-attempt3',digest==primary[app+'_jar_sha256'])
    data=BASE/'mysql-data';data.mkdir();init=BASE/'mysql-init-private.sql';private_files.append(init)
    init.write_text("ALTER USER 'root'@'localhost' IDENTIFIED BY '"+rootpass+"';",encoding='utf-8')
    q=command([MYSQL/'mysqld.exe','--no-defaults','--initialize-insecure','--basedir=D:/MySQL',f'--datadir={data}',f'--log-error={BASE/"mysql-initialize.log"}'],timeout=45);check('private-mysql-initialized',q.returncode==0)
    h=(BASE/'mysql-server.log').open('wb');handles.append(h)
    server=subprocess.Popen([str(MYSQL/'mysqld.exe'),'--no-defaults','--basedir=D:/MySQL',f'--datadir={data}',f'--port={mysqlport}','--bind-address=127.0.0.1','--mysqlx=OFF',f'--init-file={init}',f'--pid-file={BASE/"mysql.pid"}','--console'],stdout=h,stderr=subprocess.STDOUT,creationflags=FLAG)
    deadline=time.monotonic()+35
    while time.monotonic()<deadline:
        q=sql('SELECT @@version,@@server_uuid,@@port;',fail_ok=True)
        if q.returncode==0:break
        if server.poll() is not None:raise RuntimeError('Private supplement MySQL exited')
        time.sleep(.2)
    else:raise RuntimeError('Private supplement MySQL not ready')
    ident=q.stdout.decode().strip().split('\t');expected=re.search(r'server-uuid=(.+)',(data/'auto.cnf').read_text()).group(1).strip()
    check('private-mysql-identity',ident[1]==expected and int(ident[2])==mysqlport)
    result['mysql_version']=ident[0];result['mysql_port']=mysqlport;init.unlink()
    sql('CREATE DATABASE csucampuscraft CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_ci;')
    sql((REPO/'database/02-schema-with-demo.sql').read_text(encoding='utf-8-sig'),'csucampuscraft')
    sql("CREATE USER 'csucampuscraft'@'127.0.0.1' IDENTIFIED BY '"+apppass+"';")
    sql("GRANT SELECT,LOCK TABLES ON csucampuscraft.* TO 'csucampuscraft'@'127.0.0.1';")
    for table in ['category','product']:sql("GRANT INSERT,UPDATE,DELETE ON csucampuscraft."+table+" TO 'csucampuscraft'@'127.0.0.1';")
    save(EV/'application-grants.txt',rows("SHOW GRANTS FOR 'csucampuscraft'@'127.0.0.1';",None))
    initial=snapshot();save(EV/'database-original.json',json.dumps(initial,indent=2))
    with socket.socket() as s:s.bind(('127.0.0.1',8081))
    launch('csucampuscraft-admin',8081)
    result['admin_port']=8081;result['user_jar_launched']=False
    for i,path in enumerate(['/categories','/products','/products/1/restock'],1):
        cl=Client();before=snapshot();catalog_before=catalog_state()
        response=cl.post(path,{},8081)
        after=snapshot();catalog_after=catalog_state()
        record('database-writes.jsonl',{'case':'supplement-guest-post-'+str(i),'scope':'new independent request; not backfill of old full-run HTTP','http_sequence':http_no,'method':'POST','path':path,'expected_status':302,'actual_status':response[0],'before':before,'after':after,'catalog_before':catalog_before,'catalog_after':catalog_after,'catalog_deltas':deltas(catalog_before,catalog_after)})
        is_login_redirect(response,'anonymous-protected-post-'+str(i),'/')
        check('seven-tables-zero-write-'+str(i),before==after)
        check('catalog-key-rows-identical-'+str(i),catalog_before==catalog_after)
    final=snapshot();save(EV/'database-final.json',json.dumps(final,indent=2));check('all-seven-final-original',final==initial)
    check('runtime-inputs-stable',all(hashlib.sha256((REPO/line.split('  ',1)[1]).read_bytes()).hexdigest()==line.split('  ',1)[0] for line in manifest.splitlines()))
    result['http_records']=http_no;result['database_write_records']=3;result['screenshots']=0;result['overall']='PASS'
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
