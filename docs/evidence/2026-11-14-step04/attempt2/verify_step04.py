"""STEP04 isolated verification; external tools only, no repository business mutation."""
from pathlib import Path
from html.parser import HTMLParser
import os,sys,re,json,time,socket,secrets,hashlib,subprocess,datetime,traceback,urllib.request,urllib.error,urllib.parse,http.cookiejar,zipfile,struct
REPO=Path('D:/Github Projects/CSUCampusCraft')
HERE=Path(__file__).resolve().parent
RUNTIME=Path('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies')
GIT=Path('C:/Program Files/Git/cmd/git.exe')
JAVA=Path('C:/Users/Starmetor/.jdks/ms-21.0.12.1/bin/java.exe')
MYSQL=Path('D:/MySQL/bin')
BASELINE='f5372631f24dc265abda7eeeb2711584417abfe9'
TESTED=os.environ.get('STEP04_TESTED_CODE_SHA','')
if not re.fullmatch(r'[0-9a-f]{40}',TESTED):raise SystemExit('STEP04_TESTED_CODE_SHA must be exact 40-character implementation SHA')
RUN=sys.argv[1] if len(sys.argv)>1 else ''
if not re.fullmatch(r'attempt[1-9][0-9]*',RUN):raise SystemExit('Use a fresh attemptN')
BASE=HERE/'runtime'/RUN;EV=HERE/'evidence'/RUN
BASE.mkdir(parents=True,exist_ok=False);EV.mkdir(parents=True,exist_ok=False)
FLAG=subprocess.CREATE_NO_WINDOW
result={'date':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'baseline_git_sha':BASELINE,'tested_code_sha':TESTED,'checks':{},'scope':'STEP04 identity/login/logout/CSRF only; later business and TST-39 remain pending'}
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
    def __init__(self):self.jar=http.cookiejar.CookieJar();self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar),NoRedirect())
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
            http_no+=1;filename=f'http-{http_no:03}-{port}.body'
            save(EV/filename,text)
            record('http.jsonl',{'sequence':http_no,'method':method,'path':path,'port':port,'status':r.code,'content_type':h.get('Content-Type'),'location':h.get('Location'),'cookie_names':[c.name for c in self.jar],'cookie_values_recorded':False,'set_cookie_present':bool(r.headers.get_all('Set-Cookie',[])),'form_fields':sorted(form.keys()) if isinstance(form,dict) else None,'body_file':filename,'redacted':True})
        check('no-session-url-rewriting-'+str(http_no),';CSUCAMPUSCRAFT_USER_SESSION=' not in text and ';CSUCAMPUSCRAFT_ADMIN_SESSION=' not in text and ';CSUCAMPUSCRAFT_' not in h.get('Location',''))
        return r.code,h,body,dom
    def get(self,path='/',port=8080,recorded=True):return self.request(path,port,recorded=recorded)
    def post(self,path,form,port=8080):return self.request(path,port,method='POST',form=form)
def token(r):
    n=r[3].find(lambda x:x.tag=='input' and x.a.get('name')=='_csrf')
    return n.a.get('value') if n else None
def assert_page(r,status,name):
    check(name+'-status',r[0]==status,str(status))
    check(name+'-html',r[1].get('Content-Type','').startswith('text/html'))
    check(name+'-no-secrets',PASSWORD not in r[2].decode() and not re.search(r'\$2[aby]\$\d\d\$[./A-Za-z0-9]{53}',r[2].decode()))
    if status in (400,403,404,500):
        text=r[3].text()
        inline400=status==400 and r[3].find(lambda n:n.a.get('data-page-id') in ['U04','A01']) is not None and r[3].find(lambda n:'field-error' in n.a.get('class','')) is not None
        check(name+'-safe-error',(str(status) in text or inline400) and 'java.lang.' not in text and 'SELECT ' not in text and 'jdbc:mysql:' not in text)
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
    p=command(MYSQLARGS+([f'--database={db}'] if db else []),input=q.encode('utf-8'),env=env,timeout=40)
    if p.returncode and not fail_ok:
        save(EV/('sql-error-'+str(command_no)+'.json'),json.dumps({'query':q,'exit_code':p.returncode,'stderr':p.stderr.decode('utf-8',errors='replace')},ensure_ascii=False,indent=2))
        raise RuntimeError('Isolated SQL command failed')
    return p
