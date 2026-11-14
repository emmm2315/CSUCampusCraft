"""Package two fresh STEP09 attempts and clearly separated diagnostic/native observations."""
from pathlib import Path
import gzip,hashlib,json,shutil

HERE=Path(__file__).resolve().parent
RAW=HERE/'verification/evidence'
EV=HERE/'final-evidence'
REPO=Path('D:/Github Projects/CSUCampusCraft')
assert not EV.exists(), 'Do not overwrite an archive draft'
failed=json.loads((RAW/'attempt1/result.json').read_text(encoding='utf-8'))
run=json.loads((RAW/'attempt2/result.json').read_text(encoding='utf-8'))
assert failed['overall']=='FAIL' and run['overall']=='PASS'
assert failed['tracked_processes_stopped'] and run['tracked_processes_stopped']
assert all(x['passed'] for x in run['checks'].values())
metadata=json.loads((HERE/'verification/delivery-metadata.json').read_text(encoding='utf-8'))
audit=json.loads((RAW/'independent-observation-review.json').read_text(encoding='utf-8'))
assert audit['overall']=='PASS'
amount=json.loads((HERE/'native-amount-supplement/result.json').read_text(encoding='utf-8'))
assert amount['overall']=='PASS' and amount['checks']==amount['checksPassed']==13
EV.mkdir()
def sha(b):return hashlib.sha256(b).hexdigest()
def write(name,data):
    p=EV/name;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def copy(source,name):
    p=EV/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE/source,p)
compressed=[]
for attempt in ['attempt1','attempt2']:
    shutil.copytree(RAW/attempt,EV/attempt)
    for name in ['commands.jsonl','database-writes.jsonl']:
        original=RAW/attempt/name;raw=original.read_bytes();dest=EV/attempt/(name+'.gz')
        dest.write_bytes(gzip.compress(raw,compresslevel=9,mtime=0))
        assert gzip.decompress(dest.read_bytes())==raw
        (EV/attempt/name).unlink()
        compressed.append(dict(path=attempt+'/'+name+'.gz',decompressed_sha256=sha(raw),original_bytes=len(raw),compressed_bytes=dest.stat().st_size,original_stage_file_unchanged=True))
write('compressed-text-index.json',compressed)
for source,name in [
    ('source-publication.json','initial-source-publication.json'),
    ('source-fix-publication.json','source-fix-publication.json'),
    ('baseline-preservation.json','baseline-preservation.json'),
    ('backend-review.json','backend-review.json'),
    ('backend-review.md','backend-review.md'),
    ('final-source-fix-review.json','final-source-fix-review.json'),
    ('ui/static-review.json','ui-static-review.json'),
    ('ui/static-review.md','ui-static-review.md'),
    ('ui-visual-review.json','ui-visual-review.json'),
    ('review_observations.py','review_observations.py'),
    ('verification/evidence/independent-observation-review.json','independent-observation-review.json'),
    ('verification/delivery-metadata.json','delivery-metadata.json'),
    ('verification/attempts-summary.json','attempts-summary.json'),
    ('verification/attempt1-diagnostic.json','attempt1-diagnostic.json'),
    ('integrate.py','archive-tools/integrate.py'),
    ('package_evidence.py','archive-tools/package_evidence.py'),
    ('verification/cleanup.py','archive-tools/cleanup.py')]:copy(source,name)
for path in (HERE/'diagnostics').iterdir():
    if path.is_file() and path.suffix in {'.java','.log','.json'}:copy(path.relative_to(HERE), 'diagnostics/'+path.name)
for name in ['CheckoutAmountProbe.java','compile.log','result.json','metadata.json']:
    copy('native-amount-supplement/'+name,'native-amount-supplement/'+name)
for source_dir,target_dir in [(HERE/'builds-attempt1','builds/attempt1'),(HERE,'builds/attempt2')]:
    for name in ['orders-build-fresh.ps1','build-user.log','build-admin.log','build-user.json','build-admin.json','build-exits.json']:
        copy((source_dir/name).relative_to(HERE),target_dir+'/'+name)
initial=json.loads((HERE/'source-publication.json').read_text(encoding='utf-8'))
final=[]
for item in initial['files']:
    final.append(dict(path=item['path'],original_sha256=item['original_sha256'],sha256=sha((REPO/item['path']).read_bytes())))
