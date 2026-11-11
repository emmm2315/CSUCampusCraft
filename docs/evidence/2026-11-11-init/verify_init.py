from pathlib import Path
import hashlib,json,subprocess,os,time,socket,urllib.request,re,zipfile,secrets,datetime,traceback
base=Path(__file__).parent/'runtime'
ev=Path(__file__).parent/'evidence'/'attempt2';ev.mkdir(exist_ok=True)
java=Path('C:/Users/Starmetor/.jdks/ms-21.0.12.1/bin')
mysql=Path('D:/MySQL/bin')
flags=getattr(subprocess,'CREATE_NO_WINDOW',0)
result={'date':datetime.datetime.now().astimezone().isoformat(),'baseline_git_sha':'ae6f47f995fef790b5a2f513574ed2129e4409b3','source_state':'baseline plus two uncommitted spring-security-crypto POM additions; documentation excluded from runtime manifest','checks':{}}
def check(name,ok,detail):
    result['checks'][name]={'passed':bool(ok),'detail':detail}
    print(name+': '+('PASS' if ok else 'FAIL'),flush=True)
    assert ok,name
def command(args,**kw):
    return subprocess.run([str(a) for a in args],capture_output=True,creationflags=flags,**kw)
inputs=[]
for app in ['csucampuscraft-user','csucampuscraft-admin']:
    inputs.append(base/app/'pom.xml')
    inputs.extend(p for p in (base/app/'src').rglob('*') if p.is_file())
inputs.extend(p for folder in ['assets','database'] for p in (base/folder).rglob('*') if p.is_file())
manifest=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(base).as_posix()+'\n' for p in sorted(inputs,key=lambda p:p.relative_to(base).as_posix()))
(ev/'runtime-inputs.sha256').write_text(manifest,encoding='utf-8',newline='\n')
result['runtime_manifest_sha256']=hashlib.sha256(manifest.encode()).hexdigest()
for app in ['csucampuscraft-user','csucampuscraft-admin']:
    jar=base/app/'target'/f'{app}-0.0.1-SNAPSHOT.jar'
    with zipfile.ZipFile(jar) as z:
        libs=[n for n in z.namelist() if n.startswith('BOOT-INF/lib/')]
        security=[n.split('/')[-1] for n in libs if 'security' in n.lower()]
        check(app+'-crypto-packaged',security==['spring-security-crypto-6.5.11.jar'],security)
        libdir=base/(app+'-libs');libdir.mkdir(exist_ok=True)
        for n in libs:
            if n.endswith('.jar'):(libdir/n.split('/')[-1]).write_bytes(z.read(n))
    result[app+'_jar_sha256']=hashlib.sha256(jar.read_bytes()).hexdigest()
check('INIT-01-build',all('BUILD SUCCESS' in (base/f'build-{t}.log').read_text() for t in ['user','admin']),'Both Maven verify exits were zero; executable JARs produced; no src/test present')
data=base/'mysql-data-attempt2'; data.mkdir(exist_ok=True)
rootpass=secrets.token_urlsafe(24);apppass=secrets.token_urlsafe(24)
initfile=base/'mysql-init-private.sql'
initfile.write_text("ALTER USER 'root'@'localhost' IDENTIFIED BY '"+rootpass+"';\n",encoding='utf-8')
server=None;apps=[];handles=[]
def freeport():
    with socket.socket() as s:
        s.bind(('127.0.0.1',0));return s.getsockname()[1]
port=freeport()
env=os.environ.copy();env['MYSQL_PWD']=rootpass
args=[mysql/'mysql.exe','--no-defaults','--no-login-paths','--protocol=TCP','--host=127.0.0.1',f'--port={port}','--user=root','--connect-timeout=2','--default-character-set=utf8mb4','--batch','--raw','--skip-column-names','--unbuffered']
def sql(query,db=None,allowfail=False):
    p=command(args+([f'--database={db}'] if db else []),input=query.encode('utf-8'),env=env,timeout=30)
    if p.returncode and not allowfail:raise RuntimeError(p.stderr.decode('utf-8',errors='replace'))
    return p
def rows(query,db='csucampuscraft'):
    return sql(query,db).stdout.decode('utf-8').strip()
tables=['store_user','category','product','product_image','cart_item','sales_order','sales_order_item']
def counts(db):
    return [int(rows('SELECT COUNT(*) FROM '+t,db)) for t in tables]
def get(path,appport):
    with urllib.request.urlopen(f'http://127.0.0.1:{appport}'+path,timeout=3) as r:
        return r.status,r.headers.get('Content-Type',''),r.read()