def rows(q,db='csucampuscraft'):return sql("SET SESSION time_zone='+00:00';"+q,db).stdout.decode('utf-8').strip()
def literal(text):return "(CONVERT(0x"+text.encode('utf-8').hex()+" USING utf8mb4) COLLATE utf8mb4_0900_as_ci)"
def snapshot():return {t:{'rows':int(rows('SELECT COUNT(*) FROM '+t)),'sha256':hashlib.sha256(sql("SET SESSION time_zone='+00:00';SELECT * FROM "+t+' ORDER BY id;','csucampuscraft').stdout).hexdigest()} for t in TABLES}
def start_env():
    e=os.environ.copy()
    for k in ['SPRING_APPLICATION_JSON','SPRING_CONFIG_LOCATION','SPRING_CONFIG_ADDITIONAL_LOCATION','JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVA_OPTIONS']:e.pop(k,None)
    url=f'jdbc:mysql://127.0.0.1:{mysqlport}/csucampuscraft'
    e.update(CSUCAMPUSCRAFT_DB_URL=url,CSUCAMPUSCRAFT_DB_USER='csucampuscraft',CSUCAMPUSCRAFT_DB_PASSWORD=apppass,SPRING_DATASOURCE_URL=url,SPRING_DATASOURCE_USERNAME='csucampuscraft',SPRING_DATASOURCE_PASSWORD=apppass,SPRING_PROFILES_ACTIVE='default',SPRING_SQL_INIT_MODE='never')
    return e
def launch(app,port):
    log=BASE/(app+'.log');h=log.open('wb');handles.append(h)
    argv=[JAVA,'-jar',REPO/app/'target'/f'{app}-0.0.1-SNAPSHOT.jar',f'--server.port={port}']
    p=subprocess.Popen([str(x) for x in argv],env=start_env(),stdout=h,stderr=subprocess.STDOUT,creationflags=FLAG);processes.append(p)
    record('launches.jsonl',{'app':app,'port':port,'database':'csucampuscraft','database_port':mysqlport,'database_user':'csucampuscraft','password_supplied':True,'argv':[str(x) for x in argv]})
    until=time.monotonic()+55;cl=Client()
    while time.monotonic()<until:
        if p.poll() is not None:raise RuntimeError(app+' exited at startup')
        try:
            if cl.get('/login',port,recorded=False)[0]==200:return p
        except (OSError,urllib.error.URLError):pass
        time.sleep(.2)
    raise RuntimeError(app+' initialization timeout')
def fixture_update(uid,assignments,label):
    sql('UPDATE store_user SET '+assignments+' WHERE id='+str(uid)+';','csucampuscraft')
    record('fixtures.jsonl',{'fixture':label,'target_user_id':uid,'sql':assignments,'app_account':'SELECT only','source_sql_changed':False})
def restore_users():
    for uid,values in original_users.items():
        status,role,stamp=values
        sql('UPDATE store_user SET status='+literal(status)+',role='+literal(role)+',updated_at='+literal(stamp)+' WHERE id='+str(uid)+';','csucampuscraft')
def browser():
    e=start_env();e['STEP04_BROWSER_OUT']=str(EV/'browser');e['STEP04_VALID_PASSWORD']=PASSWORD;e['STEP04_INVALID_PASSWORD']=wrongpass
    p=command([RUNTIME/'node/bin/node.exe',HERE/'verify_browser.cjs'],env=e,timeout=180)
    save(EV/'browser.log',p.stdout.decode(errors='replace')+p.stderr.decode(errors='replace'))
    check('browser-real-forms',p.returncode==0 and (EV/'browser/result.json').is_file())
