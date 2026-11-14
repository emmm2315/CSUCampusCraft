from pathlib import Path
import os,socket,secrets,subprocess,json,time,shutil,re
here=Path(__file__).resolve().parent;base=here/'diagnostic-attempt2-lock-permission';base.mkdir(exist_ok=False)
runtime=base/'runtime';data=runtime/'mysql-data';runtime.mkdir()
source=here/'runtime/attempt2/mysql-data';shutil.copytree(source,data)
mysql=Path('D:/MySQL/bin');flag=subprocess.CREATE_NO_WINDOW
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
rootpw,apppw=secrets.token_urlsafe(28),secrets.token_urlsafe(28)
init=runtime/'reset-private.sql';init.write_text("ALTER USER 'root'@'localhost' IDENTIFIED BY '"+rootpw+"';\nALTER USER 'csucampuscraft'@'127.0.0.1' IDENTIFIED BY '"+apppw+"';",encoding='utf-8')
def scrub(s):
 for val in [rootpw,apppw]:s=s.replace(val,'[REDACTED]')
 return s
h=(runtime/'mysql.log').open('wb')
p=subprocess.Popen([str(mysql/'mysqld.exe'),'--no-defaults','--basedir=D:/MySQL',f'--datadir={data}',f'--port={port}','--bind-address=127.0.0.1','--mysqlx=OFF',f'--init-file={init}','--console'],creationflags=flag,stdout=h,stderr=subprocess.STDOUT)
args=[mysql/'mysql.exe','--no-defaults','--no-login-paths','--protocol=TCP','--host=127.0.0.1',f'--port={port}','--connect-timeout=2','--default-character-set=utf8mb4','--batch','--raw','--skip-column-names','--database=csucampuscraft']
results=[]
def sql(q,user='root',fail=False):
 env=os.environ.copy();env['MYSQL_PWD']=rootpw if user=='root' else apppw
 r=subprocess.run([str(x) for x in args]+['--user='+user],input=("SET time_zone='+00:00';"+q).encode(),capture_output=True,env=env,creationflags=flag,timeout=20)
 if not fail and r.returncode:raise RuntimeError('Diagnostic SQL failed '+scrub(r.stderr.decode(errors='replace')))
 return r
try:
 until=time.monotonic()+35
 while time.monotonic()<until:
  if p.poll() is not None:raise RuntimeError('Diagnostic private mysqld exited')
  q=sql('SELECT @@server_uuid,@@port;',fail=True)
  if not q.returncode:break
  time.sleep(.2)
 else:raise RuntimeError('Diagnostic private mysqld readiness timeout')
 expected=re.search(r'server-uuid=(.+)',(data/'auto.cnf').read_text()).group(1).strip()
 ident=q.stdout.decode().strip().split('\t');assert ident==[expected,str(port)]
 init.unlink()
 for tag,query in [('plain-read',"SELECT id,role,status FROM store_user WHERE id=4;"),('locking-read-before',"START TRANSACTION;SELECT id,role,status,updated_at FROM store_user WHERE id=4 FOR UPDATE;ROLLBACK;")]:
  q=sql(query,'csucampuscraft',True)
  results.append({'check':tag,'exit_code':q.returncode,'stderr':scrub(q.stderr.decode(errors='replace')),'row_count':len(q.stdout.splitlines())})
 results.append({'check':'original-grants','value':sql("SHOW GRANTS FOR 'csucampuscraft'@'127.0.0.1';").stdout.decode()})
 sql("GRANT LOCK TABLES ON csucampuscraft.* TO 'csucampuscraft'@'127.0.0.1';")
 q=sql("START TRANSACTION;SELECT id,role,status,updated_at FROM store_user WHERE id=4 FOR UPDATE;ROLLBACK;",'csucampuscraft',True)
 results.append({'check':'locking-read-after-lock-privilege','exit_code':q.returncode,'stderr':scrub(q.stderr.decode(errors='replace')),'row_count':len(q.stdout.splitlines())})
 report={'copied_failed_data_only':True,'source_datadir_unchanged':True,'actual_source_sha':'93f3c461163ff09f54b667299360068d450ca254','private_port':port,'checks':results}
 (base/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(report,ensure_ascii=False))
finally:
 if p.poll() is None:
  e=os.environ.copy();e['MYSQL_PWD']=rootpw
  subprocess.run([str(mysql/'mysqladmin.exe'),'--no-defaults','--no-login-paths','--protocol=TCP','--host=127.0.0.1',f'--port={port}','--user=root','shutdown'],env=e,capture_output=True,creationflags=flag,timeout=15)
  try:p.wait(timeout=10)
  except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=5)
 h.close()
 if init.exists():init.unlink()

