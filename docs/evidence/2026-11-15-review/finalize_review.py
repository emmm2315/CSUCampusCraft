"""Assemble the review from newly executed evidence; does not run or alter product code."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,subprocess,re
R=Path(__file__).resolve().parent; BASE='0329c9810c4ad2719c4ae95190ff516d1d21a9ed'
def read(p):return json.loads((R/p).read_text(encoding='utf-8-sig'))
def write(p,obj):(R/p).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def git(*args):
 p=subprocess.run(['git',*args],capture_output=True,encoding='utf-8',errors='replace'); return {'args':list(args),'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
stages={p.stem[6:]:read(p.name) for p in R.glob('stage-*.json')}
http=[json.loads(x) for x in (R/'http.jsonl').read_text(encoding='utf-8').splitlines()]
checks=[json.loads(x) for x in (R/'checks.jsonl').read_text(encoding='utf-8').splitlines()]
product_paths=['csucampuscraft-user/src','csucampuscraft-admin/src','csucampuscraft-user/pom.xml','csucampuscraft-admin/pom.xml','database','assets','.mvn','mvnw','mvnw.cmd']
delivery={'tested_sha':BASE,'branch':git('branch','--show-current'),'head_before_review_commit':git('rev-parse','HEAD'),'product_unchanged':git('diff','--exit-code',BASE,'--',*product_paths),'old_docs_unchanged':git('diff','--exit-code',BASE,'--','README.md','docs',':(exclude)docs/evidence/2026-11-15-review'),'allowed_changed_paths':git('status','--short')}
tracked=subprocess.run(['git','ls-files','-z'],capture_output=True).stdout.decode().split('\0')
runtime=[p for p in tracked if p and (p.startswith(('csucampuscraft-user/src/','csucampuscraft-admin/src/','database/','assets/','.mvn/')) or p in ['mvnw','mvnw.cmd','csucampuscraft-user/pom.xml','csucampuscraft-admin/pom.xml'])]
(R/'runtime-inputs.sha256').write_text(''.join(hashlib.sha256(Path(p).read_bytes()).hexdigest()+'  '+p+'\n' for p in sorted(runtime)),encoding='utf-8',newline='')
delivery['runtime_file_count']=len(runtime)
write('delivery-checks.json',delivery)
steps=[
 ('STEP01','INIT-01–05技术子项','PASS','environment.md；stage-persistence.json','clean verify、双脚本/35CHECK、同库主题、重启七表/订单/两账号车、共享图字节。种子故障回滚未跑。'),
 ('STEP02','TST-04/05/31基础子项','PASS','stage-A.json；stage-B.json','登录密码正反、CSRF/状态码、共享资源与文本转义抽查；组件/错误探针未穷举。'),
 ('STEP03','TST-01–04/33','PASS','stage-B.json；stage-supplement.json','首页排序、主题类型/排序分页、命中及空搜索、详情相册、草稿/售罄、游客文案。'),
 ('STEP04','TST-05–07/18/31/39身份','PASS','stage-A.json；stage-final-checks.json','双Cookie、退出隔离、Auth先CSRF、双端禁用/1微秒/1秒戳、错角色、他人车403/订单404。内部确认删除时点未直接观测。'),
 ('STEP05','TST-25–28顺序子项','PASS','stage-E.json；stage-C.json','分类增改删引用、商品资料/上下架、增量补货、旧表单409；并发与故障未跑。'),
 ('STEP06','TST-04/40顺序子项','存疑','stage-E.json；stage-supplement.json','增改删/父版本/跨父/末图回封面通过；缺版本实测409，TST-40文字标准400，该子项按标准FAIL。原排序工具FAIL补证通过，原记录不改。'),
 ('STEP07','TST-08–11/17车子项','PASS','stage-B.json；stage-persistence.json','加改删/同SKU合并、99/20边界、失效全行SUM徽标、版本409、持久性；失效改量409文档缺项。'),
 ('STEP08','TST-11–13','PASS','stage-C.json','85确认无DB写、令牌替换/车价变409、字段400保留、短PT2S实例实等3秒过期409；未实等默认10分钟。'),
 ('STEP09','TST-12–19/30核心','PASS','stage-C.json；stage-supplement.json','新85单1+2明细、10/12→8/11、version+1、清车/徽标0/303、顺序重放一次、篡改金额身份无效、历史快照。'),
 ('STEP10','TST-18–22/34部分','PASS','stage-D.json','失败NULL三字段、成功MOCK首次凭证/时间、重放不改；两明细取消返库一次/保留下架/不回填车；U09拒绝分支。'),
 ('STEP11','TST-19/22/29/30','PASS','stage-E.json；stage-F.json','新单CI完整号/状态/userId过滤、首次发货/重复/非法409、双端快照/北京时间。'),
 ('STEP12','TST-37–39主库子项','PASS','stage-E.json；stage-final-checks.json','五统计/卡片与SQL、仅CUSTOMER、启停幂等/单调戳/旧会话失效、正常重登。空库/错误配置未重跑。'),
]
issues=[
 {'id':'REV-01','severity':'P1','category':'验收身份条件','phenomenon':'本轮实际操作者为Codex AI；真人本人独立执行/真实姓名签署条件尚未完成，组员互评未实施。','reproduce':'查看本轮执行声明与所有脚本/工具记录；没有真人签署记录。','evidence':'checklist.md；review.json','recommendation':'本人按清单人工抽验并实名签署；不要将本轮写成组员或真人已复核通过。'},
 {'id':'REV-02','severity':'P2','category':'契约差异','phenomenon':'A10缺失productVersion实测409 PRODUCT_IMAGE_VERSION_REQUIRED；TST-40标准写400。按该文字标准此子项FAIL，STEP06存疑。','reproduce':'ADMIN登录，POST /products/61/images，仅提交合法imagePath、sortOrder及CSRF，省略productVersion。','evidence':'http.jsonl 原E缺版本请求；doc-audit/audit.json；stage-E.json','recommendation':'后续统一产品与用例/文档决定；本轮不改实现或标准。'},
 {'id':'REV-03','severity':'P2','category':'文档缺项','phenomenon':'有有效版本的失效商品实际改量返回409；需求“改量”行未明列该原因。','reproduce':'B把车商品设DRAFT，提交新数量与有效条目版本，409且七表零写。','evidence':'http.jsonl B invalid product quantity actual 409；doc-audit/summary.md','recommendation':'文档补齐失效改量及同值幂等条件。'},
 {'id':'REV-04','severity':'P2','category':'措辞观察（非功能失败）','phenomenon':'游客U03真实链接“登录后加购”，提示回本页由本人确认；规格未规定该链接精确标签。','reproduce':'游客GET /products/1（上架有货夹具）；检查data-login-to-add。','evidence':'http/0098-B.html；screenshots/03-U03-guest-login.jpg','recommendation':'后续交互文案统一/记录；流程符合先登录再手动加购。'},
 {'id':'REV-05','severity':'P2','category':'文档过时','phenomenon':'README当前阶段已写M2，后文仍写购物车/订单后续版本、下一步STEP08；测试导语仍称TST39待实施；首页路由当前行为句过时。','reproduce':'读取当前README第100/130行、测试文档业务用例导语和首页路由行。','evidence':'doc-audit/audit.json；doc-audit/summary.md','recommendation':'STEP13前更新当前说明，保留历史实测原文身份。'},
 {'id':'REV-06','severity':'P2','category':'指导书待更新','phenomenon':'Word仍称M0已完成、M1尚未开工/仅主题初始化，与当前实现不符。','reproduce':'只读解包Word document.xml读取前言；SHA前后相同。','evidence':'doc-audit/audit.json word；doc-audit/summary.md','recommendation':'本人复核后更新Word，本轮保持不动。'},
 {'id':'REV-07','severity':'P2','category':'新证据摘要索引工具缺陷','phenomenon':'402条含失败轮HTTP中226条body_sha256是写盘前文本摘要，Windows换行后不等于归档原始字节；176条直接相等。','reproduce':'运行integrity/capture_bytes.py并比较原索引和原文件字节。','evidence':'capture-byte-audit-final.json；quality-final.json','recommendation':'使用新增raw_file_sha256补偿索引校验所有原文件；原正文/索引不改。后续工具直接哈希写盘字节。'},
 {'id':'REV-08','severity':'P2','category':'覆盖边界','phenomenon':'STEP02–11受测SHA到当前基线产品diff非空，是后续业务实现；只有最新STEP12到基线为空，不能称历史所有步骤源码此后未变。','reproduce':'integrity/verify_integrity.py重算各步清单与受测blob，再git diff各SHA..基线 --产品路径。','evidence':'evidence-integrity.json；integrity/stage-G-summary.md','recommendation':'STEP13对最终SHA整体验收，不能以旧记录结论替代。'},
]
unverified=[
 '并发/竞争：TST-17、24、28并发、35末件、并发启停/相册/发货及锁等待交错。顺序重放不等于并发证明。',
 '故障注入：TST-16/23、种子提交前故障、部分写入/连接失败回滚；本轮无此类注入。',
 'P1/TST-36确认收货未选做；REST仅预留；真实支付/退款/物流不在项目范围。',
 '性能、压力、全量安全攻击、完整可访问性/浏览器矩阵、1366×768和1920×1080双视口全量回归未做。截图实际尺寸见screenshots/index.json。',
 'TST-37空业务库控制台与自然错误配置页面本轮未重跑（结构库DDL/CHECK已跑，不能替代页面）。',
 '默认PT10M未实等10分钟，过期机制通过同一JAR独立PT2S实例实等3秒验证。',
 'Tomcat内部确认属性删除的具体时点未直接读会话；仅观察禁用旧POST302、旧身份不复活、重登旧确认409，并结合当前源码。',
 '未穷举TST-01–40所有边界：%/_/!正向字面搜索、金额上溢、双礼盒数量2的独立链、全部字段长度/路径边界、错误探针全部方法等；不得把核心抽查扩大为整条用例全验。',
 'TST-32技术持久性子项已新跑，但“另一位真人组员复现”及本人实名签字尚未完成。',
]
review={'date':'2026-11-15','timezone':'Asia/Shanghai','tested_sha':BASE,'branch':'feat/review-2026-11-15','overall':'存疑','interpretation':'AI执行的核心顺序交叉检查已完成；STEP06文字契约不一致，真人独立复核/签署未完成，不替代STEP13。','executor':'Codex (AI)','reviewer':'本人（真实姓名待填）','reviewer_statement_to_be_signed':'组员互评因时间未实施，由本人执行复核','statement_status':'待本人真实执行/签署；不得将AI操作冒充本人或组员已通过','main_http_records':len(http),'main_assertions':len(checks),'raw_assertion_failures':[x for x in checks if not x['passed']],'raw_E_failure_corrected_by_separate_supplement':True,'steps':[{'step':a,'cases':b,'result':c,'evidence':d,'notes':e} for a,b,c,d,e in steps],'issues':issues,'unverified':unverified,'stages':stages,'evidence_caveats':['原attempt1工具失败保留；E原始FAIL保留。','C最初小结“改封面”过强：C提交原路径未变；独立supplement真实更换合法缺图封面路径后完成快照证明。','原body_sha256不是所有归档文件字节摘要，以capture-byte-audit-final.json的raw_file_sha256为准。','截图06只含脚本声明的虚构收货输入且未遮盖；不称全部截图收货字段已脱敏。'],'completed_at_utc':datetime.now(timezone.utc).isoformat()}
write('review.json',review)
lines=['# 2026-11-15 STEP01–12 交叉复核','', '**总体：存疑；已完成本轮 AI 辅助的核心顺序检查，尚不构成真人独立复核通过或 STEP13 整体验收。** 新跑基线 `'+BASE+'`，分支 `feat/review-2026-11-15`。产品代码、旧文档/证据、台账、Word、seed SQL均未改；只新增本目录和一条 `.gitattributes -text` 规则。本地提交，不 push、不合并。','', '执行者：Codex（AI）。复核人：**本人（真实姓名待填）**。用户拟签声明：**“组员互评因时间未实施，由本人执行复核”**；该声明待本人真实执行/签署。本轮不得写成“组员已复核通过”或“真人已独立操作”。','', '## 每步结论（仅已执行核心子项）','', '| 步骤 | 核心用例 | 结果 | 新证据 | 复现命令 | 备注 |','|---|---|---|---|---|---|']
for a,b,c,d,e in steps:
 cmd='见commands-environment.md' if a=='STEP01' else 'run_review.py（A–F）；补充见commands.md'
 lines.append('| '+a+' | '+b+' | '+c+' | '+d+' | '+cmd+' | '+e+' |')
lines+=['','P0：TST-01–35、37–40；P1：TST-36。映射和各步留STEP13部分见[checklist.md](checklist.md)。PASS仅限本轮已执行子项，缺参版本子项按现有标准FAIL，不以改标准消除差异。','', '## 新跑结果与证据入口','', f'- 正式主流程 **{len(http)} 条HTTP、{len(checks)} 条检查断言**；原始断言1项FAIL为A10重复标记工具误报，独立补充已说明并重跑通过。断言数量不是TST用例数量。', '- A/B/C/D/F、supplement、persistence、final-checks 的结构化阶段均PASS；E原始FAIL保留，不能改写成一次无失败执行。首次attempt1在身份阶段因外部工具错误中断，旧轮38条请求完整保留，不继承其通过项。','- 新85元订单：`'+read('run-state-public.json')['paid_order']+'`（最终SHIPPED）；独立取消单：`'+read('run-state-public.json')['cancelled_order']+'`（CANCELLED）。各1主单+2明细，金额85，库存/返库/版本/清车/重放见[db-checks.md](db-checks.md)。','- [http.jsonl](http.jsonl)保存逐POST七表完整有序行摘要；[sql.jsonl](sql.jsonl)保存SQL及安全字段结果；[checks.jsonl](checks.jsonl)保存真实断言；阶段结束先写小结后进入下一阶段。','- 两端clean verify输出 `BUILD SUCCESS` / `No tests to run.`，不以构建成功代替HTTP/SQL业务正确。进程/端口/JDBC真实UTC和页面北京时间动态对照见[environment.md](environment.md)、stage-F、environment/。','- 8张原始关键截图见[screenshots/index.json](screenshots/index.json)，已目视检查。实际捕获宽度748/763/1264，未冒称指定双桌面视口全验。截图06包含明确虚构收货字段；其他抓取文本未记录收货/联系原值。','', '## 问题清单','', '| 编号/严重度 | 现象 | 复现 | 证据 | 建议 |','|---|---|---|---|---|']
for x in issues: lines.append('| '+x['id']+' / '+x['severity']+' | '+x['phenomenon']+' | '+x['reproduce']+' | '+x['evidence']+' | '+x['recommendation']+' |')
lines+=['','未观察到本轮已执行范围的P0产品缺陷；这不证明未验证范围安全。REV-01是人工验收身份门槛，其他注明为契约/文档/证据工具或覆盖事项。','', '## 原失败、工具问题与独立补证','', '- 首轮attempt1：双端Cookie容器错误共用一个CSRF缓存导致用户退出403，随后预期状态码被当data参数触发TypeError，退出1；保留attempt1代码、响应、checks及error。修正新工具后从A完整重跑。','- E排序：原选择器把每张图article和两个form都计入data-image-id，得到每ID三次，原FAIL保留。supplement用article行与独立SQL新跑且复读原归档图行均一致。','- 捕获字节：402条含失败轮记录，176 raw摘要直接匹配、226存在换行转换。原文件/索引不改，新增[capture-byte-audit-final.json](capture-byte-audit-final.json)给全部实际raw SHA，逐条可精确对应；不能再称原body_sha256全为归档字节摘要。','- C封面陈述：C最初提交的是相同placeholder路径，该阶段小结“改封面”过强；独立supplement实际换成`images/review-missing-cover.svg`，两表整行及双端旧图片src保持快照。合法缺图路径是新夹具，不改素材文件。','- 汇总SQL工具曾用保留字LINES作为别名，1064退出1，尚未生成报告；原脚本及失败摘要在tools-failures/。改别名line_count后新查询成功，未改产品或旧证据。','- 环境初次PowerShell解析、MySQL沙箱权限、inspect.py命名冲突、reference路径守卫误拒绝及完整性诊断脚本错误均保留，细节见environment.md/integrity/。不把这些工具错误记为产品缺陷。','', '## 证据身份与完整性','', '- 历史13目录、4764归档文件的大小/SHA与-text新重算全部匹配；37运行清单/4461条目可从受测Git blob仅重建对应行尾精确匹配。原始Git严格字节、行尾重建、当前工作区差异分开记录。[evidence-integrity.json](evidence-integrity.json)。','- 旧步骤到当前HEAD有后续业务实现变化，最新STEP12→本轮基线产品diff为空。不能声称每步历史源码此后全部未改；本轮重新执行是当前结果依据。','- 当前199运行输入及双JAR无漂移，产品/旧README+docs/Word/旧证据相对基线差异为空，见[quality-final.json](quality-final.json)、[delivery-checks.json](delivery-checks.json)。本轮新增资料最终字节清单见artifacts.sha256（不含自身）。','', '## 未验证范围','']
lines+=['- '+x for x in unverified]
lines+=['','## 环境与复现','', 'Windows 11 / China Standard Time(UTC+08:00)；Microsoft JDK21.0.12.1、根Wrapper Maven3.9.16、MySQL8.4.9/InnoDB。全新datadir/UUID/59315，禁止开发库。用户8080、管理8081；JDBC+00:00，订单显示Asia/Shanghai。完整初始/重启PID、版本输出、启动/停止状态见[environment.md](environment.md)。','', '复现必须先重建新的隔离实例并导入原SQL，配置一个临时connection JSON（字段见common.py与环境脚本，不提交口令）。根运行 `python -X utf8 docs/evidence/2026-11-15-review/run_review.py <临时connection.json>`；A–D结束等待输入，确认小结后Enter执行E/F。脚本不是幂等重置工具，不得在开发库或本轮已变数据库直接重放85元起点断言。补充脚本/重启配合顺序见[commands.md](commands.md)。','', '本轮成果供STEP13最终SHA整验与Word更新使用；不改原台账结论，不替本人签字。','']
(R/'README.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps({'http':len(http),'assertions':len(checks),'raw_failures':len([x for x in checks if not x['passed']]),'runtime':len(runtime),'product_diff_exit':delivery['product_unchanged']['exit'],'old_docs_diff_exit':delivery['old_docs_unchanged']['exit']},ensure_ascii=False))
