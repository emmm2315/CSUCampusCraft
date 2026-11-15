"""New STEP13 external harness. Importing this module starts no process and reads no old result."""
from pathlib import Path
from html.parser import HTMLParser
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime,timezone,timedelta
from decimal import Decimal
import copy,gzip,hashlib,http.cookiejar,json,os,re,secrets,socket,subprocess,threading,time,traceback,urllib.request,urllib.error,urllib.parse,zipfile

TABLES=['store_user','category','product','product_image','cart_item','sales_order','sales_order_item']
RUNTIME=Path('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies')
JAVA=Path('C:/Users/Starmetor/.jdks/ms-21.0.12.1/bin/java.exe')
GIT=Path('C:/Program Files/Git/cmd/git.exe')
MYSQL=Path('D:/MySQL/bin')
FLAG=subprocess.CREATE_NO_WINDOW
BCRYPT=re.compile(r'\$2[aby]\$\d\d\$[./A-Za-z0-9]{53}')
COOKIE_NAMES={'u':'CSUCAMPUSCRAFT_USER_SESSION','a':'CSUCAMPUSCRAFT_ADMIN_SESSION'}
def utc():return datetime.now(timezone.utc).isoformat()
def digest(raw):return hashlib.sha256(raw).hexdigest()
def camel(s):return re.sub('_([a-z])',lambda m:m[1].upper(),s)

class Node:
    def __init__(self,tag='',attrs=(),parent=None):self.tag=tag;self.a=dict(attrs);self.parent=parent;self.children=[]
    def nodes(self):
        yield self
        for n in self.children:
            if isinstance(n,Node):yield from n.nodes()
    def find(self,p):return next((n for n in self.nodes() if p(n)),None)
    def all(self,p):return [n for n in self.nodes() if p(n)]
    def text(self):return ''.join(n.text() if isinstance(n,Node) else n for n in self.children)
class Parser(HTMLParser):
    VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
    def __init__(self,text):super().__init__(convert_charrefs=True);self.root=Node();self.stack=[self.root];self.feed(text)
    def handle_starttag(self,t,a):
        n=Node(t,a,self.stack[-1]);self.stack[-1].children.append(n)
        if t not in self.VOID:self.stack.append(n)
    def handle_endtag(self,t):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==t:self.stack=self.stack[:i];return
    def handle_data(self,x):self.stack[-1].children.append(x)
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args):return None
@dataclass
class Response:
    status:int;headers:dict;body:bytes;dom:Node;sequence:int;before:dict|None=None;after:dict|None=None;state_before:dict|None=None;state_after:dict|None=None
    def __getitem__(self,n):return (self.status,self.headers,self.body,self.dom)[n]
    @property
    def text(self):return self.body.decode('utf-8',errors='replace')

class HttpClient:
    def __init__(self,h,name='client'):
        self.h=h;self.name=name;self.jar=http.cookiejar.CookieJar();self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(self.jar),NoRedirect())
    def clone(self,name='clone'):
        other=HttpClient(self.h,name)
        for c in self.jar:other.jar.set_cookie(copy.copy(c))
        return other
    def cookie(self,end='u'):
        end=self.h.end(end);return next((c.value for c in self.jar if c.name==COOKIE_NAMES[end]),None)
    def request(self,path='/',end='u',method='GET',form=None,expected=None,zero=False,label='',audit=True):
        h=self.h;end=h.end(end);method=method.upper();start=utc();mono=time.monotonic_ns();window=h.window_id
        full=audit and window is None
        before=h.snapshot() if full else None;a=h.state() if full else None
        data=urllib.parse.urlencode(form,doseq=True).encode('utf-8') if form is not None else None
        req=urllib.request.Request(h.base(end)+path,data=data,method=method,headers={'Accept':'text/html',**({'Content-Type':'application/x-www-form-urlencoded'} if data is not None else {})})
        try:r=self.opener.open(req,timeout=45)
        except urllib.error.HTTPError as e:r=e
        raw=r.read();headers=dict(r.headers.items())
        for c in self.jar:h.secret(c.value)
        result=h.observe_http(method,path,end,r.code,headers,raw,client=self.name,form_fields=sorted(form or {}),started_at_utc=start,elapsed_ns=time.monotonic_ns()-mono,window_id=window)
        if full:
            result.before=before;result.after=h.snapshot();result.state_before=a;result.state_after=h.state()
            h.db_pair('http-'+str(result.sequence),before,a,result.after,result.state_after,http_sequence=result.sequence,path=path,end=end,automatic_audit=True)
            if method=='GET' or zero:h.check((label or path)+' seven-table zero write',before==result.after,{'http':result.sequence})
        elif window:
            h.record('db-writes.jsonl',dict(name='http-'+str(result.sequence),http_sequence=result.sequence,schema=h.schema,before=None,after=None,observation='CONCURRENT_WINDOW',window_id=window,per_request_isolation_not_claimed=True))
        elif method!='GET':raise AssertionError('A non-window POST may not omit its genuine before/after audit')
        if expected is not None:h.check(label or method+' '+path,result.status in (expected if isinstance(expected,(list,tuple,set)) else [expected]),{'http':result.sequence,'expected':expected,'observed':result.status})
        return result
    def get(self,path='/',end='u',**kw):return self.request(path,end,**kw)
    def post(self,path,form,end='u',**kw):return self.request(path,end,'POST',form,**kw)

