from pathlib import Path
import json
import manage_mysql

manifest=Path('D:/severlt/tmp/step07-validation/runtime/mysql84-attempt1/instance.json')
m=json.loads(manifest.read_text(encoding='utf-8')); directory=manifest.parent; base=Path(m['basedir'])
actual=manage_mysql.identity(base,m['port'],directory)
assert actual['uuid']==m['uuid'] and actual['datadir']==m['datadir'] and actual['port']==m['port']
def sql(query):
    r=manage_mysql.sql(base,m['port'],directory,query,m['schema'])
    if r.returncode: raise RuntimeError(r.stderr.decode('utf-8',errors='replace'))
    return r.stdout.decode('utf-8').strip()
before=sql('SELECT id,sku,stock,status,version,cover_image FROM product WHERE id IN (1,11) ORDER BY id')
sql("UPDATE product SET stock=10,status='ON_SALE',price=18.00,version=version+1,cover_image='images/step07-missing-test.png' WHERE id=1;"
    "UPDATE product SET stock=0,status='ON_SALE',version=version+1 WHERE id=11;"
    "DELETE FROM cart_item WHERE user_id=(SELECT id FROM store_user WHERE username='alice');"
    "INSERT INTO cart_item(user_id,product_id,quantity,version) SELECT id,1,2,0 FROM store_user WHERE username='alice';"
    "INSERT INTO cart_item(user_id,product_id,quantity,version) SELECT id,11,1,0 FROM store_user WHERE username='alice';")
after=sql('SELECT id,sku,stock,status,version,cover_image FROM product WHERE id IN (1,11) ORDER BY id')
Path('D:/severlt/tmp/step07-validation/browser-fixture.json').write_text(json.dumps({'isolated_uuid':m['uuid'],'before':before,'after':after,'purpose':'Browser-only missing-cover, sold-out and invalid-cart fixture; ephemeral database is stopped after verification.'},ensure_ascii=False,indent=2),encoding='utf-8')
print('Prepared isolated browser fixture (products1/11, alice cart2+1).')
