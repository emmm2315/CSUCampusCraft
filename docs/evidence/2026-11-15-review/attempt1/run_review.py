from common import *
from urllib.parse import urlencode
import sys, importlib.util, traceback

def one(r,q): return r.sql(q)[0]
def product(r,p): return one(r,'SELECT id,sku,name,price,stock,status,version,cover_image FROM product WHERE id='+str(p))
def cart(r): return r.sql('SELECT id,user_id,product_id,quantity,version FROM cart_item WHERE user_id=1 ORDER BY id')
def clear_cart(r):
    for x in cart(r): r.req(r.u,'u','POST','/cart/items/'+x['id']+'/remove',{'version':x['version']},303,label='clear alice cart row '+x['id'])
def add(r,p,q=1,expected=303): return r.req(r.u,'u','POST','/cart/items',{'productId':str(p),'quantity':str(q)},expected,label='add '+str(p)+' x '+str(q),zero=expected!=303)
def confirm(r,s=None,base='u'):
    z=r.req(s or r.u,base,'GET','/checkout',label='new confirmation')
    return r.inputs(z).get('confirmationToken'),z
def submit(r,t,expected=303,s=None,extra=None):
    d={'confirmationToken':t,'receiverName':'复核收货人','receiverPhone':'000-REVIEW','receiverAddress':'测试校区虚构地址'}
    d.update(extra or {})
    return r.req(s or r.u,'u','POST','/orders',d,expected,label='submit order',zero=expected!=303)