class Harness:
    def __init__(self,stage,repo,tested_sha,attempt='attempt1',user_port=8080,admin_port=8081):
        if not re.fullmatch('[0-9a-f]{40}',tested_sha):raise ValueError('Exact source SHA required')
        if not re.fullmatch('attempt[1-9][0-9]*',attempt):raise ValueError('Fresh attemptN required')
        self.stage=Path(stage).resolve();self.repo=Path(repo);self.tested_sha=tested_sha;self.attempt=attempt
        self.evidence=self.stage/'evidence'/attempt;self.runtime=self.stage/'runtime'/attempt
        self.evidence.mkdir(parents=True,exist_ok=False);self.runtime.mkdir(parents=True,exist_ok=False)
        self.ports={'u':user_port,'a':admin_port};self.schema='csucampuscraft';self.mysql_port=self.freeport();self.mysqlport=self.mysql_port
        self.rootpass=secrets.token_urlsafe(28);self.apppass=secrets.token_urlsafe(28);self.appuser='csu13_app'
        match=re.search(r'教学密码为\s*`([^`]+)`',(self.repo/'README.md').read_text(encoding='utf-8'))
        if not match:raise RuntimeError('Teaching credential must come from current README')
        self.password=match[1];self.secrets={self.rootpass,self.apppass,self.password};self.lock=threading.RLock();self.n=0;self.cn=0
        self.window_id=None;self.case_id=None;self.segment=None;self.checks=[];self.processes=[];self.handles=[];self.apps={};self.server=None;self.columns={};self.p0={};self.app_overrides={}
        self.plan=json.loads((self.stage/'p0-plan.json').read_text(encoding='utf-8'))
        self.result=dict(started_at_utc=utc(),started_at_local=datetime.now(timezone(timedelta(hours=8))).isoformat(),tested_sha=tested_sha,attempt=attempt,executor='Codex AI, user-authorized new STEP13 execution',human_cross_reproduction='not implemented this round; prior human review remains limited to its original scope',scope='All 39 P0 identifiers on the current exact SHA; TST36 P1 not selected')
    @staticmethod
    def freeport():
        with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
    def end(self,e):
        if e in ['u','user',self.ports['u']]:return 'u'
        if e in ['a','admin',self.ports['a']]:return 'a'
        raise ValueError('Unknown application endpoint')
    def base(self,e='u'):return 'http://127.0.0.1:'+str(self.ports[self.end(e)])
    def Client(self,name='client'):return HttpClient(self,name)
    @property
    def evidence_dir(self):return self.evidence
    @property
    def db_url(self):return self.connection_env(True)['STEP13_JDBC_URL']
    @property
    def root_credentials(self):return {'username':'root','password':self.rootpass}
    def register_secret(self,value):self.secret(value)
    def client(self,username='alice',port=None):return self.login(self.Client(username+'-'+secrets.token_hex(3)),port or self.ports['u'],username)[0]
    def get_csrf(self,client,path='/cart',port=None):return self.token(client.get(path,port or self.ports['u'],expected=200))
    def raw_request(self,client,method,path,form=None,port=None,audit=True,**kwargs):return client.request(path,port or self.ports['u'],method,form,audit=audit,**kwargs)
    def cookie_header(self,client):
        for c in client.jar:self.secret(c.value)
        return '; '.join(c.name+'='+c.value for c in client.jar)
    def prepare_request(self,client,method,path,form=None,port=None):
        return dict(url=self.base(port or self.ports['u'])+path,method=method,headers={'Cookie':self.cookie_header(client),'Content-Type':'application/x-www-form-urlencoded'},body=urllib.parse.urlencode(form or {},doseq=True))
    def secret(self,value):
        if value:
            with self.lock:self.secrets.add(str(value))
    def redact(self,text):
        for value in sorted(self.secrets,key=len,reverse=True):
            if len(value)>=8:text=text.replace(value,'[REDACTED]')
        text=BCRYPT.sub('[REDACTED-HASH]',text)
        def hide(m):
            tag=m[0]
            if re.search(r'''\bname=["'](?:_csrf|confirmationToken|password|receiverName|receiverPhone|receiverAddress)["']''',tag,re.I):tag=re.sub(r'''(\bvalue=["'])[^"']*(["'])''',r'\1[REDACTED]\2',tag,flags=re.I)
            return tag
        text=re.sub('<input\\b[^>]*>',hide,text,flags=re.I)
        text=re.sub(r'''(<textarea\b[^>]*\bname=["'](?:receiverName|receiverPhone|receiverAddress)["'][^>]*>)[\s\S]*?(</textarea>)''',r'\1[REDACTED]\2',text,flags=re.I)
        text=re.sub(r'''(<([a-z][a-z0-9]*)\b[^>]*\b(?:data-shipping-value|data-customer-contact)(?:=["'][^"']*["'])?[^>]*>)[\s\S]*?(</\2>)''',r'\1[REDACTED]\3',text,flags=re.I)
        text=re.sub(r'(?im)^(Set-Cookie|Cookie):.*$',r'\1: [REDACTED]',text)
        return text
    def save(self,path,data):
        path=self.evidence/path;path.parent.mkdir(parents=True,exist_ok=True)
        raw=self.redact(data).encode('utf-8') if isinstance(data,str) else data;path.write_bytes(raw)
        return {'path':path.relative_to(self.evidence).as_posix(),'bytes':len(raw),'sha256':digest(path.read_bytes())}
    def record(self,name,obj):
        with self.lock:
            p=self.evidence/name;p.parent.mkdir(parents=True,exist_ok=True)
            with p.open('ab') as f:f.write(self.redact(json.dumps(dict(at=utc(),**obj),ensure_ascii=False)).encode('utf-8')+b'\n')
    def check(self,name,passed,detail=None):
        item=dict(name=name,passed=bool(passed),case=self.case_id,segment=self.segment,detail=detail)
        with self.lock:self.checks.append(item)
        self.record('checks.jsonl',item);print(('PASS ' if passed else 'FAIL ')+str(self.case_id)+' '+name,flush=True)
        if not passed:raise AssertionError(name)
    def command(self,args,**kw):
        with self.lock:self.cn+=1;number=self.cn
        start=time.monotonic();p=subprocess.run([str(x) for x in args],capture_output=True,creationflags=FLAG,**kw)
        self.record('commands.jsonl',dict(sequence=number,argv=[str(x) for x in args],exit_code=p.returncode,elapsed_seconds=round(time.monotonic()-start,6)))
        return p
    def git(self,*args):
        p=self.command([GIT,'-C',self.repo,'-c','core.quotepath=false',*args],timeout=30)
        if p.returncode:raise RuntimeError('Read-only git failed')
        return p.stdout.decode('utf-8',errors='replace')
    def sql(self,q,db=None,fail_ok=False):
        args=[MYSQL/'mysql.exe','--no-defaults','--no-login-paths','--protocol=TCP','--host=127.0.0.1',f'--port={self.mysql_port}','--user=root','--connect-timeout=3','--default-character-set=utf8mb4','--batch','--raw','--skip-column-names']
        if db is not False:args.append('--database='+(db or self.schema))
        env=os.environ.copy();env['MYSQL_PWD']=self.rootpass
        p=self.command(args,input=("SET SESSION time_zone='+00:00';"+q).encode('utf-8'),env=env,timeout=50)
        if p.returncode and not fail_ok:
            self.save('sql-error-'+str(self.cn)+'.json',json.dumps(dict(query=q,exit_code=p.returncode,stderr=p.stderr.decode('utf-8',errors='replace')),ensure_ascii=False));raise RuntimeError('Private SQL command failed')
        return p
    def rows(self,q,db=None):return self.sql(q,db).stdout.decode('utf-8').strip()
    @staticmethod
    def literal(s):return '(CONVERT(0x'+str(s).encode('utf-8').hex()+' USING utf8mb4))'
    def metadata(self):
        if self.schema not in self.columns:
            data=self.rows("SELECT JSON_OBJECT('table',TABLE_NAME,'column',COLUMN_NAME,'type',DATA_TYPE) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA="+self.literal(self.schema)+' ORDER BY TABLE_NAME,ORDINAL_POSITION;')
            out={t:[] for t in TABLES}
            for line in data.splitlines():
                x=json.loads(line)
                if x['table'] in out:out[x['table']].append((x['column'],x['type']))
            self.columns[self.schema]=out
        return self.columns[self.schema]
    def snapshot(self):
        columns=self.metadata();q=''
        for t in TABLES:q+="SELECT '__CSU13_"+t+"__';SELECT COUNT(*) FROM "+t+';SELECT JSON_ARRAY('+','.join('`'+c+'`' for c,_ in columns[t])+') FROM '+t+' ORDER BY id;'
        raw=self.sql(q).stdout;out={}
        for i,t in enumerate(TABLES):
            marker=('__CSU13_'+t+'__').encode();start=raw.index(marker)+len(marker);start+=2 if raw[start:start+2]==b'\r\n' else 1
            end=raw.index(('__CSU13_'+TABLES[i+1]+'__').encode(),start) if i+1<len(TABLES) else len(raw)
            count,payload=raw[start:end].split(b'\n',1);out[t]=dict(rows=int(count),sha256=digest(payload),serialization='ordered full-field JSON_ARRAY rows, UTC')
        return out
    def state(self):
        out={}
        for t,cols in self.metadata().items():
            fields=[]
            for c,typ in cols:
                key=camel(c);expr='`'+c+'`'
                if c in ['password_hash','receiver_name','receiver_phone','receiver_address','email','phone']:key+='Sha256';expr='SHA2('+expr+',256)'
                elif typ in ['decimal','numeric']:expr='CAST('+expr+' AS CHAR)'
                fields.extend([self.literal(key),expr])
            text=self.rows('SELECT JSON_OBJECT('+','.join(fields)+') FROM '+t+' ORDER BY id;')
            out[t]={str(x['id']):x for x in map(json.loads,text.splitlines())}
        return out
    @staticmethod
    def deltas(a,b):return {t:[dict(id=i,before=a[t].get(i),after=b[t].get(i)) for i in sorted(set(a[t])|set(b[t]),key=int) if a[t].get(i)!=b[t].get(i)] for t in a}
    def db_pair(self,name,before,a,after,b,**extra):self.record('db-writes.jsonl',dict(name=name,schema=self.schema,before=before,after=after,**{t+'_before':a[t] for t in a},**{t+'_after':b[t] for t in b},deltas=self.deltas(a,b),**extra))
    def observe_http(self,method,path,end,status,headers,raw,**meta):
        text=raw.decode('utf-8',errors='replace');dom=Parser(text).root
        for n in dom.all(lambda n:n.tag=='input' and n.a.get('name') in ['_csrf','confirmationToken']):self.secret(n.a.get('value'))
        with self.lock:self.n+=1;seq=self.n
        self.check('raw response no credential/hash '+str(seq),not BCRYPT.search(text) and self.password not in text and self.rootpass not in text and self.apppass not in text)
        self.check('no URL session tracking '+str(seq),';CSUCAMPUSCRAFT_' not in text and ';CSUCAMPUSCRAFT_' not in headers.get('Location',''))
        redacted=self.redact(text).encode('utf-8');content_hash=digest(redacted);file='bodies/'+content_hash[:32]+'.html.gz';p=self.evidence/file
        if not p.exists():self.save(file,gzip.compress(redacted,mtime=0))
        self.record('http.jsonl',dict(sequence=seq,method=method,path=path,end=self.end(end),port=self.ports[self.end(end)],schema=self.schema,status=status,location=headers.get('Location'),content_type=headers.get('Content-Type'),body_file=file,redacted_content_sha256=content_hash,stored_file_sha256=digest(p.read_bytes()),stored_file_bytes=p.stat().st_size,raw_body_available=True,raw_privacy_scan_passed=True,credentials_or_session_values_recorded=False,**meta))
        return Response(status,headers,raw,dom,seq)
    def token(self,response,name='_csrf'):
        n=response.dom.find(lambda n:n.tag=='input' and n.a.get('name')==name);return n.a.get('value') if n else None
    def login(self,client=None,end='u',username=None,password=None,expected=303,return_url='/'):
        client=client or self.Client('login-'+str(username));end=self.end(end)
        page=client.get('/login?'+urllib.parse.urlencode({'returnUrl':return_url}),end,expected=200)
        old_cookie=client.cookie(end)
        r=client.post('/login',dict(username=username or ('alice' if end=='u' else 'admin'),password=self.password if password is None else password,_csrf=self.token(page),returnUrl=return_url),end,expected=expected,zero=True)
        if r.status==303:self.check('login changes session ID without exposing it',bool(old_cookie) and bool(client.cookie(end)) and old_cookie!=client.cookie(end))
        return client,r
    def follow(self,client,response,end='u',expected=200):
        target=response.headers.get('Location','');u=urllib.parse.urlsplit(target)
        self.check('redirect is local GET',response.status in [302,303] and not u.netloc and u.path.startswith('/'))
        return client.get(target,end,expected=expected)
    def post(self,client,path,form=None,end='u',expected=303,csrf=True,zero=False):
        data=dict(form or {})
        if csrf is True:data['_csrf']=self.token(client.get('/login' if path=='/login' else ('/cart' if self.end(end)=='u' else '/'),end,expected=200))
        elif isinstance(csrf,str):data['_csrf']=csrf
        return client.post(path,data,end,expected=expected,zero=zero)
    def cartrows(self,uid=1):return sorted((x for x in self.state()['cart_item'].values() if x['userId']==uid),key=lambda x:x['id'])
    def product(self,pid):return self.state()['product'][str(pid)]
    def pid(self,sku):return int(self.rows('SELECT id FROM product WHERE sku='+self.literal(sku)))
    def order(self,no):return next((x for x in self.state()['sales_order'].values() if x['orderNo'].lower()==no.lower()),None)
    def clear_cart(self,client,uid=1):
        for row in self.cartrows(uid):self.post(client,'/cart/items/'+str(row['id'])+'/remove',{'version':row['version']})
    def add(self,client,pid,quantity=1,expected=303):return self.post(client,'/cart/items',{'productId':pid,'quantity':quantity},expected=expected,zero=expected!=303)
    def shipping(self):
        d={'receiverName':'仅验收收货人'+secrets.token_hex(5),'receiverPhone':'000-STEP13','receiverAddress':'虚构校园地址 '+secrets.token_hex(7)}
        for x in d.values():self.secret(x)
        return d
    def checkout(self,client,expected=200):return client.get('/checkout',expected=expected)
    def submit(self,client,confirmation,fields=None,expected=303,**extra):
        data=dict(fields or self.shipping());data.update(confirmationToken=self.token(confirmation,'confirmationToken'),_csrf=self.token(confirmation));data.update(extra)
        r=client.post('/orders',data,expected=expected,zero=expected!=303)
        return r,self.order(urllib.parse.urlsplit(r.headers['Location']).path.rsplit('/',1)[1]) if r.status==303 else None
    def new_order85(self,client,uid=1):
        self.clear_cart(client,uid);self.add(client,self.pid('CSU-LMK-NOTE-01'),2);self.add(client,self.pid('CSU-GRAD-BOX-01'),1)
        confirm=self.checkout(client);self.check('fresh confirmation is 85',confirm.dom.find(lambda n:n.a.get('data-checkout-total')=='85.00') is not None)
        r,order=self.submit(client,confirm);self.check('fresh order amount85',order is not None and Decimal(order['totalAmount'])==Decimal('85.00'));return order
    def fixture(self,q,label):
        before=self.snapshot();a=self.state();self.sql(q);after=self.snapshot();b=self.state();self.db_pair(label,before,a,after,b,controlled_root_fixture=True,query=q)
    @contextmanager
    def case(self,tst,segment='serial'):
        old=(self.case_id,self.segment);self.case_id=tst;self.segment=segment;start=len(self.checks)
        try:yield
        except BaseException as exc:self.mark_p0(tst,segment,False,{'exception':type(exc).__name__,'message':str(exc),'checks':len(self.checks)-start});raise
        else:self.mark_p0(tst,segment,True,{'checks':len(self.checks)-start})
        finally:self.case_id,self.segment=old
    def mark_p0(self,tst,segment,passed,detail=None):
        self.p0.setdefault(tst,{})[segment]=dict(passed=bool(passed),detail=detail,at=utc());self.save('p0-matrix.json',json.dumps(self.matrix(),ensure_ascii=False,indent=2))
    def matrix(self):
        out=[]
        for row in self.plan['cases']:
            parts=self.p0.get(row['id'],{});required=row['required_segments'];done=all(p in parts for p in required);ok=done and all(parts[p]['passed'] for p in required)
            out.append(dict(row,result='PASS' if ok else 'FAIL' if any(not x['passed'] for x in parts.values()) else 'NOT_RUN',observed_segments=parts,tested_sha=self.tested_sha))
        return out
    @contextmanager
    def concurrent_window(self,name):
        if self.window_id is not None:raise RuntimeError('Concurrent windows may not overlap/reset')
        before=self.snapshot();a=self.state();self.window_id=name;start=utc()
        try:yield
        finally:
            self.window_id=None;after=self.snapshot();b=self.state();self.db_pair(name,before,a,after,b,observation='CONCURRENT_WINDOW',started_at_utc=start,finished_at_utc=utc(),per_request_isolation_not_claimed=True)
    def connection_env(self,root=False):
        return dict(STEP13_JDBC_URL=f'jdbc:mysql://127.0.0.1:{self.mysql_port}/{self.schema}?connectionTimeZone=UTC&forceConnectionTimeZoneToSession=true',STEP13_DB_USER='root' if root else self.appuser,STEP13_DB_PASSWORD=self.rootpass if root else self.apppass)

    def initialize(self):
        self.check('exact source',self.git('rev-parse','HEAD').strip()==self.tested_sha);self.result['branch']=self.git('branch','--show-current').strip();self.check('feature branch',self.result['branch']=='feat/step13-acceptance')
        status=self.git('status','--short','--untracked-files=all');self.save('git-start-status.txt',status);self.check('clean start',not status.strip())
        probes=[]
        for port in self.ports.values():
            try:
                with socket.socket() as s:s.bind(('127.0.0.1',port))
                probes.append(dict(port=port,available=True))
            except OSError as exc:probes.append(dict(port=port,available=False,error_class=type(exc).__name__,error_number=exc.errno))
        if not all(p['available'] for p in probes):self.ports={'u':18080,'a':18081}
        self.save('port-choice.json',json.dumps(dict(probed_primary=probes,selected=self.ports,fallback_only_if_observed_conflict=not all(p['available'] for p in probes)),indent=2))
        ve=os.environ.copy();ve['JAVA_HOME']=str(JAVA.parent.parent);ve['PATH']=str(JAVA.parent)+';'+os.environ['SystemRoot']+'/System32;'+os.environ['SystemRoot']+'/System32/WindowsPowerShell/v1.0'
        versions=[]
        for args in [[JAVA,'-version'],[self.repo/'mvnw.cmd','-v'],[MYSQL/'mysqld.exe','--version']]:
            p=self.command(args,env=ve,timeout=60);self.check('actual tool version exit',p.returncode==0);versions.append(p.stdout.decode('utf-8',errors='replace')+p.stderr.decode('utf-8',errors='replace'))
        self.check('actual JDK21/Maven3.9.16','21.0.' in versions[0] and 'Apache Maven 3.9.16' in versions[1]);self.save('versions.txt','\n'.join(versions))
        files=[p for app in ['csucampuscraft-user','csucampuscraft-admin'] for p in [self.repo/app/'pom.xml',*(p for p in (self.repo/app/'src').rglob('*') if p.is_file())]]
        files += [p for folder in ['database','assets','.mvn'] for p in (self.repo/folder).rglob('*') if p.is_file()]+[self.repo/'mvnw',self.repo/'mvnw.cmd']
        self.inputs={p.relative_to(self.repo).as_posix():digest(p.read_bytes()) for p in sorted(files)};manifest=''.join(v+'  '+k+'\n' for k,v in self.inputs.items());self.save('runtime-inputs.sha256',manifest);self.result.update(runtime_file_count=len(files),runtime_manifest_sha256=digest(manifest.encode()))
        for app in ['user','admin']:
            text=(self.stage.parent/('build-'+app+'.log')).read_text(encoding='utf-8',errors='replace');self.check('new clean Wrapper verify '+app,'BUILD SUCCESS' in text);self.save('build-'+app+'.log',text)
            jar=self.repo/f'csucampuscraft-{app}/target/csucampuscraft-{app}-0.0.1-SNAPSHOT.jar';self.result[app+'_jar_sha256']=digest(jar.read_bytes())
        data=self.runtime/'mysql-data';data.mkdir();init=self.runtime/'mysql-init-private.sql';init.write_text("ALTER USER 'root'@'localhost' IDENTIFIED BY '"+self.rootpass+"';",encoding='utf-8')
        p=self.command([MYSQL/'mysqld.exe','--no-defaults','--initialize-insecure','--basedir=D:/MySQL',f'--datadir={data}',f'--log-error={self.runtime/"mysql-initialize.log"}'],timeout=60);self.check('private MySQL initialize',p.returncode==0)
        log=(self.runtime/'mysql-server.log').open('wb');self.handles.append(log)
        self.server=subprocess.Popen([str(MYSQL/'mysqld.exe'),'--no-defaults','--basedir=D:/MySQL',f'--datadir={data}',f'--port={self.mysql_port}','--bind-address=127.0.0.1','--mysqlx=OFF',f'--init-file={init}',f'--pid-file={self.runtime/"mysql.pid"}','--console'],stdout=log,stderr=subprocess.STDOUT,creationflags=FLAG)
        until=time.monotonic()+40
        while time.monotonic()<until:
            p=self.sql('SELECT @@version,@@server_uuid,@@port,@@datadir,@@session.time_zone;',False,True)
            if p.returncode==0:break
            if self.server.poll() is not None:raise RuntimeError('Owned MySQL exited')
            time.sleep(.2)
        else:raise RuntimeError('Owned MySQL readiness timeout')
        ident=p.stdout.decode().strip().split('\t');uuid=re.search('server-uuid=(.+)',(data/'auto.cnf').read_text()).group(1).strip()
        self.check('private MySQL identity',ident[1]==uuid and int(ident[2])==self.mysql_port and Path(ident[3]).resolve()==data.resolve() and ident[4]=='+00:00');init.unlink()
        self.save('database-identity.json',json.dumps(dict(version=ident[0],uuid=uuid,port=self.mysql_port,private_datadir=str(data),sql_timezone='UTC'),indent=2));self.result.update(mysql_port=self.mysql_port,mysql_uuid=uuid,mysql_version=ident[0])
        self.sql("CREATE USER '"+self.appuser+"'@'127.0.0.1' IDENTIFIED BY '"+self.apppass+"';",False)
    def create_schema(self,name,kind='demo'):
        if not re.fullmatch('[a-z][a-z0-9_]{1,48}',name):raise ValueError('Owned schema identifier only')
        self.sql('CREATE DATABASE '+name+' CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_ci;',False)
        path=self.repo/'database'/('02-schema-with-demo.sql' if kind=='demo' else '01-schema.sql');self.sql(path.read_text(encoding='utf-8-sig'),name)
        self.sql('GRANT SELECT,INSERT,UPDATE,DELETE ON '+name+".* TO '"+self.appuser+"'@'127.0.0.1';",False)
        self.record('schemas.jsonl',dict(schema=name,kind=kind,source_file=path.relative_to(self.repo).as_posix(),source_sha256=digest(path.read_bytes())))
    def app_env(self):
        e=os.environ.copy()
        for k in ['SPRING_APPLICATION_JSON','SPRING_CONFIG_LOCATION','SPRING_CONFIG_ADDITIONAL_LOCATION','JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVA_OPTIONS','CSUCAMPUSCRAFT_CHECKOUT_CONFIRMATION_TTL']:e.pop(k,None)
        url=f'jdbc:mysql://127.0.0.1:{self.mysql_port}/{self.schema}'
        e.update(CSUCAMPUSCRAFT_DB_URL=url,CSUCAMPUSCRAFT_DB_USER=self.appuser,CSUCAMPUSCRAFT_DB_PASSWORD=self.apppass,SPRING_DATASOURCE_URL=url,SPRING_DATASOURCE_USERNAME=self.appuser,SPRING_DATASOURCE_PASSWORD=self.apppass,SPRING_SQL_INIT_MODE='never',SPRING_PROFILES_ACTIVE='default');e.update(self.app_overrides);return e
    def start_apps(self,schema=None):
        if schema:self.schema=schema
        if self.apps:raise RuntimeError('Stop existing owned apps before changing schemas')
        for end,app in [('u','csucampuscraft-user'),('a','csucampuscraft-admin')]:
            port=self.ports[end]
            with socket.socket() as s:s.bind(('127.0.0.1',port))
            filename=f'{app}-{len(self.processes)+1}.log';handle=(self.runtime/filename).open('wb');self.handles.append(handle)
            args=[JAVA,'-jar',self.repo/app/'target'/f'{app}-0.0.1-SNAPSHOT.jar',f'--server.port={port}','--server.address=127.0.0.1']
            p=subprocess.Popen([str(x) for x in args],env=self.app_env(),stdout=handle,stderr=subprocess.STDOUT,creationflags=FLAG);self.processes.append(p);self.apps[end]=p
            self.record('launches.jsonl',dict(app=app,pid=p.pid,port=port,schema=self.schema,mysql_port=self.mysql_port,datasource_user=self.appuser,password_supplied=True,args=[str(x) for x in args]))
            until=time.monotonic()+60
            while time.monotonic()<until:
                if p.poll() is not None:raise RuntimeError(app+' exited')
                try:
                    req=urllib.request.Request(self.base(end)+'/login');r=urllib.request.urlopen(req,timeout=2)
                    if r.status==200:break
                except (OSError,urllib.error.URLError):time.sleep(.2)
            else:raise RuntimeError('Application readiness timeout')
            owner=self.command([Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe','-NoLogo','-NoProfile','-Command',f'Get-NetTCPConnection -LocalPort {port} -State Listen | Select-Object -ExpandProperty OwningProcess'],timeout=20)
            pids=[int(x) for x in owner.stdout.decode().split() if x.isdigit()];self.check('created listener owner '+end,pids and all(x==p.pid for x in pids));self.record('listeners.jsonl',dict(end=end,pid=p.pid,port=port,observed_pids=pids,schema=self.schema))
    @staticmethod
    def stop(p):
        if p.poll() is None:
            p.terminate()
            try:p.wait(10)
            except subprocess.TimeoutExpired:p.kill();p.wait(5)
    def stop_apps(self):
        for p in self.apps.values():self.stop(p)
        self.apps={}
    def finish(self,error=None):
        self.stop_apps()
        if self.server and self.server.poll() is None:
            try:self.sql('SHUTDOWN;',False,True)
            except Exception:pass
            self.stop(self.server)
        for p in self.processes:self.stop(p)
        for f in self.handles:f.close()
        for p in self.runtime.glob('*-private.sql'):p.unlink()
        for p in self.runtime.glob('*.log'):self.save(p.name,p.read_text(encoding='utf-8',errors='replace'))
        self.result.update(finished_at_utc=utc(),finished_at_local=datetime.now(timezone(timedelta(hours=8))).isoformat(),checks=len(self.checks),checks_failed=sum(not x['passed'] for x in self.checks),p0_matrix=self.matrix(),tracked_processes_stopped=all(p.poll() is not None for p in self.processes) and (self.server is None or self.server.poll() is not None),error=self.redact(str(error)) if error else None)
        self.result['overall']='PASS' if error is None and all(x['result']=='PASS' for x in self.matrix()) else 'FAIL' if error else 'INCOMPLETE'
        self.result['runtime_inputs_stable']=all(digest((self.repo/k).read_bytes())==v for k,v in self.inputs.items()) if hasattr(self,'inputs') else False
        findings=[];texts=0;gz=0
        for p in self.evidence.rglob('*'):
            if not p.is_file() or p.suffix=='.png':continue
            raw=p.read_bytes();texts+=1
            if p.suffix=='.gz':raw=gzip.decompress(raw);gz+=1
            if BCRYPT.search(raw.decode('utf-8',errors='replace')):findings.append(dict(file=p.relative_to(self.evidence).as_posix(),kind='raw-bcrypt-pattern'))
            for secret in self.secrets:
                if len(secret)>=8 and secret.encode() in raw:findings.append(dict(file=p.relative_to(self.evidence).as_posix(),kind='known-private-value'))
        self.save('sensitive-scan.json',json.dumps(dict(overall='PASS' if not findings else 'FAIL',files_scanned=texts,gzip_decompressed=gz,known_values=len(self.secrets),values_recorded=False,findings=findings),indent=2))
        if findings or not self.result['runtime_inputs_stable']:self.result['overall']='FAIL'
        self.save('result.json',json.dumps(self.result,ensure_ascii=False,indent=2));self.save('p0-matrix.json',json.dumps(self.matrix(),ensure_ascii=False,indent=2))
        manifest=''.join(digest(p.read_bytes())+'  '+p.relative_to(self.evidence).as_posix()+'\n' for p in sorted(self.evidence.rglob('*')) if p.is_file() and p.name!='artifacts.sha256');self.save('artifacts.sha256',manifest)
        return self.result

def scanner_regression():
    positives=['$2'+prefix+'$10$'+('A'*53) for prefix in 'aby'];positives.append('context '+positives[1]+' context')
    negatives=['','ordinary public text','$2x$10$'+('A'*53),'$2a$1$'+('A'*53),'$2a$10$'+('A'*52)]
    flags=[bool(BCRYPT.search(x)) for x in positives]+[not BCRYPT.search(x) for x in negatives]
    return dict(overall='PASS' if all(flags) else 'FAIL',positive_cases=4,negative_cases=5,passed=sum(flags),synthetic_hash_values_recorded=False)