write('final-source-manifest.json',dict(tested_code_sha=run['tested_code_sha'],files=final))
base=json.loads((HERE/'baseline.json').read_text(encoding='utf-8'))
write('original-refs.json',dict(base=base['base'],refs=base['refs']))
summary=dict(metadata,baseline_git_sha=run['baseline_git_sha'],failed_tested_code_sha=failed['tested_code_sha'],branch=run['branch'],
             attempts=[dict(path='attempt1/result.json',overall='FAIL',tested_code_sha=failed['tested_code_sha']),dict(path='attempt2/result.json',overall='PASS',tested_code_sha=run['tested_code_sha'])],
             runtime_file_count=run['runtime_file_count'],runtime_manifest_sha256=run['runtime_manifest_sha256'],
             controlled_amount_checks=13,controlled_amount_proof='Separate actual-class controlled calculation, no DB or HTTP',
             team_review='待复核；组员真实姓名待填，M3前完成；STEP07/08台账状态不变')
write('result.json',summary)
br=json.loads((RAW/'attempt2/browser/result.json').read_text(encoding='utf-8'))
assert br['overall']=='PASS' and len(br['screenshots'])==24
shots='\n'.join('| '+name+' | [1366](attempt2/browser/'+name+'-1366.png) | [1920](attempt2/browser/'+name+'-1920.png) |'
                for name in sorted({x['path'].rsplit('-',1)[0] for x in br['screenshots']}))
orders='\n'.join('| '+x['name']+' | `'+x['order_no']+'` | '+x['total']+' | '+str(x['line_count'])+' |'
                 for x in metadata['order_summaries'])
