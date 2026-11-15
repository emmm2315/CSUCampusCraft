"""New final-SHA public/auth/cart/order P0 checks. No historical script is imported or executed."""
from decimal import Decimal
import json,time,urllib.parse,secrets

def page(h,r,page_id):h.check('page '+page_id,r.dom.find(lambda n:n.a.get('data-page-id')==page_id) is not None)
def badge(h,r,uid):
    wanted=sum(x['quantity'] for x in h.cartrows(uid)) if uid else 0;n=r.dom.find(lambda n:n.a.get('id')=='cart-quantity')
    h.check('SUM quantity badge includes every row',n is not None and n.a.get('data-cart-quantity')==str(wanted) and n.text().strip()==str(wanted))
def product_list(h,c,params=None,expected=200):
    p=dict(params or {});r=c.get('/products'+('?' + urllib.parse.urlencode(p) if p else ''),expected=expected)
    if expected!=200:return r
    root=r.dom.find(lambda n:n.a.get('data-page-id')=='U02');h.check('U02 root',root is not None);data=h.state();theme=p.get('categoryId');kind=p.get('type','ALL');q=p.get('q','').strip();sort=p.get('sort','DEFAULT');number=max(1,int(p.get('page',1)));size=int(p.get('size',6))
    rows=[x for x in data['product'].values() if x['status']=='ON_SALE' and (not theme or data['category'][str(x['categoryId'])]['parentId']==int(theme)) and (kind=='ALL' or data['category'][str(x['categoryId'])]['code'].endswith('_'+kind)) and q.casefold() in x['name'].casefold()]
    keys={'DEFAULT':lambda x:(x['sortOrder'],x['id']),'PRICE_ASC':lambda x:(Decimal(x['price']),x['id']),'PRICE_DESC':lambda x:(-Decimal(x['price']),x['id']),'NEWEST':lambda x:(x['createdAt'],x['id'])}
    rows=sorted(rows,key=keys[sort],reverse=sort=='NEWEST');shown=rows[(number-1)*size:number*size];cards=root.all(lambda n:n.tag=='article' and 'data-product-id' in n.a)
    h.check('catalog SQL count and stable row order',int(root.a['data-product-count'])==len(rows) and [int(n.a['data-product-id']) for n in cards]==[x['id'] for x in shown]);h.check('canonical page size',int(root.a['data-page'])==number and int(root.a['data-size'])==size)
    for n in root.all(lambda n:n.tag=='a' and 'data-page-link' in n.a):
        query=urllib.parse.parse_qs(urllib.parse.urlsplit(n.a.get('href','')).query)
        for k in ['categoryId','type','q','sort','size']:
            if k in p:h.check('pagination keeps '+k,query.get(k)==[str(p[k]).strip()])
    return r
def order_detail(h,c,no,end='u',expected=200):
    r=c.get('/orders/'+no,end,expected=expected)
    if expected!=200:
        h.check('error omits order snapshot',not r.dom.find(lambda n:'data-order-item-id' in n.a));return r
    order=h.order(no);root=r.dom.find(lambda n:n.a.get('data-page-id')==('U08' if h.end(end)=='u' else 'A07'));h.check('detail matches state/status/total',root is not None and root.a.get('data-order-status')==order['status'] and Decimal(root.a['data-order-total'])==Decimal(order['totalAmount']))
    lines=sorted((x for x in h.state()['sales_order_item'].values() if x['orderId']==order['id']),key=lambda x:x['id']);shown=root.all(lambda n:n.tag=='tr' and 'data-order-item-id' in n.a);h.check('all original snapshot items',[int(x.a['data-order-item-id']) for x in shown]==[x['id'] for x in lines])
    for n,x in zip(shown,lines):h.check('snapshot field equality '+str(x['id']),all(n.a.get(k)==str(v) for k,v in [('data-snapshot-sku',x['skuSnapshot']),('data-snapshot-name',x['productNameSnapshot']),('data-snapshot-cover',x['coverImageSnapshot']),('data-quantity',x['quantity'])]) and Decimal(n.a['data-unit-price'])==Decimal(x['unitPrice']) and Decimal(n.a['data-line-amount'])==Decimal(x['lineAmount']))
    for key in ['receiverName','receiverPhone','receiverAddress']:
        n=root.find(lambda n:n.a.get('data-shipping-value')==key);h.check('shipping snapshot digest '+key,n is not None and __import__('hashlib').sha256(n.text().encode()).hexdigest()==order[key+'Sha256'])
    return r
