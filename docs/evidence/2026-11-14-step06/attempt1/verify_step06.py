"""STEP06 isolated verification; external tools only, no repository business mutation."""
from pathlib import Path
from html.parser import HTMLParser
import os,sys,re,json,time,socket,secrets,hashlib,subprocess,datetime,traceback,urllib.request,urllib.error,urllib.parse,http.cookiejar,zipfile,struct,gzip
REPO=Path('D:/Github Projects/CSUCampusCraft')
HERE=Path(__file__).resolve().parent
RUNTIME=Path('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies')
GIT=Path('C:/Program Files/Git/cmd/git.exe')
JAVA=Path('C:/Users/Starmetor/.jdks/ms-21.0.12.1/bin/java.exe')
MYSQL=Path('D:/MySQL/bin')
BASELINE='75e4339266968edc212f160b1119ac720965c408'
TESTED=os.environ.get('STEP06_TESTED_CODE_SHA','')
if not re.fullmatch(r'[0-9a-f]{40}',TESTED):raise SystemExit('STEP06_TESTED_CODE_SHA must be exact 40-character implementation SHA')
RUN=sys.argv[1] if len(sys.argv)>1 else ''
if not re.fullmatch(r'attempt[1-9][0-9]*',RUN):raise SystemExit('Use a fresh attemptN')
BASE=HERE/'runtime'/RUN;EV=HERE/'evidence'/RUN
BASE.mkdir(parents=True,exist_ok=False);EV.mkdir(parents=True,exist_ok=False)
FLAG=subprocess.CREATE_NO_WINDOW
result={'date':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'baseline_git_sha':BASELINE,'tested_code_sha':TESTED,'checks':{},'scope':'STEP06 product images only; concurrency and faults remain STEP13'}
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
    query="".join("SELECT '__STEP06_"+t+"__';SELECT COUNT(*) FROM "+t+";SELECT * FROM "+t+" ORDER BY id;" for t in TABLES)
    data=sql(query,'csucampuscraft').stdout;out={}
    for i,t in enumerate(TABLES):
        marker=('__STEP06_'+t+'__').encode();start=data.index(marker)+len(marker)
        start+=2 if data[start:start+2]==b'\r\n' else 1
        end=data.index(('__STEP06_'+TABLES[i+1]+'__').encode(),start) if i+1<len(TABLES) else len(data)
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

def state():
    queries={
      'product':"SELECT JSON_OBJECT('id',id,'sku',sku,'categoryId',category_id,'name',name,'summaryChars',CHAR_LENGTH(COALESCE(summary,'')),'summarySha',SHA2(COALESCE(summary,''),256),'descriptionBytes',OCTET_LENGTH(COALESCE(description,'')),'descriptionSha',SHA2(COALESCE(description,''),256),'coverImage',cover_image,'price',CAST(price AS CHAR),'stock',stock,'status',status,'sortOrder',sort_order,'version',version,'createdAt',created_at,'updatedAt',updated_at) FROM product ORDER BY id;",
      'product_image':"SELECT JSON_OBJECT('id',id,'productId',product_id,'imagePath',image_path,'altText',alt_text,'sortOrder',sort_order) FROM product_image ORDER BY id;"}
    return {t:{str(x['id']):x for x in map(json.loads,rows(q).splitlines())} for t,q in queries.items()}
def deltas(a,b):
    return {t:[{'id':k,'before':a[t].get(k),'after':b[t].get(k)} for k in sorted(set(a[t])|set(b[t]),key=int) if a[t].get(k)!=b[t].get(k)] for t in a}
