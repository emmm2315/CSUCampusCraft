from pathlib import Path
import os,subprocess,secrets,socket,time,shutil,json,re,hashlib
base=Path(__file__).resolve().parent
work=base/'diagnostic-attempt2-runtime';ev=base/'diagnostic-attempt2'
work.mkdir(exist_ok=False);ev.mkdir(exist_ok=False)
source=base/'runtime/attempt2/mysql-data';data=work/'mysql-data'
shutil.copytree(source,data)
secret=secrets.token_urlsafe(28)
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
init=work/'private-init.sql';init.write_text("ALTER USER 'root'@'localhost' IDENTIFIED BY '"+secret+"';",encoding='utf-8')
argv=['D:/MySQL/bin/mysqld.exe','--no-defaults','--basedir=D:/MySQL','--datadir='+str(data),'--port='+str(port),'--bind-address=127.0.0.1','--mysqlx=OFF','--init-file='+str(init),'--console']
h=(work/'server.log').open('wb');proc=subprocess.Popen(argv,stdout=h,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
env=os.environ.copy();env['MYSQL_PWD']=secret
calls=[]
def sql(q,utc=True):
 args=['D:/MySQL/bin/mysql.exe','--no-defaults','--no-login-paths','--protocol=TCP','--host=127.0.0.1','--port='+str(port),'--user=root','--connect-timeout=2','--batch','--raw','--skip-column-names','--database=csucampuscraft']
 p=subprocess.run(args,input=(("SET SESSION time_zone='+00:00';" if utc else '')+q).encode(),env=env,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
 calls.append({'argv':args,'exit_code':p.returncode,'utc_session_explicit':utc})
 if p.returncode:raise RuntimeError('Diagnostic SQL unavailable')
 return p.stdout
tables=['store_user','category','product','product_image','cart_item','sales_order','sales_order_item']
def snap():return {t:{'rows':int(sql('SELECT COUNT(*) FROM '+t)),'sha256':hashlib.sha256(sql('SELECT * FROM '+t+' ORDER BY id;')).hexdigest()} for t in tables}
result={}
try:
 deadline=time.monotonic()+35
 while time.monotonic()<deadline:
  try:sql('SELECT 1;');break
  except RuntimeError:time.sleep(.2)
 else:raise RuntimeError('Diagnostic private server timeout')
 original=json.loads((base/'evidence/attempt2/database-original.json').read_text(encoding='utf-8'))
 before=snap();result['changed_tables_before_fix']=[t for t in tables if before[t]!=original[t]]
 result['default_timezone']=sql('SELECT @@session.time_zone,@@system_time_zone,TIMESTAMPDIFF(MINUTE,UTC_TIMESTAMP(),CURRENT_TIMESTAMP());',utc=False).decode().strip().split('\t')
 deltas=sql('SELECT id,status,role,TIMESTAMPDIFF(MINUTE,created_at,updated_at) FROM store_user ORDER BY id;').decode().splitlines()
 result['user_deltas_minutes']=[{'id':int(c[0]),'status':c[1],'role':c[2],'updated_minus_created_minutes':int(c[3])} for c in (x.split('\t') for x in deltas)]
 # Seed omitted both timestamps, so initial updated_at==created_at; modify only copied failed data.
 sql('UPDATE store_user SET updated_at=created_at WHERE id IN (1,4);')
 after=snap();result['all_tables_match_original_after_utc_timestamp_only_repair']=after==original
 result['only_restore_utc_timezone_was_wrong']=result['changed_tables_before_fix']==['store_user'] and after==original and all(x['updated_minus_created_minutes']==(-480 if x['id'] in [1,4] else 0) for x in result['user_deltas_minutes'])
 result['original_failed_datadir_modified']=False
 result['production_source_modified']=False
 result['scope']='Copied failed private data directory; read seven hashes, repaired only updated_at in copy. Original attempt and runtime data untouched.'
 result['overall']='PASS' if result['only_restore_utc_timezone_was_wrong'] else 'FAIL'
 (ev/'before-repair-snapshot.json').write_text(json.dumps(before,indent=2),encoding='utf-8')
 (ev/'after-repair-snapshot.json').write_text(json.dumps(after,indent=2),encoding='utf-8')
finally:
 try:
  args=['D:/MySQL/bin/mysqladmin.exe','--no-defaults','--no-login-paths','--protocol=TCP','--host=127.0.0.1','--port='+str(port),'--user=root','shutdown']
  p=subprocess.run(args,env=env,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=15);proc.wait(timeout=15)
 except Exception:proc.terminate();proc.wait(timeout=10)
 h.close();init.unlink(missing_ok=True)
 result['diagnostic_process_stopped']=proc.poll() is not None
 (ev/'commands.json').write_text(json.dumps(calls,indent=2),encoding='utf-8')
 (ev/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(result,ensure_ascii=False))

