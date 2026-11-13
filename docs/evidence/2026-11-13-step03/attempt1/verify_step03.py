"""STEP03 isolated, read-only application verification; no business code or test framework."""
from pathlib import Path
from html.parser import HTMLParser
import os,sys,re,json,time,socket,secrets,hashlib,subprocess,datetime,traceback,urllib.request,urllib.error,urllib.parse,http.cookiejar,html,decimal
REPO=Path('D:/Github Projects/CSUCampusCraft')
HERE=Path(__file__).resolve().parent
RUNTIME=Path('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies')
GIT=RUNTIME/'native/git/cmd/git.exe'
JAVA=Path('C:/Users/Starmetor/.jdks/ms-21.0.12.1/bin/java.exe')
MYSQL=Path('D:/MySQL/bin')
BASELINE='f9fd249b7a8c0a6ea6111133062d9e701096ef9d'
TESTED=os.environ.get('STEP03_TESTED_CODE_SHA','')
if not re.fullmatch(r'[0-9a-f]{40}',TESTED):raise SystemExit('STEP03_TESTED_CODE_SHA must identify the exact tested implementation commit')
RUN=sys.argv[1] if len(sys.argv)>1 else ''
if not re.fullmatch(r'attempt[1-9][0-9]*',RUN):raise SystemExit('Use a fresh attemptN')
BASE=HERE/'runtime'/RUN;EV=HERE/'evidence'/RUN
BASE.mkdir(parents=True,exist_ok=False);EV.mkdir(parents=True,exist_ok=False)
FLAG=subprocess.CREATE_NO_WINDOW
result={'date':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'baseline_git_sha':BASELINE,'tested_code_sha':TESTED,'checks':{},'source_state':'exact implementation commit; documentation/evidence committed separately'}
secret_values=[secrets.token_urlsafe(28),secrets.token_urlsafe(28)]
rootpass,apppass=secret_values
handles=[];processes=[];server=None;http_no=0;command_no=0;private_files=[]
TABLES=['store_user','category','product','product_image','cart_item','sales_order','sales_order_item']
ORDERS={'DEFAULT':'p.sort_order ASC,p.id ASC','PRICE_ASC':'p.price ASC,p.id ASC','PRICE_DESC':'p.price DESC,p.id ASC','NEWEST':'p.created_at DESC,p.id DESC'}
def scrub(s):
    for v in sorted(set(secret_values),key=len,reverse=True):
        if len(v)>=8:s=s.replace(v,'[REDACTED]')
    s=re.sub(r'(?i)(name=["\']_csrf["\'][^>]*value=["\'])[^"\']*(["\'])',r'\1[REDACTED]\2',s)
    s=re.sub(r'(?i)(value=["\'])[^"\']*(["\'][^>]*name=["\']_csrf["\'])',r'\1[REDACTED]\2',s)
    s=re.sub(r'(?i)(;CSUCAMPUSCRAFT_(?:USER|ADMIN)_SESSION=)[A-Za-z0-9.-]+',r'\1[REDACTED]',s)
    s=re.sub(r'(?im)^(Set-Cookie|Cookie):.*$',r'\1: [REDACTED]',s)
    s=re.sub(r'\$2[aby]\$\d\d\$[./A-Za-z0-9]{53}','[REDACTED-HASH]',s)
    return s
def save(path,text):path.write_text(scrub(text),encoding='utf-8',newline='\n')
def record(name,obj):
    with (EV/name).open('a',encoding='utf-8') as f:f.write(scrub(json.dumps(obj,ensure_ascii=False))+'\n')
def check(name,ok,detail=''):
    key=name;number=2
    while key in result['checks']:key=name+' ['+str(number)+']';number+=1
    result['checks'][key]={'passed':bool(ok),'detail':scrub(str(detail))}
    print(name+': '+('PASS' if ok else 'FAIL'),flush=True)
    if not ok:raise AssertionError(name)
def command(argv,**kw):
    global command_no
    command_no+=1;start=time.monotonic()
    p=subprocess.run([str(a) for a in argv],capture_output=True,creationflags=FLAG,**kw)
    record('commands.jsonl',{'sequence':command_no,'argv':[str(a) for a in argv],'exit_code':p.returncode,'elapsed_seconds':round(time.monotonic()-start,3)})
    return p
def git(*args):
    p=command([GIT,'-C',REPO,'-c','core.quotepath=false',*args],timeout=25)
    if p.returncode:raise RuntimeError('Read-only Git operation failed')
    return p.stdout
def freeport():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
def stop(p):
    if p.poll() is None:
        p.terminate()
        try:p.wait(timeout=10)
        except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