def images(pid):return sorted((x for x in state()['product_image'].values() if x['productId']==pid),key=lambda x:(x['sortOrder'],x['id']))
def product(pid):return state()['product'][str(pid)]
def version(pid):return str(product(pid)['version'])
def pid_by_sku(sku):return int(rows('SELECT id FROM product WHERE sku='+literal(sku)))
def unchanged_other(a,b):return all(a[t]==b[t] for t in TABLES if t not in ['product','product_image'])
def snapshot_pair(name,before,a,after,b,**extra):
    delta=deltas(a,b);match=re.search(r'/products/([0-9]+)',extra.get('path',''))
    ids={match.group(1)} if match else set()
    ids.update(x['id'] for x in delta['product'])
    for x in delta['product_image']:
        for y in [x['before'],x['after']]:
            if y:ids.add(str(y['productId']))
    def relevant(s):return {'product':{k:v for k,v in s['product'].items() if k in ids},'product_image':{k:v for k,v in s['product_image'].items() if str(v['productId']) in ids}}
    record('database-writes.jsonl',dict(name=name,before=before,after=after,target_before=relevant(a),target_after=relevant(b),deltas=delta,**extra))
def write(cl,path,form,status,name,csrf=True,back=None,album=True,allow_product_fields=('version','updatedAt')):
    data=dict(form)
    if csrf:
        r=cl.get(back or path.split('/images')[0]+'/images',8081);assert_page(r,200,name+'-form')
        data['_csrf']=token(r);check(name+'-token',bool(data['_csrf']))
    before=snapshot();a=state();r=cl.post(path,data,8081);after=snapshot();b=state()
    snapshot_pair(name,before,a,after,b,path=path,status=r[0],expected_status=status,csrf_supplied=csrf,form_fields=sorted(data))
    assert_page(r,status,name)
    check(name+'-other-five-tables-unchanged',unchanged_other(before,after))
    if status!=303:check(name+'-rejected-zero-write',before==after)
    else:
        u=urllib.parse.urlsplit(r[1].get('Location',''))
        check(name+'-internal-get-redirect',not u.netloc and (re.fullmatch('/products/[0-9]+/images',u.path) is not None if album else u.path=='/products'))
        check(name+'-redirect-no-model-leak','csrfToken' not in u.query and 'currentUser' not in u.query)
        if album:
            for key in a['product']:
                old,new=a['product'][key],b['product'][key]
                check(name+'-parent-'+key+'-forbidden-columns-unchanged',all(old[k]==new[k] for k in old if k not in allow_product_fields))
    return r,a,b
def raw_post(cl,path,form,status,name):return write(cl,path,form,status,name,csrf=False)
def album(cl,pid,name):
    r=cl.get('/products/'+str(pid)+'/images',8081);assert_page(r,200,name)
    n=r[3].find(lambda n:n.a.get('data-page-id')=='A10');expected=images(pid)
    check(name+'-root',n is not None and n.a.get('data-product-id')==str(pid))
    check(name+'-version',n.a.get('data-product-version')==version(pid))
    check(name+'-count',int(n.a.get('data-image-count','-1'))==len(expected))
    actual=[int(x.a['data-image-id']) for x in n.all(lambda x:x.tag=='article' and 'data-image-id' in x.a)]
    check(name+'-database-order',actual==[x['id'] for x in expected],{'actual':actual,'expected':[x['id'] for x in expected]})
    for f in n.all(lambda x:x.tag=='form'):
        check(name+'-form-single-csrf',len(f.all(lambda x:x.tag=='input' and x.a.get('name')=='_csrf'))==1)
        pv=f.find(lambda x:x.tag=='input' and x.a.get('name')=='productVersion')
        check(name+'-form-current-version',pv is not None and pv.a.get('value')==version(pid))
    record('sql-reference.jsonl',{'name':name,'parent':product(pid),'ordered_images':expected})
    return r
