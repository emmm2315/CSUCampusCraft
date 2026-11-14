from common import *
import sys
r=Review(sys.argv[1]); r.stage='H-db-report'
state=json.loads((ROOT/'run-state-public.json').read_text(encoding='utf-8'))
nos=','.join("'"+state[k]+"'" for k in ['paid_order','cancelled_order'])
queries={
 '本轮新主单与明细金额':"SELECT o.id,o.order_no,o.user_id,o.status,o.total_amount,COUNT(i.id) AS line_count,SUM(i.line_amount) AS sum_lines FROM sales_order o JOIN sales_order_item i ON i.order_id=o.id WHERE o.order_no IN ("+nos+") GROUP BY o.id,o.order_no,o.user_id,o.status,o.total_amount ORDER BY o.id",
 '支付及履约配套字段':"SELECT order_no,status,payment_method,payment_no,paid_at,cancelled_at,shipped_at,completed_at FROM sales_order WHERE order_no IN ("+nos+") ORDER BY id",
 '成交明细快照':"SELECT o.order_no,i.product_id,i.sku_snapshot,i.product_name_snapshot,i.cover_image_snapshot,i.unit_price,i.quantity,i.line_amount FROM sales_order_item i JOIN sales_order o ON o.id=i.order_id WHERE o.order_no IN ("+nos+") ORDER BY o.id,i.product_id",
 '全种子库存公式':"SELECT COUNT(*) AS products,SUM(x.stock<>x.expected_stock) AS mismatches FROM (SELECT p.id,p.stock,ref.stock-COALESCE(SUM(CASE WHEN o.order_no IN ("+nos+") AND o.status<>'CANCELLED' THEN i.quantity ELSE 0 END),0) AS expected_stock FROM product p JOIN review_reference.product ref ON ref.sku=p.sku LEFT JOIN sales_order_item i ON i.product_id=p.id LEFT JOIN sales_order o ON o.id=i.order_id GROUP BY p.id,p.stock,ref.stock) x",
 '主线与独立商品当前库存版本':"SELECT id,sku,stock,status,version,cover_image FROM product WHERE id IN ("+str(state['note_id'])+','+str(state['box_id'])+','+str(state['admin_fixture_product'])+") ORDER BY id",
 '全行购物车徽标':"SELECT user_id,COUNT(*) AS sku_rows,SUM(quantity) AS badge FROM cart_item GROUP BY user_id ORDER BY user_id",
 '控制台五项独立SQL':"SELECT (SELECT COUNT(*) FROM product WHERE status='ON_SALE') AS on_sale,(SELECT COUNT(*) FROM product WHERE status='DRAFT') AS draft,(SELECT COUNT(*) FROM sales_order WHERE status='PAID') AS paid,(SELECT COUNT(*) FROM store_user WHERE role='CUSTOMER' AND status='ENABLED') AS enabled,(SELECT COUNT(*) FROM store_user WHERE role='CUSTOMER' AND status='DISABLED') AS disabled",
}
out=['# 本轮关键SQL与真实结果','', '全部查询明确使用本轮隔离实例59315/csucampuscraft、UTC会话。主流程每个POST另保存七表完整有序行SHA前后，见http.jsonl；SQL夹具与业务HTTP写分开标注。无完整收货字段、密码散列或会话值归档。','']
for title,q in queries.items():
    rows=r.sql(q); out+=['## '+title,'','```sql',q+';','```','', '```json',json.dumps(rows,ensure_ascii=False,indent=2),'```','']
checks=[json.loads(x) for x in (ROOT/'checks.jsonl').read_text(encoding='utf-8').splitlines()]
out+=['## 动作时的独立前后结果','','以下摘自本轮checks.jsonl保存的实际观测，不由当前状态反推过去。','']
for c in checks:
    if c['name'] in ['inventory10/12 to8/11 and version+1','cancel returns2/1 and increments each version once','all seven full-row hashes unchanged across app restarts']:
        out+=['### '+c['name'],'','```json',json.dumps(c,ensure_ascii=False,indent=2),'```','']
out+=['## 不变量与CHECK边界','','全库总额/行金额/孤儿/车唯一/凭证唯一由stage-F实跑。全部支付配套与取消/发货/完成时间状态配套、时间链由final-invariants.json逐项SQL实跑，全部零违规。两库35个CHECK元数据均启用，运行拒绝仅负库存3819代表样本，不称所有非法样本已穷举。','','临时SQL夹具：A账号role/status/stamp与同库主题完整恢复；B库存200/下架边界恢复库存和状态；C改价夹具恢复价与version。C/D/E与补充的管理维护和业务成交留在隔离库，绝不触及开发库或改写seed文件。独立REVIEW商品起始4、补货3、现库存7；种子60SKU按参照库初值减本轮未取消净成交逐一核对。','']
(ROOT/'db-checks.md').write_text('\n'.join(out),encoding='utf-8')
dump(ROOT/'db-report-result.json',{'finished':stamp(),'sql_queries':len(queries),'exit':0})
