"""AI curl demonstration for human step 6; never records human confirmation."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlencode
from datetime import datetime, timezone
import hashlib, json, os, subprocess, sys, tempfile

OUT = Path(__file__).parent
TARGET = OUT / 'step6-security-demo-attempt2.json'
TABLES = ['store_user', 'category', 'product', 'product_image', 'cart_item', 'sales_order', 'sales_order_item']

def now(): return datetime.now(timezone.utc).isoformat()
def sql(query):
    p = subprocess.run([cfg['mysql_exe'], '--defaults-file='+cfg['root_defaults_file'],
        '--skip-password', '--default-character-set=utf8mb4', '--batch', '--raw',
        '--skip-column-names', '--database='+cfg['database'],
        '--execute', "SET time_zone='+00:00'; "+query], capture_output=True)
    if p.returncode: raise RuntimeError('Isolated SQL read failed, exit='+str(p.returncode))
    return p.stdout

def snapshot():
    result = {}
    for table in TABLES:
        count, rows = sql('SELECT COUNT(*) FROM '+table+'; SELECT * FROM '+table+' ORDER BY id;').split(b'\n', 1)
        result[table] = {'rows':int(count.strip()), 'ordered_full_rows_sha256':hashlib.sha256(rows).hexdigest()}
    return result

class Inputs(HTMLParser):
    def __init__(self, text): super().__init__(); self.values={}; self.feed(text)
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=='input' and a.get('name'): self.values[a['name']]=a.get('value','')

def request(label, base, method, path, expected, jar, data=None):
    index=len(result['http'])+1
    header=tmp/('headers-'+str(index)); body=tmp/('body-'+str(index))
    args=['curl.exe','--silent','--show-error','--noproxy','*','--max-time','15',
        '--request',method,'--cookie',str(jar),'--cookie-jar',str(jar),
        '--dump-header',str(header),'--output',str(body),'--write-out','%{http_code}']
    payload=None
    if data is not None:
        args+=['--data-binary','@-']; payload=urlencode(data).encode('utf-8')
    args.append(base+path)
    p=subprocess.run(args,input=payload,capture_output=True)
    if p.returncode: raise RuntimeError('curl failed for '+label+', exit='+str(p.returncode))
    status=int(p.stdout.decode('ascii')); text=body.read_text(encoding='utf-8',errors='replace')
    headers=header.read_text(encoding='utf-8',errors='replace').splitlines()
    location=next((x.split(':',1)[1].strip() for x in headers if x.lower().startswith('location:')),None)
    csrf_rejected='CSRF_REJECTED' in text
    record={'at_utc':now(),'label':label,'method':method,'url':base+path,
        'curl_exit_code':p.returncode,'status':status,'expected':expected,'location':location,
        'form_fields':sorted(data.keys()) if data else [],
        'cookie_names_set':[x.split(':',1)[1].split('=',1)[0].strip() for x in headers if x.lower().startswith('set-cookie:')],
        'safe_error_code':'CSRF_REJECTED' if csrf_rejected else None,
        'body_sha256':hashlib.sha256(body.read_bytes()).hexdigest(),
        'raw_body_and_headers_archived':False,'executor':'AI curl demo; human observation pending'}
    result['http'].append(record)
    print(label+': HTTP '+str(status)+((' -> '+location) if location else '')+
          (' [CSRF_REJECTED]' if csrf_rejected else ''),flush=True)
    if status!=expected: raise RuntimeError('Unexpected HTTP '+str(status)+' for '+label+'; expected '+str(expected)+'; stopped immediately')
    return text,record

if TARGET.exists(): raise SystemExit('Refusing to overwrite prior step6 evidence')
cfg=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8-sig'))
result={'step':6,'executor':'AI curl demonstration at user request',
    'human_observation':'pending; user must confirm output before step7',
    'prior_preparation_failure':'step6-security-demo.json: sandbox temp-directory access denied before any HTTP request; preserved unmodified',
    'started_at_utc':now(),'http':[],'expected_main_statuses':[302,403,404]}
try:
    identity=sql('SELECT @@port,@@datadir,@@server_uuid,DATABASE();').decode('utf-8').strip().split('\t')
    samepath=lambda a,b:os.path.normcase(os.path.normpath(a))==os.path.normcase(os.path.normpath(b))
    if (int(identity[0])!=cfg['db_port'] or not samepath(identity[1],cfg['datadir'])
            or identity[2]!=cfg['server_uuid'] or identity[3]!=cfg['database']):
        raise RuntimeError('Instance identity mismatch; no demonstration performed')
    result['isolated_identity']={'port':int(identity[0]),'datadir':identity[1],
        'uuid':identity[2],'database':identity[3]}
    orders=sql("SELECT o.order_no,u.username,o.status,o.total_amount FROM sales_order o JOIN store_user u ON u.id=o.user_id WHERE u.username='alice' AND o.order_no NOT LIKE 'DEMO-%' ORDER BY o.id;").decode('utf-8').splitlines()
    if len(orders)!=1: raise RuntimeError('Expected exactly one new alice order; found '+str(len(orders)))
    fields=orders[0].split('\t'); order=fields[0]
    result['target_order']={'order_no':order,'owner':fields[1],'status':fields[2],'amount':fields[3],
        'source':'AI read-only SQL lookup of unique new order, not an added human observation'}
    result['before']=snapshot()
    with tempfile.TemporaryDirectory(prefix='step6-http-', dir=cfg['temp_directory']) as temporary:
        tmp=Path(temporary)
        parent=os.path.normcase(os.path.abspath(cfg['temp_directory']))
        target=os.path.normcase(os.path.abspath(temporary))
        if os.path.commonpath([parent,target])!=parent or target==parent:
            raise RuntimeError('Temporary credential directory guard failed')
        anonymous=tmp/'anonymous.jar'; bob=tmp/'bob.jar'
        _,r1=request('1. anonymous admin GET /',cfg['admin_url'],'GET','/',302,anonymous)
        if not r1['location'] or not r1['location'].startswith('/login'):
            raise RuntimeError('Anonymous redirect does not target login')
        _,r2=request('2. public POST /login without CSRF',cfg['user_url'],'POST','/login',403,anonymous,{'username':'bob'})
        if r2['safe_error_code']!='CSRF_REJECTED':raise RuntimeError('403 did not expose the expected safe CSRF error code')
        login,_=request('setup: bob login form',cfg['user_url'],'GET','/login',200,bob)
        token=Inputs(login).values.get('_csrf')
        if not token: raise RuntimeError('Bob login form token absent')
        request('setup: bob login',cfg['user_url'],'POST','/login',303,bob,
            {'username':'bob','password':'CSUCampusCraft123!','_csrf':token})
        own,_=request('setup: bob protected orders',cfg['user_url'],'GET','/orders',200,bob)
        if 'data-authenticated="true"' not in own or 'data-page-id="U07"' not in own:
            raise RuntimeError('Could not prove bob protected page is authenticated')
        request('3. authenticated bob GET alice order',cfg['user_url'],'GET','/orders/'+order,404,bob)
    result['temporary_cookie_header_body_directory_removed']=not Path(temporary).exists()
    result['after']=snapshot()
    result['seven_tables_unchanged']=result['before']==result['after']
    if not result['seven_tables_unchanged']: raise RuntimeError('Business data changed during read/login demo; stop and investigate')
    result['AI_demo_result']='PASS'
except Exception as exc:
    result['AI_demo_result']='FAIL'; result['error']=str(exc)
finally:
    result['finished_at_utc']=now()
    TARGET.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
print('AI demo result: '+result['AI_demo_result']+'; human confirmation pending',flush=True)
print('Evidence: '+str(TARGET),flush=True)
sys.exit(0 if result['AI_demo_result']=='PASS' else 1)