class Node:
    def __init__(self,tag='',attrs=None,parent=None):
        self.tag=tag;self.a=dict(attrs or []);self.parent=parent;self.children=[]
    def nodes(self):
        yield self
        for child in self.children:
            if isinstance(child,Node):yield from child.nodes()
    def find(self,predicate):return next((n for n in self.nodes() if predicate(n)),None)
    def all(self,predicate):return [n for n in self.nodes() if predicate(n)]
    def text(self):return ''.join(x.text() if isinstance(x,Node) else x for x in self.children)
class Parser(HTMLParser):
    VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
    def __init__(self,text):
        super().__init__(convert_charrefs=True);self.root=Node();self.stack=[self.root];self.feed(text)
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
    def __init__(self):
        self.jar=http.cookiejar.CookieJar()
        self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar),NoRedirect())
    def get(self,path='/',port=8080,recorded=True):
        global http_no
        req=urllib.request.Request(f'http://127.0.0.1:{port}'+path,headers={'Accept':'text/html'})
        try:r=self.opener.open(req,timeout=8)
        except urllib.error.HTTPError as e:r=e
        body=r.read();headers=dict(r.headers.items());text=body.decode('utf-8',errors='replace')
        dom=Parser(text).root
        for c in self.jar:
            if c.value:secret_values.append(c.value)
        for n in dom.all(lambda x:x.tag=='input' and x.a.get('name')=='_csrf'):
            if n.a.get('value'):secret_values.append(n.a['value'])
        if recorded:
            http_no+=1;filename=f'http-{http_no:03}-{port}.body'
            save(EV/filename,text)
            record('http.jsonl',{'sequence':http_no,'method':'GET','path':path,'status':r.code,'content_type':headers.get('Content-Type'),'location':headers.get('Location'),'cookie_values_recorded':False,'set_cookie_present':any(k.lower()=='set-cookie' for k in headers),'body_file':filename,'redacted':True})
        return r.code,headers,body,dom
def clean_href(href):
    u=urllib.parse.urlsplit(href)
    return urllib.parse.urlunsplit(('', '',u.path.split(';')[0],u.query,''))
def query(params):return '/products'+('?' + urllib.parse.urlencode(params) if params else '')
def marker(dom,key,value=None):return dom.find(lambda n:key in n.a and (value is None or n.a[key]==str(value)))
def product_nodes(dom):
    found=[]
    for n in dom.all(lambda n:'data-product-id' in n.a):
        parent=n.parent;duplicate=False
        while parent is not None and parent is not dom.parent:
            if 'data-product-id' in parent.a:duplicate=True;break
            parent=parent.parent
        if not duplicate:found.append(n)
    return found
def product_ids(dom):return [int(n.a['data-product-id']) for n in product_nodes(dom)]
mysqlport=freeport();env=os.environ.copy();env['MYSQL_PWD']=rootpass
MYSQLARGS=[MYSQL/'mysql.exe','--no-defaults','--no-login-paths','--protocol=TCP','--host=127.0.0.1',f'--port={mysqlport}','--user=root','--connect-timeout=2','--default-character-set=utf8mb4','--batch','--raw','--skip-column-names','--unbuffered']
def sql(q,db=None,fail_ok=False):
    p=command(MYSQLARGS+([f'--database={db}'] if db else []),input=q.encode('utf-8'),env=env,timeout=40)
    if p.returncode and not fail_ok:raise RuntimeError('Isolated SQL command failed; see command exit status')
    return p
def rows(q,db='csucampuscraft'):
    return sql("SET SESSION time_zone='+00:00';"+q,db).stdout.decode('utf-8').strip()
def literal(text):return "CONVERT(0x"+text.encode('utf-8').hex()+" USING utf8mb4)"
def snapshot():
    return {t:{'rows':int(rows('SELECT COUNT(*) FROM '+t)),'sha256':hashlib.sha256(sql("SET SESSION time_zone='+00:00';SELECT * FROM "+t+' ORDER BY id;','csucampuscraft').stdout).hexdigest()} for t in TABLES}
def expected(params):
    where=["p.status='ON_SALE'","c.parent_id IS NOT NULL"]
    if params.get('categoryId'):where.append('c.parent_id='+str(int(params['categoryId'])))
    typ=params.get('type','ALL')
    if typ!='ALL':
        suffix='_'+typ;where.append('RIGHT(c.code,'+str(len(suffix))+')='+literal(suffix))
    q=params.get('q','').strip()
    if q:
        escaped=q.replace('!','!!').replace('%','!%').replace('_','!_')
        where.append('p.name LIKE '+literal('%'+escaped+'%')+" ESCAPE '!'")
    select="SELECT p.id,p.sku,p.price,p.stock,p.name FROM product p JOIN category c ON c.id=p.category_id WHERE "+' AND '.join(where)+' ORDER BY '+ORDERS[params.get('sort','DEFAULT')]+';'
    raw=rows(select)
    result_rows=[]
    for line in raw.splitlines():
        cols=line.split('\t',4)
        result_rows.append({'id':int(cols[0]),'sku':cols[1],'price':cols[2],'stock':int(cols[3]),'name':cols[4]})
    record('sql-expected.jsonl',{'query':select,'parameters':params,'products':result_rows})
    return result_rows