readme=f'''# STEP09 原子下单与本人订单实测证据

2026-11-14，从已包含 STEP08 的干净 main `{run['baseline_git_sha']}` 创建 `feat/step09-orders`。最终受测源码 **`{run['tested_code_sha']}`**。**修复后全新私有库 attempt2 完整自动验收通过，台账待复核。** 负责人/复核人真实姓名待填，AI 自动和视觉复核不能代替组员签字。STEP07/08 台账及旧证据保持原样。

## 轮次与失败修复

- [attempt1](attempt1/result.json)：源码 `{failed['tested_code_sha']}`，529 项断言、64 条 HTTP。85 元下单、两明细、扣库/version、清车、徽标0、重复提交409及 U08 已正常；随后 HTTP64 GET /orders 实际500，整轮 FAIL 原样保留。私有 MySQL 62964。
- 根因是 MyBatis 对 record 的属性映射不把派生 `getOffset()` 当作 `offset`：`#{{query.offset}}` 参数绑定抛出 ReflectionException。真实发布类的 MetaObject 和 DefaultParameterHandler 重现见 [诊断](diagnostics/)、[失败补记](attempt1-diagnostic.json)。仅增加 record 风格 `offset()`，保留原算法与 getOffset API；[修复清单](source-fix-publication.json)。不改分页、需求或字段语义。
- [attempt2](attempt2/result.json)：源码 `{run['tested_code_sha']}`，另建新库、重新构建双端、从种子完整重跑，全部通过。原失败不改写、不从首轮继承85元成功结论。[两轮索引与捕获时点](attempts-summary.json)；失败 result SHA 与诊断时捕获值一致，HTTP正文逐项解压校验。没有虚构失败瞬间全目录的历史封条。
- 修复增加原生 MetaObject 和实际参数绑定回归，默认 offset0、第二页10均通过。初始 [后端自检](backend-review.json) 是运行前作者自查，未发现该兼容问题，不能当作最终通过；[最终修复复核](final-source-fix-review.json) 说明后端14文件仅 OrderQuery 改变。

## 环境、输入与构建

Windows 11，Microsoft JDK 21.0.12.1、Wrapper Maven 3.9.16，MySQL 8.4.9/InnoDB。失败轮私有端口62964、成功轮 **62151**，UUID与datadir分别核对；两个 JAR 同库 `csucampuscraft` 运行于127.0.0.1:8080/8081，实际监听 PID 归属检查通过，所有SQL连接UTC。[数据库身份](attempt2/database-identity.json)、[监听](attempt2/listener-ownership.jsonl)、[启动](attempt2/launches.jsonl)、[版本](attempt2/versions.txt)。原开发库未触及。

两轮均真实执行两端 Wrapper verify；固定 JAVA_HOME JDK21 且 Maven 不在 PATH，以现有离线 settings/cache 运行，均 BUILD SUCCESS/退出0。失败首轮说明构建成功不等于业务验收通过。[原始构建脚本和日志](builds/)分别保留，不覆盖。未改 POM/Wrapper，不新增依赖或测试框架。

成功轮 **161** 个运行输入，清单 SHA-256 **`{run['runtime_manifest_sha256']}`**，起测工作区干净，结束逐项未漂移。[输入清单](attempt2/runtime-inputs.sha256)、[最终源码清单](final-source-manifest.json)、[受测差异](attempt2/implementation-diff.patch)。管理端、database SQL、共享素材未改。

## 成功与拒绝的数据库对照

成功轮1865主断言、226HTTP、88POST均有自动七表前后摘要；184份自动对照，加具名重复观察共258份。49次POST/orders中3次303成功、46次拒绝零写（302×2、400×20、403×4、409×20）。[HTTP](attempt2/http.jsonl)、[全部逐请求对照](attempt2/database-writes.jsonl.gz)、[订单观察](attempt2/order-observations.jsonl)、[分类指标](delivery-metadata.json)。七表摘要按id排序、全字段计算；安全行状态只保留收货三字段SHA，不写完整收货内容。

| 场景 | 实际订单号 | 金额 | 明细数 |
| --- | --- | --- | --- |
{orders}

前三单由真实 HTTP POST 创建，最后一单由独立 native 实际 Service 调用创建，分别计数。原始10单20明细最终变为14单27明细。每次成功均核对：只新增本人一张PENDING_PAYMENT主单与对应明细，六项支付/状态时间字段NULL；金额为当前锁内单价乘数量，客户端金额/userId等无效；只改已确认商品stock/version/updated_at，其他商品资料不变；只删除本人确认且数量/version相符的车行；store_user/category/product_image不变。

85元主线先用真实购物车移除清空alice种子车，再加2本18元方格本和1盒49元礼盒；一次事务产生1主单+2明细，库存10/12→8/11、两商品version各+1、车清空，303目标U08及首页徽标0。后续浏览器夹具又为alice加了2本方格本+1盒礼盒，因此**截图及最终alice徽标3属于后续重新加购阶段**；native bob下单只清bob车，不清alice的新车，不能误写“最终全库空车”。

拒绝包括字段缺失/空白/超长/补充平面字符、CSRF缺失/错误、游客、被禁用/认证戳失效、令牌缺失/替换/跨会话/跨账号/真实PT1S过期、另一会话改量/版本往返/加购/移除、改价/下架/售罄/库存不足、商品MAX版本及金额溢出；每次拒绝七表完全不变、无部分订单/扣库/清车。字段400保留有效确认，409作废当前确认；CSRF403在事务前拒绝。串行重复提交只能成交一次，不将它称为并发证明。

## 事务、快照与查询

OrderSubmissionCoordinator持本端会话监视器，调用独立Spring代理OrderService.submit。显式READ_COMMITTED的首个数据库操作为CustomerWriteGuard锁store_user并复验ENABLED/CUSTOMER/UTC微秒authStamp，然后检查最新本人确认/完整车；商品按ID升序FOR UPDATE。锁内重算价格/状态/库存/版本和金额，首条INSERT前再次核对令牌及到期时间。订单号为SecureRandom16字节转32位hex、加CSU-共36字符，匹配既有回跳白名单；数据库不区分大小写唯一键兜底，冲突回滚，不自动重试写。

同事务插主单/全部快照明细；扣库SQL含stock下限、version及状态条件，version+1；清车带userId/itemId/productId/quantity/version，逐条检查影响行数。事务代理返回成功后才消费对应确认；会话已结束的清理不把已提交订单伪装成数据库回滚。技术故障走既有通用500页并作废确认；遇不确定响应时，用户应先查本人订单/购物车，不自动重放。

原生 [NativeOrderWriteProbe](attempt2/NativeOrderWriteProbe.java)/[日志](attempt2/native-probe.log) **70项通过、14个SQL事件**：实际RC、同一物理连接、首次用户锁、故意倒序确认输入后的商品升序锁、每次DML影响1行。独立持有的另一JDBC连接观察到订单已提交可见，且事务已结束后才发生令牌删除。它额外产生bob85元订单，外层七表对照单独归档；没有做竞争、故障注入或中途回滚模拟。

U07始终本人过滤；完整订单号精确且不区分大小写、0–40码点，状态白名单、默认10/允许1–50、created_at/id倒序，count/list同where，超页给有效页入口。未知、格式不符和他人详情统一404，省略订单及收货数据。U08只读成交快照，种子历史状态可看，支付/取消入口本步不显示。下单后root SQL夹具同时改商品name/price/cover/DRAFT，订单两表摘要不变、本人U08仍显示旧快照；夹具不是后台HTTP。[快照对照](attempt2/snapshot-immutability.jsonl)、[读页对照](attempt2/detail-observations.jsonl)。

独立重读归档响应及SQL：3次HTTP和1次native成功逐项变化正确、46次拒绝零写、31份U07和10份U08页面与SQL一致，正文/PNG摘要也重核。[独立复核](independent-observation-review.json)。收货字段只存SHA或结构化遮盖，独立HTTP过程在内存比较本人字段哈希，不保存原文。

## 金额补充的实际边界

HTTP“aggregate-overflow”价格夹具同时使一条行小计超限，因此不把它冒称为独立的“只有总额越界”HTTP证明。另用实际固定JAR的CheckoutService做 [受控原生金额补充](native-amount-supplement/result.json)：**13/13通过**，两行各1件、单价各6,000,000,000.00，每行合法而合计12,000,000,000.00超过DECIMAL(12,2)，得到409且清旧确认；单行单件9,999,999,999.99可确认且两位小数。该补充没有启动应用、连接DB、执行HTTP或订单事务，也不是故障注入。实际JAR/类字节对照见metadata.json。

## 截图与脱敏

浏览器326断言、28次真实导航/失败提交均有HTTP和七表记录；24张原始全页PNG，分别在1366×768和1920×1080视口生成，实际逐张视觉复核通过。[视觉记录](ui-visual-review.json)。订单成功由HTTP和native证明，截图浏览真实新订单，不冒称浏览器点击完成下单。全部收货输入/快照遮挡，遮罩图不单独证明字段原文或脚本；真实DOM断言和逐字段SHA是对应证明。fullPage高度可能超过视口高度。

| 场景 | 1366×768视口 | 1920×1080视口 |
| --- | --- | --- |
{shots}

成功轮敏感扫描159份文本、120份解压正文、148个已知私密值，零命中；失败轮保留各自扫描。[成功扫描](attempt2/sensitive-scan.json)。最终包另外逐文本/gzip扫描；HTTP正文解压SHA与索引一致，commands/database-writes仅归档副本无损gzip，原stage文件未改。[压缩索引](compressed-text-index.json)、evidence-files.json保存字节摘要（不包含自身）。不归档密码、Cookie/CSRF/确认原值、完整收货信息、JAR/class/cache或MySQL数据目录。

## 尚未实施与停机

管理端订单详情尚在STEP11且本轮不改admin，因此“两端HTTP详情快照”本步只完成用户端+SQL，管理端HTTP补验明确留STEP11。支付/取消STEP10、发货STEP11；TST12–19/30/34只记录本步下单/查询/独立礼盒部分，TST16/17/35及所有并发、故障注入留STEP13。未把正常事务和拒绝前零写证明扩张为已完成中途故障回滚。

STEP08的ORDER_SUBMISSION_PENDING已从用户端生产源码和模板移除；历史文档/旧证据保留原事实。两轮进程均已停止；私有目录经绝对路径范围核对后清理见cleanup.json。main、原分支/远端引用及3606份既有证据不变，后续仅在功能分支提交本轮文档和新证据，不push。
'''
(EV/'README.md').write_text(readme,encoding='utf-8',newline='\n')
print(json.dumps(dict(archive=str(EV),files=len([p for p in EV.rglob('*') if p.is_file()]),overall=summary['overall'])))
