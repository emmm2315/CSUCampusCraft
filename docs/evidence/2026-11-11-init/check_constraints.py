from pathlib import Path
import subprocess,os,secrets,socket,time,json,re,hashlib
base=Path(__file__).parent/'runtime';ev=Path(__file__).parent/'evidence'/'attempt2'
flags=subprocess.CREATE_NO_WINDOW
mysql=Path('D:/MySQL/bin');data=base/'mysql-data-attempt2'
assert data.resolve().is_relative_to(base.resolve())
password=secrets.token_urlsafe(24); init=base/'checks-audit-private.sql'
init.write_text("ALTER USER 'root'@'localhost' IDENTIFIED BY '"+password+"';",encoding='utf-8')
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
env=os.environ.copy();env['MYSQL_PWD']=password
args=[str(mysql/'mysql.exe'),'--no-defaults','--no-login-paths','--protocol=TCP','--host=127.0.0.1',f'--port={port}','--user=root','--batch','--raw','--skip-column-names','--connect-timeout=2','--default-character-set=utf8mb4']
def run(q):
 return subprocess.run(args,input=q.encode(),env=env,capture_output=True,creationflags=flags,timeout=15)
log=open(base/'checks-audit-server.log','wb')
p=subprocess.Popen([str(mysql/'mysqld.exe'),'--no-defaults','--basedir=D:/MySQL',f'--datadir={data}',f'--port={port}','--bind-address=127.0.0.1','--mysqlx=OFF',f'--init-file={init}','--console'],creationflags=flags,stdout=log,stderr=subprocess.STDOUT)
try:
 until=time.monotonic()+30
 while time.monotonic()<until:
  c=run('SELECT @@server_uuid,@@port;')
  if c.returncode==0:break
  if p.poll() is not None:raise RuntimeError('mysqld exited')
  time.sleep(.2)
 else:raise RuntimeError('audit startup timed out')
 uuid=re.search('server-uuid=(.+)',(data/'auto.cnf').read_text()).group(1).strip()
 assert c.stdout.decode().strip()==uuid+'\t'+str(port)
 expected=set(re.findall(r'CONSTRAINT (ck_\w+) CHECK',(base/'database/01-schema.sql').read_text(encoding='utf-8')))
 q="SELECT tc.TABLE_NAME,tc.CONSTRAINT_NAME,tc.ENFORCED,cc.CHECK_CLAUSE FROM information_schema.TABLE_CONSTRAINTS tc JOIN information_schema.CHECK_CONSTRAINTS cc ON cc.CONSTRAINT_SCHEMA=tc.CONSTRAINT_SCHEMA AND cc.CONSTRAINT_NAME=tc.CONSTRAINT_NAME WHERE tc.CONSTRAINT_SCHEMA='csucampuscraft' AND tc.CONSTRAINT_TYPE='CHECK' ORDER BY tc.TABLE_NAME,tc.CONSTRAINT_NAME;"
 c=run(q);assert c.returncode==0,c.stderr.decode()
 (ev/'check-constraints.tsv').write_bytes(c.stdout)
 rows=[r.split('\t') for r in c.stdout.decode().strip().splitlines()]
 assert len(rows)==35 and {r[1] for r in rows}==expected and all(r[2]=='YES' for r in rows)
 d={'passed':True,'count':35,'all_enforced':True,'names_match_01_schema':True,'baseline_git_sha':'ae6f47f995fef790b5a2f513574ed2129e4409b3','runtime_manifest_sha256':hashlib.sha256((ev/'runtime-inputs.sha256').read_bytes()).hexdigest()}
 (ev/'check-audit-result.json').write_text(json.dumps(d,indent=2),encoding='utf-8')
 print('35 CHECK constraints match exact SQL names and all ENFORCED=YES')
finally:
 init.unlink(missing_ok=True)
 subprocess.run([str(mysql/'mysqladmin.exe'),'--no-defaults','--no-login-paths','--protocol=TCP','--host=127.0.0.1',f'--port={port}','--user=root','shutdown'],env=env,capture_output=True,creationflags=flags,timeout=15)
 try:p.wait(timeout=10)
 except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=5)
 log.close()

