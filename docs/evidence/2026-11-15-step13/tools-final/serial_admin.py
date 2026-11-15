"""New final-SHA STEP13 administrative regression, real HTTP and seven-table audits."""
from decimal import Decimal
import json,urllib.parse

def edit_form(p,**changes):
    d={k:p.get(k) or '' for k in ['categoryId','name','summary','description','coverImage','price','sortOrder','version']}
    d.update(changes);return d

def image_rows(h,pid):
    return sorted([r for r in h.state()['product_image'].values() if r['productId']==pid],key=lambda r:(r['sortOrder'],r['id']))

def counts(h):
    s=h.state()
    return [sum(p['status']==v for p in s['product'].values()) for v in ['ON_SALE','DRAFT']]+[sum(o['status']=='PAID' for o in s['sales_order'].values())]+[sum(u['role']=='CUSTOMER' and u['status']==v for u in s['store_user'].values()) for v in ['ENABLED','DISABLED']]

def dashboard(h,admin,label):
    page=admin.get('/',end='a',expected=200)
    n=page.dom.find(lambda n:n.a.get('data-page-id')=='A02')
    keys=['data-on-sale-count','data-draft-count','data-paid-order-count','data-enabled-customer-count','data-disabled-customer-count']
    observed=[int(n.a[k]) for k in keys] if n else []
    h.check('dashboard five independent SQL counts '+label,observed==counts(h),{'observed':observed,'sql':counts(h),'http':page.sequence})
    for href in ['/products?status=ON_SALE','/products?status=DRAFT','/orders?status=PAID','/customers?status=ENABLED','/customers?status=DISABLED']:
        h.check('dashboard filter card '+href,page.dom.find(lambda n:n.tag=='a' and n.a.get('href')==href) is not None)
    return page

