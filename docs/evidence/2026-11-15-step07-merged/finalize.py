from pathlib import Path
from html.parser import HTMLParser
import json, shutil, hashlib, collections, gzip, re, sys
here=Path(__file__).resolve().parent
attempt=sys.argv[1]
assert re.fullmatch(r'attempt[1-9][0-9]*',attempt)
source=here/'evidence'/attempt
result=json.loads((source/'result.json').read_text(encoding='utf-8'))
assert result['overall']=='PASS' and result['tracked_processes_stopped']
out=here.parent/'final-evidence'
assert not out.exists()
out.mkdir()
for p in (here/'evidence').iterdir():
    if p.is_dir() and re.fullmatch(r'attempt[1-9][0-9]*',p.name):
        shutil.copytree(p,out/p.name)
        log=here/(p.name+'-run.log')
        if log.exists():shutil.copy2(log,out/p.name/'console.log')
canonical={hashlib.sha256(p.read_bytes()).hexdigest():p for p in (out/attempt).rglob('*.png')}
references=[]
for d in out.iterdir():
    if d.is_dir() and d.name!=attempt:
        for p in d.rglob('*.png'):
            digest=hashlib.sha256(p.read_bytes()).hexdigest()
            if digest in canonical:
                references.append({'original_path':p.relative_to(out).as_posix(),'canonical_path':canonical[digest].relative_to(out).as_posix(),'sha256':digest,'bytes':p.stat().st_size,'original_stage_file_preserved':True})
                p.unlink()
