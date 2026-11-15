"""Prepare project-document candidates from actual STEP13 summary; no repository writes."""
import pathlib,json,re,hashlib
S=pathlib.Path(__file__).resolve().parent;R=pathlib.Path('D:/Github Projects/CSUCampusCraft')
def run():
    data=json.loads((S/'final-summary.json').read_text(encoding='utf-8-sig'))
    ok=(data['overall']=='PASS' and data['p0_pass']==data['p0_total']==39 and len(data['concurrency'])==8 and len(data['faults'])==5 and all(x['status']=='PASS' for x in data['concurrency']+data['faults']) and all(data[k] for k in ['structure_empty','admin_only_empty','demo_initial_counts','demo85','restart','snapshot','evidence_integrity','sensitive_scan','cleanup','home_filter_badge_supplement']))
    assert ok,'Incomplete evidence cannot mark M3 passed'
    sha=data['source_sha'];e='evidence/2026-11-15-step13';out=S/'candidates';out.mkdir(exist_ok=True)
    result={}
    def save(name,text,original):
        p=out/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8',newline='\n');result[name]={'old_sha256':hashlib.sha256(original).hexdigest(),'new_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
    path=R/'docs/开发计划与任务.md';original=path.read_bytes();text=original.decode('utf-8-sig').replace('\r\n','\n')
    old=text.splitlines()[2]
    new=f'当前状态：STEP01–12 已交付并通过各步自动实测及 2026-11-15 高宇弘本人复核；组员互评未实施，AI 辅助实测。STEP13 已针对干净受测提交 `{sha}` 新跑 39 条 P0 技术验收、8 类真实并发和 5 类触发器故障回滚，完成结构空库、ADMIN-only 空业务库、演示库、重启及交付材料核对，M3 通过。P1（STEP14、TST-36）未选做。既有步骤与本人签署的原事实不改；本轮自动执行不冒充新增真人抽验。详见[STEP13 实测记录](测试与验收用例.md#step13-实测记录)与[新证据]({e}/README.md)。'
    text=text.replace(old,new,1)
    text=text.replace('| M3 | STEP13 | 进行中（STEP13 待执行，P0 全量/并发/故障注入未开始） |','| M3 | STEP13 | 通过（最终 SHA 全 P0 技术验收；2026-11-15 本人复核沿原实际范围；组员互评未实施） |',1)
    text=text.replace('| P1 | STEP14 | 待决定 |','| P1 | STEP14 | 未选做 |',1)
    heading='### STEP13 并发回滚与整体验收\n'
    text=text.replace(heading,heading+f'\n状态：通过。受测 `{sha}`；39/39 个 P0 编号技术范围通过，8/8 并发场景与 5/5 故障回滚完成。干净源码、两端 JAR、199 个运行输入与原始字节索引见[证据入口]({e}/README.md)。本人复核沿既有 2026-11-15 签署范围，本轮为本人授权的 AI 自动实测；TST-32 的另一位真人复现未实施。以下原操作与门槛保留。\n',1)
    ledger=f'| STEP13 | 高宇弘（本人授权、AI 执行自动实测与材料整理）；本人复核沿 2026-11-15 原签署范围，组员互评未实施 | STEP01–12、M1/M2 已通过；干净 main d577179 新建 feat/step13-acceptance | 通过 | 测试提交 `{sha}`，起测工作区干净，199 个运行输入与两端 JAR 起末无漂移；文档与证据另提交，不冒充新的受测源码 | 39 条 P0 技术验收、8 并发、5 回滚、空库与演示复现、重启；[实测](测试与验收用例.md#step13-实测记录)、[新原始证据]({e}/README.md) | P1 未选做；真人组员复现与组员互评未实施；真实支付/物流、REST、性能未验证或未实现，不据本轮扩大范围。 |\n'
    text=text.replace('\n状态只使用未开始、进行中、待复核、通过、失败、未选做。','\n'+ledger+'\n状态只使用未开始、进行中、待复核、通过、失败、未选做。',1)
    save('docs/开发计划与任务.md',text,original)
    path=R/'docs/测试与验收用例.md';original=path.read_bytes();text=original.decode('utf-8-sig').replace('\r\n','\n');old=text.splitlines()[4]
    text=text.replace(old,f'STEP01–12 已交付并通过各步自动实测与 2026-11-15 本人复核（高宇弘；组员互评未实施）。STEP13 已在最终受测 `{sha}` 新跑 39 条 P0 技术验收、8 类并发与 5 类触发器回滚并完成新空库复现、双端重启与归档核对，M3 通过。本轮为本人授权的 AI 自动执行，未新增真人组员复现或签署；TST-32 的技术子项和人员执行边界分别记录。TST-36/P1 未选做。以下旧实测的 SHA、失败和历史状态不改，不用旧结论替代本轮。',1)
    rows=['| 用例 | 最终结果 | 新断言与证据 | 备注 |','| --- | --- | --- | --- |']
    for x in data['matrix']:
        note='AI 新库复现与重启技术子项通过；另一位真人复现未实施。' if x['id']=='TST-32' else f'同 SHA 新独立实例的[首页/联合筛选/失效徽标补验]({e}/home-filter-supplement/attempt1/result.json)一并核对。' if x['id'] in ['TST-02','TST-03','TST-09'] else '按现行契约新跑；不继承旧步骤结果。'
        rows.append(f"| {x['id']} | 通过 | [分组最终矩阵]({e}/p0-matrix.json)逐片段映射至原始结果；原请求和七表索引见对应组。 | {note} |")
    crows=['| 场景 | 同步与结果 | 新证据 |','| --- | --- | --- |']+[f"| {x['name']} | {x['observed']} | [{x['status']}]({e}/{x['evidence']}) |" for x in data['concurrency']]
    drows=['| 注入点 | 七表及回滚结果 | 新证据 |','| --- | --- | --- |']+[f"| {x['name']} | {x['observed']} | [{x['status']}]({e}/{x['evidence']}) |" for x in data['faults']]
    section=f'''### STEP13 实测记录

**结论：39 条 P0 编号的技术验收、8 类真实并发与 5 类触发器回滚通过，M3 完成。** 受测提交 `{sha}`，分支 `feat/step13-acceptance`；从干净 main 创建，不合并、不推送。产品代码、SQL、POM、Wrapper 与共享素材未改；文档/证据在测试后单独提交。新结果来自本 SHA 与新隔离实例，旧证据不改。运行输入 199 个，清单及两端 JAR 的实际 SHA-256 见[版本与制品]({e}/source-and-artifacts.json)。

环境：{data['environment_text']}。真实构建、PID/监听归属、JDBC Hikari UTC、页面北京时间、运行输入与清理记录均在新目录；两端 `clean verify` 均退出 0，不以构建成功替代业务实测。

结构库七表全空，无账号不可登录；单独 ADMIN-only 空业务库五计数全 0。演示库初始七表 4/15/60/100/10/10/20。新真实订单 `{data['demo_order_no']}` 从 HTTP 清种子车、加 2×18.00 + 49.00，确认 85.00 后创建 1 主单/2 明细、库存 10/12→8/11、版本各+1、清车及徽标0，模拟支付、后台发货、U08 联动与重启持久性均核对。下单后改变商品现值，两端仍读成交快照。

'''+'\n'.join(rows)+'\n\nTST-36（P1）未选做；真实支付与物流、REST 未实现。\n\n'+ '\n'.join(crows)+'\n\n'+ '\n'.join(drows)+f'''

并发使用新外部 Java 多线程 CountDownLatch 和独立 JDBC 连接/锁探针，保存实际起止与响应；C3 是并发 HTTP 在既有会话 monitor 处串行，未冒称同时进入两个数据库事务。拒绝分支在串行阶段逐请求证明零写，并发阶段以组级前后及独立目标归因，不伪造每请求隔离快照。故障为隔离库条件触发器 SIGNAL，不是产品开关；每案创建、真实错误、七表回滚、DROP 无残留均保留。自增分配器间隙不属于已提交行回滚承诺。

首页选中卡片售罄、创建时间及排序值并列、无毕业主题与有主题无可售商品、主题+类型+关键词联合分页、含失效条目的跨页 SUM 徽标，另在同一产品 SHA/JAR 的新独立实例补验通过。补充与主轮数据分开存放，不把主轮的种子排序观察扩大为这些边界已验证。

失败与复测：{data['failure_text']}。原始轮次不覆盖，工具错误不记产品缺陷。同一 SHA/JAR 分组验收：顺序/空库/重启/浏览器取 `attempt5` 的已通过片段（其整体仍为 FAIL）；8C/5D 全部取新私有库 `attempt6`，不追认 5 的 C1。父[最终矩阵]({e}/p0-matrix.json)逐片段指回原件；HTTP/SQL/敏感扫描/截图/独立重放及逐文件原始字节核对见[新证据]({e}/README.md)。

执行与复核：本轮由高宇弘授权 Codex AI 执行；2026-11-15 本人已签署的七项抽验保留原范围，不写成本轮真人完成 39 用例或并发注入。组员互评和另一位真人的 TST-32 复现未实施。按本轮授权保留此人员边界，不编造新增签署；P1 未选做。

'''
    marker='## 业务用例\n';assert marker in text;text=text.replace(marker,section+marker,1)
    stale='STEP13 整体验收待执行，未覆盖的并发、竞争、故障注入及最终 SHA 全链路复测留 STEP13，TST-36 为 P1 未选做。'
    current='STEP13 已按本节标准在最终受测 SHA 分组完成 39 条 P0 技术验收，8 类并发与 5 类故障回滚见新增实测记录；原步骤结果与工具失败保留各自身份。TST-36 为 P1 未选做。'
    before,standards=text.split(marker,1);assert standards.count(stale)==1;standards=standards.replace(stale,current,1)
    text=before+marker+standards;save('docs/测试与验收用例.md',text,original)
    path=R/'README.md';original=path.read_bytes();text=original.decode('utf-8-sig').replace('\r\n','\n')
    start=text.index('## 当前阶段\n');end=text.index('\nMySQL 8.4',start)
    text=text[:start]+f'''## 当前阶段

M0–M3 已完成。STEP13 最终受测 `{sha}`（干净源码）在新隔离 MySQL 上按同 SHA/JAR 分组完成 39/39 P0 技术验收、8/8 真实并发与 5/5 触发器回滚；结构空库、ADMIN-only 空业务库、演示库、85 元链路、双端重启及成交快照核对通过。主5原整体工具 FAIL 与新6并发/回滚 PASS 各自保留，父矩阵逐片段溯源。两端根 Wrapper `clean verify` 均退出 0。产品源码未改，文档/证据随后独立提交；提交身份以 Git 历史与交付说明为准。[STEP13 证据](docs/{e}/README.md)、[全 P0 矩阵](docs/{e}/p0-matrix.json)、[实验报告](docs/实验报告.md)、[答辩演示脚本](docs/答辩演示脚本.md)。

STEP01–12 的高宇弘本人复核与原签署保留；STEP13 为本人授权的 AI 自动执行，不新增真人签署，不写成组员互评。TST-32 技术复现已新跑，另一位真人复现未实施。P1 确认收货未选做；真实支付、物流与 REST 未实现，性能未验证。历次失败及修复记录继续保留。[本人抽验与签署](docs/evidence/2026-11-15-review/README.md#本人执行记录2026-11-15)。
'''+text[end:]
    save('README.md',text,original)
    (out/'document-changes.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':run()