def A(r):
    r.begin('A'); before=r.digest()
    guest=r.fresh()
    r.req(guest,'u','GET','/',label='guest public 200')
    for b,p in [('u','/cart/items'),('a','/products')]:
        r.req(guest,b,'POST',p,{},302,label='unauthenticated before CSRF '+b,csrf=False,zero=True)
    for b,user in [('u','alice'),('a','admin')]:
        for wrong,pwd in [(user,'wrong-review-password'),('disabled','CSUCampusCraft123!'),('admin' if b=='u' else 'alice','CSUCampusCraft123!')]:
            s=r.login(b,wrong,pwd,200)
            r.req(s,b,'GET','/cart' if b=='u' else '/',expected=302,label='rejected login has no protected identity')
    both=r.login('u','alice'); r.login('a','admin',session=both)
    r.check('two different cookie names coexist',set(both.cookies.keys())=={'CSUCAMPUSCRAFT_USER_SESSION','CSUCAMPUSCRAFT_ADMIN_SESSION'},list(both.cookies.keys()))
    r.req(both,'u','GET','/cart'); r.req(both,'a','GET','/')
    r.req(both,'u','POST','/logout',{},303); r.req(both,'a','GET','/',label='admin survives user logout')
    r.login('u','alice',session=both); r.req(both,'a','GET','/'); r.req(both,'a','POST','/logout',{},303)
    r.req(both,'u','GET','/cart',label='user survives admin logout')
    r.u=r.login('u','alice'); r.a=r.login('a','admin')
    r.req(r.u,'a','GET','/',302,label='user cookie cannot authenticate admin')
    r.req(r.a,'u','GET','/cart',302,label='admin cookie cannot authenticate user')
    for s,b,p in [(r.u,'u','/cart/items'),(r.a,'a','/products')]:
        r.req(s,b,'POST',p,{},403,label='authenticated missing CSRF '+b,csrf=False,zero=True)
        r.req(s,b,'POST',p,{'_csrf':'f'*64},403,label='authenticated wrong CSRF '+b,csrf=False,zero=True)
    for b,id_,role in [('u',1,'ADMIN'),('a',4,'CUSTOMER')]:
        original=one(r,'SELECT status,role,updated_at FROM store_user WHERE id='+str(id_)); s=r.login(b,'alice' if b=='u' else 'admin')
        try:
            r.sql("UPDATE store_user SET role='"+role+"',updated_at='"+original['updated_at']+"' WHERE id="+str(id_))
            r.req(s,b,'GET','/cart' if b=='u' else '/',403,label='valid authStamp wrong role '+b)
        finally: r.sql("UPDATE store_user SET role='"+original['role']+"',updated_at='"+original['updated_at']+"' WHERE id="+str(id_))
    for b,id_,name in [('u',1,'alice'),('a',4,'admin')]:
        original=one(r,'SELECT status,updated_at FROM store_user WHERE id='+str(id_))
        try:
            s=r.login(b,name)
            r.sql("UPDATE store_user SET status='DISABLED',updated_at=updated_at+INTERVAL 1 MICROSECOND WHERE id="+str(id_))
            r.req(s,b,'GET','/cart' if b=='u' else '/',302,label='disabled next protected request '+b)
            r.req(s,b,'GET','/',200 if b=='u' else 302,label='disabled public/protected '+b)
            r.sql("UPDATE store_user SET status='"+original['status']+"',updated_at='"+original['updated_at']+"' WHERE id="+str(id_))
            r.req(s,b,'GET','/cart' if b=='u' else '/',302,label='cleared identity does not revive '+b)
            for unit in ['MICROSECOND','SECOND']:
                s=r.login(b,name)
                r.sql('UPDATE store_user SET updated_at=updated_at+INTERVAL 1 '+unit+' WHERE id='+str(id_))
                r.req(s,b,'GET','/cart' if b=='u' else '/',302,label=b+' authStamp change 1 '+unit)
                r.sql("UPDATE store_user SET updated_at='"+original['updated_at']+"' WHERE id="+str(id_))
                r.req(s,b,'GET','/cart' if b=='u' else '/',302,label='stamp identity cleared '+b)
        finally: r.sql("UPDATE store_user SET status='"+original['status']+"',updated_at='"+original['updated_at']+"' WHERE id="+str(id_))
    r.u=r.login('u','alice'); r.a=r.login('a','admin'); r.bob=r.login('u','bob')
    other=one(r,'SELECT id,version FROM cart_item WHERE user_id=2 LIMIT 1')
    for action in ['quantity','remove']:
        r.req(r.u,'u','POST','/cart/items/'+other['id']+'/'+action,{'version':other['version'],'quantity':'2'},403,label='other cart '+action,zero=True)
    otherorder=one(r,'SELECT order_no FROM sales_order WHERE user_id=2 LIMIT 1')['order_no']
    r.req(r.u,'u','GET','/orders/'+otherorder,404,label='other order concealed')
    for p in ['/payment','/cancel']:
        r.req(r.u,'u','POST','/orders/'+otherorder+p,{'result':'SUCCESS'},404,label='other order action concealed '+p,zero=True)
    r.check('A fixtures fully restored seven tables',before==r.digest())
    r.finish('A',['登录/错密/禁用/错角色、Cookie并存与互用拒绝、两向退出隔离、Auth先CSRF、双端微秒与秒认证戳、他人车403/订单404均为本轮HTTP。','会话身份清理通过恢复原戳后仍302观察；结算确认内部清除未在A直接读取会话，E以旧确认重新登录后409补充（登录本身也会清确认，不单独证明内部移除）。','身份root夹具仅修改本次隔离实例账号role/status/stamp，并完整恢复。'])

