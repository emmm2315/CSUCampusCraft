"""Preserve safe final DB facts before authorized cleanup; no business writes."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import json, os, subprocess, sys

out=Path(__file__).parent/'final-sql-state.json'
if out.exists(): raise SystemExit('Refusing to overwrite final SQL evidence')
cfg=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8-sig'))
record={'captured_at_local':datetime.now(timezone(timedelta(hours=8))).isoformat(),
        'executor':'AI read-only corroboration after human confirmation; not additional human observations',
        'queries':[],'private_shipping_or_password_columns_selected':False}
def read(query):
    p=subprocess.run([cfg['mysql_exe'],'--defaults-file='+cfg['root_defaults_file'],'--skip-password',
        '--default-character-set=utf8mb4','--batch','--raw','--database='+cfg['database'],
        '--execute',"SET time_zone='+00:00'; "+query],capture_output=True,encoding='utf-8',errors='replace')
    if p.returncode: raise RuntimeError('Read-only SQL failed: exit '+str(p.returncode))
    lines=p.stdout.splitlines(); fields=lines[0].split('\t') if lines else []
    rows=[dict(zip(fields,line.split('\t'))) for line in lines[1:]]
    record['queries'].append({'sql':query,'exit_code':p.returncode,'rows':rows});return rows
try:
    identity=read('SELECT @@port AS port,@@datadir AS datadir,@@server_uuid AS uuid,DATABASE() AS db,@@version AS version;')[0]
    norm=lambda s:os.path.normcase(os.path.normpath(s))
    if (int(identity['port'])!=cfg['db_port'] or identity['uuid']!=cfg['server_uuid']
        or identity['db']!=cfg['database'] or norm(identity['datadir'])!=norm(cfg['datadir'])):
        raise RuntimeError('Isolated DB identity mismatch; stopped')
    record['identity']=identity
    orders=read("SELECT o.id,o.order_no,o.user_id,o.status,o.total_amount,o.payment_method,o.payment_no,o.created_at,o.paid_at,o.shipped_at,o.cancelled_at FROM sales_order o JOIN store_user u ON u.id=o.user_id WHERE u.username='alice' AND o.order_no NOT LIKE 'DEMO-%' ORDER BY o.id;")
    if len(orders)!=1: raise RuntimeError('New alice order was not unique')
    record['new_order']=orders[0]
    record['new_order_items']=read('SELECT product_id,sku_snapshot,product_name_snapshot,unit_price,quantity,line_amount FROM sales_order_item WHERE order_id='+orders[0]['id']+' ORDER BY product_id;')
    record['alice']=read("SELECT id,username,role,status,updated_at FROM store_user WHERE username='alice';")[0]
    record['alice_cart']=read("SELECT COUNT(*) AS rows_,COALESCE(SUM(ci.quantity),0) AS quantity FROM cart_item ci JOIN store_user u ON u.id=ci.user_id WHERE u.username='alice';")[0]
    record['main_products']=read("SELECT id,sku,stock,version,status FROM product WHERE sku IN ('CSU-LMK-NOTE-01','CSU-GRAD-BOX-01') ORDER BY id;")
    record['dashboard']=read("SELECT (SELECT COUNT(*) FROM product WHERE status='ON_SALE') AS on_sale,(SELECT COUNT(*) FROM product WHERE status='DRAFT') AS draft,(SELECT COUNT(*) FROM sales_order WHERE status='PAID') AS paid,(SELECT COUNT(*) FROM store_user WHERE role='CUSTOMER' AND status='ENABLED') AS enabled_customers,(SELECT COUNT(*) FROM store_user WHERE role='CUSTOMER' AND status='DISABLED') AS disabled_customers;")[0]
    record['album_product_5']=read('SELECT p.id,p.sku,p.version,COUNT(pi.id) AS image_count FROM product p LEFT JOIN product_image pi ON pi.product_id=p.id WHERE p.id=5 GROUP BY p.id,p.sku,p.version;')[0]
    record['result']='CAPTURED'
except Exception as error:
    record.update(result='FAIL',error=str(error))
finally:
    out.write_bytes((json.dumps(record,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
print(json.dumps({'result':record['result'],'new_order':record.get('new_order',{}).get('order_no'),
    'status':record.get('new_order',{}).get('status'),'dashboard':record.get('dashboard'),
    'album_product_5':record.get('album_product_5')},ensure_ascii=False))
sys.exit(0 if record['result']=='CAPTURED' else 1)
