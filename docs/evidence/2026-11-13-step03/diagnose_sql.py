from pathlib import Path
import os,subprocess,socket,time,secrets,json
here=Path(__file__).parent
run=here/'runtime'/'attempt1'
out=here/'diagnostic-attempt1';out.mkdir(exist_ok=False)
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
pw=secrets.token_urlsafe(30)
init=run/'diagnostic-private-init.sql';init.write_text("ALTER USER 'root'@'localhost' IDENTIFIED BY '"+pw+"';",encoding='utf-8')
log=(out/'mysql-diagnostic.log').open('wb')
args=['D:/MySQL/bin/mysqld.exe','--no-defaults','--datadir='+str(run/'mysql-data'),'--port='+str(port),'--bind-address=127.0.0.1','--mysqlx=0','--init-file='+str(init),'--console']
p=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
env=os.environ.copy();env['MYSQL_PWD']=pw
client=['D:/MySQL/bin/mysql.exe','--no-defaults','--no-login-paths','--protocol=TCP','--host=127.0.0.1','--port='+str(port),'--user=root','--connect-timeout=2','--default-character-set=utf8mb4','--batch','--raw','--skip-column-names','--database=csucampuscraft']
try:
    for _ in range(80):
        c=subprocess.run(client,input=b'SELECT 1;',capture_output=True,env=env,creationflags=subprocess.CREATE_NO_WINDOW)
        if c.returncode==0:break
        if p.poll() is not None:raise RuntimeError('Diagnostic server startup failed')
        time.sleep(.1)
    q="SET SESSION time_zone='+00:00';SELECT parent_id,code FROM category WHERE code=CONVERT(0x4c414e444d41524b5f53544154494f4e455259 USING utf8mb4);"
    c=subprocess.run(client,input=q.encode(),capture_output=True,env=env,creationflags=subprocess.CREATE_NO_WINDOW)
    (out/'sql-diagnostic.json').write_text(json.dumps({'query':q,'exit_code':c.returncode,'stdout':c.stdout.decode(errors='replace'),'stderr':c.stderr.decode(errors='replace')},indent=2),encoding='utf-8')
    print(c.returncode,c.stderr.decode(errors='replace'))
finally:
    c=subprocess.run(['D:/MySQL/bin/mysqladmin.exe','--no-defaults','--no-login-paths','--protocol=TCP','--host=127.0.0.1','--port='+str(port),'--user=root','shutdown'],capture_output=True,env=env,creationflags=subprocess.CREATE_NO_WINDOW)
    if p.poll() is None:
        try:p.wait(timeout=10)
        except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=5)
    init.unlink(missing_ok=True);log.close()
