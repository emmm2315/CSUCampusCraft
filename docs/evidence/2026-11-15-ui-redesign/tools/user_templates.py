from pathlib import Path
import re, json
ROOT=Path('D:/Github Projects/CSUCampusCraft')
STAGE=Path(__file__).resolve().parent.parent
BASE=ROOT/'csucampuscraft-user/src/main/resources/templates'
OWNED={'fragments/layout.html','fragments/fields.html','fragments/alerts.html','fragments/images.html'}
labels={'home.html':'CAMPUS COLLECTION','login.html':'CUSTOMER SIGN IN','products/list.html':'PRODUCT CATALOGUE','products/detail.html':'PRODUCT DETAILS','cart/index.html':'SHOPPING CART','checkout/index.html':'CHECKOUT CONFIRMATION','checkout/conflict.html':'CHECKOUT NOTICE','orders/index.html':'MY ORDERS','orders/detail.html':'ORDER DETAILS','orders/payment.html':'SIMULATED PAYMENT','orders/action-conflict.html':'ORDER NOTICE','error/400.html':'INVALID REQUEST','error/403.html':'ACCESS RESTRICTED','error/404.html':'PAGE NOT FOUND','error/409.html':'DATA CONFLICT','error/500.html':'SERVICE UNAVAILABLE','verification/foundation.html':'FOUNDATION CHECK'}
def extra_class(text,old,new):
    return re.sub(r'class="([^"]*)"',lambda m:'class="'+m.group(1)+((' '+new) if old in m.group(1).split() and new not in m.group(1).split() else '')+'"',text)
modified=[]
for p in sorted(BASE.rglob('*.html')):
    rel=p.relative_to(BASE).as_posix()
    if rel in OWNED:continue
    raw=p.read_bytes();newline='\r\n' if b'\r\n' in raw else '\n';text=raw.decode('utf-8').replace('\r\n','\n')
    for old,new in [('page-heading','ef-page-head'),('section-heading','ef-section-head'),('empty-state','ef-empty'),('button-row','ef-actions'),('table-container','ef-table-wrap'),('error-page','ef-error'),('order-status','ef-state'),('stock-badge','ef-state'),('cart-summary','ef-summary'),('checkout-total-panel','ef-summary'),('catalog-type-tabs','ef-filter-tabs'),('catalog-breadcrumb','ef-metadata')]:
        text=extra_class(text,old,new)
    if rel in labels:
        match=re.search(r'(?m)^([ \t]*)<h1\b',text)
        assert match,rel
        insert=match.group(1)+'<p class="ef-eyebrow">'+labels[rel]+'</p>\n'
        text=text[:match.start()]+insert+text[match.start():]
    if rel=='home.html':
        text=extra_class(text,'catalog-home-heading','ef-hero')
        text=extra_class(text,'catalog-search','ef-hero-search')
        text=extra_class(text,'graduation-banner','ef-graduation')
        text=text.replace('<div>\n            <p class="eyebrow">中南大学校园文创</p>','<div class="ef-hero-copy">\n            <p class="eyebrow">中南大学校园文创</p>',1)
        needle='            <p class="ef-eyebrow">CAMPUS COLLECTION</p>\n'
        assert text.count(needle)==1
        text=text.replace(needle,needle+'            <p class="ef-wordmark" aria-hidden="true">CAMPUS<br><span>CRAFT.</span></p>\n',1)
        for name,kicker in [('themes-heading','CAMPUS THEMES'),('newest-heading','NEW ARRIVALS'),('featured-heading','FEATURED COLLECTION')]:
            # Keep the original h2 and every existing Chinese label unchanged.
            text=text.replace('<h2 id="'+name+'">','<p class="ef-eyebrow">'+kicker+'</p><h2 id="'+name+'">',1)
    if rel=='products/list.html':
        text=extra_class(text,'catalog-filter-panel','ef-filter-panel')
        text=extra_class(text,'catalog-grid','ef-records')
    if rel=='products/detail.html':
        text=extra_class(text,'catalog-detail-main','ef-feature')
        text=extra_class(text,'catalog-detail-info','ef-detail-copy')
        text=extra_class(text,'catalog-sku','ef-metadata')
    if rel=='fragments/catalog.html':
        text=extra_class(text,'product-card','ef-product-record')
        text=extra_class(text,'product-card-sku','ef-metadata')
        text=extra_class(text,'product-price','ef-number')
    if rel=='login.html':
        text=extra_class(text,'auth-panel','ef-auth')
        text=text.replace('<h1>用户登录</h1>','<h1 class="ef-auth-title">用户登录</h1>',1)
        text=text.replace('</header>','</header>\n    <div class="ef-auth-body">',1)
        index=text.rfind('</section>');assert index>=0
        text=text[:index]+'    </div>\n'+text[index:]
    if '<table' in text:
        text=re.sub(r'<table\b([^>]*)>',lambda m:'<table'+m.group(1)+('' if re.search(r'\brole=',m.group(1)) else ' role="table"')+'>',text)
        def caption(m):
            table=m.group(0)
            if '<caption' not in table:
                table=table.replace('>','><caption class="sr-only">'+labels.get(rel,'商品资料').replace('_',' ')+'</caption>',1)
            return table
        text=re.sub(r'<table\b[^>]*>[\s\S]*?</table>',caption,text)
    # Scroll regions remain keyboard reachable without changing form fields/ids.
    text=re.sub(r'(<div\b[^>]*class="[^"]*table-container[^"]*")',r'\1 tabindex="0" role="region" aria-label="商品与订单数据表，可横向滚动"',text)
    dest=STAGE/'candidate'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True)
    new=text.replace('\n',newline).encode('utf-8');assert new!=raw,rel
    dest.write_bytes(new);modified.append(p.relative_to(ROOT).as_posix())
(STAGE/'user-template-changes.json').write_text(json.dumps(modified,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'user_template_candidates':len(modified),'files':modified},ensure_ascii=False))