def verify_list(client,params,name,db='csucampuscraft'):
    r=client.get(query(params));check(name+'-status',r[0]==200,'Public list read')
    dom=r[3];root=marker(dom,'data-product-count')
    check(name+'-markers',root is not None and marker(dom,'data-page-id','U02') is not None)
    expected_rows=expected(params) if db=='csucampuscraft' else []
    page=max(1,int(params.get('page',1)));size=int(params.get('size',6))
    check(name+'-count',int(root.a['data-product-count'])==len(expected_rows),len(expected_rows))
    check(name+'-page',int(root.a['data-page'])==page,page)
    check(name+'-size',int(root.a['data-page-size'])==size,size)
    start=(page-1)*size;wanted=expected_rows[start:start+size] if start<len(expected_rows) else []
    check(name+'-ids',product_ids(dom)==[p['id'] for p in wanted],{'actual':product_ids(dom),'expected':[p['id'] for p in wanted]})
    for n,p in zip(product_nodes(dom),wanted):
        check(name+'-card-'+str(p['id']),n.a.get('data-product-sku')==p['sku'] and decimal.Decimal(n.a['data-price'])==decimal.Decimal(p['price']) and int(n.a['data-stock'])==p['stock'])
    for n in dom.all(lambda x:x.tag=='a' and 'data-page-link' in x.a):
        href=clean_href(n.a.get('href',''));args=dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(href).query,keep_blank_values=True))
        equivalent=lambda p:{'categoryId':str(p.get('categoryId') or ''),'type':p.get('type','ALL'),'q':p.get('q','').strip(),'sort':p.get('sort','DEFAULT'),'size':str(p.get('size',6))}
        check(name+'-page-link-'+n.a['data-page-link'],equivalent(args)==equivalent(params),'All filter conditions retained')
    for f in dom.all(lambda n:n.tag=='form' and n.a.get('method','get').lower()=='get'):
        inputs=f.all(lambda n:n.tag=='input')
        check(name+'-read-form-'+str(len(result['checks'])),not any(n.a.get('name')=='_csrf' for n in inputs) and all(n.a.get('value')=='1' for n in inputs if n.a.get('name')=='page'))
    if page>max(1,(len(expected_rows)+size-1)//size):
        check(name+'-out-of-range-recovery',len(wanted)==0 and bool(dom.all(lambda x:x.tag=='a' and 'data-page-link' in x.a)),'Empty page has a valid page link')
    return dom
def home(client,db='csucampuscraft',expect_grad=True):
    r=client.get();dom=r[3];check(db+'-home-http',r[0]==200 and marker(dom,'data-page-id','U01') is not None)
    themes=rows('SELECT id,code,name FROM category WHERE parent_id IS NULL ORDER BY sort_order,id;',db)
    themes=[x.split('\t') for x in themes.splitlines()] if themes else []
    check(db+'-home-theme-count',int(marker(dom,'data-theme-count').a['data-theme-count'])==len(themes))
    actual=dom.all(lambda n:'data-theme-code' in n.a)
    check(db+'-home-theme-order',[n.a['data-theme-code'] for n in actual]==[x[1] for x in themes])
    for section,order,limit in [('newest','p.created_at DESC,p.id DESC',3),('featured','p.sort_order ASC,p.id ASC',4)]:
        box=marker(dom,'data-section',section)
        check(db+'-'+section+'-section',box is not None)
        expected_ids=[int(x) for x in rows("SELECT p.id FROM product p WHERE p.status='ON_SALE' ORDER BY "+order+' LIMIT '+str(limit)+';',db).splitlines()]
        check(db+'-'+section+'-ids',product_ids(box)==expected_ids,expected_ids)
    banner=marker(dom,'data-graduation-link')
    check(db+'-home-graduation',bool(banner)==bool(expect_grad))
    if banner:
        args=dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(clean_href(banner.a['href'])).query))
        gid=rows("SELECT id FROM category WHERE code='GRADUATION' AND parent_id IS NULL;",db)
        check(db+'-graduation-query',args.get('categoryId')==gid and args.get('type')=='ALL')
    for n in dom.all(lambda n:n.tag=='a' and ('data-secondary-category-id' in n.a or 'data-secondary-code' in n.a)):
        if 'data-secondary-category-id' in n.a:
            condition='id='+str(int(n.a['data-secondary-category-id']))
        else:condition='code='+literal(n.a['data-secondary-code'])
        child=rows('SELECT parent_id,code FROM category WHERE '+condition+';',db).split('\t')
        typ='STATIONERY' if child[1].endswith('_STATIONERY') else 'SOUVENIR'
        args=dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(clean_href(n.a['href'])).query))
        check(db+'-secondary-link-'+n.a.get('data-secondary-category-id',n.a.get('data-secondary-code','unknown')),args.get('categoryId')==child[0] and args.get('type')==typ)
    return dom
