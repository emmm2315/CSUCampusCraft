"""STEP02 isolated HTTP verification. No framework dependency; run only after root approves."""
from pathlib import Path
import os,sys,re,json,time,socket,secrets,hashlib,subprocess,datetime,traceback,zipfile,urllib.request,urllib.error,urllib.parse,http.cookiejar,html
from html.parser import HTMLParser

REPO=Path('D:/Github Projects/CSUCampusCraft')
HERE=Path(__file__).resolve().parent
RUNTIME=Path('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1111-574-0_26.1111.574.0_x64__3k8sg7r9htsxt/dependencies')
GIT=RUNTIME/'native/git/cmd/git.exe'
JAVA=Path('C:/Users/Starmetor/.jdks/ms-21.0.12.1/bin')
MYSQL=Path('D:/MySQL/bin')
MAVEN=Path('C:/Users/Starmetor/.m2/wrapper/dists/apache-maven-3.9.16/0daed3be3ebd1c706f0e69e8b07c6b73f5cc4ea3dfce72a8d0ec2e849ca2ddb0/bin/mvn.cmd')
BASELINE='022f50196ceb7b89880dabe1c369360e8f6136c3'
TESTED=os.environ.get('STEP02_TESTED_CODE_SHA','b35b0a48a0fb0e60919a41ddfe4496c96ee236b0')
if not re.fullmatch(r'[0-9a-f]{40}',TESTED):raise SystemExit('Exact tested code SHA required')
FLAG=subprocess.CREATE_NO_WINDOW
RUN=sys.argv[1] if len(sys.argv)>1 else 'attempt1'
if not re.fullmatch(r'attempt[0-9]+',RUN):raise SystemExit('Choose attemptN')
BASE=HERE/'runtime'/RUN
EV=HERE/'evidence'/RUN
BASE.mkdir(parents=True,exist_ok=False)
EV.mkdir(parents=True,exist_ok=False)
result={'date':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'baseline_git_sha':BASELINE,'tested_code_sha':TESTED,'source_state':'exact implementation commit; documentation and verification evidence will be committed separately','checks':{},'profile_boundaries':{'default':'verification probes absent','verification':'non-business probes only'}}
secret_values=[]
handles=[]
processes=[]
server=None
rootpass=secrets.token_urlsafe(28)
apppass=secrets.token_urlsafe(28)
secret_values.extend([rootpass,apppass])
http_no=0
commands_no=0
private_files=[]
def scrub_text(s):
    for v in sorted(set(secret_values),key=len,reverse=True):
        if len(v)>=8:s=s.replace(v,'[REDACTED]')
    s=re.sub(r'(?i)(name=["\']_csrf["\'][^>]*value=["\'])[^"\']*(["\'])',r'\1[REDACTED]\2',s)
    s=re.sub(r'(?i)(value=["\'])[^"\']*(["\'][^>]*name=["\']_csrf["\'])',r'\1[REDACTED]\2',s)
    s=re.sub(r'(?im)^(Set-Cookie|Cookie):.*$',r'\1: [REDACTED]',s)
    return s
def save_text(path,value):
    path.write_text(scrub_text(value),encoding='utf-8',newline='\n')
def append_json(filename,value):
    with (EV/filename).open('a',encoding='utf-8') as f:f.write(scrub_text(json.dumps(value,ensure_ascii=False))+'\n')
def check(name,ok,detail=''):
    result['checks'][name]={'passed':bool(ok),'detail':scrub_text(str(detail))}
    print(name+': '+('PASS' if ok else 'FAIL'),flush=True)
    if not ok:raise AssertionError(name)
def command(argv,**kw):
    global commands_no
    commands_no+=1
    start=time.monotonic()
    p=subprocess.run([str(v) for v in argv],capture_output=True,creationflags=FLAG,**kw)
    append_json('commands.jsonl',{'sequence':commands_no,'argv':[str(v) for v in argv],'exit_code':p.returncode,'elapsed_seconds':round(time.monotonic()-start,3)})
    return p
def git(*a):
    p=command([GIT,'-C',REPO,'-c','core.quotepath=false',*a],timeout=20)
    if p.returncode:raise RuntimeError('Git read failed')
    return p.stdout
def freeport():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
def stop(p):
    if p.poll() is None:
        p.terminate()
        try:p.wait(timeout=10)
        except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):return None
