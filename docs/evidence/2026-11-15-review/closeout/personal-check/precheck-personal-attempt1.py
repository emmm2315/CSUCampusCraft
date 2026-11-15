"""AI setup precheck only. Never checkout, create order, pay, ship or change users."""
from pathlib import Path
from html.parser import HTMLParser
from datetime import datetime, timezone
import hashlib, json, subprocess, time, sys
import requests

OUT = Path('docs/evidence/2026-11-15-review/closeout/personal-check')
CFG_PATH = Path(sys.argv[1])
cfg = json.loads(CFG_PATH.read_text(encoding='utf-8-sig'))
TABLES = ['store_user','category','product','product_image','cart_item','sales_order','sales_order_item']
commands = []
def sql(query):
    args=[cfg['mysql_exe'],'--defaults-file='+cfg['root_defaults_file'],'--skip-password','--default-character-set=utf8mb4','--database='+cfg['database'],'--batch','--raw','--execute',"SET time_zone='+00:00'; "+query]
    p=subprocess.run(args,capture_output=True,encoding='utf-8',errors='replace')
    commands.append({'kind':'mysql','sql':query,'exit_code':p.returncode,'raw_rows_not_saved_for_private_tables':True})
    if p.returncode: raise RuntimeError('mysql query failed: '+p.stderr)
    lines=p.stdout.splitlines()
    return [dict(zip(lines[0].split('\t'),x.split('\t'))) for x in lines[1:]] if lines else []
def digest():
    result={}
    for t in TABLES:
        rows=sql('SELECT * FROM '+t+' ORDER BY id')
        result[t]={'row_count':len(rows),'full_ordered_rows_sha256':hashlib.sha256(json.dumps(rows,sort_keys=True,ensure_ascii=False).encode()).hexdigest()}
    return result
def save(name,obj):
    (OUT/name).write_bytes((json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
class Inputs(HTMLParser):
    def __init__(self,text): super().__init__(); self.fields={}; self.feed(text)
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='input' and a.get('name'): self.fields[a['name']]=a.get('value','')

records=[]
started=datetime.now(timezone.utc).isoformat()
for side in ['user','admin']:
    url=cfg[side+'_url']
    ready=False
    for attempt in range(90):
        try:
            response=requests.get(url+'/login',timeout=2)
            if response.status_code==200: ready=True; break
        except requests.RequestException: pass
        time.sleep(.5)
    if not ready: raise RuntimeError(side+' login not ready')

before=digest()
for side,user,protected in [('user','alice','/cart'),('admin','admin','/')]:
    s=requests.Session();s.trust_env=False;url=cfg[side+'_url']
    initial=s.get(url+'/login',timeout=10); initial.encoding='utf-8'
    token=Inputs(initial.text).fields.get('_csrf')
    if initial.status_code!=200 or not token: raise RuntimeError(side+' login form missing token')
    posted=s.post(url+'/login',data={'username':user,'password':'CSUCampusCraft123!','_csrf':token},allow_redirects=False,timeout=10)
    page=s.get(url+protected,allow_redirects=False,timeout=10)
    records.extend([
        {'executor':'AI setup precheck, not human step','side':side,'method':'GET','url':url+'/login','status':initial.status_code,'csrf_present':bool(token)},
        {'executor':'AI setup precheck, not human step','side':side,'method':'POST','url':url+'/login','request':{'username':user,'password':'[PUBLIC_SEED_PASSWORD_OMITTED]','_csrf':'[OMITTED]'},'status':posted.status_code,'location':posted.headers.get('Location'),'cookie_names':sorted(s.cookies.keys())},
        {'executor':'AI setup precheck, not human step','side':side,'method':'GET','url':url+protected,'status':page.status_code,'authenticated_marker':('data-authenticated="true"' in page.text) if side=='user' else ('data-page-id="A02"' in page.text)}
    ])
    if posted.status_code!=303 or page.status_code!=200: raise RuntimeError(side+' login precheck failed')
after=digest()
fixture=sql("SELECT ci.id AS cart_item_id,u.username,p.id AS product_id,p.sku,ci.quantity,ci.version AS cart_version,p.version AS product_version,p.price,p.stock,p.status,p.price*ci.quantity AS subtotal FROM cart_item ci JOIN store_user u ON u.id=ci.user_id JOIN product p ON p.id=ci.product_id WHERE u.username='alice' ORDER BY p.id")
totals=sql("SELECT COUNT(*) AS sku_rows,SUM(ci.quantity) AS pieces,SUM(ci.quantity*p.price) AS total_amount FROM cart_item ci JOIN store_user u ON u.id=ci.user_id JOIN product p ON p.id=ci.product_id WHERE u.username='alice'")
no_album=sql("SELECT p.id,p.sku,p.name,p.status,p.version FROM product p WHERE p.status='ON_SALE' AND NOT EXISTS(SELECT 1 FROM product_image i WHERE i.product_id=p.id) ORDER BY p.id LIMIT 1")
check_ok=(before==after and totals[0]=={'sku_rows':'2','pieces':'3','total_amount':'85.00'} and [x['stock'] for x in fixture]==['10','12'] and all(x['cart_version']=='0' and x['product_version']=='0' and x['status']=='ON_SALE' for x in fixture))
report={'started_at_utc':started,'finished_at_utc':datetime.now(timezone.utc).isoformat(),'executor':'Codex AI preparation only; human seven-step check not begun','checkout_requested':False,'business_actions_requested':False,'login_precheck_requests':records,'before_login':before,'after_login':after,'seven_tables_unchanged_by_login_precheck':before==after,'fixture_kind':'root SQL fixture only; not human manual cart actions','fixture':fixture,'fixture_totals':totals,'no_album_candidate_for_future_human_step7':no_album,'result':'READY' if check_ok else 'PREPARATION_FAILED','human_step_results_recorded':False,'commands':commands}
save('login-and-fixture-precheck.json',report)
print(json.dumps({'result':report['result'],'user_url':cfg['user_url'],'admin_url':cfg['admin_url'],'fixture':fixture,'totals':totals,'no_album_candidate':no_album,'business_actions_requested':False},ensure_ascii=False))
if not check_ok: raise SystemExit(1)
