from common import *
import sys
r=Review(sys.argv[1]); r.n=max(json.loads(x)['id'] for x in (ROOT/'http.jsonl').read_text(encoding='utf-8').splitlines()); r.state=json.loads((ROOT/'run-state-public.json').read_text(encoding='utf-8')); r.begin('final-checks')
r.u=r.login('u','alice'); r.a=r.login('a','admin')
token_page=r.req(r.u,'u','GET','/checkout',label='valid confirmation before disable')
t=r.inputs(token_page).get('confirmationToken'); r.check('confirmation existed before disable',bool(t))
r.req(r.a,'a','POST','/customers/1/status',{'targetStatus':'DISABLED'},303,label='disable with outstanding confirmation')
r.req(r.u,'u','POST','/orders',{'confirmationToken':t,'receiverName':'复核收货人','receiverPhone':'000-REVIEW','receiverAddress':'测试校区虚构地址'},302,label='disabled old confirmation protected POST before CSRF',csrf=False,zero=True)
r.req(r.a,'a','POST','/customers/1/status',{'targetStatus':'ENABLED'},303,label='reenable after invalid protected POST')
r.req(r.u,'u','GET','/orders',302,label='cleared old identity remains invalid')
r.login('u','alice',session=r.u)
r.req(r.u,'u','POST','/orders',{'confirmationToken':t,'receiverName':'复核收货人','receiverPhone':'000-REVIEW','receiverAddress':'测试校区虚构地址'},409,label='old confirmation unavailable after relogin',zero=True)

checks={
 'payment_pairing':"SELECT id FROM sales_order WHERE (status IN ('PENDING_PAYMENT','CANCELLED') AND NOT(payment_method IS NULL AND payment_no IS NULL AND paid_at IS NULL)) OR (status IN ('PAID','SHIPPED','COMPLETED') AND (payment_method IS NULL OR payment_method<>'MOCK' OR payment_no IS NULL OR CHAR_LENGTH(TRIM(payment_no))=0 OR paid_at IS NULL))",
 'cancel_time_pairing':"SELECT id FROM sales_order WHERE (status='CANCELLED')<>(cancelled_at IS NOT NULL)",
 'ship_time_pairing':"SELECT id FROM sales_order WHERE (status IN ('SHIPPED','COMPLETED'))<>(shipped_at IS NOT NULL)",
 'completed_time_pairing':"SELECT id FROM sales_order WHERE (status='COMPLETED')<>(completed_at IS NOT NULL)",
 'time_sequence':"SELECT id FROM sales_order WHERE paid_at<created_at OR cancelled_at<created_at OR shipped_at<paid_at OR completed_at<shipped_at",
}
observed={}
for name,q in checks.items():
    observed[name]={'sql':q,'rows':r.sql(q)}; r.check(name+' no violations',not observed[name]['rows'])
dump(ROOT/'final-invariants.json',observed)
r.finish('final-checks',['已有效确认→管理端禁用→原确认POST无CSRF仍先302且七表零写→启用后旧身份不复活→正常重登后原确认409。','HTTP只能证明旧确认不可用；登录动作本身也会清确认，未直接读取Tomcat内部会话属性，不能单独证明AuthFilter删除确认的具体内部时点。','全库支付三字段/取消发货完成时间与状态配套及时间链逐项独立SQL零违规；不等于逐个CHECK非法写穷举。'])
dump(ROOT/'final-checks-result.json',{'checks':len(r.checks),'failures':[x for x in r.checks if not x['passed']]})
sys.exit(1 if any(not x['passed'] for x in r.checks) else 0)