def launch(app,appport,db='csucampuscraft'):
    log=open(base/(app+'-launch.log'),'ab');handles.append(log)
    e=os.environ.copy()
    e.update(CSUCAMPUSCRAFT_DB_URL=f'jdbc:mysql://127.0.0.1:{port}/{db}',CSUCAMPUSCRAFT_DB_USER='csucampuscraft',CSUCAMPUSCRAFT_DB_PASSWORD=apppass)
    p=subprocess.Popen([str(java/'java.exe'),'-jar',str(base/app/'target'/f'{app}-0.0.1-SNAPSHOT.jar'),f'--server.port={appport}'],stdout=log,stderr=subprocess.STDOUT,env=e,creationflags=flags)
    apps.append(p)
    until=time.monotonic()+45
    while time.monotonic()<until:
        if p.poll() is not None:raise RuntimeError(app+' process exited')
        try:
            res=get('/',appport)
            if res[0]==200:return p,res
        except Exception:time.sleep(.2)
    raise RuntimeError(app+' startup timeout')
def stop(p):
    if p.poll() is None:
        p.terminate()
        try:p.wait(timeout=10)
        except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
try:
    p=command([mysql/'mysqld.exe','--no-defaults','--initialize-insecure','--basedir=D:/MySQL',f'--datadir={data}',f'--log-error={base/"mysql-initialize.log"}'],timeout=40)
    check('private-mysql-initialized',p.returncode==0,'New isolated datadir; existing MySQL service not used')
    log=open(base/'mysql-server.log','wb');handles.append(log)
    server=subprocess.Popen([str(mysql/'mysqld.exe'),'--no-defaults','--basedir=D:/MySQL',f'--datadir={data}',f'--port={port}','--bind-address=127.0.0.1','--mysqlx=OFF',f'--pid-file={base/"mysql.pid"}',f'--init-file={initfile}','--console'],stdout=log,stderr=subprocess.STDOUT,creationflags=flags)
    until=time.monotonic()+35
    while time.monotonic()<until:
        if server.poll() is not None:raise RuntimeError('private mysql process exited')
        try:
            p=sql('SELECT @@version,@@server_uuid,@@port;',allowfail=True)
            if p.returncode==0:break
        except Exception:pass
        time.sleep(.2)
    else:raise RuntimeError('mysql timeout')
    ident=p.stdout.decode().strip().split('\t')
    uuid=re.search(r'server-uuid=(.+)',(data/'auto.cnf').read_text()).group(1).strip()
    check('private-mysql-identity',ident[1]==uuid and int(ident[2])==port,'UUID matched isolated datadir and selected port')
    result['mysql_version']=ident[0];result['mysql_port']=port
    initfile.unlink()
    for db in ['csucampuscraft','csucampuscraft_structure','csucampuscraft_reject']:
        sql(f'CREATE DATABASE {db} CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_ci;')
    sql("CREATE USER 'csucampuscraft'@'127.0.0.1' IDENTIFIED BY '"+apppass+"';")
    for db in ['csucampuscraft','csucampuscraft_structure']:
        sql("GRANT SELECT,INSERT,UPDATE,DELETE ON "+db+".* TO 'csucampuscraft'@'127.0.0.1';")
    sql((base/'database/01-schema.sql').read_text(encoding='utf-8'),'csucampuscraft_structure')
    sql((base/'database/02-schema-with-demo.sql').read_text(encoding='utf-8'),'csucampuscraft')
    check('INIT-02-structure',counts('csucampuscraft_structure')==[0]*7,counts('csucampuscraft_structure'))
    check('INIT-02-demo',counts('csucampuscraft')==[4,15,60,100,10,10,20],counts('csucampuscraft'))
    check('INIT-02-hierarchy',rows("SELECT COUNT(*) FROM (SELECT c.id FROM category c LEFT JOIN product p ON p.category_id=c.id WHERE c.parent_id IS NOT NULL GROUP BY c.id HAVING COUNT(p.id)<>6) q;")=='0','Each second-level category has six products')
    check('INIT-02-order-totals',rows("SELECT COUNT(*) FROM sales_order o JOIN (SELECT order_id,SUM(line_amount) amt FROM sales_order_item GROUP BY order_id) i ON o.id=i.order_id WHERE o.total_amount<>i.amt;")=='0','All order totals equal snapshot lines')
    fail=(base/'database/02-schema-with-demo.sql').read_text(encoding='utf-8')
    assert fail.count('(SELECT COUNT(*) FROM store_user) <> 4')==1
    fail=fail.replace('(SELECT COUNT(*) FROM store_user) <> 4','(SELECT COUNT(*) FROM store_user) <> 5')
    p=sql(fail,'csucampuscraft_reject',True)
    check('INIT-02-seed-rollback',p.returncode!=0 and counts('csucampuscraft_reject')==[0]*7,'Forced precommit count assertion failed; seven DDL tables remain and all seed rows rolled back')
    (ev/'rollback-error.txt').write_bytes(p.stderr)
    for appport in [8080,8081]:
        with socket.socket() as s:s.bind(('127.0.0.1',appport))
    empty,res=launch('csucampuscraft-user',8080,'csucampuscraft_structure')
    check('INIT-03-empty',b'data-theme-count="0"' in res[2],'HTTP200 empty state on structure-only DB')
    stop(empty)
    up,ur=launch('csucampuscraft-user',8080)
    check('INIT-03-user-alone',b'data-csucampuscraft-app="user"' in ur[2] and b'data-theme-count="5"' in ur[2],'User standalone HTTP200 and five themes')
    stop(up)
    ap,ar=launch('csucampuscraft-admin',8081)
    check('INIT-03-admin-alone',b'data-csucampuscraft-app="admin"' in ar[2] and b'data-theme-count="5"' in ar[2],'Admin standalone HTTP200 and five themes')
    up,ur=launch('csucampuscraft-user',8080)
    for appport in [8080,8081]:
        status,ctype,body=get('/',appport)
        check('INIT-03-both-'+str(appport),status==200 and b'data-theme-count="5"' in body,'HTTP200 simultaneous')
    sql("UPDATE category SET name='本轮联通测试' WHERE code='LANDMARK';",'csucampuscraft')
    for appport in [8080,8081]:
        check('INIT-03-shared-change-'+str(appport),'本轮联通测试'.encode() in get('/',appport)[2],'Both ports read same committed name')
    before=counts('csucampuscraft')
    stop(up);stop(ap)
    up,_=launch('csucampuscraft-user',8080);ap,_=launch('csucampuscraft-admin',8081)
    check('INIT-04-restart',counts('csucampuscraft')==before and all('本轮联通测试'.encode() in get('/',n)[2] for n in [8080,8081]),'Both restarted applications retain shared change and seven table counts')
    sql("UPDATE category SET name='校园地标' WHERE code='LANDMARK';",'csucampuscraft')
    check('INIT-04-restored',all('校园地标'.encode() in get('/',n)[2] for n in [8080,8081]),'Original name restored in DB and both pages')
    original=(base/'assets/images/catalog-placeholder.svg').read_bytes()
    for appport in [8080,8081]:
        s,t,b=get('/images/catalog-placeholder.svg',appport)
        check('INIT-05-'+str(appport),s==200 and 'image/svg+xml' in t and b==original,{'http':s,'content_type':t,'sha256':hashlib.sha256(b).hexdigest()})
    hashes=rows("SELECT password_hash FROM store_user ORDER BY id;").splitlines()
    (base/'seed-hashes.txt').write_text('\n'.join(hashes),encoding='utf-8')
    harness=base/'CryptoSmoke.java'
    harness.write_text('''import java.nio.file.*;
import java.util.*;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
public class CryptoSmoke {
 public static void main(String[] args)throws Exception {
  var e=new BCryptPasswordEncoder(10);
  var lines=Files.readAllLines(Path.of(args[0]));
  if(lines.size()!=4 || new HashSet<>(lines).size()!=4)throw new AssertionError("seed count or salts");
  for(var h:lines)if(!h.startsWith("$2a$10$")||!e.matches("CSUCampusCraft123!",h)||e.matches("wrong-password",h))throw new AssertionError("seed check");
  var h=e.encode("new-teaching-password");
  if(!h.startsWith("$2a$10$")||!e.matches("new-teaching-password",h))throw new AssertionError("encode");
  System.out.println("BCrypt PASS four seeds positive and negative plus cost10 encode");
 }
}
''',encoding='utf-8')
    for app in ['csucampuscraft-user','csucampuscraft-admin']:
        cp=str(base/(app+'-libs')/'*')
        p=command([java/'javac.exe','-encoding','UTF-8','-cp',cp,str(harness)],timeout=15)
        check(app+'-crypto-compile',p.returncode==0,p.stderr.decode(errors='replace')[:200])
        p=command([java/'java.exe','-cp',str(base)+';'+cp,'CryptoSmoke',base/'seed-hashes.txt'],timeout=15)
        check(app+'-crypto-runtime',p.returncode==0,p.stdout.decode().strip())
    result['overall']='PASS'
except Exception as e:
    result['overall']='FAIL';result['error']=str(e);traceback.print_exc()
finally:
    for p in apps:stop(p)
    if server and server.poll() is None:
        try:
            p=command([mysql/'mysqladmin.exe','--no-defaults','--no-login-paths','--protocol=TCP','--host=127.0.0.1',f'--port={port}','--user=root','shutdown'],env=env,timeout=12)
            server.wait(timeout=12)
        except Exception:stop(server)
    for h in handles:h.close()
    if initfile.exists():initfile.unlink()
    (ev/'init-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print('EVIDENCE '+str(ev/'init-result.json'),flush=True)
if result['overall']!='PASS':raise SystemExit(1)