def run(h,user,admin):
    # Independent clients avoid relying on identities invalidated by earlier modules.
    user,_=h.login(username='alice');admin,_=h.login(end='a',username='admin')
    def post(path,d=None,status=303):return h.post(admin,path,d or {},end='a',expected=status,zero=status!=303)
    def create_cat(d):
        r=post('/categories',d)
        cid=int(urllib.parse.parse_qs(urllib.parse.urlsplit(r.headers['Location']).query)['createdId'][0])
        row=h.state()['category'][str(cid)]
        h.check('category generated ID return and PK readback',row['id']==cid and row['name']==d['name'],{'id':cid,'http':r.sequence})
        return cid
    def create_product(d):
        post('/products',d)
        return h.pid(d['sku'])
    with h.case('TST-25'):
        shortest=create_cat(dict(code='Z',name='一级编码下界',sortOrder=''))
        h.check('one-character code and empty sort accepted',h.state()['category'][str(shortest)]['code']=='Z' and h.state()['category'][str(shortest)]['sortOrder']==0)
        root=create_cat(dict(code='S13'+'X'*18,name='STEP13最终验收主题',sortOrder='100'))
        child=create_cat(dict(parentId=root,type='STATIONERY',name='STEP13测试文具',sortOrder='0'))
        h.check('21-code child32 exactly',len(h.state()['category'][str(child)]['code'])==32)
        create_cat(dict(parentId=root,type='SOUVENIR',name='STEP13测试周边'))
        for d,status in [
            (dict(code='Y'*22,name='不可写超长'),400),(dict(code='',name='不可写空编码'),400),
            (dict(code=('S13'+'X'*18).lower(),name='重复编码'),409),
            (dict(code='OTHER13',name='STEP13最终验收主题'),409),
            (dict(parentId=root,type='STATIONERY',name='重复类型'),409),
            (dict(parentId=root,type='ILLEGAL',name='非法类型'),400),
            (dict(parentId=999999,type='STATIONERY',name='未知父'),404),
            (dict(parentId=child,type='STATIONERY',name='禁止三级'),409),
            (dict(code='S13NEG',name='负排序',sortOrder='-1'),400),
            (dict(code='S13LONG',name='界'*51),400)]:post('/categories',d,status)
        base=dict(sku='STEP13-ADMIN-PRIMARY',categoryId=child,name='STEP13验收商品',price='20.00',stock='10',sortOrder='100',coverImage='',summary='',description='纯文本设计说明')
        pid=create_product(base);p=h.product(pid)
        h.check('new product draft version0 default cover',p['status']=='DRAFT' and p['version']==0 and p['coverImage']=='images/catalog-placeholder.svg')
        user.get('/products/'+str(pid),expected=404)
        for key,value,status in [('sku',base['sku'].lower(),409),('categoryId',root,400),('categoryId',999999,404),('sku','S'*41,400),('name','界'*121,400),('price','0',400),('price','0.001',400),('price','10000000000.00',400),('summary','界'*501,400),('description','界'*21846,400),('stock','-1',400),('sortOrder','-1',400),('coverImage','https://invalid.test/image.svg',400),('coverImage','images/../secret',400)]:
            d=dict(base,sku='STEP13-REJECT-'+key);d[key]=value;post('/products',d,status)
        # The minimum and maximum legal monetary bounds are accepted without purchasing them.
        for suffix,price in [('MIN','0.01'),('MAX','9999999999.99')]:
            boundary=create_product(dict(base,sku='STEP13-BOUND-'+suffix,name='界'*120,summary='界'*500,price=price,stock='',sortOrder=''))
            b=h.product(boundary);h.check('legal product amount '+suffix,Decimal(b['price'])==Decimal(price) and b['stock']==0 and b['sortOrder']==0)
        post('/products/'+str(pid)+'/publish',{'version':p['version']});user.get('/products/'+str(pid),expected=200)
        post('/products/'+str(pid)+'/publish',{'version':h.product(pid)['version']},409)
        post('/products/'+str(pid)+'/unpublish',{'version':h.product(pid)['version']});user.get('/products/'+str(pid),expected=404)
        h.check('new theme public without client changes',user.get('/',expected=200).dom.find(lambda n:n.a.get('data-theme-code')=='S13'+'X'*18) is not None)
        current=h.state()['category'][str(root)];post('/categories/'+str(root),dict(name=current['name']+'已编辑',sortOrder=101,code='IGNORED',parentId=child))
        edited=h.state()['category'][str(root)];h.check('category code parent immutable',edited['code']==current['code'] and edited['parentId']==current['parentId'])
    with h.case('TST-26'):
        post('/categories/'+str(root)+'/remove',{},409);post('/categories/'+str(child)+'/remove',{},409)
        empty=create_cat(dict(code='S13EMPTY',name='STEP13可删空类'))
        post('/categories/'+str(empty)+'/remove');h.check('empty category deleted',str(empty) not in h.state()['category'])
    with h.case('TST-28'):
        old=h.product(pid);post('/products/'+str(pid)+'/restock',dict(quantity='3',stock='0',version='0'));new=h.product(pid)
        h.check('restock adds actual current and increments once',new['stock']==old['stock']+3 and new['version']==old['version']+1)
        for q in ['',0,-1,'1.5','n/a','2147483648']:post('/products/'+str(pid)+'/restock',dict(quantity=q),400)
        for field,value in [('stock',2147483647),('version',9223372036854775807)]:
            saved=h.product(pid);h.fixture('UPDATE product SET '+field+'='+str(value)+' WHERE id='+str(pid),'restock overflow '+field)
            post('/products/'+str(pid)+'/restock',dict(quantity=1),409)
            # Fixture restoration is labelled SQL, not a product operation or an order reversal.
            h.fixture('UPDATE product SET stock='+str(saved['stock'])+',version='+str(saved['version'])+' WHERE id='+str(pid),'restore isolated restock overflow fixture')
    with h.case('TST-27'):
        post('/products/'+str(pid)+'/publish',dict(version=h.product(pid)['version']))
        h.clear_cart(user);h.add(user,pid,2);old=h.product(pid);oldform=edit_form(old,name='不能覆盖购买后的库存',sku='FORGED',stock='0')
        _,order=h.submit(user,h.checkout(user))
        post('/products/'+str(pid),oldform,409)
        bought=h.product(pid);h.check('old editor cannot undo purchase',bought['stock']==old['stock']-2 and bought['version']==old['version']+1)
        cancel_form=edit_form(bought,name='不能覆盖取消后的库存')
        h.post(user,'/orders/'+order['orderNo']+'/cancel')
        post('/products/'+str(pid),cancel_form,409)
        restored=h.product(pid);h.check('old editor cannot undo refund',restored['stock']==old['stock'] and restored['version']==bought['version']+1)
        same=edit_form(restored,sku='FORGED',stock='0');before=h.snapshot();post('/products/'+str(pid),same)
        h.check('same details with forged SKU stock is no-op',h.snapshot()==before)
        post('/products/'+str(pid),edit_form(restored,name=restored['name']+'已编辑',sku='FORGED',stock='0'))
        changed=h.product(pid);h.check('details preserve immutable SKU stock',changed['sku']==restored['sku'] and changed['stock']==restored['stock'] and changed['version']==restored['version']+1)
    with h.case('TST-38'):
        # Known fake usernames used only for isolated LIKE/empty-order fixtures.
        h.fixture("INSERT INTO store_user(username,password_hash,display_name,role,status) SELECT 's13%_!literal',password_hash,'STEP13字面筛选顾客','CUSTOMER','ENABLED' FROM store_user WHERE role='ADMIN' LIMIT 1",'isolated no-order customer for literal matching')
        targets=[r for r in h.state()['store_user'].values() if r['username']=='s13%_!literal'];uid=targets[0]['id']
        for query in [{},{'q':'%','status':'ALL'},{'q':'_','status':'ENABLED'},{'q':'!','size':1},{'status':'DISABLED'},{'size':1,'page':2},{'q':'not-found-step13'},{'page':99999}]:
            page=admin.get('/customers?'+urllib.parse.urlencode(query),end='a',expected=200)
            allrows=[x for x in h.state()['store_user'].values() if x['role']=='CUSTOMER' and str(query.get('q','')).lower() in x['username'].lower() and (query.get('status','ALL')=='ALL' or x['status']==query['status'])]
            allrows.sort(key=lambda x:x['id']);size=int(query.get('size',10));number=max(1,int(query.get('page',1)));expected=allrows[(number-1)*size:number*size]
            n=page.dom.find(lambda n:n.a.get('data-page-id')=='A08');rows=page.dom.all(lambda n:n.tag=='tr' and 'data-customer-id' in n.a)
            h.check('CUSTOMER list count and ordered SQL filter',n is not None and int(n.a['data-customer-count'])==len(allrows) and [int(n.a['data-customer-id']) for n in rows]==[x['id'] for x in expected],{'query':query,'http':page.sequence})
        for query in ['status=BAD','page=x','size=0','size=51','q='+('x'*51),'q=a&q=b','status=ALL&status=ENABLED']:
            admin.get('/customers?'+query,end='a',expected=400)
        admin.get('/customers/'+str(uid),end='a',expected=200)
        orderpage=admin.get('/orders?userId='+str(uid),end='a',expected=200);h.check('valid no-order customer normal empty',not any(x for x in h.state()['sales_order'].values() if x['userId']==uid) and orderpage.dom.find(lambda n:n.a.get('data-order-count')=='0') is not None)
        for bad,status in [('999999',404),('4',404),('0',400),('x',400)]:admin.get('/customers/'+bad,end='a',expected=status)
        detail=admin.get('/customers/1',end='a',expected=200);h.check('customer associated order URL',detail.dom.find(lambda n:n.tag=='a' and n.a.get('href')=='/orders?userId=1') is not None)
        admin.get('/orders?userId=1&status=ALL&size=1&page=2',end='a',expected=200)
    with h.case('TST-39'):
        olda,_=h.login(username='alice');oldb,_=h.login(username='alice');h.clear_cart(olda);h.add(olda,pid,1);confirmation=h.checkout(olda)
        before=h.state()['store_user']['1'];post('/customers/1/status',dict(targetStatus='DISABLED'));disabled=h.state()['store_user']['1']
        h.check('disable only status monotonically advances microtimestamp',disabled['status']=='DISABLED' and disabled['updatedAt']>before['updatedAt'])
        snap=h.snapshot();post('/customers/1/status',dict(targetStatus='DISABLED'));h.check('repeated disable zero DML',h.snapshot()==snap)
        olda.get('/cart',expected=302)
        post('/customers/1/status',dict(targetStatus='ENABLED'));enabled=h.state()['store_user']['1'];h.check('enable advances timestamp',enabled['updatedAt']>disabled['updatedAt'])
        snap=h.snapshot();post('/customers/1/status',dict(targetStatus='ENABLED'));h.check('repeated enable zero DML',h.snapshot()==snap)
        olda.get('/orders',expected=302);oldb.get('/cart',expected=302)
        # Both independent sessions remain unused during immediate disable/re-enable.
        a,_=h.login(username='alice');b,_=h.login(username='alice')
        post('/customers/1/status',dict(targetStatus='DISABLED'));post('/customers/1/status',dict(targetStatus='ENABLED'))
        for c in [a,b]:c.get('/cart',expected=302)
        user,_=h.login(username='alice');user.get('/cart',expected=200);user.get('/orders',expected=200)
        # New CSRF with old confirmation proves confirmation invalidity rather than CSRF failure.
        fields=h.shipping();fields.update(confirmationToken=h.token(confirmation,'confirmationToken'),_csrf=h.token(user.get('/cart',expected=200)))
        user.post('/orders',fields,expected=409,zero=True)
        for target,d,status in [('4',dict(targetStatus='DISABLED'),404),('999999',dict(targetStatus='DISABLED'),404),('1',dict(targetStatus='BAD'),400),('1',dict(targetStatus=['ENABLED','DISABLED']),400)]:post('/customers/'+target+'/status',d,status)
    with h.case('TST-40'):
        album='/products/'+str(pid)+'/images';cover=h.product(pid)['coverImage'];old=h.product(pid)
        post(album,dict(imagePath='images/catalog-placeholder.svg',altText='<script>step13-album</script>',sortOrder=2,productVersion=old['version']))
        image=image_rows(h,pid)[-1];h.check('album create parent increments once',h.product(pid)['version']==old['version']+1 and image['id']>0)
        escaped=user.get('/products/'+str(pid),expected=200)
        h.check('album alternate text safe in attribute','&lt;script&gt;step13-album&lt;/script&gt;' in escaped.text and not any(n.tag=='script' and 'step13-album' in n.text() for n in escaped.dom.nodes()))
        v=h.product(pid)['version'];same=dict(imagePath=image['imagePath'],altText=image['altText'],sortOrder=image['sortOrder'],productVersion=v)
        before=h.snapshot();post(album+'/'+str(image['id']),same);h.check('album same-value valid-version no DML',h.snapshot()==before)
        post(album+'/'+str(image['id']),dict(same,sortOrder=0,altText='STEP13首图'));h.check('album edit increments parent once',h.product(pid)['version']==v+1)
        for version,status in [('',409),('n/a',400),('-1',400),('9223372036854775808',400),([1,2],400),(str(v),409)]:
            post(album,dict(imagePath='images/catalog-placeholder.svg',productVersion=version),status)
        post(album,dict(imagePath='images/catalog-placeholder.svg'),409)
        for field,value in [('imagePath',''),('imagePath','x'*256),('imagePath','/images/x'),('imagePath','https://invalid.test/x'),('imagePath','images/../x'),('imagePath','images/a%20b'),('imagePath','images/a?b'),('imagePath','images/a#b'),('imagePath','images/a\\b'),('altText','界'*121),('sortOrder','-1'),('sortOrder','1.1'),('sortOrder','2147483648')]:
            d=dict(imagePath='images/catalog-placeholder.svg',altText='',sortOrder=0,productVersion=h.product(pid)['version']);d[field]=value;post(album,d,400)
        foreign=next(x for x in h.state()['product_image'].values() if x['productId']!=pid)
        post(album+'/'+str(foreign['id']),dict(imagePath='images/catalog-placeholder.svg',productVersion=h.product(pid)['version']),404)
        post(album+'/'+str(foreign['id'])+'/remove',dict(productVersion=h.product(pid)['version']),404)
        oldform=edit_form(h.product(pid),name='旧相册资料')
        legal='images/'+'x'*248
        post(album,dict(imagePath=legal,altText='界'*120,sortOrder='',productVersion=h.product(pid)['version']))
        h.check('legal image255 alt120 default sort',any(x['imagePath']==legal and len(x['altText'])==120 and x['sortOrder']==0 for x in image_rows(h,pid)))
        post('/products/'+str(pid),oldform,409)
        a=admin.get(album,end='a',expected=200);u=user.get('/products/'+str(pid),expected=200)
        ids=[str(x['id']) for x in image_rows(h,pid)]
        observed=list(dict.fromkeys(n.a['data-image-id'] for n in a.dom.nodes() if 'data-image-id' in n.a))
        public=[n.a['data-image-id'] for n in u.dom.nodes() if n.tag=='figure' and 'data-image-id' in n.a]
        h.check('album SQL sort-order ID sequence in both pages',observed==ids and public==ids,{'sql':ids,'admin':observed,'user':public})
        h.check('album text escaped no script element',not any(n.tag=='script' and 'step13-album' in n.text() for n in u.dom.nodes()))
        for image in image_rows(h,pid):post(album+'/'+str(image['id'])+'/remove',dict(productVersion=h.product(pid)['version']))
        u=user.get('/products/'+str(pid),expected=200);h.check('last image removal preserves independent cover',not image_rows(h,pid) and h.product(pid)['coverImage']==cover and cover in u.text)
        post(album,dict(imagePath='images/catalog-placeholder.svg',altText='STEP13交付相册',sortOrder=0,productVersion=h.product(pid)['version']))
        h.save('serial-admin-fixtures.json',json.dumps(dict(product_id=pid,category_root=root,category_child=child,no_order_customer=uid),ensure_ascii=False,indent=2))
    with h.case('TST-31','admin-security'):
        for path,data in [('/customers/'+str(uid)+'/status',dict(targetStatus='DISABLED')),('/products/'+str(pid)+'/images',dict(imagePath='images/catalog-placeholder.svg',productVersion=h.product(pid)['version']))]:
            h.post(admin,path,data,end='a',expected=403,csrf=False,zero=True)
            h.post(admin,path,data,end='a',expected=403,csrf='invalid-step13-csrf',zero=True)
        post('/customers/'+str(uid)+'/status',dict(targetStatus='DISABLED'))
        post('/customers/'+str(uid)+'/status',dict(targetStatus='ENABLED'))
        post('/products/'+str(pid)+'/images',dict(imagePath='images/catalog-placeholder.svg',altText='合法CSRF新增',productVersion=h.product(pid)['version']))
        post('/products/'+str(pid),edit_form(h.product(pid),description='<script>step13-product</script>'))
        p=user.get('/products/'+str(pid),expected=200)
        h.check('product description rendered as escaped ordinary text','&lt;script&gt;step13-product&lt;/script&gt;' in p.text and not any(n.tag=='script' and 'step13-product' in n.text() for n in p.dom.nodes()))
    with h.case('TST-37'):
        dashboard(h,admin,'initial')
        p=h.product(pid);post('/products/'+str(pid)+'/unpublish',dict(version=p['version']));dashboard(h,admin,'unpublished')
        post('/products/'+str(pid)+'/publish',dict(version=h.product(pid)['version']));dashboard(h,admin,'published')
        h.fixture('UPDATE product SET stock=0 WHERE id='+str(pid),'zero-stock still on-sale dashboard fixture');dashboard(h,admin,'on-sale soldout counted')
        post('/customers/'+str(uid)+'/status',dict(targetStatus='DISABLED'));dashboard(h,admin,'customer disabled')
        post('/customers/'+str(uid)+'/status',dict(targetStatus='ENABLED'));dashboard(h,admin,'customer enabled')
        # Payment/shipping counts are checked against every changed committed state.
        post('/products/'+str(pid)+'/restock',dict(quantity=10));h.clear_cart(user);h.add(user,pid,1)
        _,pending=h.submit(user,h.checkout(user));dashboard(h,admin,'new pending excluded')
        h.post(user,'/orders/'+pending['orderNo']+'/payment',dict(result='SUCCESS'));dashboard(h,admin,'payment changes PAID')
        post('/orders/'+pending['orderNo']+'/ship');dashboard(h,admin,'shipment leaves PAID')
        # Fresh pooled connections enforce the deliberately restricted SELECT grants.
        # This is an isolated environment permission fixture, not product fault code.
        h.stop_apps()
        h.sql("REVOKE SELECT ON "+h.schema+".* FROM '"+h.appuser+"'@'127.0.0.1';GRANT SELECT ON "+h.schema+".store_user TO '"+h.appuser+"'@'127.0.0.1';",False)
        try:
            h.start_apps();restricted,_=h.login(end='a',username='admin')
            error=restricted.get('/',end='a',expected=500)
            h.check('dashboard natural SELECT failure is error not fabricated zero',error.dom.find(lambda n:'data-dashboard-unavailable' in n.a) is not None and error.dom.find(lambda n:'data-dashboard-count' in n.a) is None and 'DASHBOARD_QUERY_FAILED' in error.text)
        finally:
            h.stop_apps();h.sql("GRANT SELECT ON "+h.schema+".* TO '"+h.appuser+"'@'127.0.0.1';REVOKE SELECT ON "+h.schema+".store_user FROM '"+h.appuser+"'@'127.0.0.1';",False);h.start_apps()
        user,_=h.login(username='alice');admin,_=h.login(end='a',username='admin');dashboard(h,admin,'recovered real query')
    return user,admin