def session_probe():
    old=snapshot()
    for uid in [1,4]:fixture_update(uid,"updated_at='2026-11-14 03:04:05.123456'",'nonzero-microsecond-authStamp-probe')
    fixture_before=snapshot();save(EV/'database-probe-before.json',json.dumps(fixture_before,indent=2))
    for app,package in [('csucampuscraft-user','org.csucampuscraft.storefront'),('csucampuscraft-admin','org.csucampuscraft.admin')]:
        extracted=BASE/(app+'-probe');classes=extracted/'classes';libs=extracted/'lib';classes.mkdir(parents=True);libs.mkdir()
        jar=REPO/app/'target'/f'{app}-0.0.1-SNAPSHOT.jar'
        with zipfile.ZipFile(jar) as z:
            for n in z.namelist():
                if n.startswith('BOOT-INF/classes/') and not n.endswith('/'):
                    target=classes/n[len('BOOT-INF/classes/'):];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(n))
                elif n.startswith('BOOT-INF/lib/') and n.endswith('.jar'):(libs/Path(n).name).write_bytes(z.read(n))
        cp=str(classes)+';'+str(libs/'*')+';'+str(extracted)
        p=command([JAVA.parent/'javac.exe','-cp',cp,'-d',extracted,HERE/'AuthSessionProbe.java'],timeout=45)
        save(EV/(app+'-probe-compile.log'),p.stdout.decode(errors='replace')+p.stderr.decode(errors='replace'))
        check(app+'-probe-compile',p.returncode==0)
        e=start_env();e['STEP04_VALID_PASSWORD']=PASSWORD;e['STEP04_INVALID_PASSWORD']=wrongpass;e['STEP04_PROBE_PACKAGE']=package;e['STEP04_PROBE_PORT']=str(freeport())
        p=command([JAVA,'-cp',cp,'AuthSessionProbe'],env=e,timeout=65)
        save(EV/(app+'-session-probe.log'),p.stdout.decode(errors='replace')+p.stderr.decode(errors='replace'))
        check(app+'-native-session-probe',p.returncode==0 and '"overall":"PASS"' in p.stdout.decode(errors='replace'))
    check('session-probe-app-zero-write',snapshot()==fixture_before)
    restore_users()
    check('session-probe-fixtures-restored',snapshot()==old)