def order_list(h,c,params=None,end='u',uid=1,expected=200):
    p=dict(params or {});r=c.get('/orders'+('?' + urllib.parse.urlencode(p) if p else ''),end,expected=expected)
    if expected!=200:return r
    root=r.dom.find(lambda n:n.a.get('data-page-id')==('U07' if h.end(end)=='u' else 'A06'));number=max(1,int(p.get('page',1)));size=int(p.get('size',10));no=p.get('orderNo','').strip();status=p.get('status','ALL');target=uid if h.end(end)=='u' else int(p['userId']) if p.get('userId') else None
    rows=sorted((x for x in h.state()['sales_order'].values() if (target is None or x['userId']==target) and (not no or x['orderNo'].lower()==no.lower()) and (status=='ALL' or x['status']==status)),key=lambda x:(x['createdAt'],x['id']),reverse=True);shown=rows[(number-1)*size:number*size]
    h.check('order count and exact CI/owner/status filters',root is not None and int(root.a['data-order-count'])==len(rows) and [int(x.a['data-order-id']) for x in root.all(lambda n:n.tag=='tr' and 'data-order-id' in n.a)]==[x['id'] for x in shown])
    for n in root.all(lambda n:n.tag=='a' and 'data-page-link' in n.a):
        qs=urllib.parse.parse_qs(urllib.parse.urlsplit(n.a['href']).query)
        for k in ['orderNo','status','userId','size']:
            if k in p:h.check('order page preserves '+k,qs.get(k)==[str(p[k]).strip()])
    return r
def payment(h,c,no,result='SUCCESS',expected=303,zero=False):return h.post(c,'/orders/'+no+'/payment',{'result':result},expected=expected,zero=zero)
def cancel(h,c,no,expected=303,zero=False):return h.post(c,'/orders/'+no+'/cancel',expected=expected,zero=zero)