def detail(client,pid,name,empty=False):
    r=client.get('/products/'+str(pid));dom=r[3]
    data=rows('SELECT p.id,p.sku,p.price,p.stock,p.name,p.cover_image,c.name,pc.name,p.description FROM product p JOIN category c ON c.id=p.category_id JOIN category pc ON pc.id=c.parent_id WHERE p.id='+str(pid)+';')
    wanted=None if empty or not data else data.split('\t',8)
    if not wanted:
        check(name+'-404',r[0]==404);return dom
    check(name+'-200',r[0]==200 and marker(dom,'data-page-id','U03') is not None)
    root=marker(dom,'data-page-id','U03')
    check(name+'-identity',root.a.get('data-product-id')==str(pid) and root.a.get('data-product-sku')==wanted[1])
    text=dom.text()
    check(name+'-text',all(x in text for x in [wanted[1],wanted[4],wanted[6],wanted[7]]) and decimal.Decimal(root.a['data-price'])==decimal.Decimal(wanted[2]) and root.a.get('data-stock')==wanted[3])
    images=rows('SELECT id,sort_order FROM product_image WHERE product_id='+str(pid)+' ORDER BY sort_order,id;').splitlines()
    pairs=[x.split('\t') for x in images]
    gallery=dom.all(lambda n:'data-image-id' in n.a)
    check(name+'-gallery-order',[(n.a['data-image-id'],n.a['data-image-sort']) for n in gallery]==[tuple(x) for x in pairs])
    check(name+'-gallery-count',int(root.a['data-gallery-count'])==len(pairs))
    buttons=dom.all(lambda n:n.tag=='button' and ('购物车' in n.text() or '加购' in n.text()))
    def disabled(n):
        if 'disabled' in n.a:return True
        parent=n.parent
        while parent is not None:
            if parent.tag=='fieldset' and 'disabled' in parent.a:return True
            parent=parent.parent
        return False
    check(name+'-disabled-purchase',bool(buttons) and all(disabled(n) for n in buttons) and 'STEP07' in r[2].decode() and not dom.all(lambda n:n.tag=='form' and n.a.get('method','get').lower()!='get') and not dom.all(lambda n:n.tag=='a' and '/login' in n.a.get('href','')))
    if wanted[3]=='0':check(name+'-sold-out','售罄' in text)
    if not pairs:
        imgs=dom.all(lambda n:n.tag=='img');check(name+'-cover-fallback',bool(imgs) and urllib.parse.urlsplit(imgs[0].a.get('src','')).path.split(';')[0]=='/'+wanted[5])
    return dom
def browser(phase,cases):
    env_browser=os.environ.copy();env_browser['STEP03_BROWSER_OUT']=str(EV/'browser'/phase);env_browser['STEP03_BROWSER_CASES']=json.dumps(cases,ensure_ascii=False)
    p=command([RUNTIME/'node/bin/node.exe',HERE/'verify_browser.cjs'],env=env_browser,timeout=180)
    save(EV/('browser-'+phase+'.log'),p.stdout.decode(errors='replace')+p.stderr.decode(errors='replace'))
    check('browser-'+phase,p.returncode==0 and (EV/'browser'/phase/'result.json').is_file(),'Real Edge screenshots and DOM checks')
def launch(app,port,db):
    log=BASE/(app+'-'+db+'.log');h=log.open('wb');handles.append(h)
    e=os.environ.copy()
    for key in ['SPRING_APPLICATION_JSON','SPRING_CONFIG_LOCATION','SPRING_CONFIG_ADDITIONAL_LOCATION','JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVA_OPTIONS']:e.pop(key,None)
    dburl=f'jdbc:mysql://127.0.0.1:{mysqlport}/{db}'
    e.update(CSUCAMPUSCRAFT_DB_URL=dburl,CSUCAMPUSCRAFT_DB_USER='csucampuscraft',CSUCAMPUSCRAFT_DB_PASSWORD=apppass,SPRING_DATASOURCE_URL=dburl,SPRING_DATASOURCE_USERNAME='csucampuscraft',SPRING_DATASOURCE_PASSWORD=apppass,SPRING_PROFILES_ACTIVE='default',SPRING_SQL_INIT_MODE='never')
    argv=[JAVA,'-jar',REPO/app/'target'/f'{app}-0.0.1-SNAPSHOT.jar',f'--server.port={port}']
    p=subprocess.Popen([str(x) for x in argv],env=e,stdout=h,stderr=subprocess.STDOUT,creationflags=FLAG);processes.append(p)
    record('launches.jsonl',{'app':app,'port':port,'database':db,'database_port':mysqlport,'database_user':'csucampuscraft','password_supplied':True,'argv':[str(x) for x in argv]})
    until=time.monotonic()+50;cl=Client()
    while time.monotonic()<until:
        if p.poll() is not None:raise RuntimeError(app+' exited at startup')
        try:
            if cl.get(port=port,recorded=False)[0]==200:return p
        except (OSError,urllib.error.URLError):pass
        time.sleep(.2)
    raise RuntimeError(app+' initialization timeout')


