from pathlib import Path
import os,subprocess,socket,time,secrets,json,zipfile
here=Path(__file__).parent
run=here/'runtime'/'attempt2'
out=here/'diagnostic-attempt2';out.mkdir(exist_ok=False)
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
    extract=out/'jar';extract.mkdir()
    with zipfile.ZipFile('D:/Github Projects/CSUCampusCraft/csucampuscraft-user/target/csucampuscraft-user-0.0.1-SNAPSHOT.jar') as z:
        for n in z.namelist():
            if n.startswith('BOOT-INF/classes/') or n.startswith('BOOT-INF/lib/'):z.extract(n,extract)
    cp=str(extract/'BOOT-INF/classes')+';'+str(extract/'BOOT-INF/lib/*')+';'+str(out)
    javac='C:/Users/Starmetor/.jdks/ms-21.0.12.1/bin/javac.exe'
    java='C:/Users/Starmetor/.jdks/ms-21.0.12.1/bin/java.exe'
    c=subprocess.run([javac,'-encoding','UTF-8','-cp',cp,'-d',str(out),str(here/'MapperDiagnostic.java')],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
    (out/'compile.log').write_bytes(c.stdout+c.stderr)
    if c.returncode:raise RuntimeError('compile failed')
    url='jdbc:mysql://127.0.0.1:'+str(port)+'/csucampuscraft'
    env.update({'CSUCAMPUSCRAFT_DB_URL':url,'CSUCAMPUSCRAFT_DB_USER':'root','CSUCAMPUSCRAFT_DB_PASSWORD':pw,'SPRING_DATASOURCE_URL':url,'SPRING_DATASOURCE_USERNAME':'root','SPRING_DATASOURCE_PASSWORD':pw,'SPRING_SQL_INIT_MODE':'never','SPRING_PROFILES_ACTIVE':'default'})
    c=subprocess.run([java,'-Dfile.encoding=UTF-8','-cp',cp,'MapperDiagnostic'],capture_output=True,env=env,creationflags=subprocess.CREATE_NO_WINDOW,timeout=45)
    text=(c.stdout+c.stderr).decode('utf-8',errors='replace').replace(pw,'[REDACTED]')
    (out/'mapper-diagnostic.log').write_text(text,encoding='utf-8');print(text)
finally:
    c=subprocess.run(['D:/MySQL/bin/mysqladmin.exe','--no-defaults','--no-login-paths','--protocol=TCP','--host=127.0.0.1','--port='+str(port),'--user=root','shutdown'],capture_output=True,env=env,creationflags=subprocess.CREATE_NO_WINDOW)
    if p.poll() is None:
        try:p.wait(timeout=10)
        except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=5)
    init.unlink(missing_ok=True);log.close()