def user_detail(pid,name):
    r=Client().get('/products/'+str(pid),8080);assert_page(r,200,name)
    gallery=r[3].find(lambda n:'data-product-gallery' in n.a);expected=images(pid)
    figures=gallery.all(lambda n:n.tag=='figure' and 'data-image-id' in n.a)
    check(name+'-order',[int(n.a['data-image-id']) for n in figures]==[x['id'] for x in expected])
    for n,x in zip(figures,expected):
        img=n.find(lambda y:y.tag=='img');alt=x['altText'] or product(pid)['name']
        check(name+'-alt-'+str(x['id']),img.a.get('alt')==alt and n.find(lambda y:y.tag=='figcaption').text()==alt)
    check(name+'-escaped-text','<script>step06()</script>' not in r[2].decode())
    if not expected:check(name+'-cover-fallback',r[3].find(lambda n:'data-gallery-empty' in n.a) is not None)
    return r
def input_form(pid,**changes):
    f={'imagePath':'images/catalog-placeholder.svg','altText':'相册验收','sortOrder':'0','productVersion':version(pid)};f.update(changes);return f
def add(cl,pid,name,**changes):
    before=version(pid);r,a,b=write(cl,'/products/'+str(pid)+'/images',input_form(pid,**changes),303,name)
    inserted=[x for x in b['product_image'].values() if str(x['id']) not in a['product_image']]
    check(name+'-one-row-added',len(inserted)==1);check(name+'-version-plus-one',int(version(pid))==int(before)+1)
    return inserted[0]['id']
def fixture(pid,assignments,name):
    before=snapshot();a=state();sql('UPDATE product SET '+assignments+' WHERE id='+str(pid)+';','csucampuscraft');after=snapshot();b=state()
    record('fixtures.jsonl',{'name':name,'controlled_root_fixture':True,'assignments':assignments,'before':before,'after':after,'deltas':deltas(a,b)})
