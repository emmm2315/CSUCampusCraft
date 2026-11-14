import json, subprocess, pathlib, re, hashlib, requests, html
ROOT=pathlib.Path(__file__).resolve().parents[4]
OUT=pathlib.Path(__file__).resolve().parent
s=json.loads((OUT/'state.json').read_text(encoding='utf-8-sig'))
cmdlog=OUT.parent/'commands-environment.md'
def query(name,sql,database='csucampuscraft'):
    (OUT/(name+'.sql')).write_text(sql,encoding='utf-8')
    argv=['D:/MySQL/bin/mysql.exe','--defaults-file='+s['rootConfig'],'--skip-password','--database='+database,'--batch','--raw']
    with cmdlog.open('a',encoding='utf-8') as f:f.write('\n`'+' '.join(argv)+' < environment/'+name+'.sql`\n')
    p=subprocess.run(argv,input=sql.encode('utf-8'),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    (OUT/(name+'.tsv')).write_bytes(p.stdout)
    (OUT/(name+'.stderr.log')).write_bytes(p.stderr)
    return {'exitCode':p.returncode,'result':p.stdout.decode('utf-8','replace')}
http=[]
for url in ['http://127.0.0.1:8080/','http://127.0.0.1:8081/login']:
    r=requests.get(url,timeout=15);http.append({'method':'GET','url':url,'status':r.status_code})
a=requests.Session();r=a.get('http://127.0.0.1:8081/login',timeout=15)
token=html.unescape(re.search(r'name="_csrf"[^>]*value="([^"]+)"',r.text).group(1))
r=a.post('http://127.0.0.1:8081/login',data={'_csrf':token,'username':'admin','password':'CSUCampusCraft123!'},allow_redirects=False,timeout=15)
http.append({'method':'POST','url':'http://127.0.0.1:8081/login','fields':['username','password','_csrf'],'status':r.status_code,'location':r.headers.get('Location'),'cookieNames':list(a.cookies.keys())})
r=a.get('http://127.0.0.1:8081/',timeout=15);http.append({'method':'GET','url':'http://127.0.0.1:8081/','status':r.status_code})
(OUT/'startup-http.json').write_text(json.dumps(http,ensure_ascii=False,indent=2),encoding='utf-8')
results={}
results['server']=query('server',"SELECT VERSION() version,@@server_uuid server_uuid,@@port port,@@datadir datadir,@@pid_file pid_file,@@global.time_zone global_time_zone,@@session.time_zone root_session_time_zone,@@system_time_zone system_time_zone,@@default_storage_engine default_storage_engine; SHOW GRANTS FOR 'review_app'@'127.0.0.1';")
results['checks']=query('checks',"SELECT tc.CONSTRAINT_SCHEMA,tc.TABLE_NAME,tc.CONSTRAINT_NAME,cc.CHECK_CLAUSE,tc.ENFORCED FROM information_schema.TABLE_CONSTRAINTS tc JOIN information_schema.CHECK_CONSTRAINTS cc ON cc.CONSTRAINT_SCHEMA=tc.CONSTRAINT_SCHEMA AND cc.CONSTRAINT_NAME=tc.CONSTRAINT_NAME WHERE tc.CONSTRAINT_SCHEMA IN ('csucampuscraft','review_schema') AND tc.CONSTRAINT_TYPE='CHECK' ORDER BY tc.CONSTRAINT_SCHEMA,tc.TABLE_NAME,tc.CONSTRAINT_NAME;")
results['sessions']=query('sessions',"SELECT t.THREAD_ID,t.PROCESSLIST_ID,t.PROCESSLIST_USER,t.PROCESSLIST_DB,t.PROCESSLIST_HOST,v.VARIABLE_NAME,v.VARIABLE_VALUE,a.ATTR_NAME,a.ATTR_VALUE FROM performance_schema.threads t JOIN performance_schema.variables_by_thread v ON t.THREAD_ID=v.THREAD_ID LEFT JOIN performance_schema.session_connect_attrs a ON t.PROCESSLIST_ID=a.PROCESSLIST_ID WHERE t.PROCESSLIST_USER='review_app' AND v.VARIABLE_NAME='time_zone' ORDER BY t.PROCESSLIST_ID,a.ORDINAL_POSITION;")
results['indexes']=query('indexes',"SELECT TABLE_SCHEMA,TABLE_NAME,INDEX_NAME,NON_UNIQUE,SEQ_IN_INDEX,COLUMN_NAME FROM information_schema.STATISTICS WHERE TABLE_SCHEMA IN ('csucampuscraft','review_schema') ORDER BY TABLE_SCHEMA,TABLE_NAME,INDEX_NAME,SEQ_IN_INDEX;")
results['jars']={}
for side in ['user','admin']:
    jar=ROOT/f'csucampuscraft-{side}/target/csucampuscraft-{side}-0.0.1-SNAPSHOT.jar'
    results['jars'][side]={'path':str(jar),'bytes':jar.stat().st_size,'sha256':hashlib.sha256(jar.read_bytes()).hexdigest()}
(OUT/'inspection-result.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v['exitCode'] for k,v in results.items() if 'exitCode' in v},ensure_ascii=False))