def B(r):
    r.begin('B'); g=r.fresh()
    p1=one(r,"SELECT id FROM product WHERE sku='CSU-LMK-NOTE-01'")['id']; p2=one(r,"SELECT id FROM product WHERE sku='CSU-GRAD-BOX-01'")['id']
    r.state.update(note_id=p1,box_id=p2)
    z=r.req(g,'u','GET','/'); r.check('five homepage themes',len(r.attrs(z,'data-theme-code'))==5)
    newest=[x['id'] for x in r.sql("SELECT id FROM product WHERE status='ON_SALE' ORDER BY created_at DESC,id DESC LIMIT 3")]
    featured=[x['id'] for x in r.sql("SELECT id FROM product WHERE status='ON_SALE' ORDER BY sort_order,id LIMIT 4")]
    sections=re.split(r'<section',z.text)
    for name,expected in [('newest',newest),('featured',featured)]:
        sec=next((s for s in sections if 'data-section="'+name+'"' in s),'')
        actual=re.findall(r'data-product-id="(\d+)"',sec)
        r.check('homepage '+name+' SQL order',actual==expected,{'actual':actual,'expected':expected})
    for path,sqlwhere,order in [('/products?categoryId=500&type=SOUVENIR&page=1&size=3','c.parent_id=500 AND c.code LIKE \'%SOUVENIR\'','p.sort_order,p.id'),('/products?sort=PRICE_ASC&page=2&size=3','1=1','p.price,p.id'),('/products?sort=PRICE_DESC&size=6','1=1','p.price DESC,p.id'),('/products?sort=NEWEST&size=6','1=1','p.created_at DESC,p.id DESC')]:
        # Graduation ID is obtained from DB; do not guess IDs from historical evidence.
        grad=one(r,"SELECT id FROM category WHERE code='GRADUATION'")['id']
        path=path.replace('categoryId=500','categoryId='+grad); sqlwhere=sqlwhere.replace('=500','='+grad)
        zz=r.req(g,'u','GET',path); rows=r.attrs(zz,'data-product-id')
        size=int(re.search(r'size=(\d+)',path).group(1)); off=size if 'page=2' in path else 0
        expected=[x['id'] for x in r.sql("SELECT p.id FROM product p JOIN category c ON c.id=p.category_id WHERE p.status='ON_SALE' AND "+sqlwhere+' ORDER BY '+order+' LIMIT '+str(size)+' OFFSET '+str(off))]
        r.check('list SQL exact '+path,rows==expected,{'actual':rows,'expected':expected})
    for path,code in [('/products?q=ZZZ_REVIEW_NO_MATCH',200),('/products?page=99999',200),('/products?type=WRONG',400),('/products?size=51',400),('/products/999999999',404)]: r.req(g,'u','GET',path,code)
    z=r.req(g,'u','GET','/products/'+p1); r.check('guest U03 login wording', '登录后加购' in z.text and 'data-login-to-add' in z.text,{'wording':'登录后加购'})
    gallery=[x['id'] for x in r.sql('SELECT id FROM product_image WHERE product_id='+p1+' ORDER BY sort_order,id')]
    r.check('detail gallery SQL order',r.attrs(z,'data-image-id')==gallery)
    draft=one(r,"SELECT id FROM product WHERE status='DRAFT' LIMIT 1")['id']; sold=one(r,"SELECT id FROM product WHERE status='ON_SALE' AND stock=0 LIMIT 1")['id']
    r.req(g,'u','GET','/products/'+draft,404); zs=r.req(g,'u','GET','/products/'+sold); r.check('sold out visible', '售罄' in zs.text)
    for b in ['u','a']:
        img=r.req(g,b,'GET','/images/catalog-placeholder.svg'); r.check('shared image bytes '+b,img.content==Path('assets/images/catalog-placeholder.svg').read_bytes(),img.headers.get('Content-Type'))
    clear_cart(r); r.req(r.u,'u','GET','/checkout',409,label='empty cart checkout')
    add(r,p1); add(r,p1); x=cart(r)[0]; r.check('same SKU merged quantity 2',len(cart(r))==1 and x['quantity']=='2')
    r.req(r.u,'u','POST','/cart/items/'+x['id']+'/quantity',{'quantity':'3','version':x['version']},303,label='change cart quantity')
    r.req(r.u,'u','POST','/cart/items/'+x['id']+'/quantity',{'quantity':'4','version':x['version']},409,label='stale cart version',zero=True)
    for q in [0,100,'1.5']: add(r,p1,q,400)
    add(r,draft,1,404); add(r,sold,1,409)
    original=product(r,p1)
    try:
        r.sql('UPDATE product SET stock=200,updated_at=updated_at WHERE id='+p1)
        x=cart(r)[0]; r.req(r.u,'u','POST','/cart/items/'+x['id']+'/quantity',{'quantity':'99','version':x['version']},303,label='99 upper boundary')
        add(r,p1,1,409)
        r.sql("UPDATE product SET status='DRAFT',updated_at=updated_at WHERE id="+p1)
        z=r.req(r.u,'u','GET','/cart'); r.check('invalid row badge includes all quantity',r.attrs(z,'data-cart-quantity')[0]=='99' and r.attrs(z,'data-cart-invalid-count')==['1'])
        r.req(r.u,'u','GET','/checkout',409,label='invalid cart checkout')
        x=cart(r)[0]; r.req(r.u,'u','POST','/cart/items/'+x['id']+'/quantity',{'quantity':'2','version':x['version']},409,label='invalid product quantity actual 409',zero=True)
        r.req(r.u,'u','POST','/cart/items/'+x['id']+'/remove',{'version':x['version']},303,label='invalid product can remove')
    finally: r.sql("UPDATE product SET stock="+original['stock']+",status='"+original['status']+"',updated_at=updated_at WHERE id="+p1)
    ids=[x['id'] for x in r.sql("SELECT id FROM product WHERE status='ON_SALE' AND stock>0 ORDER BY id LIMIT 21")]
    for p in ids[:20]: add(r,p)
    add(r,ids[20],1,409)
    r.check('20 SKU retained',len(cart(r))==20)
    clear_cart(r); add(r,p1,2); add(r,p2,1)
    z=r.req(r.u,'u','GET','/cart'); r.check('85 setup cart and badge',r.attrs(z,'data-cart-total')==['85.00'] and r.attrs(z,'data-cart-quantity')[0]=='3')
    r.finish('B',['首页/四种排序/筛选分页与独立SQL逐项比对；U03游客文案记录为“登录后加购”。','本轮真实HTTP覆盖同SKU合并、改量、移除、99/100、20/21 SKU、旧版本409、草稿404/售罄409及失效徽标。stock=200与DRAFT仅为隔离SQL边界夹具，结束恢复库存/状态，未改种子SQL文件。','已清alice种子车并使用HTTP备好2×18+1×49；后续阶段将成交。未测试并发及重启持久性。'])