def static_manifest():
    out={}
    for p in sorted((REPO/'assets').rglob('*')):
        if p.is_file():out['assets/'+p.relative_to(REPO/'assets').as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    for app in ['csucampuscraft-user','csucampuscraft-admin']:
        with zipfile.ZipFile(REPO/app/'target'/f'{app}-0.0.1-SNAPSHOT.jar') as z:
            for n in z.namelist():
                if n.startswith('BOOT-INF/classes/static/images/') and not n.endswith('/'):out[app+'/'+n]=hashlib.sha256(z.read(n)).hexdigest()
    return out
def static_pair(path,name,expected=200):
    arr=[]
    for port in [8080,8081]:
        req=urllib.request.Request('http://127.0.0.1:'+str(port)+'/'+urllib.parse.quote(path,safe='/'))
        try:r=urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req,timeout=10)
        except urllib.error.HTTPError as e:r=e
        body=r.read();arr.append({'port':port,'status':r.code,'content_type':r.headers.get('Content-Type'),'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()})
    record('static-resources.jsonl',{'name':name,'path':path,'observations':arr})
    check(name+'-http-status',all(x['status']==expected for x in arr))
    if expected==200:
        check(name+'-same-type-bytes',arr[0]['content_type']==arr[1]['content_type'] and arr[0]['sha256']==arr[1]['sha256'])
        candidates=list((REPO/'assets').rglob(Path(path).name));check(name+'-asset-source-present',len(candidates)==1)
        check(name+'-source-equals-served',hashlib.sha256(candidates[0].read_bytes()).hexdigest()==arr[0]['sha256'])
def native_probe():
    extracted=BASE/'native-probe';classes=extracted/'classes';libs=extracted/'lib';classes.mkdir(parents=True);libs.mkdir()
    with zipfile.ZipFile(REPO/'csucampuscraft-admin/target/csucampuscraft-admin-0.0.1-SNAPSHOT.jar') as z:
        for n in z.namelist():
            if n.startswith('BOOT-INF/classes/') and not n.endswith('/'):
                p=classes/n[len('BOOT-INF/classes/'):];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
            elif n.startswith('BOOT-INF/lib/') and n.endswith('.jar'):(libs/Path(n).name).write_bytes(z.read(n))
    cp=str(classes)+';'+str(libs/'*')+';'+str(extracted)
    p=command([JAVA.parent/'javac.exe','-cp',cp,'-d',extracted,HERE/'AlbumWriteProbe.java'],timeout=45)
    save(EV/'native-compile.log',p.stdout.decode(errors='replace')+p.stderr.decode(errors='replace'));check('native-probe-compile',p.returncode==0)
    e=start_env();e.update(STEP06_ROOT_PASSWORD=rootpass,STEP06_MYSQL_PORT=str(mysqlport))
    before=snapshot();a=state();p=command([JAVA,'-cp',cp,'AlbumWriteProbe'],env=e,timeout=110);after=snapshot();b=state()
    save(EV/'native-probe.log',p.stdout.decode(errors='replace')+p.stderr.decode(errors='replace'))
    snapshot_pair('native-album-service-probe',before,a,after,b)
    check('native-probe',p.returncode==0 and '"overall":"PASS"' in p.stdout.decode(errors='replace'))
    check('native-five-tables-stable',unchanged_other(before,after))
def browser(cookie,cases):
    e=start_env();e.update(STEP06_BROWSER_OUT=str(EV/'browser'),STEP06_BROWSER_CASES=json.dumps(cases,ensure_ascii=False),STEP06_ADMIN_COOKIE=cookie)
    before=snapshot();p=command([RUNTIME/'node/bin/node.exe',HERE/'verify_browser.cjs'],env=e,timeout=180)
    save(EV/'browser.log',p.stdout.decode(errors='replace')+p.stderr.decode(errors='replace'));check('browser',p.returncode==0)
    br=json.loads((EV/'browser/result.json').read_text());check('browser-completed',br.get('completed') and br['overall']=='PASS')
    result['browser_checks']=len(br['checks']);result['screenshots']=len(br['screenshots']);check('browser-zero-write',snapshot()==before)

try:
    check('tested-code-head',git('rev-parse','HEAD').decode().strip()==TESTED)
    result['branch']=git('branch','--show-current').decode().strip();check('feature-branch',result['branch']=='feat/step06-admin-images')
    status=git('status','--short','--untracked-files=all').decode();save(EV/'git-input-status.txt',status);check('tested-worktree-clean',not status.strip())
    save(EV/'implementation-diff.patch',git('diff',BASELINE+'..'+TESTED,'--','csucampuscraft-admin').decode('utf-8'))
    inputs=[]
    for app in ['csucampuscraft-user','csucampuscraft-admin']:
        inputs.append(REPO/app/'pom.xml');inputs.extend(p for p in (REPO/app/'src').rglob('*') if p.is_file())
    inputs.extend(p for d in ['database','assets','.mvn'] for p in (REPO/d).rglob('*') if p.is_file());inputs.extend([REPO/'mvnw',REPO/'mvnw.cmd'])
    manifest=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(REPO).as_posix()+'\n' for p in sorted(inputs,key=lambda x:x.relative_to(REPO).as_posix()))
    save(EV/'runtime-inputs.sha256',manifest);result['runtime_manifest_sha256']=hashlib.sha256(manifest.encode()).hexdigest();result['runtime_file_count']=len(inputs)
    for name in ['verify_step06.py','verify_browser.cjs','AlbumWriteProbe.java']:save(EV/name,(HERE/name).read_text(encoding='utf-8-sig'))
    builddir=Path(os.environ.get('STEP06_BUILD_LOG_DIR',HERE.parent));exits=json.loads((builddir/'build-exits.json').read_text(encoding='utf-8-sig'))
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
    ident=p.stdout.decode().strip().split('\t');uuid=re.search(r'server-uuid=(.+)',(data/'auto.cnf').read_text()).group(1).strip()
    check('isolated-mysql-identity',ident[1]==uuid and int(ident[2])==mysqlport and Path(ident[3]).resolve()==data.resolve());result['mysql_version']=ident[0];result['mysql_port']=mysqlport;init.unlink()
    save(EV/'database-identity.json',json.dumps({'version':ident[0],'uuid':uuid,'port':mysqlport,'datadir_is_private':True,'every_connection_timezone':'UTC','collation':'utf8mb4_0900_as_ci'},indent=2))
    sql('CREATE DATABASE csucampuscraft CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_ci;')
    sql((REPO/'database/02-schema-with-demo.sql').read_text(encoding='utf-8-sig'),'csucampuscraft')
    sql("CREATE USER 'csucampuscraft'@'127.0.0.1' IDENTIFIED BY '"+apppass+"';")
    sql("GRANT SELECT,LOCK TABLES ON csucampuscraft.* TO 'csucampuscraft'@'127.0.0.1';")
    sql("GRANT INSERT,UPDATE,DELETE ON csucampuscraft.product_image TO 'csucampuscraft'@'127.0.0.1';")
    sql("GRANT UPDATE ON csucampuscraft.product TO 'csucampuscraft'@'127.0.0.1';")
    save(EV/'application-grants.txt',rows("SHOW GRANTS FOR 'csucampuscraft'@'127.0.0.1';",None))
    original=snapshot();save(EV/'database-original.json',json.dumps(original,indent=2));check('seed-counts',[original[t]['rows'] for t in TABLES]==[4,15,60,100,10,10,20])
    for port in [8080,8081]:
        with socket.socket() as s:s.bind(('127.0.0.1',port))
    launch('csucampuscraft-user',8080);launch('csucampuscraft-admin',8081)
    pid=pid_by_sku('CSU-GRAD-BOX-01');other=pid_by_sku('CSU-LMK-NOTE-01');path='/products/'+str(pid)+'/images'
    guest=Client();is_login_redirect(guest.get(path,8081),'guest-album',path)
    for suffix in ['', '/1','/1/remove']:raw_post(guest,path+suffix,{},302,'guest-post'+suffix.replace('/','-'))
    cl=Client();r,_,_=login(cl,8081,name='admin');assert_page(r,303,'admin-login');album(cl,pid,'seed-album');user_detail(pid,'seed-user-order')
    static_pair('images/catalog-placeholder.svg','placeholder-dual-apps');static_pair(product(pid)['coverImage'],'gift-cover-dual-apps')
    raw_post(cl,path,input_form(pid),403,'missing-csrf');raw_post(cl,path,dict(input_form(pid),_csrf='not-the-session-token'),403,'wrong-csrf')
    before=snapshot();sql("UPDATE store_user SET role='CUSTOMER',updated_at=updated_at WHERE id=4;",'csucampuscraft');record('fixtures.jsonl',{'name':'wrong-role-controlled-fixture','before':before,'after':snapshot(),'preserve_auth_stamp':True})
    try:raw_post(cl,path,{},403,'wrong-role-before-csrf');assert_page(cl.get(path,8081),403,'wrong-role-get')
    finally:sql("UPDATE store_user SET role='ADMIN',updated_at=updated_at WHERE id=4;",'csucampuscraft')
    check('role-fixture-restored-entire-row',snapshot()==before)
    assert_page(cl.get('/products/999999999/images',8081),404,'unknown-product-get')
    added=add(cl,pid,'add-escaped-alt',imagePath=product(pid)['coverImage'],altText='<script>step06()</script>',sortOrder='5')
    album(cl,pid,'added-album');user_detail(pid,'added-user-order')
    addedpath=path+'/'+str(added)
    old=version(pid);write(cl,addedpath,input_form(pid,imagePath=product(pid)['coverImage'],altText='调整后的替代文本',sortOrder='25'),303,'edit-order-alt')
    check('edit-version-plus-one',int(version(pid))==int(old)+1);album(cl,pid,'edited-album');user_detail(pid,'edited-user-order')
    duplicate=add(cl,pid,'add-repeated-path-tied-sort',imagePath=product(pid)['coverImage'],altText='',sortOrder='25')
    check('tied-order-id',[x['id'] for x in images(pid) if x['sortOrder']==25]==sorted(x['id'] for x in images(pid) if x['sortOrder']==25));user_detail(pid,'blank-alt-fallback-and-tie')
    target=next(x for x in images(pid) if x['id']==added);before=snapshot();old=version(pid)
    write(cl,addedpath,input_form(pid,imagePath=target['imagePath'],altText=target['altText'],sortOrder=str(target['sortOrder'])),303,'same-value-edit')
    check('same-value-full-snapshot-unchanged',snapshot()==before and version(pid)==old)
    cross=images(other)[0]['id']
    for suffix in ['', '/remove']:write(cl,path+'/'+str(cross)+suffix,input_form(pid),404,'cross-product-image'+suffix.replace('/','-'))
    for suffix in ['', '/remove']:write(cl,path+'/999999999'+suffix,input_form(pid),404,'unknown-image'+suffix.replace('/','-'))
    stale=str(int(version(pid))-1)
    for suffix in ['', '/'+str(added),'/'+str(added)+'/remove']:
        for tag,value in [('missing',None),('blank',''),('stale',stale),('nonnumeric','abc'),('negative','-1'),('overflow','9223372036854775808')]:
            f=input_form(pid)
            if value is None:f.pop('productVersion')
            else:f['productVersion']=value
            write(cl,path+suffix,f,409 if tag in ['missing','blank','stale'] else 400,tag+'-version'+suffix.replace('/','-'))
    write(cl,path+'/'+str(cross),input_form(pid,productVersion=stale),409,'version-before-cross-product-ownership')
    write(cl,'/products/999999999/images',dict(input_form(pid),productVersion=''),404,'missing-parent-before-version',back=path)
    invalid_paths=['','/images/a.svg','//example.test/a.svg','https://example.test/a.svg','images/../a.svg','images/a..b.svg','images\\a.svg','images/a%20b.svg','images/a?b.svg','images/a#b.svg','images/a:b.svg','images/./a.svg','images/\x01a.svg','images/\x7fa.svg','images/\u0085a.svg','images/'+'a'*249]
    for index,value in enumerate(invalid_paths):write(cl,path,input_form(pid,imagePath=value),400,'invalid-image-path-'+str(index))
    for field,value in [('altText','中'*121),('sortOrder','-1'),('sortOrder','1.1'),('sortOrder','abc'),('sortOrder','2147483648')]:write(cl,path,input_form(pid,**{field:value}),400,'invalid-'+field+'-'+str(len(value))+'-'+value[:3])
    unicode_id=add(cl,pid,'unicode-space-path-120-alt',imagePath=' images/校园 文创.svg ',altText='中'*120,sortOrder='2147483647')
    check('path-trimmed',next(x for x in images(pid) if x['id']==unicode_id)['imagePath']=='images/校园 文创.svg')
    blank_id=add(cl,pid,'blank-sort-default-zero',imagePath='images/absent-step06.svg',sortOrder='',altText='')
    maxpath_id=add(cl,pid,'255-character-path-accepted',imagePath='images/'+'a'*248,sortOrder='100')
    check('sort-default-zero',next(x for x in images(pid) if x['id']==blank_id)['sortOrder']==0)
    static_pair('images/absent-step06.svg','missing-resource-raw-404',404)
    # Genuine MAX version branches; controlled root fixture is kept separately from application POSTs.
    original_version=version(pid);fixture(pid,'version=9223372036854775807,updated_at=updated_at','max-version-fixture')
    write(cl,path,input_form(pid),409,'max-version-create-zero-write')
    target=next(x for x in images(pid) if x['id']==added)
    write(cl,addedpath,input_form(pid,imagePath=target['imagePath'],altText='changed at max',sortOrder=str(target['sortOrder'])),409,'max-version-edit-zero-write')
    write(cl,addedpath+'/remove',{'productVersion':version(pid)},409,'max-version-remove-zero-write')
    before=snapshot();write(cl,addedpath,input_form(pid,imagePath=target['imagePath'],altText=target['altText'],sortOrder=str(target['sortOrder'])),303,'max-version-noop-allowed');check('max-noop-entire-state-unchanged',snapshot()==before)
    fixture(pid,'version='+original_version+',updated_at=updated_at','restore-version-after-max-fixture')
    # Old product form becomes stale after album changes; SKU/stock are not posted as edits.
    product_before=product(pid);old_version=version(pid);add(cl,pid,'album-bump-before-stale-product-form')
    f={'categoryId':str(product_before['categoryId']),'name':product_before['name'],'price':product_before['price'],'summary':'旧资料表单','description':'旧资料','coverImage':product_before['coverImage'],'sortOrder':str(product_before['sortOrder']),'version':old_version}
    write(cl,'/products/'+str(pid),f,409,'stale-product-form-after-album',back='/products/'+str(pid)+'/edit',album=False)
    stale_album=version(pid);write(cl,'/products/'+str(pid)+'/restock',{'quantity':'1'},303,'restock-invalidates-album-form',back='/products/'+str(pid)+'/edit',album=False)
    write(cl,path,input_form(pid,productVersion=stale_album),409,'stale-album-after-restock')
    # Remove every image from another seeded public product via genuine app operations.
    empty=pid_by_sku('CSU-LMK-BOOKMARK-01');empty_path='/products/'+str(empty)+'/images';cover_before=product(empty)['coverImage']
    for x in images(empty):write(cl,empty_path+'/'+str(x['id'])+'/remove',{'productVersion':version(empty)},303,'remove-image-'+str(x['id']))
    check('last-remove-cover-independent',product(empty)['coverImage']==cover_before);album(cl,empty,'empty-album-keeps-add-form');user_detail(empty,'last-image-cover-fallback')
    missing=pid_by_sku('CSU-CLB-STAND-01');check('missing-cover-seed-empty-album',not images(missing));user_detail(missing,'missing-cover-empty-album');static_pair(product(missing)['coverImage'],'missing-cover-raw-404',404)
    native_probe()
    cases=[
      {'name':'a10-edited-gallery','port':8081,'path':path,'kind':'A10'},
      {'name':'a10-seed-gallery','port':8081,'path':'/products/'+str(other)+'/images','kind':'A10'},
      {'name':'a10-empty-fallback','port':8081,'path':empty_path,'kind':'A10'},
      {'name':'a10-missing-cover','port':8081,'path':'/products/'+str(missing)+'/images','kind':'A10','fallback':True},
      {'name':'a04-album-entry','port':8081,'path':'/products','kind':'A04'},
      {'name':'a05-album-entry','port':8081,'path':'/products/'+str(pid)+'/edit','kind':'A05'},
      {'name':'u03-edited-gallery','port':8080,'path':'/products/'+str(pid),'kind':'U03','fallback':True},
      {'name':'u03-seed-gallery','port':8080,'path':'/products/'+str(other),'kind':'U03'},
      {'name':'u03-empty-cover','port':8080,'path':'/products/'+str(empty),'kind':'U03'},
      {'name':'u03-missing-cover','port':8080,'path':'/products/'+str(missing),'kind':'U03','fallback':True},
      {'name':'a10-draft-product','port':8081,'path':'/products/'+str(pid_by_sku('CSU-CLB-FOLDER-02'))+'/images','kind':'A10'},
      {'name':'u03-sold-out','port':8080,'path':'/products/'+str(pid_by_sku('CSU-SPT-STAND-01')),'kind':'U03'}]
    browser(cl.cookie(8081),cases)
    final=snapshot();save(EV/'database-final.json',json.dumps(final,indent=2));check('final-five-other-tables-unchanged',unchanged_other(original,final))
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
