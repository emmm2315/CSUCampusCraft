from common import *
import sys
r=Review(sys.argv[1]); r.n=max(json.loads(x)['id'] for x in (ROOT/'http.jsonl').read_text(encoding='utf-8').splitlines())
r.state=json.loads((ROOT/'run-state-public.json').read_text(encoding='utf-8')); r.begin('persistence')
before=r.digest(); original=r.sql("SELECT id,name,updated_at FROM category WHERE code='LANDMARK'")[0]
r.a=r.login('a','admin'); r.u=r.login('u','alice')
changed='复核同库持久性主题'; cid=original['id']
r.sql("UPDATE category SET name='"+changed+"' WHERE id="+cid)
for b,s,path in [('u',r.u,'/'),('a',r.a,'/categories')]:
    z=r.req(s,b,'GET',path,label='same DB theme changed '+b); r.check('theme visible '+b,changed in z.text)
renamed=r.digest(); dump(ROOT/'persistence-before-restart.json',{'at':stamp(),'seven_tables':renamed,'theme':original,'temporary_name':changed})
print('RESTART_READY: both apps may now restart; press Enter afterwards',flush=True)
input()
r.a=r.login('a','admin'); r.u=r.login('u','alice'); r.bob=r.login('u','bob')
for b,s,path in [('u',r.u,'/'),('a',r.a,'/categories')]:
    z=r.req(s,b,'GET',path,label='theme after restart '+b); r.check('theme persisted after restart '+b,changed in z.text)
r.check('all seven full-row hashes unchanged across app restarts',renamed==r.digest(),{'before':renamed,'after':r.digest()})
for s,user in [(r.u,1),(r.bob,2)]:
    z=r.req(s,'u','GET','/cart'); count=r.sql('SELECT COUNT(*) AS rows_,COALESCE(SUM(quantity),0) AS qty FROM cart_item WHERE user_id='+str(user))[0]
    r.check('cart persists including badge user'+str(user),r.attrs(z,'data-cart-quantity')[0]==count['qty'] and int(count['rows_'])>0,count)
for b,s in [('u',r.u),('a',r.a)]: r.req(s,b,'GET','/orders/'+r.state['paid_order'],label='new order persists after restart '+b)
r.sql("UPDATE category SET name='"+original['name'].replace("'","''")+"',updated_at='"+original['updated_at']+"' WHERE id="+cid)
r.check('temporary theme fully restored',before==r.digest())
r.finish('persistence',['INIT-03/04同库改名及双端应用重启持久性新跑；管理端当前根为统计，主题在当前分类页核对，不把历史M0根主题页当当前行为。','完整七表行摘要跨重启相同，alice和bob非空车与徽标恢复，新85元订单双端可读。','TST-32技术重启子项已补，另一位真人组员复现/实名条件仍未满足；没有故障注入。'])
dump(ROOT/'persistence-result.json',{'checks':len(r.checks),'failures':[x for x in r.checks if not x['passed']]})
sys.exit(1 if any(not x['passed'] for x in r.checks) else 0)