(out/'artifact-references.json').write_text(json.dumps({'scope':'Only byte-identical failed screenshots may reference the successful original; stage attempts stay unchanged','references':references},ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
for name in ['prepare.py','helpers.pyfrag','cases.pyfrag','journey.pyfrag','previous-template.py.txt','run_attempt.py','selfcheck.py','audit_evidence.py','finalize.py','preparation-selfcheck.json']:
    shutil.copy2(here/name,out/name)
shutil.copy2(source/'runtime-inputs.sha256',out/'runtime-inputs.sha256')
for name in ['cart-build-fresh.ps1','build-user.json','build-admin.json','build-exits.json']:
    shutil.copy2(here.parent/name,out/name)
http=[json.loads(x) for x in (source/'http.jsonl').read_text(encoding='utf-8').splitlines()]
writes=[json.loads(x) for x in (source/'database-writes.jsonl').read_text(encoding='utf-8').splitlines()]
posts=[x for x in http if x['method']=='POST'];auto=[x for x in writes if x.get('automatic_all_posts')]
assert {x['sequence'] for x in posts}=={x['http_sequence'] for x in auto}
assert all(x['before']==x['after'] for x in auto if x['status'] not in [303])
assert all(all(x['before'][t]==x['after'][t] for t in x['before'] if t!='cart_item') for x in auto)
class Markers(HTMLParser):
    def __init__(self):super().__init__();self.ids=[];self.anchors=[];self.inputs=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if a.get('id'):self.ids.append(a['id'])
        if a.get('href','').startswith('#') and len(a['href'])>1:self.anchors.append(a['href'][1:])
        if tag=='input':self.inputs.append(a)
bodychecks=[]
for r in http:
    if r['status'] not in [400,409]:continue
    dom=Markers();dom.feed(gzip.decompress((source/r['body_file']).read_bytes()).decode('utf-8'))
    bodychecks.append({'http_sequence':r['sequence'],'status':r['status'],'unique_ids':len(dom.ids)==len(set(dom.ids)),'error_anchors_resolve':all(x in dom.ids for x in dom.anchors),'invalid_quantity_raw_abc_retained':any(x.get('name')=='quantity' and x.get('value')=='abc' for x in dom.inputs)})
assert all(x['unique_ids'] and x['error_anchors_resolve'] for x in bodychecks)
assert any(x['invalid_quantity_raw_abc_retained'] for x in bodychecks)
coverage={'passed':True,'http_posts':len(posts),'automatic_seven_table_db_pairs':len(auto),'all_rejected_posts_zero_write':True,'other_six_tables_unchanged_every_post':True,'real_browser_journey_posts_audited':2,'inline_error_html_checks':bodychecks,'notes':'Every real HTTP POST, including login/logout/guest/CSRF/role rejection, has seven-table hashes and complete non-sensitive cart row versions/timestamps; product snapshots prove inventory/version unchanged.'}
(out/'http-post-coverage.json').write_text(json.dumps(coverage,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
native_log=(source/'native-probe.log').read_text(encoding='utf-8')
native=json.loads(next(x for x in native_log.splitlines() if x.startswith('{"overall":')))
assert native['overall']=='PASS'
wait=json.loads(next(x[len('AUTH_LOCK_WAIT '):] for x in native_log.splitlines() if x.startswith('AUTH_LOCK_WAIT ')))
assert wait['cartAndProductsUnchanged'] and wait['waitObservedMillis']>=0
(out/'auth-lock-wait.json').write_text(json.dumps(wait,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
journey=json.loads((source/'journey/result.json').read_text(encoding='utf-8'))
assert journey['overall']=='PASS' and len(journey['posts'])==2 and len(journey['screenshots'])==4
assert len(list(source.rglob('*.png')))==28
summary=dict(result)
summary.update(native_checks=native['checks'],auth_lock_wait=wait,journey_checks=len(journey['checks']),journey_posts=len(journey['posts']),readonly_browser_screenshots=24,journey_screenshots=4)

summary.update(attempt=attempt,http_count=len(http),http_status_counts=dict(collections.Counter(str(x['status']) for x in http)),http_posts=len(posts),database_pairs=len(writes),group_cross_review='姓名待填；组员交叉复核待补，M3前完成')
(out/'result.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
failed=[]
for d in (here/'evidence').iterdir():
    if d.name!=attempt and (d/'result.json').exists():
        r=json.loads((d/'result.json').read_text(encoding='utf-8'));failed.append({'attempt':d.name,'overall':r['overall'],'error':r.get('error','')})
readme=f'''# STEP07 合并后持久购物车与导航徽标实测证据

- 实际受测完整 Git SHA：`{result['tested_code_sha']}`；main 基线：`{result['baseline_git_sha']}`；分支 `{result['branch']}`。
- 结论：**PASS（自动验收，组员实名复核待补）**，成功轮 `{attempt}`。起测工作区干净，见 `{attempt}/git-input-status.txt`。运行输入 {result['runtime_file_count']} 个，清单 SHA-256 `{result['runtime_manifest_sha256']}`，结束逐项确认无漂移。
- JDK 21、Wrapper Maven 3.9.16、MySQL {result['mysql_version']}；独立库 `csucampuscraft` 端口 `{result['mysql_port']}`；双端 JAR 监听127.0.0.1:8080/8081。版本原输出、库UUID/私有目录与监听PID见成功轮 versions.txt / database-identity.json / listener-ownership.jsonl。
- 两端真实Wrapper verify均BUILD SUCCESS、退出0；完整本机执行参数在 `cart-build-fresh.ps1`，新终端不含Maven PATH，固定JDK与独立缓存；两端元信息在build-user/admin.json，日志在成功轮，未新增依赖或测试框架。

本目录名 `2026-11-15-step07-merged` 按用户指定的合并批次；执行时间使用系统真实时钟，见 result.json 的 date，未伪造未来日期。双方旧结果分别见[本地原记录](../2026-11-14-step07/README.md)和[组员原字节记录](../2026-11-14-step07-member/README.md)，它们都不代替本轮新 SHA 的新测试。

## 覆盖与可复核记录

- 主工具 {len(result['checks'])} 项断言通过；HTTP {len(http)} 条、POST {len(posts)} 次，每一POST有自动七表前后对照。`{attempt}/database-writes.jsonl`保存本人完整车行id/user/product/quantity/version/时间、商品现价/库存/状态/version及全7表有序原始行SHA；敏感账号/订单只保留表摘要。
- TST-08：身份→CSRF→角色→格式→锁当前用户复验→商品状态→合并数量/品种/库存。覆盖无身份302、缺错CSRF403、错角色403、参数400、未知/下架404、售罄/库存/合并超99/第21种409。单次1/99成功，同SKU一行、新行version0，实际改量增1。
- TST-09：首页、列表、详情、购物车、登录、400/403/404/409/500错误页及游客均核对本人全部SUM(quantity)，包括失效行；不按行数、商品状态或库存过滤。退出、重新登录、全新客户端与实际同JAR重启后购物车恢复；bob只读本人车。失败重新认证后的匿名页面徽标归0。
- TST-10/17购物车顺序部分：跨账号条目403、不存在404、旧版本409；同值有效版本303且零DML，MAX版本同值可303、实际变更409、移除MAX版本仍可成功；20种中失效行仍计数，已有SKU在满20种时可加量。
- TST-11本步部分：读取当前价格并以BigDecimal计算有效条目小计，清种子车后2×18.00+49.00=85.00；后台SQL夹具下架/售罄/减库存后车行保留并分别说明原因，不计入有效小计，仍可移除。整车结算按钮本步始终禁用，未注册/链接checkout/orders。
- 所有拒绝POST表摘要相同；每个成功购物车写仅允许本人cart_item变化，其余六表（包括产品库存/version、已有订单快照）不变。根SQL夹具独立记录于fixtures.jsonl，结束恢复原产品/账号全部受控字段，不能当作后台业务入口。
- 实际合并用户JAR原生Service补充（{native['checks']}项） `CartWriteProbe.java` / native-probe.log：先操作者FOR UPDATE、写事务READ COMMITTED、同连接；缺身份/旧戳/禁用/错角色在车表前拒绝；有效同值无DML，数量变化带version条件；真实徽标SQL为SUM且无JOIN/COUNT。各写SQL跟踪另断言商品读取无FOR UPDATE。独立root连接持有用户行，P_S data_lock_waits真实确认Service等待后禁用并推进微秒认证戳提交，Service锁内拒绝且车/商品无变；重启用旧戳仍拒绝。AUTH_LOCK_WAIT原始日志及auth-lock-wait.json记录真实连接/等待/时间，不是两HTTP抢购或订单并发。
- 本轮先在default profile执行购物车矩阵及同JAR重启；随后仅为复用STEP02既有400/403/404/409/500 GET错误探针重启到verification profile，另核库存/车数据无变化。不增加生产测试端点，不做业务故障注入。
- 28张PNG：`{attempt}/browser/`保留24张两桌面视口只读检查，`{attempt}/journey/`另有4张真实游客流程图（1366）。游客详情没有POST表单，只显示登录后加购链接；实际点击→登录303返回详情（0件、无自动重放）→本人手动点击一次真实加购→303购物车（1件），两次真实浏览器POST都由仅本机工具observer逐请求记录七表前后、与所有HTTP同一索引；不是生产探针。每图有完整SHA/尺寸/视口，28张全部是本次新生成。
- http.jsonl的正文经脱敏后gzip去重，索引记解压后SHA；最终sensitive-data-scan.json解压每一正文和命令日志检查CSRF/Cookie/会话/BCrypt/已知教学口令。evidence-files.json列除自身外所有文件字节SHA。

## 边界、差异与轮次

- 用户验收段将下架统列409，但本轮核心契约/SRS/HLD/原TST-08矩阵明确加购DRAFT为404；按细化矩阵执行。身份存在且错角色403，只有身份/状态/戳失效才清身份并302登录。
- 有效版本同值改量不写数据，所以即使商品已失效或version为MAX仍可成功；实际改量下架/不可用为409，原生异常验证稳定code CART_PRODUCT_UNAVAILABLE，页面提示移除后继续选购；售罄或不足仍409。删除不加版，可删除MAX版本行。没有把购物车有效性检查当作库存预留。
- TST-08–10只按本轮真实分支覆盖；TST-11的有效结算确认/下单、TST-17并发/旧确认/订单清车留后续STEP08/09/13；认证锁等待是本轮实际补充，只证明等待期间禁用后的事务内复验；不把它当作购物车双请求、订单竞争或后段故障回滚证明。
- 其他轮次：{json.dumps(failed,ensure_ascii=False)}。若出现FAIL，保留原始结果和日志，不能改写为通过；相同截图可按artifact-references.json完整SHA共享，原stage保留。
- 姓名待填；负责人（Codex生成初稿，本人核对与验证）、组员复核待补（M3前完成）。AI执行单元不代替组员签字。

## 运行与停机

验收脚本、native源码、浏览器脚本归档在成功轮。应用账号仅获SELECT/LOCK TABLES与cart_item的INSERT/UPDATE/DELETE，其他六表无DML权限；账号、商品变化仅私有库root夹具。每个SQL连接先设UTC，生产数据库未触及。`tracked_processes_stopped=true`确认受控进程均退出，cleanup.json记录经绝对路径范围校验后的私有目录清理；秘密文件不进入归档。
'''
(out/'README.md').write_text(readme,encoding='utf-8',newline='\n')
print(json.dumps({'published':str(out),'overall':summary['overall'],'http':len(http),'posts':len(posts),'screenshots':result['screenshots']},ensure_ascii=False))
