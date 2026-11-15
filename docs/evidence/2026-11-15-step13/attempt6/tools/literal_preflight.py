"""New tool-only SQL literal proof. No app/JAR, seed, old runner or product mutation."""
from pathlib import Path
import json,os,socket,subprocess,time,datetime
from harness import Harness,MYSQL,FLAG
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'literal-preflight';BASE.mkdir(exist_ok=False)
data=BASE/'mysql-data';data.mkdir();logs=[];server=None;checks={};results=[]
with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
def run(args,**kw):return subprocess.run([str(x) for x in args],capture_output=True,creationflags=FLAG,**kw)
def sql(q):return run([MYSQL/'mysql.exe','--no-defaults','--no-login-paths','--host=127.0.0.1',f'--port={port}','--user=root','--batch','--raw','--skip-column-names','--default-character-set=utf8mb4'],input=q.encode('utf-8'),timeout=30)
def query(name,q,predicate):
    p=sql(q);value=p.stdout.decode('utf-8').strip();ok=p.returncode==0 and predicate(value);checks[name]=bool(ok);results.append(dict(name=name,sql=q,exit_code=p.returncode,output=value,stderr=p.stderr.decode('utf-8',errors='replace'),passed=ok));assert ok,name
try:
    p=run([MYSQL/'mysqld.exe','--no-defaults','--initialize-insecure','--basedir=D:/MySQL',f'--datadir={data}',f'--log-error={BASE/"initialize.log"}'],timeout=60);assert p.returncode==0
    log=(BASE/'server.log').open('wb');logs.append(log);server=subprocess.Popen([str(MYSQL/'mysqld.exe'),'--no-defaults','--basedir=D:/MySQL',f'--datadir={data}',f'--port={port}','--bind-address=127.0.0.1','--mysqlx=OFF','--console'],stdout=log,stderr=subprocess.STDOUT,creationflags=FLAG)
    until=time.monotonic()+35
    while time.monotonic()<until:
        p=sql('SELECT @@port;')
        if p.returncode==0:break
        if server.poll() is not None:raise RuntimeError('owned preflight MySQL exited')
        time.sleep(.2)
    assert p.stdout.decode().strip()==str(port)
    lit=Harness.literal
    query('literal coercibility4',"SELECT COERCIBILITY("+lit('literal')+"),CHARSET("+lit('literal')+"),COLLATION("+lit('literal')+");",lambda s:s.split('\t')[:2]==['4','utf8mb4'])
    p=sql("CREATE DATABASE csu13_literal CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_ci;CREATE TABLE csu13_literal.t(sku VARCHAR(40) COLLATE utf8mb4_0900_as_ci,name VARCHAR(80) COLLATE utf8mb4_0900_as_ci);INSERT INTO csu13_literal.t VALUES('MiXeD','中文界😀');");assert p.returncode==0
    query('business case insensitive SKU column',"SELECT COUNT(*) FROM csu13_literal.t WHERE sku="+lit('mixed')+';',lambda s:s=='1')
    query('business UTF8 name column',"SELECT COUNT(*) FROM csu13_literal.t WHERE name="+lit('中文界😀')+';',lambda s:s=='1')
    query('information_schema utf8mb3 column',"SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA="+lit('csu13_literal')+' AND TABLE_NAME='+lit('t')+';',lambda s:s=='1')
    query('performance_schema MESSAGE_TEXT comparison',"SELECT COUNT(*) FROM performance_schema.events_statements_history_long WHERE MESSAGE_TEXT="+lit('STEP13_LITERAL_MARKER')+';',lambda s:s.isdigit())
    query('JSON_OBJECT key',"SELECT JSON_OBJECT("+lit('safeKey')+",1);",lambda s:json.loads(s)=={'safeKey':1})
    for i,value in enumerate(['','中文','😀',"back\\slash'quote!%_"]):query('HEX roundtrip '+str(i),'SELECT HEX('+lit(value)+');',lambda s,v=value:s.upper()==v.encode('utf-8').hex().upper())
finally:
    if server is not None:
        if server.poll() is None:
            try:sql('SHUTDOWN;')
            except Exception:pass
            Harness.stop(server)
    for f in logs:f.close()
    record=dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),overall='PASS' if len(checks)==10 and all(checks.values()) else 'FAIL',checks=checks,observations=results,private_port=port,server_stopped=server is None or server.poll() is not None,scope='External literal SQL tool preflight only; no HTTP/product/seed or formal P0 verdict',credentials_or_personal_values=False)
    (BASE/'result.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(overall=record['overall'],checks=len(checks),port=port,server_stopped=record['server_stopped'])))