def C(r):
    r.begin('C'); p1=r.state['note_id']; p2=r.state['box_id']; before=r.digest()
    t,z=confirm(r); r.check('U06 total85', '¥85.00' in z.text); r.check('confirmation no database writes',before==r.digest())
    t2,z2=confirm(r); r.check('reopen replaces opaque token',t!=t2 and len(t2)>=32)
    submit(r,t,409); t,z=confirm(r)
    submit(r,t,400,extra={'receiverName':' '})
    # The field-error response must retain the still valid confirmation value.
    last=(ROOT/'http.jsonl').read_text(encoding='utf-8').splitlines()[-1]
    rr=r.req(r.u,'u','POST','/orders',{'confirmationToken':t,'receiverName':'x'*51,'receiverPhone':'000-REVIEW','receiverAddress':'测试校区虚构地址'},400,label='overlong shipping field',zero=True)
    r.check('field400 preserves token',r.inputs(rr).get('confirmationToken')==t)
    x=cart(r)[0]; r.req(r.u,'u','POST','/cart/items/'+x['id']+'/quantity',{'version':x['version'],'quantity':'3'},303)
    submit(r,t,409); x=cart(r)[0]; r.req(r.u,'u','POST','/cart/items/'+x['id']+'/quantity',{'version':x['version'],'quantity':'2'},303)
    t,z=confirm(r); pr=product(r,p1)
    try:
        r.sql('UPDATE product SET price=19.00,version=version+1 WHERE id='+p1); submit(r,t,409)
    finally: r.sql('UPDATE product SET price='+pr['price']+',version='+pr['version']+',updated_at=updated_at WHERE id='+p1)
    # Short TTL auxiliary is the same packaged product and independent HTTP session.
    cfg=json.loads(Path(r.cfgpath).read_text(encoding='utf-8-sig'))
    if cfg.get('short_user_url'):
        saved=r.cfg['user_url']; r.cfg['user_url']=cfg['short_user_url']
        try:
            s=r.login('u','alice'); et,_=confirm(r,s); time.sleep(3); submit(r,et,409,s)
        finally: r.cfg['user_url']=saved
    else: r.check('short TTL expiry was run',False,'Auxiliary instance unavailable; do not claim expiry passed')
    stock0=[product(r,p) for p in [p1,p2]]; count0=int(one(r,'SELECT COUNT(*) AS n FROM sales_order')['n'])
    t,z=confirm(r); rr=submit(r,t,extra={'totalAmount':'0.01','userId':'2','user_id':'2','price':'0.01'})
    no=rr.headers.get('Location','').split('/')[-1]; r.state['paid_order']=no
    order=one(r,"SELECT id,order_no,user_id,status,total_amount,created_at,payment_method,payment_no,paid_at FROM sales_order WHERE order_no='"+no+"'")
    items=r.sql('SELECT id,order_id,product_id,sku_snapshot,product_name_snapshot,cover_image_snapshot,unit_price,quantity,line_amount FROM sales_order_item WHERE order_id='+order['id']+' ORDER BY product_id')
    stock1=[product(r,p) for p in [p1,p2]]
    r.check('one main two lines amount and owner',int(one(r,'SELECT COUNT(*) AS n FROM sales_order')['n'])==count0+1 and len(items)==2 and order['total_amount']=='85.00' and order['user_id']=='1' and [x['line_amount'] for x in items]==['36.00','49.00'],{'order':order,'items':items})
    r.check('inventory10/12 to8/11 and version+1',[x['stock'] for x in stock0]==['10','12'] and [x['stock'] for x in stock1]==['8','11'] and all(int(b['version'])==int(a['version'])+1 for a,b in zip(stock0,stock1)),{'before':stock0,'after':stock1})
    z=r.req(r.u,'u','GET','/orders/'+no); r.check('U08 cart badge zero',r.attrs(z,'data-cart-quantity')[0]=='0' and len(cart(r))==0)
    r.req(r.u,'u','GET','/orders',label='U07 order list')
    submit(r,t,409); add(r,p1); submit(r,t,409); r.check('old confirmation preserves later cart',len(cart(r))==1)
    clear_cart(r)
    # Product details mutate through management HTTP; snapshots must stay byte-identical.
    olditems=json.dumps(items,sort_keys=True); oldorder=r.sql('SELECT * FROM sales_order WHERE id='+order['id'],log=False)
    pr=product(r,p1); cat=one(r,'SELECT category_id FROM product WHERE id='+p1)['category_id']
    r.state['preorder_note_version']=stock0[0]['version']
    data={'categoryId':cat,'name':'REVIEW_CHANGED_NAME','price':'25.00','summary':'review','description':'<script>REVIEW_XSS</script>','coverImage':'images/catalog-placeholder.svg','sortOrder':'0','version':pr['version']}
    r.req(r.a,'a','POST','/products/'+p1,data,303,label='admin changes purchased product details')
    pr=product(r,p1); r.req(r.a,'a','POST','/products/'+p1+'/unpublish',{'version':pr['version']},303,label='admin unpublishes purchased product')
    for b,s in [('u',r.u),('a',r.a)]:
        zz=r.req(s,b,'GET','/orders/'+no); r.check('snapshot rendering unchanged '+b,items[0]['product_name_snapshot'] in zz.text and 'REVIEW_CHANGED_NAME' not in zz.text and '¥85.00' in zz.text)
    nowitems=r.sql('SELECT id,order_id,product_id,sku_snapshot,product_name_snapshot,cover_image_snapshot,unit_price,quantity,line_amount FROM sales_order_item WHERE order_id='+order['id']+' ORDER BY product_id')
    r.check('snapshot both tables byte identical after product changes',olditems==json.dumps(nowitems,sort_keys=True) and oldorder==r.sql('SELECT * FROM sales_order WHERE id='+order['id'],log=False))
    r.state['snapshot_order']=no; r.state['snapshot_items']=items
    r.finish('C',['新85元主单和两明细通过真实POST产生；篡改金额/userId不采信；10/12→8/11且各version+1，成功303到U08，清车/徽标0。','旧令牌/车变/价变/字段400及令牌保留、短TTL过期按实际check记录；重复提交是顺序重放，不是并发证明。','通过管理端HTTP改商品名/价/封面/描述再下架，订单两表完整行摘要/快照内容不变，U08/A07仍旧名称和85元。该商品暂保留DRAFT供D取消分支，下阶段恢复资料后重建另单。'])