class TokenParser(HTMLParser):
    def __init__(self):
        super().__init__();self.tokens=[];self.labels=[];self.inputs=[];self.ids=[];self.links=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if a.get('id'):self.ids.append(a['id'])
        if tag=='label':self.labels.append(a.get('for'))
        if tag=='input':
            self.inputs.append(a)
            if a.get('name')=='_csrf':self.tokens.append(a.get('value',''))
        if tag=='a':self.links.append(a.get('href',''))
class Client:
    def __init__(self):
        self.jar=http.cookiejar.CookieJar()
        self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar),NoRedirect())
    def request(self,port,path='/',method='GET',form=None,headers=None,record=True):
        global http_no
        data=None if form is None else urllib.parse.urlencode(form,doseq=True).encode()
        h=dict(headers or {})
        if data is not None:h.setdefault('Content-Type','application/x-www-form-urlencoded')
        req=urllib.request.Request(f'http://127.0.0.1:{port}'+path,data=data,headers=h,method=method)
        try:r=self.opener.open(req,timeout=6)
        except urllib.error.HTTPError as e:r=e
        body=r.read();status=r.code;rh=dict(r.headers.items())
        text=body.decode('utf-8',errors='replace')
        parser=TokenParser();parser.feed(text)
        for token in parser.tokens:
            if token and token!='[REDACTED]':secret_values.append(token)
        for cookie in self.jar:
            if cookie.value:secret_values.append(cookie.value)
        if record:
            http_no+=1
            cleaned=scrub_text(text)
            filename=f'http-{http_no:03}-{port}.body'
            if 'image/' in rh.get('Content-Type','') and not 'svg' in rh.get('Content-Type',''):
                bodyhash=hashlib.sha256(body).hexdigest()
                save_text(EV/filename,'[BINARY BODY OMITTED] sha256='+bodyhash)
            else:save_text(EV/filename,cleaned)
            append_json('http.jsonl',{'sequence':http_no,'method':method,'path':path,'request_form_fields':list(dict(form or []).keys()) if not isinstance(form,dict) else list(form.keys()),'status':status,'location':rh.get('Location'),'content_type':rh.get('Content-Type'),'cookie_header_recorded':False,'set_cookie_present':any(k.lower()=='set-cookie' for k in rh),'body_file':filename,'body_is_redacted':True})
        return status,rh,body
    def token(self,port,path='/__verification/foundation'):
        status,headers,body=self.request(port,path)
        parser=TokenParser();parser.feed(body.decode())
        check('csrf-form-token-'+str(port),status==200 and len(parser.tokens)==1 and bool(parser.tokens[0]),'Exactly one hidden token, raw value excluded')
        return parser.tokens[0],parser,body
def launch(app,port,db='csucampuscraft',profile=None):
    log_path=BASE/(app+'-'+(profile or 'default')+'-'+db+'.log')
    handle=log_path.open('wb');handles.append(handle)
    env=os.environ.copy()
    env.update(CSUCAMPUSCRAFT_DB_URL=f'jdbc:mysql://127.0.0.1:{mysqlport}/{db}',CSUCAMPUSCRAFT_DB_USER='csucampuscraft',CSUCAMPUSCRAFT_DB_PASSWORD=apppass)
    argv=[JAVA/'java.exe','-jar',REPO/app/'target'/f'{app}-0.0.1-SNAPSHOT.jar',f'--server.port={port}']
    if profile:argv.append('--spring.profiles.active='+profile)
    p=subprocess.Popen([str(v) for v in argv],env=env,stdout=handle,stderr=subprocess.STDOUT,creationflags=FLAG)
    processes.append(p)
    append_json('launches.jsonl',{'app':app,'profile':profile or 'default','port':port,'database_url':env['CSUCAMPUSCRAFT_DB_URL'],'database_user':'csucampuscraft','password_supplied':True,'argv':[str(v) for v in argv]})
    ready=Client();until=time.monotonic()+50
    while time.monotonic()<until:
        if p.poll() is not None:raise RuntimeError(app+' startup exited')
        try:
            r=ready.request(port,record=False)
            if r[0]==200:return p
        except (OSError,urllib.error.URLError):pass
        time.sleep(.2)
    raise RuntimeError(app+' startup timed out')
mysqlport=freeport()
env=os.environ.copy();env['MYSQL_PWD']=rootpass
mysqlargs=[MYSQL/'mysql.exe','--no-defaults','--no-login-paths','--protocol=TCP','--host=127.0.0.1',f'--port={mysqlport}','--user=root','--connect-timeout=2','--default-character-set=utf8mb4','--batch','--raw','--skip-column-names','--unbuffered']
def sql(q,db=None,fail_ok=False):
    p=command(mysqlargs+([f'--database={db}'] if db else []),input=q.encode('utf-8'),env=env,timeout=35)
    if p.returncode and not fail_ok:raise RuntimeError('Isolated SQL command failed: '+scrub_text(p.stderr.decode(errors='replace')[:250]))
    return p
