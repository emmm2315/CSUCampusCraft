from pathlib import Path
from html.parser import HTMLParser
import gzip, hashlib, json, re, sys
from datetime import datetime
from urllib.parse import urlsplit, parse_qs

base=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent
def raw(rel):
    p=base/rel
    if not p.exists():p=Path(str(p)+'.gz')
    data=p.read_bytes()
    return gzip.decompress(data) if p.suffix=='.gz' else data
def read(rel):return json.loads(raw(rel).decode('utf-8-sig'))
def lines(rel):return [json.loads(x) for x in raw(rel).decode('utf-8-sig').splitlines()]

r=read('result.json')
assert r['overall']=='PASS' and r['tested_code_sha']=='9e61c3e88761519fc63a4d99cafb006a51eacfa5'
assert all(v['passed'] for v in r['checks'].values())
attempt=r.get('attempt','attempt2')
http=lines(attempt+'/http.jsonl')
writes=lines(attempt+'/database-writes.jsonl')
auto=[w for w in writes if w.get('automatic_all_posts')]
posts={x['sequence'] for x in http if x['method']=='POST'}
assert len(auto)==len(posts)==r['http_posts']
assert {w['http_sequence'] for w in auto}==posts
rejected=inserted=updated=removed=noops=0
for w in auto:
    assert len(w['before'])==len(w['after'])==7
    assert all(w['before'][t]==w['after'][t] for t in w['before'] if t!='cart_item'),w['name']
    assert not w['deltas']['product'],w['name']
    if w['status']!=303:
        rejected+=1
        assert w['before']==w['after'] and not any(w['deltas'].values()),w['name']
    is_cart=w['path']=='/cart/items' or re.fullmatch(r'/cart/items/[0-9]+/(quantity|remove)',w['path'])
    if not is_cart:
        assert w['before']==w['after'] and not any(w['deltas'].values()),w['name']
        continue
    changes=w['deltas']['cart_item']
    assert len(changes)<=1,w['name']
    if not changes:
        assert w['before']==w['after'],w['name']
        if w['status']==303:noops+=1
        continue
    assert w['status']==303,w['name']
    d=changes[0];old,new=d['before'],d['after']
    uid=(new or old)['userId']
    if w['path']=='/cart/items':
        assert new is not None,w['name']
    else:
        assert int(w['path'].split('/')[3])==int(d['id']),w['name']
    matches=[m for m in writes if not m.get('automatic_all_posts') and m.get('path')==w['path']
             and m.get('status')==w['status'] and m['before']==w['before'] and m['after']==w['after']]
    assert matches and any(m.get('actor_user_id')==uid for m in matches),w['name']
    if old is None:
        inserted+=1
        assert new['version']==0 and 1<=new['quantity']<=99,w['name']
    elif new is None:
        removed+=1
        assert w['path'].endswith('/remove'),w['name']
    else:
        updated+=1
        assert all(new[k]==old[k] for k in ['id','userId','productId','createdAt']),w['name']
        assert new['quantity']!=old['quantity'] and 1<=new['quantity']<=99,w['name']
        assert new['version']==old['version']+1,w['name']
    own=[v for v in w['cart_after'].values() if v['userId']==uid]
    assert len(own)<=20 and len({v['productId'] for v in own})==len(own),w['name']