def D(r):
    r.begin('D'); no=r.state['paid_order']; p1=r.state['note_id']; p2=r.state['box_id']
    baseline=[product(r,p) for p in [p1,p2]]
    r.req(r.u,'u','GET','/orders/'+no+'/payment',200,label='U09 mock payment page')
    r.req(r.u,'u','POST','/orders/'+no+'/payment',{'result':'BAD'},400,label='illegal payment result',zero=True)
    r.req(r.u,'u','POST','/orders/'+no+'/payment',{'result':'SUCCESS'},403,label='U09 missing CSRF',csrf=False,zero=True)
    r.req(r.u,'u','POST','/orders/'+no+'/payment',{'result':'FAILURE'},303,label='mock failure',zero=True)
    pay=lambda n:one(r,"SELECT order_no,status,payment_method,payment_no,paid_at,cancelled_at,shipped_at FROM sales_order WHERE order_no='"+n+"'")
    failed=pay(no); r.check('FAILURE retains pending and null triple',failed['status']=='PENDING_PAYMENT' and all(failed[k]=='NULL' for k in ['payment_method','payment_no','paid_at']))
    r.req(r.u,'u','POST','/orders/'+no+'/payment',{'result':'SUCCESS'},303,label='first mock success')
    first=pay(no); r.check('SUCCESS PAID MOCK receipt and time',first['status']=='PAID' and first['payment_method']=='MOCK' and first['payment_no']!='NULL' and first['paid_at']!='NULL')
    r.req(r.u,'u','POST','/orders/'+no+'/payment',{'result':'SUCCESS'},303,label='success replay',zero=True)
    r.check('first payment fields immutable',first==pay(no)); r.check('payment no inventory changes',baseline==[product(r,p) for p in [p1,p2]])
    for action,data in [('payment',{'result':'FAILURE'}),('cancel',{})]: r.req(r.u,'u','POST','/orders/'+no+'/'+action,data,409,label='PAID illegal '+action,zero=True)
    # Restore seed presentation via admin edit, without touching inventory/version manually.
    seed=r.state['snapshot_items'][0]; pr=product(r,p1); cat=one(r,'SELECT category_id FROM product WHERE id='+p1)['category_id']
    r.req(r.a,'a','POST','/products/'+p1,{'categoryId':cat,'name':seed['product_name_snapshot'],'price':seed['unit_price'],'coverImage':seed['cover_image_snapshot'],'summary':'review restored','description':'review restored','sortOrder':'0','version':pr['version']},303,label='restore product name price cover')
    pr=product(r,p1); r.req(r.a,'a','POST','/products/'+p1+'/publish',{'version':pr['version']},303,label='restore ON_SALE for second order')
    add(r,p1,2); add(r,p2); token,_=confirm(r); rr=submit(r,token); cancelno=rr.headers['Location'].split('/')[-1]; r.state['cancelled_order']=cancelno
    pr=product(r,p1); r.req(r.a,'a','POST','/products/'+p1+'/unpublish',{'version':pr['version']},303,label='down product before cancellation')
    stock0=[product(r,p) for p in [p1,p2]]
    # Add another SKU after successful submission, to prove cancellation leaves subsequent cart alone.
    add(r,p2); cart0=cart(r)
    r.req(r.u,'u','POST','/orders/'+cancelno+'/cancel',{},303,label='cancel two-item pending order')
    stock1=[product(r,p) for p in [p1,p2]]; cancelled=pay(cancelno)
    r.check('cancel returns2/1 and increments each version once',all(int(b['stock'])==int(a['stock'])+q and int(b['version'])==int(a['version'])+1 for a,b,q in zip(stock0,stock1,[2,1])),{'before':stock0,'after':stock1})
    r.check('cancel state no payment and draft preserved',cancelled['status']=='CANCELLED' and cancelled['cancelled_at']!='NULL' and stock1[0]['status']=='DRAFT')
    r.check('cancel does not refill or delete subsequent cart',cart0==cart(r))
    r.req(r.u,'u','POST','/orders/'+cancelno+'/cancel',{},303,label='repeat cancellation',zero=True)
    r.check('repeat cancellation preserves first time',pay(cancelno)==cancelled)
    r.req(r.u,'u','POST','/orders/'+cancelno+'/payment',{'result':'SUCCESS'},409,label='cancelled cannot pay',zero=True)
    r.req(r.bob,'u','GET','/orders/'+no+'/payment',404,label='other U09 hidden')
    r.req(r.a,'a','POST','/orders/'+cancelno+'/ship',{},409,label='cancelled cannot ship',zero=True)
    r.finish('D',['FAILURE零写/NULL三字段，SUCCESS首次凭证时间、重放不改、PAID拒绝失败支付/取消409。支付未变商品库存/版本。','第二张新两明细单取消返2/1各version+1；下架状态保留，重复取消零写/首次时间保留、不回填或清掉后续车条目，已取消支付/发货409。','U09页面/CSRF/他人404/非法result400均新跑；支付取消竞争/返库故障注入明确未跑。'])