def rows(q,db='csucampuscraft'):return sql(q,db).stdout.decode('utf-8').strip()
tables=['store_user','category','product','product_image','cart_item','sales_order','sales_order_item']
def snapshot():
    out={}
    for t in tables:
        data=sql("SET SESSION time_zone='+00:00'; SELECT * FROM "+t+' ORDER BY id;','csucampuscraft').stdout
        out[t]={'rows':int(rows('SELECT COUNT(*) FROM '+t)),'sha256':hashlib.sha256(data).hexdigest()}
    return out
def count(client,port):
    r=client.request(port,'/__verification/counter')
    check('counter-http-'+str(port),r[0]==200,'Verification-only read')
    return json.loads(r[2])['acceptedPosts']
try:
    check('tested-code-head',git('rev-parse','HEAD').decode().strip()==TESTED,'Exact implementation commit based on user-supplied M0 baseline')
    result['branch']=git('branch','--show-current').decode().strip()
    save_text(EV/'git-input-status.txt',git('status','--short','--untracked-files=all').decode('utf-8'))
    save_text(EV/'runtime-input-diff.patch',git('diff',BASELINE+'..'+TESTED,'--','csucampuscraft-user','csucampuscraft-admin').decode('utf-8'))
    inputs=[]
    for app in ['csucampuscraft-user','csucampuscraft-admin']:
        inputs.append(REPO/app/'pom.xml');inputs.extend(p for p in (REPO/app/'src').rglob('*') if p.is_file())
    inputs.extend(p for folder in ['database','assets'] for p in (REPO/folder).rglob('*') if p.is_file())
    manifest=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(REPO).as_posix()+'\n' for p in sorted(inputs,key=lambda p:p.relative_to(REPO).as_posix()))
    save_text(EV/'runtime-inputs.sha256',manifest)
    result['runtime_manifest_sha256']=hashlib.sha256(manifest.encode()).hexdigest()
    result['runtime_file_count']=len(inputs)
    for kind in ['user','admin']:
        buildlog=HERE.parent/('build-'+kind+'.log')
        content=buildlog.read_text(encoding='utf-8',errors='replace')
        check('build-'+kind,'BUILD SUCCESS' in content,'Root ran actual repository Maven verify with exit 0')
        save_text(EV/('build-'+kind+'.log'),content)
    versions=[]
    for a in [[JAVA/'java.exe','-version'],[MAVEN,'-v'],[MYSQL/'mysqld.exe','--version']]:
        ve=os.environ.copy();ve['JAVA_HOME']=str(JAVA.parent)
        p=command(a,env=ve,timeout=20);check('version-'+str(len(versions)),p.returncode==0)
        versions.append(p.stdout.decode(errors='replace')+p.stderr.decode(errors='replace'))
    save_text(EV/'versions.txt','\n'.join(versions))
    for app in ['csucampuscraft-user','csucampuscraft-admin']:
        jar=REPO/app/'target'/f'{app}-0.0.1-SNAPSHOT.jar'
        result[app+'_jar_sha256']=hashlib.sha256(jar.read_bytes()).hexdigest()
        classes=BASE/(app+'-classes');libs=BASE/(app+'-libs')
        classes.mkdir();libs.mkdir()
        with zipfile.ZipFile(jar) as z:
            names=z.namelist()
            check(app+'-only-crypto',all('spring-security-' not in n or 'spring-security-crypto-' in n for n in names),'No security filter-chain starter packaged')
            for n in names:
                if n.startswith('BOOT-INF/classes/') and not n.endswith('/'):
                    dst=classes/n.removeprefix('BOOT-INF/classes/');dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(z.read(n))
                if n.startswith('BOOT-INF/lib/') and n.endswith('.jar'):(libs/Path(n).name).write_bytes(z.read(n))
    data=BASE/'mysql-data';data.mkdir()
    init=BASE/'mysql-init-private.sql';private_files.append(init)
    init.write_text("ALTER USER 'root'@'localhost' IDENTIFIED BY '"+rootpass+"';",encoding='utf-8')
    p=command([MYSQL/'mysqld.exe','--no-defaults','--initialize-insecure','--basedir=D:/MySQL',f'--datadir={data}',f'--log-error={BASE/"mysql-initialize.log"}'],timeout=45)
    check('isolated-mysql-created',p.returncode==0,'New private datadir; no existing MySQL service')
    mh=(BASE/'mysql-server.log').open('wb');handles.append(mh)
    server=subprocess.Popen([str(MYSQL/'mysqld.exe'),'--no-defaults','--basedir=D:/MySQL',f'--datadir={data}',f'--port={mysqlport}','--bind-address=127.0.0.1','--mysqlx=OFF',f'--init-file={init}',f'--pid-file={BASE/"mysql.pid"}','--console'],creationflags=FLAG,stdout=mh,stderr=subprocess.STDOUT)
    until=time.monotonic()+35
    while time.monotonic()<until:
        if server.poll() is not None:raise RuntimeError('Private MySQL exited')
        p=sql('SELECT @@version,@@server_uuid,@@port;',fail_ok=True)
        if p.returncode==0:break
        time.sleep(.2)
    else:raise RuntimeError('Private MySQL readiness timeout')
    identity=p.stdout.decode().strip().split('\t')
    uuid=re.search(r'server-uuid=(.+)',(data/'auto.cnf').read_text()).group(1).strip()
    check('isolated-mysql-identity',identity[1]==uuid and int(identity[2])==mysqlport,'UUID and bound port match private datadir before mutation')
    result['mysql_version']=identity[0];result['mysql_port']=mysqlport
    init.unlink()
    for db in ['csucampuscraft','csucampuscraft_structure']:
        sql('CREATE DATABASE '+db+' CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_ci;')
    sql("CREATE USER 'csucampuscraft'@'127.0.0.1' IDENTIFIED BY '"+apppass+"';")
    for db in ['csucampuscraft','csucampuscraft_structure']:
        sql('GRANT SELECT,INSERT,UPDATE,DELETE ON '+db+".* TO 'csucampuscraft'@'127.0.0.1';")
    sql((REPO/'database/01-schema.sql').read_text(encoding='utf-8'),'csucampuscraft_structure')
    sql((REPO/'database/02-schema-with-demo.sql').read_text(encoding='utf-8'),'csucampuscraft')
    before=snapshot();save_text(EV/'database-before.json',json.dumps(before,indent=2))
    for port in [8080,8081]:
        with socket.socket() as so:so.bind(('127.0.0.1',port))
    # Empty states on both distinct applications.
    for app,port in [('csucampuscraft-user',8080),('csucampuscraft-admin',8081)]:
        p=launch(app,port,'csucampuscraft_structure')
        r=Client().request(port)
        check(app+'-empty-home',r[0]==200 and b'data-theme-count="0"' in r[2] and '暂无主题。请确认演示数据已导入。'.encode() in r[2],'Original M0 empty wording preserved')
        stop(p)
    # Default profile: only current public initialization route, no verification or business.
    for app,port in [('csucampuscraft-user',8080),('csucampuscraft-admin',8081)]:
        p=launch(app,port)
        client=Client();r=client.request(port)
        check(app+'-default-home',r[0]==200 and f'data-csucampuscraft-app="{app.rsplit("-",1)[1]}"'.encode() in r[2] and b'data-theme-count="5"' in r[2],'Both app marker and five themes')
        for path in ['/__verification/foundation','/__verification/counter','/__verification/errors/500','/__verification/validation?kind=integer&value=1','/not-a-route','/login','/products','/categories','/cart','/orders']:
            r=client.request(port,path);check(app+'-default-404-'+path.replace('/','_'),r[0]==404,'No business or probe route registered')
        stop(p)
    running=[]
    for app,port in [('csucampuscraft-user',8080),('csucampuscraft-admin',8081)]:
        running.append(launch(app,port,profile='verification'))
    for app,port in [('csucampuscraft-user',8080),('csucampuscraft-admin',8081)]:
        label=app
        client=Client();token,parser,body=client.token(port)
        check(label+'-labels',all(x and x in parser.ids for x in parser.labels) and bool(parser.labels),'for/id references exist')
        check(label+'-csrf-hidden',sum(a.get('name')=='_csrf' and a.get('type')=='hidden' for a in parser.inputs)==1,'One shared-fragment hidden token')
        field_match=re.search(r'<p\b[^>]*id="probeText-error"[^>]*>(.*?)</p>',body.decode(),re.S)
        field_text=html.unescape(re.sub('<[^>]+>','',field_match.group(1))).strip() if field_match else None
        field_input=next((a for a in parser.inputs if a.get('id')=='probeText'),{})
        check(label+'-field-error-visible',field_text=='请修改此验证字段' and field_input.get('aria-describedby')=='probeText-error' and field_input.get('aria-invalid')=='true' and '#probeText' in parser.links,'Field error text, description reference and summary anchor rendered correctly')
        payload='<script>alert("quote")</script>'
        r=client.request(port,'/__verification/foundation?'+urllib.parse.urlencode({'text':payload}))
        text=r[2].decode()
        check(label+'-escaped-text',r[0]==200 and '<script>alert(' not in text and '&lt;script&gt;' in text and '&lt;/script&gt;' in text,'Text escaped with visible quote payload')
        for status in [400,403,404,409,500]:
            r=client.request(port,f'/__verification/errors/{status}')
            decoded=r[2].decode()
            check(label+'-error-'+str(status),r[0]==status and str(status) in decoded,'Correct status and rendered page')
            if status==500:
                check(label+'-technical-redaction','VERIFICATION_SQL_PASSWORD_STACK_SENTINEL' not in decoded and 'java.lang.' not in decoded and 'SQLException' not in decoded,'No sentinel, stack or SQL details in response')
        for kind,value,wanted in [('integer','1',200),('integer','1.5',400),('integer','2147483648',400),('money','9999999999.99',200),('money','10000000000.00',400),('money','1.001',400),('enum','FIRST',200),('enum','not-an-enum',400),('length','x'*121,400)]:
            r=client.request(port,'/__verification/validation?'+urllib.parse.urlencode({'kind':kind,'value':value}))
            check(label+'-validation-'+kind+'-'+str(len(result['checks'])),r[0]==wanted,'Boundary through HTTP adapter')
        baseline_count=count(client,port)
        other=Client();other_token,_,_=other.token(port)
        cases=[
            ('missing',client,'POST',[],{},''),
            ('wrong',client,'POST',[('_csrf','not-a-valid-token')],{},''),
            ('other-session',client,'POST',[('_csrf',other_token)],{},''),
            ('duplicate',client,'POST',[('_csrf',token),('_csrf',token)],{},''),
            ('header-only',client,'POST',[],{'X-CSRF-TOKEN':token},''),
            ('query-only',client,'POST',[],{},'?'+urllib.parse.urlencode({'_csrf':token})),
        ]
        for method in ['HEAD','OPTIONS','PUT','PATCH','DELETE']:
            cases.append(('non-get-'+method,client,method,[],{},''))
        for accept_name,accept in [('absent',None),('html','text/html'),('json','application/json')]:
            for case,cl,method,form,headers,query in cases:
                actual_headers=dict(headers)
                if accept is not None:actual_headers['Accept']=accept
                r=cl.request(port,'/__verification/submit'+query,method,form,actual_headers)
                check(label+'-csrf-'+accept_name+'-'+case,r[0]==403,'Denied before verification handler')
                if method!='HEAD':
                    content_type=r[1].get('Content-Type','')
                    page=r[2].decode('utf-8')
                    marker='data-csucampuscraft-app="'+app.rsplit('-',1)[1]+'"'
                    check(label+'-csrf-html-'+accept_name+'-'+case,'text/html' in content_type and 'data-error-status="403"' in page and marker in page,'SSR 403 required regardless of Accept negotiation')
                check(label+'-csrf-counter-'+accept_name+'-'+case,count(client,port)==baseline_count,'No accepted handler invocation')
        r=client.request(port,'/__verification/submit','POST',[('_csrf',token)])
        check(label+'-csrf-valid',r[0]==303 and r[1].get('Location') in ['/','http://127.0.0.1:'+str(port)+'/'],'Valid token reaches non-business POST and sees 303')
        check(label+'-csrf-valid-counter',count(client,port)==baseline_count+1,'Exactly one accepted handler call')
        css=client.request(port,'/css/app.css')
        check(label+'-css',css[0]==200 and css[2]==(REPO/app/'src/main/resources/static/css/app.css').read_bytes(),'CSS response equals checked-in resource')
        svg=client.request(port,'/images/catalog-placeholder.svg')
        check(label+'-shared-svg',svg[0]==200 and svg[2]==(REPO/'assets/images/catalog-placeholder.svg').read_bytes(),'Shared asset unchanged')
    browser=HERE.parent/'verify_browser.cjs'
    save_text(EV/'verify_browser.cjs',browser.read_text(encoding='utf-8-sig'))
    browserenv=os.environ.copy();browserenv['STEP02_BROWSER_OUT']=str(EV/'browser')
    p=command([RUNTIME/'node/bin/node.exe',browser],env=browserenv,timeout=90)
    save_text(EV/'browser-run.log',p.stdout.decode(errors='replace')+p.stderr.decode(errors='replace'))
    check('real-browser-checks',p.returncode==0 and (EV/'browser/result.json').is_file(),'Bundled Playwright and local Edge; screenshots contain no hidden token values')
    after=snapshot();save_text(EV/'database-after.json',json.dumps(after,indent=2))
    check('database-seven-table-zero-write',before==after,'All seven ordered logical row snapshots unchanged, including values and row counts')
    # Classpath probes use each actual executable JAR's unpacked classes and dependencies.
    hashes=rows('SELECT password_hash FROM store_user ORDER BY id;').splitlines()
    secret_values.extend(hashes)
    hf=BASE/'private-seed-hashes.txt';private_files.append(hf);hf.write_text('\n'.join(hashes),encoding='utf-8')
    sqltext=(REPO/'database/02-schema-with-demo.sql').read_text(encoding='utf-8')
    seed_raw=re.search(r'教学演示密码统一为\s+([^；\s]+)',sqltext).group(1)
    secret_values.append(seed_raw)
    for app,suffix in [('csucampuscraft-user','storefront'),('csucampuscraft-admin','admin')]:
        cp=str(BASE/(app+'-classes'))+';'+str(BASE/(app+'-libs')/'*')
        harness=HERE/'FoundationChecks.java'
        p=command([JAVA/'javac.exe','-encoding','UTF-8','-cp',cp,'-d',BASE,harness],timeout=25)
        save_text(EV/(app+'-harness-compile.log'),p.stdout.decode(errors='replace')+p.stderr.decode(errors='replace'))
        check(app+'-harness-compile',p.returncode==0,'Compiled without testing framework')
        probeenv=os.environ.copy();probeenv['STEP02_SEED_RAW']=seed_raw
        p=command([JAVA/'java.exe','-cp',str(BASE)+';'+cp,'FoundationChecks','org.csucampuscraft.'+suffix+'.foundation',hf],env=probeenv,timeout=30)
        output=p.stdout.decode(errors='replace')+p.stderr.decode(errors='replace')
        save_text(EV/(app+'-harness.log'),output)
        check(app+'-harness-runtime',p.returncode==0 and 'FOUNDATION_CHECKS_PASS' in output,'Production PasswordService, ReturnUrlPolicy and InputChecks exercised')
    check('two-end-css-equal',(REPO/'csucampuscraft-user/src/main/resources/static/css/app.css').read_bytes()==(REPO/'csucampuscraft-admin/src/main/resources/static/css/app.css').read_bytes(),'Exact identical styles')
    source_stable=True
    for line in manifest.splitlines():
        sha,rel=line.split('  ',1)
        source_stable=source_stable and hashlib.sha256((REPO/rel).read_bytes()).hexdigest()==sha
    check('source-inputs-stable',source_stable,'All runtime inputs immutable during verification')
    result['overall']='PASS'
