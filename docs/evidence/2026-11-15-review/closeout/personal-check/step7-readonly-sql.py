"""Read-only comparison values for human step 7. Does not send any A10 request."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import json, os, subprocess, sys

out=Path(__file__).parent/'step7-sql-reference.json'
if out.exists(): raise SystemExit('Refusing to overwrite an existing reference snapshot')
cfg=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8-sig'))
record={'phase':'human step7 pending','executor':'AI read-only SQL reference',
        'A10_request_sent_by_AI':False,'human_confirmation':None,
        'captured_at_local':datetime.now(timezone(timedelta(hours=8))).isoformat(),'queries':[]}

def read(query):
    args=[cfg['mysql_exe'],'--defaults-file='+cfg['root_defaults_file'],'--skip-password',
          '--default-character-set=utf8mb4','--batch','--raw','--database='+cfg['database'],
          '--execute',"SET time_zone='+00:00'; "+query]
    p=subprocess.run(args,capture_output=True,encoding='utf-8',errors='replace')
    if p.returncode: raise RuntimeError('Isolated read-only SQL failed, exit='+str(p.returncode))
    lines=p.stdout.splitlines(); fields=lines[0].split('\t') if lines else []
    rows=[dict(zip(fields,x.split('\t'))) for x in lines[1:]]
    record['queries'].append({'sql':query,'exit_code':p.returncode,'rows':rows})
    return rows

try:
    identity=read('SELECT @@port AS port,@@datadir AS datadir,@@server_uuid AS uuid,DATABASE() AS db;')[0]
    norm=lambda s:os.path.normcase(os.path.normpath(s))
    if (int(identity['port'])!=cfg['db_port'] or norm(identity['datadir'])!=norm(cfg['datadir'])
        or identity['uuid']!=cfg['server_uuid'] or identity['db']!=cfg['database']):
        raise RuntimeError('Isolated instance identity does not match; stop')
    summary=read("SELECT (SELECT COUNT(*) FROM product WHERE status='ON_SALE') AS on_sale,"
                 "(SELECT COUNT(*) FROM product WHERE status='DRAFT') AS draft,"
                 "(SELECT COUNT(*) FROM sales_order WHERE status='PAID') AS paid,"
                 "(SELECT COUNT(*) FROM store_user WHERE role='CUSTOMER' AND status='ENABLED') AS enabled_customers,"
                 "(SELECT COUNT(*) FROM store_user WHERE role='CUSTOMER' AND status='DISABLED') AS disabled_customers;")[0]
    candidate=read("SELECT p.id,p.sku,p.name,p.version,0 AS image_count FROM product p "
                   "WHERE p.status='ON_SALE' AND NOT EXISTS(SELECT 1 FROM product_image pi WHERE pi.product_id=p.id) "
                   "ORDER BY p.id LIMIT 1;")
    if len(candidate)!=1: raise RuntimeError('No empty-album candidate found; stop')
    record.update(result='READY_FOR_HUMAN_COMPARISON',dashboard=summary,album_candidate=candidate[0])
    print('A02 SQL: on_sale='+summary['on_sale']+', draft='+summary['draft']+', paid='+summary['paid']+
          ', enabled_customers='+summary['enabled_customers']+', disabled_customers='+summary['disabled_customers'])
    print('Empty album: product='+candidate[0]['id']+', sku='+candidate[0]['sku']+
          ', version='+candidate[0]['version']+', image_count=0')
    print('No A10 HTTP request sent; human action and confirmation pending.')
except Exception as error:
    record.update(result='FAIL',error=str(error))
finally:
    out.write_bytes((json.dumps(record,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
if record['result']=='FAIL':
    print(record['error']); sys.exit(1)