def run(h,user,admin):
    guest=h.Client('public');data=h.state();note=h.pid('CSU-LMK-NOTE-01');gift=h.pid('CSU-GRAD-BOX-01');alt=next(x['id'] for x in data['product'].values() if x['status']=='ON_SALE' and x['stock']>=5 and x['id'] not in [note,gift])
    graduation=next(x for x in data['category'].values() if x['code']=='GRADUATION' and x['parentId'] is None)
    with h.case('TST-01'):
        home=guest.get('/',expected=200);page(h,home,'U01');h.check('five theme roots',len(home.dom.all(lambda n:'data-theme-code' in n.a))==5);product_list(h,guest);detail=guest.get('/products/'+str(gift),expected=200);page(h,detail,'U03');h.check('public current SKU and price',detail.dom.find(lambda n:n.a.get('data-product-sku')=='CSU-GRAD-BOX-01' and Decimal(n.a.get('data-price'))==Decimal('49')) is not None)
    with h.case('TST-02'):
        home=guest.get('/',expected=200);sales=[x for x in data['product'].values() if x['status']=='ON_SALE']
        for name,wanted in [('newest',sorted(sales,key=lambda x:(x['createdAt'],x['id']),reverse=True)[:3]),('featured',sorted(sales,key=lambda x:(x['sortOrder'],x['id']))[:4])]:
            section=home.dom.find(lambda n:n.a.get('data-section')==name);h.check(name+' exact SQL ordering',[int(n.a['data-product-id']) for n in section.all(lambda n:n.tag=='article' and 'data-product-id' in n.a)]==[x['id'] for x in wanted])
    with h.case('TST-03'):
        theme=next(x for x in data['category'].values() if x['parentId'] is None)
        for kind in ['ALL','STATIONERY','SOUVENIR']:
            for sort in ['DEFAULT','PRICE_ASC','PRICE_DESC','NEWEST']:product_list(h,guest,{'categoryId':theme['id'],'type':kind,'sort':sort,'page':2,'size':2})
        for kind in ['STATIONERY','SOUVENIR']:product_list(h,guest,{'type':kind})
        original=h.product(alt);h.fixture('UPDATE product SET name='+h.literal('STEP13 % _ \\ ! literal')+',updated_at=updated_at WHERE id='+str(alt),'catalog literal search fixture')
        for q in ['%','_','\\','!','not-found','界'*120]:product_list(h,guest,{'q':q,'size':50})
        product_list(h,guest,{'page':0});product_list(h,guest,{'page':9999,'size':2})
        h.fixture('UPDATE product SET name='+h.literal(original['name'])+',updated_at=updated_at WHERE id='+str(alt),'restore literal name')
        child=next(x for x in data['category'].values() if x['parentId'] is not None)
        for p,code in [({'categoryId':999999},404),({'categoryId':child['id']},404),({'type':'x'},400),({'sort':'price;drop'},400),({'size':0},400),({'size':51},400),({'page':'x'},400),({'q':'x'*121},400)]:product_list(h,guest,p,code)
    with h.case('TST-04'):
        for sku,code in [('CSU-CLB-FOLDER-02',404),('CSU-SPT-STAND-01',200),('CSU-CLB-STAND-01',200)]:guest.get('/products/'+str(h.pid(sku)),expected=code)
        guest.get('/products/999999',expected=404);h.add(user,h.pid('CSU-SPT-STAND-01'),1,409)
        no_gallery=int(h.rows("SELECT p.id FROM product p WHERE p.status='ON_SALE' AND NOT EXISTS(SELECT 1 FROM product_image pi WHERE pi.product_id=p.id) ORDER BY p.id LIMIT 1"));r=guest.get('/products/'+str(no_gallery),expected=200);h.check('empty gallery falls back cover markup',r.dom.find(lambda n:'data-gallery-empty' in n.a) is not None)
        paths=[]
        for end in ['u','a']:
            r=guest.get('/images/catalog-placeholder.svg',end,expected=200);paths.append(r.body);h.check('placeholder media type','image/svg+xml' in r.headers.get('Content-Type',''))
        h.check('shared static identical source bytes',paths[0]==paths[1]==(h.repo/'assets/images/catalog-placeholder.svg').read_bytes())
    with h.case('TST-33'):
        root=guest.get('/',expected=200);link=root.dom.find(lambda n:'data-graduation-link' in n.a);qs=urllib.parse.parse_qs(urllib.parse.urlsplit(link.a['href']).query);h.check('graduation by code theme',qs.get('categoryId')==[str(graduation['id'])] and qs.get('type')==['ALL'])
        for kind in ['ALL','STATIONERY','SOUVENIR']:product_list(h,guest,{'categoryId':graduation['id'],'type':kind,'q':'','page':2,'size':2})
        cat=data['category'][str(data['product'][str(gift)]['categoryId'])];h.check('gift own SKU under graduation souvenir',cat['parentId']==graduation['id'] and cat['code'].endswith('_SOUVENIR'))
    with h.case('TST-05'):
        for end,ok in [('u','alice'),('a','admin')]:
            messages=[]
            for name,passw in [(ok,'wrong-step13-password'),('missing-step13',None),('disabled',None),('admin' if end=='u' else 'alice',None)]:
                c=h.Client('failed-'+end+'-'+name);_,r=h.login(c,end,name,passw,expected=200);error=r.dom.find(lambda n:'data-auth-error' in n.a);h.check('generic failed auth message',error is not None);messages.append(error.text().strip());c.get('/cart' if end=='u' else '/',end,expected=302)
            h.check('all failure causes use exactly one visible message '+end,len(set(messages))==1)
        _,r=h.login(h.Client('good-customer'),'u','alice');h.check('enabled CUSTOMER login',r.status==303);_,r=h.login(h.Client('good-admin'),'a','admin');h.check('enabled ADMIN login',r.status==303)
    with h.case('TST-06'):
        both=h.Client('both');h.login(both,'u','alice');h.login(both,'a','admin');h.check('two named cookies',bool(both.cookie('u')) and bool(both.cookie('a')) and both.cookie('u')!=both.cookie('a'))
        h.post(both,'/logout',end='u');both.get('/',end='a',expected=200);both.get('/cart',expected=302);h.login(both,'u','alice');h.post(both,'/logout',end='a');both.get('/cart',expected=200);both.get('/',end='a',expected=302)
    with h.case('TST-07'):
        b=h.client('bob',h.ports['u']);h.fixture("UPDATE store_user SET status='DISABLED',updated_at=GREATEST(CURRENT_TIMESTAMP(6),updated_at+INTERVAL 1 MICROSECOND) WHERE id=2",'disable bob root identity fixture');b.post('/cart/items',{'productId':'bad','quantity':'bad'},expected=302,zero=True)
        h.fixture("UPDATE store_user SET status='ENABLED',updated_at=GREATEST(CURRENT_TIMESTAMP(6),updated_at+INTERVAL 1 MICROSECOND) WHERE id=2",'reenable bob root identity fixture');b.get('/cart',expected=302)
    h.clear_cart(user)
    with h.case('TST-08'):
        for field,value in [('productId','x'),('productId','0'),('quantity','0'),('quantity','100'),('quantity','-1'),('quantity','1.1'),('quantity','x')]:
            d={'productId':note,'quantity':1};d[field]=value;h.post(user,'/cart/items',d,expected=400,zero=True)
        h.post(user,'/cart/items',{'productId':note},expected=400,zero=True);h.add(user,999999,1,404);h.add(user,h.pid('CSU-CLB-FOLDER-02'),1,404);h.add(user,note,11,409)
        wrong_role=h.client('bob',h.ports['u']);role_csrf=h.token(wrong_role.get('/cart',expected=200));h.fixture("UPDATE store_user SET role='ADMIN',updated_at=updated_at WHERE id=2",'root active-session wrong-role fixture')
        wrong_role.post('/cart/items',{'productId':note,'quantity':1,'_csrf':role_csrf},expected=403,zero=True);h.fixture("UPDATE store_user SET role='CUSTOMER',updated_at=updated_at WHERE id=2",'restore root wrong-role fixture')
        h.add(user,note,1);h.add(user,note,1);row=h.cartrows()[0];h.check('same SKU merge one row2version1',len(h.cartrows())==1 and row['quantity']==2 and row['version']==1);h.clear_cart(user)
        p=h.product(alt);h.fixture('UPDATE product SET stock=150,updated_at=updated_at WHERE id='+str(alt),'cart99 stock fixture');h.add(user,alt,99);h.add(user,alt,1,409);h.clear_cart(user);h.fixture('UPDATE product SET stock='+str(p['stock'])+',updated_at=updated_at WHERE id='+str(alt),'restore cart99 stock')
        choices=[x['id'] for x in h.state()['product'].values() if x['status']=='ON_SALE' and x['stock']>=3][:21]
        for pid in choices[:20]:h.add(user,pid)
        h.add(user,choices[0]);h.add(user,choices[20],1,409);h.check('20 kinds existing SKU still merges',len(h.cartrows())==20);h.clear_cart(user)
    with h.case('TST-10'):
        h.add(user,note);old=h.cartrows()[0];b=h.client('bob',h.ports['u'])
        for suffix,d in [('quantity',{'quantity':2,'version':old['version']}),('remove',{'version':old['version']})]:h.post(b,'/cart/items/'+str(old['id'])+'/'+suffix,d,expected=403,zero=True)
        h.post(user,'/cart/items/999999/remove',{'version':0},expected=404,zero=True);h.post(user,'/cart/items/'+str(old['id'])+'/quantity',{'quantity':1,'version':old['version']},zero=True)
        h.post(user,'/cart/items/'+str(old['id'])+'/quantity',{'quantity':2,'version':old['version']});h.post(user,'/cart/items/'+str(old['id'])+'/quantity',{'quantity':3,'version':old['version']},expected=409,zero=True);h.clear_cart(user)
    with h.case('TST-11'):
        p=h.product(alt)
        for assignments in ["status='DRAFT'",'stock=0','stock=1']:
            h.add(user,alt,2);h.fixture('UPDATE product SET '+assignments+',updated_at=updated_at WHERE id='+str(alt),'invalid cart root fixture');r=user.get('/cart',expected=200);badge(h,r,1);h.check('invalid line retained',r.dom.find(lambda n:n.a.get('data-cart-invalid-count')=='1') is not None);user.get('/checkout',expected=409);row=h.cartrows()[0];h.post(user,'/cart/items/'+str(row['id'])+'/quantity',{'quantity':2,'version':row['version']},zero=True);h.post(user,'/cart/items/'+str(row['id'])+'/quantity',{'quantity':3,'version':row['version']},expected=409,zero=True);h.clear_cart(user);h.fixture('UPDATE product SET stock='+str(p['stock'])+',status='+h.literal(p['status'])+',updated_at=updated_at WHERE id='+str(alt),'restore invalid cart fixture')
        user.get('/checkout',expected=409)
    h.add(user,note,2);h.add(user,gift)
    with h.case('TST-12'):
        r=h.checkout(user)
        for field,size in [('receiverName',50),('receiverPhone',30),('receiverAddress',255)]:
            for value in ['','  ','x'*(size+1),'😀'*(size+1)]:
                d=h.shipping();d[field]=value;h.submit(user,r,d,expected=400)
    with h.case('TST-31'):
        for csrf in [False,'wrong-csrf']:h.post(user,'/cart/items',{'productId':note,'quantity':1},csrf=csrf,expected=403,zero=True)
        r=h.checkout(user);d=h.shipping();d.update(receiverName='<script>step13_literal</script>',receiverPhone='');out,_=h.submit(user,r,d,expected=400);n=out.dom.find(lambda n:n.tag=='input' and n.a.get('name')=='receiverName');h.check('script is literal field text',n is not None and n.a.get('value')==d['receiverName'] and not out.dom.find(lambda n:n.tag=='script' and 'step13_literal' in n.text()))
        for csrf in [False,'wrong-csrf']:h.post(user,'/orders',{'confirmationToken':h.token(r,'confirmationToken'),**h.shipping()},csrf=csrf,expected=403,zero=True)
    with h.case('TST-13'):
        r=h.checkout(user);latest=h.checkout(user);h.submit(user,r,expected=409)
        b=h.client('alice',h.ports['u']);r=h.checkout(user);row=h.cartrows()[0];h.post(b,'/cart/items/'+str(row['id'])+'/quantity',{'quantity':row['quantity']+1,'version':row['version']});h.submit(user,r,expected=409);row=h.cartrows()[0];h.post(b,'/cart/items/'+str(row['id'])+'/quantity',{'quantity':2,'version':row['version']})
        r=h.checkout(user);h.add(b,alt);h.submit(user,r,expected=409);added=next(x for x in h.cartrows() if x['productId']==alt);h.check('new unconfirmed row retained',added['quantity']==1);h.post(b,'/cart/items/'+str(added['id'])+'/remove',{'version':added['version']})
        r=h.checkout(user);p=h.product(note);h.fixture('UPDATE product SET price=price+0.01,updated_at=updated_at WHERE id='+str(note),'old confirmation current price change');h.submit(user,r,expected=409);h.fixture('UPDATE product SET price='+p['price']+',updated_at=updated_at WHERE id='+str(note),'restore confirmed price')
        h.stop_apps();h.app_overrides={'CSUCAMPUSCRAFT_CHECKOUT_CONFIRMATION_TTL':'PT1S'};h.start_apps();user=h.client('alice',h.ports['u']);admin=h.client('admin',h.ports['a']);r=h.checkout(user);time.sleep(1.4);h.submit(user,r,expected=409);h.stop_apps();h.app_overrides={};h.start_apps();user=h.client('alice',h.ports['u']);admin=h.client('admin',h.ports['a'])
    with h.case('TST-15'):
        p=h.product(note)
        for assignment in ['stock=1',"status='DRAFT'"]:
            r=h.checkout(user);h.fixture('UPDATE product SET '+assignment+',updated_at=updated_at WHERE id='+str(note),'order conflict root fixture');h.submit(user,r,expected=409);h.check('failed order preserves whole cart',len(h.cartrows())==2);h.fixture('UPDATE product SET stock='+str(p['stock'])+',status='+h.literal(p['status'])+',updated_at=updated_at WHERE id='+str(note),'restore order conflict fixture')
    with h.case('TST-14'):
        h.clear_cart(user);h.add(user,note,2);h.add(user,gift);r=h.checkout(user);before=h.snapshot();a=h.state();h.check('actual initial stock10/12',a['product'][str(note)]['stock']==10 and a['product'][str(gift)]['stock']==12)
        boundary=dict(receiverName='边界'+secrets.token_hex(12)+'学'*24,receiverPhone='0'+secrets.token_hex(14)+'0',receiverAddress='仅验收'+secrets.token_hex(16)+'校'*220)
        for value in boundary.values():h.secret(value)
        h.check('legal receiver maximum codepoint boundaries',[len(boundary[k]) for k in ['receiverName','receiverPhone','receiverAddress']]==[50,30,255])
        response,main=h.submit(user,r,boundary,totalAmount='0.01',user_id='2');after=h.snapshot();b=h.state();h.db_pair('main-real85',before,a,after,b,order_no=main['orderNo'])
        h.check('1main2items85pending',len(h.deltas(a,b)['sales_order'])==1 and len(h.deltas(a,b)['sales_order_item'])==2 and main['status']=='PENDING_PAYMENT' and main['userId']==1 and Decimal(main['totalAmount'])==85)
        for pid,qty in [(note,2),(gift,1)]:h.check('stock/version exact '+str(pid),b['product'][str(pid)]['stock']==a['product'][str(pid)]['stock']-qty and b['product'][str(pid)]['version']==a['product'][str(pid)]['version']+1)
        h.check('confirmed cart empty',not h.cartrows());badge(h,h.follow(user,response),1);h.submit(user,r,expected=409)
    no=main['orderNo']
    with h.case('TST-18'):
        b=h.client('bob',h.ports['u']);order_detail(h,b,no,expected=404)
        for action in ['payment','cancel']:h.post(b,'/orders/'+no+'/'+action,{'result':'SUCCESS','user_id':'1'},expected=404,zero=True)
    with h.case('TST-19'):
        saved=h.product(note);snap=h.snapshot();h.fixture('UPDATE product SET name='+h.literal('STEP13 changed current name')+",price=19.25,cover_image='images/step13-missing-cover.svg',status='DRAFT',updated_at=updated_at WHERE id="+str(note),'after-sale actual current product change');h.check('order tables keep all fields',all(h.snapshot()[t]==snap[t] for t in ['sales_order','sales_order_item']));order_detail(h,user,no);order_detail(h,admin,no,'a')
        with h.case('TST-20'):
            payment(h,user,no,'FAILURE',zero=True);h.check('failure preserves pending/null payment',h.order(no)['status']=='PENDING_PAYMENT' and all(h.order(no)[k] is None for k in ['paymentMethod','paymentNo','paidAt']));old_products=h.snapshot()['product'];payment(h,user,no);paid=h.order(no);payment(h,user,no,zero=True);h.check('first receipt/time retained',h.order(no)==paid and paid['paymentMethod']=='MOCK' and paid['paymentNo'] and paid['paidAt']);h.check('payment no stock mutation',h.snapshot()['product']==old_products);payment(h,user,no,'FAILURE',409,True)
        h.fixture('UPDATE product SET name='+h.literal(saved['name'])+',price='+saved['price']+',cover_image='+h.literal(saved['coverImage'])+',status='+h.literal(saved['status'])+',updated_at=updated_at WHERE id='+str(note),'restore current product fixture');order_detail(h,user,no);order_detail(h,admin,no,'a')
    with h.case('TST-29'):
        h.post(admin,'/orders/'+no+'/ship',end='a');shipped=h.order(no);h.check('only PAID becomes SHIPPED first time',shipped['status']=='SHIPPED' and shipped['shippedAt']>=shipped['paidAt']);h.post(admin,'/orders/'+no+'/ship',end='a',zero=True);h.check('first shipment retained',h.order(no)==shipped);order_detail(h,user,no);order_detail(h,admin,no,'a')
        for state in ['PENDING_PAYMENT','CANCELLED']:
            seed=next(x for x in h.state()['sales_order'].values() if x['status']==state);h.post(admin,'/orders/'+seed['orderNo']+'/ship',end='a',expected=409,zero=True)
    with h.case('TST-21'):
        cancelled=h.new_order85(user);cno=cancelled['orderNo'];h.add(user,alt);cart_before=h.snapshot()['cart_item'];before=h.state();h.fixture("UPDATE product SET status='DRAFT',updated_at=updated_at WHERE id="+str(note),'DRAFT before refund')
        with h.case('TST-22'):
            cancel(h,user,cno);after=h.state();h.check('DRAFT refunded but remains DRAFT',after['product'][str(note)]['status']=='DRAFT');h.check('cancelled order',h.order(cno)['status']=='CANCELLED');payment(h,user,cno,expected=409,zero=True);h.post(admin,'/orders/'+cno+'/ship',end='a',expected=409,zero=True)
        for pid,qty in [(note,2),(gift,1)]:h.check('exact refund stock+version '+str(pid),after['product'][str(pid)]['stock']==before['product'][str(pid)]['stock']+qty and after['product'][str(pid)]['version']==before['product'][str(pid)]['version']+1)
        h.check('current new cart not restored/cleared',h.snapshot()['cart_item']==cart_before);first=h.order(cno);cancel(h,user,cno,zero=True);h.check('duplicate cancel preserves first entire order',h.order(cno)==first);h.fixture("UPDATE product SET status='ON_SALE',updated_at=updated_at WHERE id="+str(note),'restore DRAFT refund fixture')
    with h.case('TST-34'):
        h.clear_cart(user);h.add(user,gift,2);r=h.checkout(user);products=h.state()['product'];response,box=h.submit(user,r);lines=[x for x in h.state()['sales_order_item'].values() if x['orderId']==box['id']];h.check('2gift independent98',Decimal(box['totalAmount'])==98 and len(lines)==1 and lines[0]['quantity']==2);h.check('components untouched',{k:v for k,v in h.state()['product'].items() if int(k)!=gift}=={k:v for k,v in products.items() if int(k)!=gift});cancel(h,user,box['orderNo']);h.check('gift stock returned only',h.product(gift)['stock']==products[str(gift)]['stock'])
    with h.case('TST-30'):
        for end,c in [('u',user),('a',admin)]:
            for p in [{},{'orderNo':no.lower()},{'orderNo':no[:10]},{'status':'SHIPPED','size':1,'page':2},{'page':999,'size':2}]:order_list(h,c,p,end)
            for p in [{'orderNo':'x'*41},{'status':'x'},{'size':51},{'page':'x'}]:order_list(h,c,p,end,expected=400)
        for p in [{'userId':1,'orderNo':no.lower()},{'userId':2,'orderNo':no},{'userId':3}]:order_list(h,admin,p,'a')
        for uid in [4,999999]:order_list(h,admin,{'userId':uid},'a',expected=404)
    with h.case('TST-09'):
        h.clear_cart(user);h.add(user,note,2);h.add(user,gift);bob=h.client('bob',h.ports['u']);h.clear_cart(bob,2);h.add(bob,alt,2)
        for path,status in [('/',200),('/products',200),('/products/'+str(gift),200),('/cart',200),('/orders',200),('/products/999999',404)]:badge(h,user.get(path,expected=status),1)
        badge(h,guest.get('/',expected=200),None);badge(h,bob.get('/cart',expected=200),2);h.check('accounts own different rows',all(x['userId']==1 for x in h.cartrows(1)) and all(x['userId']==2 for x in h.cartrows(2)))
    return dict(user=user,admin=admin,main_order_no=no,graduationCategoryId=graduation['id'],giftProductId=gift,missingProductId=h.pid('CSU-CLB-STAND-01'),noGalleryProductId=no_gallery,customerId=1)