original_users={}
try:
    check('tested-code-head',git('rev-parse','HEAD').decode().strip()==TESTED)
    result['branch']=git('branch','--show-current').decode().strip()
    check('feature-branch',result['branch']=='feat/step04-auth')
    status=git('status','--short','--untracked-files=all').decode('utf-8')
    save(EV/'git-input-status.txt',status);check('tested-worktree-clean',not status.strip())
    save(EV/'implementation-diff.patch',git('diff',BASELINE+'..'+TESTED,'--','csucampuscraft-user','csucampuscraft-admin').decode('utf-8'))
    inputs=[]
    for app in ['csucampuscraft-user','csucampuscraft-admin']:
        inputs.append(REPO/app/'pom.xml');inputs.extend(p for p in (REPO/app/'src').rglob('*') if p.is_file())
    inputs.extend(p for d in ['database','assets','.mvn'] for p in (REPO/d).rglob('*') if p.is_file());inputs.extend([REPO/'mvnw',REPO/'mvnw.cmd'])
    manifest=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(REPO).as_posix()+'\n' for p in sorted(inputs,key=lambda x:x.relative_to(REPO).as_posix()))
    save(EV/'runtime-inputs.sha256',manifest);result['runtime_manifest_sha256']=hashlib.sha256(manifest.encode()).hexdigest();result['runtime_file_count']=len(inputs)
    for name in ['verify_step04.py','verify_browser.cjs','AuthSessionProbe.java']:save(EV/name,(HERE/name).read_text(encoding='utf-8-sig'))
    builddir=Path(os.environ.get('STEP04_BUILD_LOG_DIR',HERE.parent))
    exits=json.loads((builddir/'build-exits.json').read_text(encoding='utf-8-sig'))
    for app in ['user','admin']:
        text=(builddir/('build-'+app+'.log')).read_text(encoding='utf-8',errors='replace')
        check('wrapper-build-'+app,exits[app]==0 and 'BUILD SUCCESS' in text)
        save(EV/('build-'+app+'.log'),text)
    save(EV/'build-exits.json',json.dumps(exits,indent=2))
    versionenv=os.environ.copy();versionenv['JAVA_HOME']=str(JAVA.parent.parent)
    versionenv['PATH']=str(JAVA.parent)+';'+os.environ['SystemRoot']+'/System32;'+os.environ['SystemRoot']+';'+os.environ['SystemRoot']+'/System32/WindowsPowerShell/v1.0'
    for key in ['MAVEN_HOME','M2_HOME','MAVEN_ARGS']:versionenv.pop(key,None)
    versions=[]
    for args in [[JAVA,'-version'],[REPO/'mvnw.cmd','-v'],[MYSQL/'mysqld.exe','--version']]:
        p=command(args,env=versionenv,timeout=60);check('tool-version-'+str(len(versions)),p.returncode==0);versions.append(p.stdout.decode(errors='replace')+p.stderr.decode(errors='replace'))
    check('wrapper-maven-pin','Apache Maven 3.9.16' in versions[1]);save(EV/'versions.txt','\n'.join(versions))
    for app in ['csucampuscraft-user','csucampuscraft-admin']:result[app+'_jar_sha256']=hashlib.sha256((REPO/app/'target'/f'{app}-0.0.1-SNAPSHOT.jar').read_bytes()).hexdigest()
    data=BASE/'mysql-data';data.mkdir();init=BASE/'mysql-init-private.sql';private_files.append(init)
    init.write_text("ALTER USER 'root'@'localhost' IDENTIFIED BY '"+rootpass+"';",encoding='utf-8')
    p=command([MYSQL/'mysqld.exe','--no-defaults','--initialize-insecure','--basedir=D:/MySQL',f'--datadir={data}',f'--log-error={BASE/"mysql-initialize.log"}'],timeout=45)
    check('isolated-mysql-created',p.returncode==0)
    h=(BASE/'mysql-server.log').open('wb');handles.append(h)
    server=subprocess.Popen([str(MYSQL/'mysqld.exe'),'--no-defaults','--basedir=D:/MySQL',f'--datadir={data}',f'--port={mysqlport}','--bind-address=127.0.0.1','--mysqlx=OFF',f'--init-file={init}',f'--pid-file={BASE/"mysql.pid"}','--console'],stdout=h,stderr=subprocess.STDOUT,creationflags=FLAG)
    until=time.monotonic()+35
    while time.monotonic()<until:
        if server.poll() is not None:raise RuntimeError('Private MySQL startup failed')
        p=sql('SELECT @@version,@@server_uuid,@@port;',fail_ok=True)
        if p.returncode==0:break
        time.sleep(.2)
    else:raise RuntimeError('Private MySQL readiness timeout')
    identity=p.stdout.decode().strip().split('\t');uuid=re.search(r'server-uuid=(.+)',(data/'auto.cnf').read_text()).group(1).strip()
    check('isolated-mysql-identity',identity[1]==uuid and int(identity[2])==mysqlport)
    result['mysql_version']=identity[0];result['mysql_port']=mysqlport;init.unlink()
    sql('CREATE DATABASE csucampuscraft CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_ci;')
    sql("CREATE USER 'csucampuscraft'@'127.0.0.1' IDENTIFIED BY '"+apppass+"';")
    sql("GRANT SELECT ON csucampuscraft.* TO 'csucampuscraft'@'127.0.0.1';")
    save(EV/'application-read-only-grants.txt',rows("SHOW GRANTS FOR 'csucampuscraft'@'127.0.0.1';",db=None))
    sql((REPO/'database/02-schema-with-demo.sql').read_text(encoding='utf-8-sig'),'csucampuscraft')
    original=snapshot();save(EV/'database-original.json',json.dumps(original,indent=2))
    for uid in [1,4]:original_users[uid]=rows('SELECT status,role,updated_at FROM store_user WHERE id='+str(uid)+';').split('\t')
    for port in [8080,8081]:
        with socket.socket() as s:s.bind(('127.0.0.1',port))
    launch('csucampuscraft-user',8080);launch('csucampuscraft-admin',8081)

    # Anonymous boundaries and identity-before-CSRF precedence.
    for port in [8080,8081]:
        cl=Client();login_page(cl,port,'first-no-cookie-'+str(port));login_page(cl,port,'with-cookie-'+str(port))
        for static in ['/css/app.css','/js/app.js','/images/catalog-placeholder.svg']:
            check('public-static-'+str(port)+static,cl.get(static,port)[0]==200)
        for bare in ['/css','/js','/images']:
            assert_page(cl.get(bare,port),404,'public-bare-static-'+str(port)+bare)
        paths=['/cart','/checkout','/orders','/orders/QA-NOT-EXISTS'] if port==8080 else ['/','/categories','/products','/orders','/customers']
        for path in paths:
            target=path+('?page=2' if path=='/orders' else '')
            is_login_redirect(Client().get(target,port),'protected-get-'+str(port)+path,target)
        for path in ['/logout','/orders']:
            is_login_redirect(Client().post(path,{},port),'anonymous-post-before-csrf-'+str(port)+path,'/')
        r=Client().request('/orders',port,method='POST',data=b'{invalid json',content_type='application/json')
        is_login_redirect(r,'anonymous-malformed-post-before-csrf-'+str(port),'/')
    assert_page(Client().get('/'),200,'user-home-public')
    assert_page(Client().get('/products'),200,'user-list-public')
    is_login_redirect(Client().get('/',8081),'admin-home-private','/')
    is_login_redirect(Client().get('/QA-UNIMPLEMENTED-PREFIX',8081),'admin-any-unknown-prefix-private','/')
    # Login CSRF and server-side field validation; no viable identity on failure.
    for port in [8080,8081]:
        cl=Client();page=login_page(cl,port,'csrf-form-'+str(port))
        for form,label in [({'username':'alice','password':PASSWORD},'missing'),({'username':'alice','password':PASSWORD,'_csrf':'0'*64},'wrong')]:
            assert_page(cl.post('/login',form,port),403,'login-csrf-'+label+'-'+str(port))
        for form,label in [({'password':PASSWORD},'missing-username'),({'username':'alice'},'missing-password'),({'username':' '*5,'password':PASSWORD},'blank-username'),({'username':'a'*51,'password':PASSWORD},'long-username'),({'username':'alice','password':''},'empty-password')]:
            form['_csrf']=token(page)
            r=cl.post('/login',form,port);assert_page(r,400,'login-fields-'+label+'-'+str(port))
            p=r[3].find(lambda n:n.tag=='input' and n.a.get('name')=='password')
            check('login-fields-password-empty-'+label+'-'+str(port),p is None or not p.a.get('value'))
        failures=[]
        for username,pwd,label in [('alice' if port==8080 else 'admin',wrongpass,'wrong-password'),('QA_NO_ACCOUNT',PASSWORD,'unknown-account'),('disabled',PASSWORD,'disabled-account'),('admin' if port==8080 else 'alice',PASSWORD,'wrong-role'),('alice' if port==8080 else 'admin',PASSWORD+' ','password-not-trimmed')]:
            cl=Client();r,_,_=login(cl,port,username,pwd,name='failed-'+label+'-'+str(port))
            assert_page(r,200,'credentials-'+label+'-'+str(port))
            n=r[3].find(lambda n:'data-auth-error' in n.a)
            check('credentials-common-error-present-'+label+'-'+str(port),n is not None and bool(n.text().strip()))
            failures.append(n.text().strip())
            check('credentials-no-logout-'+label+'-'+str(port),not has_logout(r))
            is_login_redirect(cl.get('/cart' if port==8080 else '/',port),'credentials-no-identity-'+label+'-'+str(port))
        check('all-authentication-failures-identical-'+str(port),len(set(failures))==1)
    after_failures=snapshot();save(EV/'database-after-failures.json',json.dumps(after_failures,indent=2));check('failed-authentication-zero-write',after_failures==original)

    # Correct login, ID rotation, csrf retained, unimplemented paths and returnUrl.
    for port in [8080,8081]:
        cl=Client();r,old,t=login(cl,port,name='good-'+str(port))
        check('good-login-303-'+str(port),r[0]==303 and r[1].get('Location')=='/')
        check('session-id-changed-'+str(port),bool(old) and bool(cl.cookie(port)) and old!=cl.cookie(port))
        logged_in(cl,port,'authorized-entry-'+str(port))
        nextform=login_page(cl,port,'retained-csrf-'+str(port))
        check('csrf-retained-after-login-'+str(port),token(nextform)==t)
        for path in (['/cart','/checkout','/orders','/orders/QA-NOT-EXISTS'] if port==8080 else ['/categories','/products','/orders','/customers']):
            assert_page(cl.get(path,port),404,'authenticated-unimplemented-'+str(port)+path)
        if port==8081:assert_page(cl.get('/QA-UNIMPLEMENTED-PREFIX',port),404,'admin-unknown-prefix-after-auth')
        assert_page(cl.post('/orders',{'_csrf':t},port),404,'authenticated-valid-csrf-unimplemented-post-'+str(port))
        assert_page(cl.post('/orders',{},port),403,'authenticated-missing-csrf-'+str(port))
        logged_in(cl,port,'csrf-failure-does-not-logout-'+str(port))
        assert_page(cl.post('/login',{'username':'QA_NO_ACCOUNT','password':wrongpass},port),403,'relogin-bad-csrf-'+str(port))
        logged_in(cl,port,'bad-csrf-relogin-preserves-identity-'+str(port))
        bad=cl.post('/login',{'username':'QA_NO_ACCOUNT','password':wrongpass,'_csrf':t},port)
        assert_page(bad,200,'relogin-bad-credentials-'+str(port))
        check('failed-relogin-no-stale-user-nav-'+str(port),not has_logout(bad))
        is_login_redirect(cl.get('/cart' if port==8080 else '/',port),'failed-relogin-clears-old-identity-'+str(port))
        valid='/orders?page=2' if port==8080 else '/products?page=2'
        cl=Client();first=cl.get(valid,port);is_login_redirect(first,'returnUrl-challenge-'+str(port),valid)
        r,_,_=login(cl,port,return_url=valid,name='valid-return-'+str(port))
        check('valid-return-url-'+str(port),r[0]==303 and r[1].get('Location')==valid)
        assert_page(cl.get(valid,port),404,'allowed-return-unimplemented-'+str(port))
        for url in ['https://example.invalid/','//example.invalid/','/../cart','/logout','/login','/products/%2f..','/products?x=%250d%250aLocation%3Aevil']:
            cl=Client();r,_,_=login(cl,port,return_url=url,name='invalid-return-'+str(port))
            check('invalid-return-fallback-'+str(port)+'-'+str(len(result['checks'])),r[0]==303 and r[1].get('Location')=='/')
    check('successful-authentication-zero-write',snapshot()==original)
    # Same actual cookie jar on same host contains both independently authenticated sessions.
    both=Client();ru,_,tu=login(both,8080,name='both-user');ra,_,ta=login(both,8081,name='both-admin')
    check('both-cookie-names-independent',both.cookie(8080) is not None and both.cookie(8081) is not None and both.cookie(8080)!=both.cookie(8081))
    check('cross-end-csrf-rejected',both.post('/logout',{'_csrf':tu},8081)[0]==403)
    logged_in(both,8081,'admin-survives-cross-token')
    r=both.post('/logout',{'_csrf':tu},8080);check('user-logout-303',r[0]==303 and r[1].get('Location')=='/')
    is_login_redirect(both.get('/cart',8080),'user-logged-out')
    logged_in(both,8081,'admin-survives-user-logout')
    _,_,tu=login(both,8080,name='both-user-again')
    r=both.post('/logout',{'_csrf':ta},8081);check('admin-logout-fixed-login-303',r[0]==303 and r[1].get('Location')=='/login')
    is_login_redirect(both.get('/',8081),'admin-logged-out')
    logged_in(both,8080,'user-survives-admin-logout')
    check('login-logout-zero-write',snapshot()==original)

    # Controlled root fixtures verify per-request account, role and microsecond checks.
    for port,uid in [(8080,1),(8081,4)]:
        target='/cart' if port==8080 else '/'
        cl=Client();r,_,_=login(cl,port,name='before-disable-'+str(port))
        fixture_update(uid,"status='DISABLED',updated_at=GREATEST(CURRENT_TIMESTAMP(6),updated_at+INTERVAL 1 MICROSECOND)",'disable-authenticated-account')
        before=snapshot()
        is_login_redirect(cl.get(target,port),'disabled-read-clears-'+str(port))
        is_login_redirect(cl.post('/orders',{},port),'disabled-write-before-csrf-'+str(port))
        check('disabled-app-zero-write-'+str(port),snapshot()==before)
        restore_users();is_login_redirect(cl.get(target,port),'reenabled-old-session-stays-invalid-'+str(port))
        r,_,_=login(cl,port,name='reenabled-new-login-'+str(port));check('reenabled-fresh-login-'+str(port),r[0]==303)
        logged_in(cl,port,'reenabled-entry-'+str(port))
        other_role='ADMIN' if port==8080 else 'CUSTOMER'
        fixture_update(uid,'role='+literal(other_role)+',updated_at=updated_at','role-mismatch-stamp-preserved')
        before=snapshot();assert_page(cl.get(target,port),403,'authenticated-role-mismatch-'+str(port));check('role-rejection-zero-write-'+str(port),snapshot()==before)
        restore_users()
        cl=Client();r,_,_=login(cl,port,name='before-microsecond-'+str(port))
        fixture_update(uid,'updated_at=updated_at+INTERVAL 1 MICROSECOND','one-microsecond-auth-stamp-change')
        before=snapshot();is_login_redirect(cl.get(target,port),'microsecond-change-rejected-'+str(port));check('stamp-rejection-zero-write-'+str(port),snapshot()==before)
        restore_users()
    check('main-fixtures-restored',snapshot()==original)
    session_probe()
    browser()
    final=snapshot();save(EV/'database-final.json',json.dumps(final,indent=2));check('all-seven-tables-restored',final==original)
    check('runtime-inputs-stable',all(hashlib.sha256((REPO/line.split('  ',1)[1]).read_bytes()).hexdigest()==line.split('  ',1)[0] for line in manifest.splitlines()))
    result['overall']='PASS'