restore_actions=[]
try:
    check('tested-code-head',git('rev-parse','HEAD').decode().strip()==TESTED)
    result['branch']=git('branch','--show-current').decode().strip()
    check('feature-branch',result['branch']=='feat/step03-catalog')
    save(EV/'git-input-status.txt',git('status','--short','--untracked-files=all').decode('utf-8'))
    save(EV/'implementation-diff.patch',git('diff',BASELINE+'..'+TESTED,'--','csucampuscraft-user','csucampuscraft-admin','.mvn','mvnw','mvnw.cmd').decode('utf-8'))
    inputs=[]
    for app in ['csucampuscraft-user','csucampuscraft-admin']:
        inputs.append(REPO/app/'pom.xml');inputs.extend(p for p in (REPO/app/'src').rglob('*') if p.is_file())
    inputs.extend(p for f in ['database','assets','.mvn'] for p in (REPO/f).rglob('*') if p.is_file())
    inputs.extend([REPO/'mvnw',REPO/'mvnw.cmd'])
    manifest=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(REPO).as_posix()+'\n' for p in sorted(inputs,key=lambda x:x.relative_to(REPO).as_posix()))
    save(EV/'runtime-inputs.sha256',manifest);result['runtime_manifest_sha256']=hashlib.sha256(manifest.encode()).hexdigest();result['runtime_file_count']=len(inputs)
    save(EV/'verify_step03.py',Path(__file__).read_text(encoding='utf-8-sig'))
    builddir=Path(os.environ.get('STEP03_BUILD_LOG_DIR',HERE.parent))
    exits=json.loads((builddir/'build-exits.json').read_text(encoding='utf-8-sig'))
    for app in ['user','admin']:
        text=(builddir/('build-'+app+'.log')).read_text(encoding='utf-8',errors='replace')
        check('wrapper-build-'+app,exits[app]==0 and 'BUILD SUCCESS' in text,'Actual repository Maven Wrapper build')
        save(EV/('build-'+app+'.log'),text)
    save(EV/'build-exits.json',json.dumps(exits,indent=2))
    versionenv=os.environ.copy();versionenv['JAVA_HOME']=str(JAVA.parent.parent)
    versionenv['PATH']=str(JAVA.parent)+';'+os.environ['SystemRoot']+'/System32;'+os.environ['SystemRoot']+';'+os.environ['SystemRoot']+'/System32/WindowsPowerShell/v1.0'
    versionenv.pop('MAVEN_HOME',None);versionenv.pop('M2_HOME',None);versionenv.pop('MAVEN_ARGS',None)
    versions=[]
    for args in [[JAVA,'-version'],[REPO/'mvnw.cmd','-v'],[MYSQL/'mysqld.exe','--version']]:
        p=command(args,env=versionenv,timeout=60);check('tool-version-'+str(len(versions)),p.returncode==0)
        versions.append(p.stdout.decode(errors='replace')+p.stderr.decode(errors='replace'))
    check('wrapper-maven-pin','Apache Maven 3.9.16' in versions[1],'Fresh subprocess PATH excludes Maven')
    save(EV/'versions.txt','\n'.join(versions))
    result['wrapper_version_without_maven_path']='3.9.16'
    for app in ['csucampuscraft-user','csucampuscraft-admin']:
        result[app+'_jar_sha256']=hashlib.sha256((REPO/app/'target'/f'{app}-0.0.1-SNAPSHOT.jar').read_bytes()).hexdigest()
    data=BASE/'mysql-data';data.mkdir()
    init=BASE/'mysql-init-private.sql';private_files.append(init)
    init.write_text("ALTER USER 'root'@'localhost' IDENTIFIED BY '"+rootpass+"';",encoding='utf-8')
    p=command([MYSQL/'mysqld.exe','--no-defaults','--initialize-insecure','--basedir=D:/MySQL',f'--datadir={data}',f'--log-error={BASE/"mysql-initialize.log"}'],timeout=45)
    check('isolated-mysql-created',p.returncode==0)
    h=(BASE/'mysql-server.log').open('wb');handles.append(h)
    server=subprocess.Popen([str(MYSQL/'mysqld.exe'),'--no-defaults','--basedir=D:/MySQL',f'--datadir={data}',f'--port={mysqlport}','--bind-address=127.0.0.1','--mysqlx=OFF',f'--init-file={init}',f'--pid-file={BASE/"mysql.pid"}','--console'],creationflags=FLAG,stdout=h,stderr=subprocess.STDOUT)
    until=time.monotonic()+35
    while time.monotonic()<until:
        if server.poll() is not None:raise RuntimeError('Private MySQL exited')
        p=sql('SELECT @@version,@@server_uuid,@@port;',fail_ok=True)
        if p.returncode==0:break
        time.sleep(.2)
    else:raise RuntimeError('Private MySQL readiness timeout')
    identity=p.stdout.decode().strip().split('\t')
    uuid=re.search(r'server-uuid=(.+)',(data/'auto.cnf').read_text()).group(1).strip()
    check('isolated-mysql-identity',identity[1]==uuid and int(identity[2])==mysqlport)
    result['mysql_version']=identity[0];result['mysql_port']=mysqlport;init.unlink()
    for db in ['csucampuscraft','csucampuscraft_structure']:
        sql('CREATE DATABASE '+db+' CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_ci;')
    sql("CREATE USER 'csucampuscraft'@'127.0.0.1' IDENTIFIED BY '"+apppass+"';")
    for db in ['csucampuscraft','csucampuscraft_structure']:
        sql('GRANT SELECT ON '+db+".* TO 'csucampuscraft'@'127.0.0.1';")
    save(EV/'application-read-only-grants.txt',rows("SHOW GRANTS FOR 'csucampuscraft'@'127.0.0.1';",db=None))
    sql((REPO/'database/01-schema.sql').read_text(encoding='utf-8-sig'),'csucampuscraft_structure')
    sql((REPO/'database/02-schema-with-demo.sql').read_text(encoding='utf-8-sig'),'csucampuscraft')
    plans=[]
    for query_sql in [
        "SELECT p.id FROM product p WHERE p.status='ON_SALE' ORDER BY p.sort_order,p.id LIMIT 6 OFFSET 0",
        "SELECT p.id FROM product p JOIN category c ON c.id=p.category_id JOIN category t ON t.id=c.parent_id AND t.parent_id IS NULL WHERE p.status='ON_SALE' AND t.id=1 ORDER BY p.sort_order,p.id LIMIT 6 OFFSET 0"
    ]:
        plans.append(query_sql+';'+chr(10)+rows('EXPLAIN '+query_sql+';'))
    save(EV/'query-plans.txt',chr(10).join(plans))
    original=snapshot();save(EV/'database-original.json',json.dumps(original,indent=2))
    check('seed-physical-product-count',original['product']['rows']==60)
    check('seed-visible-product-count',rows("SELECT COUNT(*) FROM product WHERE status='ON_SALE';")=='54')
    check('seed-draft-product-count',rows("SELECT COUNT(*) FROM product WHERE status='DRAFT';")=='6')
    for port in [8080,8081]:
        with socket.socket() as s:s.bind(('127.0.0.1',port))
    user=launch('csucampuscraft-user',8080,'csucampuscraft_structure')
    empty=Client();home(empty,'csucampuscraft_structure',False)
    verify_list(empty,{},'empty-default',db='csucampuscraft_structure')
    r=empty.get('/products/1');check('empty-detail-404',r[0]==404)
    browser('empty',[
        {'name':'empty-home','path':'/','kind':'home','status':200},
        {'name':'empty-products','path':'/products','kind':'list','status':200},
        {'name':'empty-detail','path':'/products/1','kind':'error','status':404}
    ])
    stop(user)
    user=launch('csucampuscraft-user',8080,'csucampuscraft');admin=launch('csucampuscraft-admin',8081,'csucampuscraft')
    cl=Client();home(cl)
    ar=Client().get(port=8081)
    check('admin-regression-home',ar[0]==200 and b'data-theme-count="5"' in ar[2] and b'data-csucampuscraft-app="admin"' in ar[2])
    for path in ['/login','/logout','/cart','/orders','/categories','/__verification/foundation']:
        check('forbidden-user-get-'+path.replace('/','_'),cl.get(path)[0]==404)
    for path in ['/products','/categories','/customers','/orders','/login']:
        check('unimplemented-admin-get-'+path.replace('/','_'),cl.get(path,8081)[0]==404)
    verify_list(cl,{},'demo-default')
    verify_list(cl,{'q':'   '},'blank-keyword')
    verify_list(cl,{'q':'😀'*120},'unicode-keyword-length120')
    for sort in ORDERS:
        for page in [1,2]:verify_list(cl,{'sort':sort,'size':50,'page':page},'sort-'+sort+'-'+str(page))
    for typ in ['ALL','STATIONERY','SOUVENIR']:
        verify_list(cl,{'type':typ},'type-cross-'+typ)
        verify_list(cl,{'categoryId':5,'type':typ,'q':'毕业','sort':'PRICE_ASC','size':2},'graduation-'+typ)
    for cid in range(1,6):verify_list(cl,{'categoryId':cid,'size':50},'theme-'+str(cid))
    for page in ['0','-10','-9223372036854775808','9223372036854775807']:
        verify_list(cl,{'page':page},'page-'+page)
    verify_list(cl,{'page':2,'size':1,'categoryId':5,'type':'STATIONERY','q':'毕业','sort':'PRICE_DESC'},'combined-page2')
    for params in [
        {'type':'INVALID'},{'type':'stationery'},{'sort':'price;DROP TABLE product'},
        {'size':0},{'size':51},{'size':'1.5'},{'page':'abc'},{'page':'1.2'},
        {'page':'9223372036854775808'},{'size':'9223372036854775808'},
        {'categoryId':'one'},{'categoryId':'9223372036854775808'},{'q':'a'*121},{'q':'😀'*121}
    ]:
        check('invalid-params-'+str(http_no),cl.get(query(params))[0]==400,params)
    for cid in [0,-1,999999,101,502]:
        check('unknown-or-secondary-theme-'+str(cid),cl.get(query({'categoryId':cid}))[0]==404)
    for path in ['/products/not-id','/products/9223372036854775808']:
        check('invalid-product-id-'+str(http_no),cl.get(path)[0]==400)
    for pid in [0,-1,999999,9223372036854775807]:
        check('unknown-product-id-'+str(pid),cl.get('/products/'+str(pid))[0]==404)
    check('draft-detail-404',cl.get('/products/30')[0]==404,'CSU-CLB-FOLDER-02')
    for pid,label in [(56,'graduation-box'),(47,'sold-out'),(36,'missing-cover')]:detail(cl,pid,label)
    check('gift-box-seed',rows("SELECT CONCAT(price,'/',stock) FROM product WHERE sku='CSU-GRAD-BOX-01';")=='49.00/12')
    noalbum=int(rows("SELECT p.id FROM product p LEFT JOIN product_image i ON i.product_id=p.id WHERE p.status='ON_SALE' GROUP BY p.id HAVING COUNT(i.id)=0 ORDER BY p.id LIMIT 1;"))
    detail(cl,noalbum,'no-album')
    detail(cl,1,'album-sequence')
    demo_cases=[
        {'name':'home','path':'/','kind':'home','status':200},
        {'name':'products','path':'/products','kind':'list','status':200},
        {'name':'combined','path':query({'categoryId':5,'type':'STATIONERY','q':'毕业','sort':'PRICE_ASC','size':2}),'kind':'list','status':200},
        {'name':'pagination','path':query({'page':2,'size':6}),'kind':'list','status':200},
        {'name':'out-of-range','path':query({'page':9223372036854775807}),'kind':'list','status':200},
        {'name':'unknown-category','path':query({'categoryId':999999}),'kind':'error','status':404},
        {'name':'secondary-category','path':query({'categoryId':101}),'kind':'error','status':404},
        {'name':'draft','path':'/products/30','kind':'error','status':404},
        {'name':'sold-out','path':'/products/47','kind':'detail','status':200,'placeholder':True},
        {'name':'gift-box','path':'/products/56','kind':'detail','status':200,'placeholder':True},
        {'name':'no-album','path':'/products/'+str(noalbum),'kind':'detail','status':200,'placeholder':True},
        {'name':'missing-cover','path':'/products/36','kind':'detail','status':200,'placeholder':True}
    ]
    demo_cases.extend({'name':'sort-'+s.lower(),'path':query({'sort':s}),'kind':'list','status':200} for s in ORDERS)
    demo_cases.extend({'name':'invalid-'+k,'path':query({k:v}),'kind':'error','status':400} for k,v in [('type','INVALID'),('sort','INVALID'),('size',51),('page','wrong')])
    demo_cases.extend({'name':'graduation-'+typ.lower(),'path':query({'categoryId':5,'type':typ,'q':'毕业','page':2,'size':1}),'kind':'list','status':200} for typ in ['ALL','STATIONERY','SOUVENIR'])
    browser('demo',demo_cases)
    after_demo=snapshot();save(EV/'database-after-demo.json',json.dumps(after_demo,indent=2))
    check('demo-app-zero-write',after_demo==original,'Seven full ordered row hashes, not just counts')
    # Read-only applications remain running; only the fixture controller below changes rows.
    old1=rows('SELECT name,description FROM product WHERE id=1;').split('\t',1)
    old2=rows('SELECT name,description FROM product WHERE id=2;').split('\t',1)
    restores=[
        'UPDATE product SET name='+literal(old1[0])+',description='+literal(old1[1])+',updated_at=updated_at WHERE id=1;',
        'UPDATE product SET name='+literal(old2[0])+',description='+literal(old2[1])+',updated_at=updated_at WHERE id=2;'
    ]
    restore_actions.extend(restores)
    fixture_name='STEP03 percent% under_score back\\slash bang! <script>alert(1)</script>'
    fixture_description='<script>fixture()</script> 普通文本 "双引号" 与单引号'
    sql('UPDATE product SET name='+literal(fixture_name)+',description='+literal(fixture_description)+',updated_at=updated_at WHERE id=1;','csucampuscraft')
    sql("UPDATE product SET name="+literal('STEP03 percentX underXscore backXslash bangX')+',updated_at=updated_at WHERE id=2;','csucampuscraft')
    record('fixtures.jsonl',{'fixture':'literal-search-and-escaped-description','temporary_product_ids':[1,2],'created_by':'isolated root SQL only','source_sql_changed':False,'app_account':'SELECT only'})
    fixture_before=snapshot();save(EV/'database-fixture-before.json',json.dumps(fixture_before,indent=2))
    for token in ['%','_','\\','!','STEP03',"<script>","%' OR 1=1 --"]:
        d=verify_list(cl,{'q':token},'literal-query-'+str(len(result['checks'])))
        if token in ['%','_','\\','!']:check('literal-single-match-'+str(ord(token)),product_ids(d)==[1])
    r=cl.get('/products/1');text=r[2].decode()
    check('description-escaped',r[0]==200 and '<script>fixture()' not in text and '&lt;script&gt;fixture()&lt;/script&gt;' in text)
    fixture_after=snapshot();save(EV/'database-fixture-after.json',json.dumps(fixture_after,indent=2))
    check('fixture-app-zero-write',fixture_before==fixture_after,'No app writes inside separately identified fixtures')
    browser('fixtures',[
        {'name':'literal-percent','path':query({'q':'%'}),'kind':'list','status':200},
        {'name':'literal-underscore','path':query({'q':'_'}),'kind':'list','status':200},
        {'name':'literal-backslash','path':query({'q':'\\'}),'kind':'list','status':200},
        {'name':'escaped-description','path':'/products/1','kind':'detail','status':200,'placeholder':True}
    ])
    for q in restores:sql(q,'csucampuscraft')
    restore_actions.clear()
    check('literal-fixtures-restored',snapshot()==original)
    grad=rows("SELECT id,code FROM category WHERE code='GRADUATION' AND parent_id IS NULL;").split('\t')
    restore_actions.append('UPDATE category SET code='+literal(grad[1])+',updated_at=updated_at WHERE id='+grad[0]+';')
    sql('UPDATE category SET code='+literal('GRADUATION_QA_HIDDEN')+',updated_at=updated_at WHERE id='+grad[0]+';','csucampuscraft')
    record('fixtures.jsonl',{'fixture':'missing-GRADUATION-code','temporary_category_id':int(grad[0]),'mechanism':'rename code while preserving id and updated_at; restore afterward','source_sql_changed':False})
    no_grad_before=snapshot();home(cl,expect_grad=False)
    browser('missing-graduation',[{'name':'no-graduation-banner','path':'/','kind':'home','status':200}])
    check('missing-graduation-app-zero-write',snapshot()==no_grad_before)
    for q in restore_actions:sql(q,'csucampuscraft')
    restore_actions.clear()
    home(cl)
    final=snapshot();save(EV/'database-final.json',json.dumps(final,indent=2))
    check('all-fixtures-restored',final==original)
    css_user=cl.get('/css/app.css');css_admin=cl.get('/css/app.css',8081)
    check('shared-css-response',css_user[2]==css_admin[2]==(REPO/'csucampuscraft-user/src/main/resources/static/css/app.css').read_bytes())
    svg=cl.get('/images/catalog-placeholder.svg')
    check('shared-image-response',svg[2]==(REPO/'assets/images/catalog-placeholder.svg').read_bytes())
    source_stable=all(hashlib.sha256((REPO/line.split('  ',1)[1]).read_bytes()).hexdigest()==line.split('  ',1)[0] for line in manifest.splitlines())
    check('source-inputs-stable',source_stable)
    result['overall']='PASS'