def F(r):
    r.begin('F')
    queries={
      'orders_amount':"SELECT o.id FROM sales_order o LEFT JOIN sales_order_item i ON i.order_id=o.id GROUP BY o.id,o.total_amount HAVING COUNT(i.id)=0 OR o.total_amount<>SUM(i.line_amount)",
      'line_amount':"SELECT id FROM sales_order_item WHERE line_amount<>unit_price*quantity",
      'orphan_items':"SELECT i.id FROM sales_order_item i LEFT JOIN sales_order o ON o.id=i.order_id LEFT JOIN product p ON p.id=i.product_id WHERE o.id IS NULL OR p.id IS NULL",
      'cart_unique':"SELECT user_id,product_id,COUNT(*) AS n FROM cart_item GROUP BY user_id,product_id HAVING COUNT(*)>1",
      'payment_unique':"SELECT payment_no,COUNT(*) AS n FROM sales_order WHERE payment_no IS NOT NULL GROUP BY payment_no HAVING COUNT(*)>1",
      'time_and_fields':"SELECT id FROM sales_order WHERE (paid_at<created_at OR cancelled_at<created_at OR shipped_at<paid_at OR completed_at<shipped_at) OR (status IN ('PAID','SHIPPED','COMPLETED') AND (payment_method IS NULL OR payment_no IS NULL OR paid_at IS NULL)) OR (status IN ('PENDING_PAYMENT','CANCELLED') AND (payment_method IS NOT NULL OR payment_no IS NOT NULL OR paid_at IS NOT NULL))",
    }
    for name,q in queries.items(): rows=r.sql(q); r.check(name+' no violations',not rows,rows)
    p1=r.state['note_id']; p2=r.state['box_id']
    rows=r.sql("SELECT p.id,p.sku,p.stock,COALESCE(SUM(CASE WHEN o.id>10 AND o.status<>'CANCELLED' THEN i.quantity ELSE 0 END),0) AS net_review_sold FROM product p LEFT JOIN sales_order_item i ON i.product_id=p.id LEFT JOIN sales_order o ON o.id=i.order_id WHERE p.id IN ("+p1+','+p2+') GROUP BY p.id,p.sku,p.stock ORDER BY p.id')
    seeds={p1:10,p2:12}; r.check('seed stock minus review net orders exact',all(int(x['stock'])==seeds[x['id']]-int(x['net_review_sold']) for x in rows),rows)
    for s,user in [(r.u,1),(r.bob,2)]:
        z=r.req(s,'u','GET','/cart'); n=one(r,'SELECT COALESCE(SUM(quantity),0) AS n FROM cart_item WHERE user_id='+str(user))['n']; r.check('badge SQL SUM user'+str(user),r.attrs(z,'data-cart-quantity')[0]==n)
    c=r.sql("SELECT tc.TABLE_NAME,tc.CONSTRAINT_NAME,tc.ENFORCED,cc.CHECK_CLAUSE FROM information_schema.TABLE_CONSTRAINTS tc JOIN information_schema.CHECK_CONSTRAINTS cc ON cc.CONSTRAINT_SCHEMA=tc.CONSTRAINT_SCHEMA AND cc.CONSTRAINT_NAME=tc.CONSTRAINT_NAME WHERE tc.CONSTRAINT_SCHEMA=DATABASE() AND tc.CONSTRAINT_TYPE='CHECK' ORDER BY tc.TABLE_NAME,tc.CONSTRAINT_NAME")
    r.check('35 CHECK constraints enforced',len(c)==35 and all(x['ENFORCED']=='YES' for x in c))
    # A representative CHECK rejection, transaction rolled back on this isolated fixture.
    q="START TRANSACTION; UPDATE product SET stock=-1 WHERE id="+p1+"; ROLLBACK"
    args=[r.cfg['mysql_exe'],'--defaults-extra-file='+r.cfg['root_defaults_file'],'--database='+r.cfg['database'],'--execute',q]
    pp=subprocess.run(args,capture_output=True,encoding='utf-8',errors='replace')
    dump(ROOT/'check-rejection.json',{'sql':q,'exit':pp.returncode,'stderr':pp.stderr}); r.check('negative stock CHECK rejection observed',pp.returncode!=0 and '3819' in pp.stderr)
    no=r.state['snapshot_order']; z=r.req(r.u,'u','GET','/orders/'+no); za=r.req(r.a,'a','GET','/orders/'+no)
    row=one(r,"SELECT created_at FROM sales_order WHERE order_no='"+no+"'")
    from datetime import timedelta
    target=(datetime.fromisoformat(row['created_at'])+timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
    r.check('both pages Asia Shanghai created-time',target in z.text and target in za.text,{'db_UTC':row['created_at'],'expected_display':target})
    r.finish('F',['独立SQL核对全库金额/小计/孤儿/车唯一/支付凭证唯一/时间链字段；主线库存按种子10/12减本轮未取消成交核对。','管理员新增REVIEW商品及补货单列为E夹具，不能套用原60商品种子公式。35个CHECK元数据均核对，仅负库存运行拒绝做代表，不称穷举35种非法写。','订单业务状态迁移会改主单状态时间；商品改资料后的“快照两表不变”在C动作前后已精确比较，不声称支付/发货后主单所有列不变。'])

if __name__=='__main__':
    r=Review(sys.argv[1])
    try:
        for fn in [A,B,C,D]: fn(r)
        print('A-D_COMPLETE; press Enter to execute E/F after inspection',flush=True)
        input()
        r.begin('E')
        spec=importlib.util.spec_from_file_location('admin_review',ROOT/'admin'/'admin_review.py'); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); mod.run(r)
        F(r)
        dump(ROOT/'execution-summary.json',{'finished':stamp(),'checks':len(r.checks),'failures':[x for x in r.checks if not x['passed']],'state':r.state})
        print('REVIEW_EXECUTION_COMPLETE',flush=True)
    except Exception:
        dump(ROOT/'runner-error.json',{'at':stamp(),'stage':r.stage,'traceback':traceback.format_exc()}); print(traceback.format_exc(),flush=True); r.finish(r.stage,['Execution interrupted: see runner-error.json. Do not inherit unrun checks.']); sys.exit(1)