except Exception as e:
    result['overall']='FAIL';result['error']=scrub(type(e).__name__+': '+str(e));save(EV/'failure.txt',traceback.format_exc());print(result['error'],flush=True)
finally:
    if original_users and server and server.poll() is None:
        try:restore_users();result['fixture_cleanup_succeeded']=True
        except Exception:result['fixture_cleanup_succeeded']=False
    for p in processes:stop(p)
    if server and server.poll() is None:
        try:command([MYSQL/'mysqladmin.exe','--no-defaults','--no-login-paths','--protocol=TCP','--host=127.0.0.1',f'--port={mysqlport}','--user=root','shutdown'],env=env,timeout=15);server.wait(timeout=15)
        except Exception:stop(server)
    for h in handles:h.close()
    for p in private_files:p.unlink(missing_ok=True)
    for p in BASE.glob('*.log'):save(EV/p.name,p.read_text(encoding='utf-8',errors='replace'))
    result['tracked_processes_stopped']=all(p.poll() is not None for p in processes) and (server is None or server.poll() is not None)
    result['http_records']=http_no
    save(EV/'result.json',json.dumps(result,ensure_ascii=False,indent=2));print('RESULT '+str(EV/'result.json'),flush=True)
if result['overall']!='PASS':raise SystemExit(1)