except Exception as e:
    result['overall']='FAIL';result['error']=scrub(type(e).__name__+': '+str(e))
    save(EV/'failure.txt',traceback.format_exc());print(result['error'],flush=True)
finally:
    if restore_actions and server and server.poll() is None:
        restored=True
        for q in restore_actions:
            try:sql(q,'csucampuscraft')
            except Exception:restored=False
        result['fixture_cleanup_succeeded']=restored
    for p in processes:stop(p)
    if server and server.poll() is None:
        try:
            command([MYSQL/'mysqladmin.exe','--no-defaults','--no-login-paths','--protocol=TCP','--host=127.0.0.1',f'--port={mysqlport}','--user=root','shutdown'],env=env,timeout=15);server.wait(timeout=15)
        except Exception:stop(server)
    for h in handles:h.close()
    for p in private_files:p.unlink(missing_ok=True)
    for p in BASE.glob('*.log'):save(EV/p.name,p.read_text(encoding='utf-8',errors='replace'))
    result['tracked_processes_stopped']=all(p.poll() is not None for p in processes) and (server is None or server.poll() is not None)
    save(EV/'result.json',json.dumps(result,ensure_ascii=False,indent=2))
    print('RESULT '+str(EV/'result.json'),flush=True)
if result['overall']!='PASS':raise SystemExit(1)