except Exception as e:
    result['overall']='FAIL';result['error']=scrub_text(type(e).__name__+': '+str(e))
    save_text(EV/'failure.txt',traceback.format_exc());print(result['error'],flush=True)
finally:
    for p in processes:stop(p)
    if server and server.poll() is None:
        try:
            command([MYSQL/'mysqladmin.exe','--no-defaults','--no-login-paths','--protocol=TCP','--host=127.0.0.1',f'--port={mysqlport}','--user=root','shutdown'],env=env,timeout=15)
            server.wait(timeout=15)
        except Exception:stop(server)
    for handle in handles:handle.close()
    for p in private_files:p.unlink(missing_ok=True)
    result['tracked_processes_stopped']=all(p.poll() is not None for p in processes) and (server is None or server.poll() is not None)
    for log in BASE.glob('*.log'):
        save_text(EV/log.name,log.read_text(encoding='utf-8',errors='replace'))
    for f in EV.rglob('*'):
        if f.is_file():
            text=f.read_text(encoding='utf-8',errors='replace')
            check_secret=any(v in text for v in secret_values if len(v)>=8)
            if check_secret:save_text(f,text)
    save_text(EV/'result.json',json.dumps(result,ensure_ascii=False,indent=2))
    print('RESULT '+str(EV/'result.json'),flush=True)
if result['overall']!='PASS':raise SystemExit(1)


