"""Separate new observations correcting review-tool gaps; original FAIL stays intact."""
from common import *
from urllib.parse import urlencode
import sys

r=Review(sys.argv[1])
prior=[json.loads(x) for x in (ROOT/'http.jsonl').read_text(encoding='utf-8').splitlines()]
r.n=max(x['id'] for x in prior)
r.state=json.loads((ROOT/'run-state-public.json').read_text(encoding='utf-8'))
r.begin('supplement')
r.u=r.login('u','alice'); r.a=r.login('a','admin')
one=lambda q:r.sql(q)[0]
pid=r.state['admin_fixture_product']; note=r.state['note_id']; no=r.state['snapshot_order']

# Repeat album writes on the dedicated fixture, select ARTICLE rows rather than form markers.
for alt,sort in [('补充后图','20'),('补充前图','10')]:
    p=one(f'SELECT version FROM product WHERE id={pid}')
    r.req(r.a,'a','POST',f'/products/{pid}/images',{'imagePath':'images/catalog-placeholder.svg','altText':alt,'sortOrder':sort,'productVersion':p['version']},303,label='supplement album add')
imgs=r.sql(f'SELECT id,image_path,sort_order FROM product_image WHERE product_id={pid} ORDER BY sort_order,id')
z=r.req(r.a,'a','GET',f'/products/{pid}/images',label='supplement album precise row selector')
actual=[a['data-image-id'] for t,a in Elements(z.text).tags if t=='article' and 'data-image-id' in a]
expected=[i['id'] for i in imgs]
r.check('A10 article rows order equals SQL',actual==expected,{'actual':actual,'expected':expected,'correction':'Original E compared article plus two form markers per image; original FAIL retained.'})
# Independently re-read the archived original body; do not overwrite it.
original=next(x for x in prior if x['label']=='E A10 album order')
old_html=(ROOT/original['body']).read_text(encoding='utf-8')
original_rows=[a['data-image-id'] for t,a in Elements(old_html).tags if t=='article' and 'data-image-id' in a]
r.check('original E article rows matched its SQL order',original_rows==['160','159'],{'original_http':original['id'],'actual_article_rows':original_rows,'expected_from_original_checks':['160','159']})
for i in imgs:
    p=one(f'SELECT version FROM product WHERE id={pid}')
    r.req(r.a,'a','POST',f'/products/{pid}/images/{i["id"]}/remove',{'productVersion':p['version']},303,label='supplement album remove')

# C submitted the same cover path as before. This NEW action truly changes it.
order_before=r.sql("SELECT * FROM sales_order WHERE order_no='"+no+"'",log=False)
items_before=r.sql('SELECT * FROM sales_order_item WHERE order_id='+order_before[0]['id'],log=False)
p=one(f'SELECT id,category_id,name,price,cover_image,summary,description,sort_order,version FROM product WHERE id={note}')
new_cover='images/review-missing-cover.svg'
r.check('supplement cover path will actually change',p['cover_image']!=new_cover,{'before':p['cover_image'],'after':new_cover})
d={'categoryId':p['category_id'],'name':p['name'],'price':p['price'],'coverImage':new_cover,'summary':p['summary'],'description':p['description'],'sortOrder':p['sort_order'],'version':p['version']}
r.req(r.a,'a','POST',f'/products/{note}',d,303,label='actual cover-path change after order')
r.check('cover changed in current product',one(f'SELECT cover_image FROM product WHERE id={note}')['cover_image']==new_cover)
r.check('cover change leaves both historical tables identical',order_before==r.sql("SELECT * FROM sales_order WHERE order_no='"+no+"'",log=False) and items_before==r.sql('SELECT * FROM sales_order_item WHERE order_id='+order_before[0]['id'],log=False))
for b,s in [('u',r.u),('a',r.a)]:
    page=r.req(s,b,'GET','/orders/'+no,label='historical cover remains '+b)
    sources=r.attrs(page,'src')
    r.check('historical cover path from snapshot '+b,'/images/catalog-placeholder.svg' in sources and '/'+new_cover not in sources,sources)

# Query actual fixture name using literal SQL LIKE and compare list IDs plus total.
fixture_name=one(f'SELECT name FROM product WHERE id={pid}')['name']
page=r.req(r.u,'u','GET','/products?'+urlencode({'q':fixture_name,'size':50}),label='exact name search')
r.check('literal full name result and total',r.attrs(page,'data-product-id')==[str(pid)] and r.attrs(page,'data-product-count')==['1'])

# Full seed inventory equation, using a newly imported reference schema and only this run's orders.
new_orders=[r.state['paid_order'],r.state['cancelled_order']]
quoted=','.join("'"+n+"'" for n in new_orders)
rows=r.sql("SELECT p.id,p.sku,p.stock,ref.stock AS seed_stock,COALESCE(SUM(CASE WHEN o.order_no IN ("+quoted+") AND o.status<>'CANCELLED' THEN i.quantity ELSE 0 END),0) AS review_net_sold FROM product p JOIN review_reference.product ref ON ref.sku=p.sku LEFT JOIN sales_order_item i ON i.product_id=p.id LEFT JOIN sales_order o ON o.id=i.order_id GROUP BY p.id,p.sku,p.stock,ref.stock ORDER BY p.id")
r.check('all60 seed inventory = imported seed minus net review orders',len(rows)==60 and all(int(x['stock'])==int(x['seed_stock'])-int(x['review_net_sold']) for x in rows),{'products':len(rows),'mismatches':[x for x in rows if int(x['stock'])!=int(x['seed_stock'])-int(x['review_net_sold'])]})
fixture=one(f'SELECT stock,version FROM product WHERE id={pid}')
r.check('independent fixture stock4 plus restock3 remains7',fixture['stock']=='7',fixture)

# Role-based denial was observed in A; add no-CSRF protected POST to confirm same filter order.
original=one('SELECT role,updated_at FROM store_user WHERE id=4')
try:
    r.sql("UPDATE store_user SET role='CUSTOMER',updated_at='"+original['updated_at']+"' WHERE id=4")
    r.req(r.a,'a','POST','/products',{},403,label='authenticated wrong admin role refuses write',csrf=False,zero=True)
finally: r.sql("UPDATE store_user SET role='"+original['role']+"',updated_at='"+original['updated_at']+"' WHERE id=4")

r.finish('supplement',['E原始FAIL保留。新相册操作按article[data-image-id]对应独立SQL，原已归档页面按同样行选择器复查，证明重复data标记造成工具误报。','C原小结声称封面变化过强：该次仅提交同一placeholder路径。本补充真实把当前封面换为合法但不存在的images/review-missing-cover.svg，历史两表整行不变，U08/A07仍读旧封面路径。源素材只有placeholder，未新增产品素材。','全60种子SKU基于新导入reference schema比较库存公式；独立新增REVIEW商品为4+3=7。','HTTP日志续编号，不覆写原响应；原C短TTL为http180–183，使用environment/short-ttl-state.json中的18080；其余本轮请求u=8080/a=8081。'])
dump(ROOT/'supplement-result.json',{'finished':stamp(),'checks':len(r.checks),'failures':[x for x in r.checks if not x['passed']],'original_failure_retained':True})
sys.exit(1 if any(not c['passed'] for c in r.checks) else 0)