class Badge(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.attributes=None;self.value='';self.active=False
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if a.get('id')=='cart-quantity':self.attributes=a;self.active=True
    def handle_data(self,value):
        if self.active:self.value+=value
    def handle_endtag(self,tag):
        if self.active:self.active=False

indexed={x['sequence']:x for x in http}
badges=lines(attempt+'/badge-observations.jsonl')
for obs in badges:
    response=indexed[obs['http_sequence']]
    body=raw(attempt+'/'+response['body_file'])
    assert hashlib.sha256(body).hexdigest()==response['redacted_body_sha256']
    b=Badge();b.feed(body.decode('utf-8'))
    expected=str(obs['expected_sum_all_rows'])
    assert b.attributes and b.value.strip()==expected and b.attributes['data-cart-quantity']==expected,obs['name']
journey=read(attempt+'/journey/result.json')
assert journey['overall']=='PASS' and journey['completed'] and all(c['passed'] for c in journey['checks'])
nav=[x for x in http if x.get('transport')=='actual Playwright navigation']
assert [(x['method'],urlsplit(x['path']).path,x['status']) for x in nav]==[
    ('GET','/products/56',200),('GET','/login',200),('POST','/login',303),
    ('GET','/products/56',200),('POST','/cart/items',303),('GET','/cart',200)]
assert parse_qs(urlsplit(nav[1]['path']).query)['returnUrl']==['/products/56']
class Purchase(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.post=0;self.add=0;self.login=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='form' and a.get('method','').lower()=='post':
            self.post+=1
            if 'data-add-cart' in a:self.add+=1
        if tag=='a' and 'data-login-to-add' in a:self.login.append(a['href'])
for i,guest in [(0,True),(3,False)]:
    response=nav[i];body=raw(attempt+'/'+response['body_file']).decode('utf-8')
    p=Purchase();p.feed(body)
    b=Badge();b.feed(body)
    assert b.value.strip()=='0'
    if guest:
        assert p.post==p.add==0 and len(p.login)==1
        assert parse_qs(urlsplit(p.login[0]).query)['returnUrl']==['/products/56']
    else:assert p.add==1 and not p.login
for response in [nav[2],nav[4]]:
    audit=next(x for x in auto if x['http_sequence']==response['sequence'])
    if response['path']=='/login':assert audit['before']==audit['after']
    else:
        change=audit['deltas']['cart_item'];assert len(change)==1 and change[0]['before'] is None
        assert change[0]['after']['quantity']==1 and change[0]['after']['version']==0
    assert response['body_available'] is False  # Browser redirect body was unavailable, never reconstructed.
native=raw(attempt+'/native-probe.log').decode('utf-8')
native_result=next(json.loads(x) for x in native.splitlines() if x.startswith('{"overall"'))
assert native_result['overall']=='PASS' and native_result['checks']==r['native_checks']==91
for label in ['unavailable-change-stable-code','unavailable-change-409','unavailable-same-quantity-noop',
              'mid-disable-wait-observed-in-performance-schema','mid-disable-rejected-after-lock',
              'mid-disable-only-user-query','mid-disable-cart-and-products-zero-write',
              'mid-disable-old-actor-does-not-revive','mid-disable-reenable-zero-write']:
    assert 'CHECK '+label+'=true' in native,label
for line in native.splitlines():
    if line.startswith('SQL_TRACE') and re.search(r'\bfrom\s+product\b',line,re.I):
        assert 'for update' not in line.lower()
wait=read('auth-lock-wait.json')
logged_wait=json.loads(next(x[len('AUTH_LOCK_WAIT '):] for x in native.splitlines() if x.startswith('AUTH_LOCK_WAIT ')))
assert wait==logged_wait and wait['cartAndProductsUnchanged']
assert 0<=wait['waitObservedMillis']<=wait['elapsedMillis']<=wait['boundSeconds']*1000
assert datetime.fromisoformat(wait['initialStampUtc'])<datetime.fromisoformat(wait['disabledStampUtc'])<datetime.fromisoformat(wait['reenabledStampUtc'])
report={
    'result':'PASS','reviewer':'independent Codex root; named human review pending',
    'tested_sha':r['tested_code_sha'],'http_records':len(http),'automatic_post_db_pairs':len(auto),
    'non303_posts_zero_write':rejected,'cart_insert_posts':inserted,'cart_update_posts':updated,
    'cart_remove_posts':removed,'cart_noop_posts':noops,'badge_html_observations':len(badges),
    'real_guest_journey_posts_checked':2,'guest_no_form_and_auth_form_preserved':True,
    'unavailable_quantity_code_and409_native_checked':True,'auth_midwait_native_checked':True,
    'wait_first_observed_offset_ms':wait['waitObservedMillis'],'wait_supplement_total_ms':wait['elapsedMillis'],
    'findings':[],
    'coverage':'Every POST matched one automatic seven-table pair; other six tables unchanged; cart mutation only one row belonging to the named actor, initial version0/actual-update+1, <=20 unique SKUs; response gzip SHA and actual badge HTML agree with recorded SQL SUM.',
    'limits':'Fresh HTTP/native plus observed actor-lock/disable interleaving; no cart/order double-request concurrency, checkout/order flow, or injected failure after DML.'
}
(base/'independent-observation-review.json').write_bytes((json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps(report,ensure_ascii=False))
