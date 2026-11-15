# 2026-11-15 STEP01–12 交叉复核

**总体：存疑；已完成本轮 AI 辅助的核心顺序检查，尚不构成真人独立复核通过或 STEP13 整体验收。** 新跑基线 `0329c9810c4ad2719c4ae95190ff516d1d21a9ed`，分支 `feat/review-2026-11-15`。产品代码、旧文档/证据、台账、Word、seed SQL均未改；只新增本目录和一条 `.gitattributes -text` 规则。本地提交，不 push、不合并。

执行者：Codex（AI）。复核人：**本人（真实姓名待填）**。用户拟签声明：**“组员互评因时间未实施，由本人执行复核”**；该声明待本人真实执行/签署。本轮不得写成“组员已复核通过”或“真人已独立操作”。

## 每步结论（仅已执行核心子项）

| 步骤 | 核心用例 | 结果 | 新证据 | 复现命令 | 备注 |
|---|---|---|---|---|---|
| STEP01 | INIT-01–05技术子项 | PASS | environment.md；stage-persistence.json | 见commands-environment.md | clean verify、双脚本/35CHECK、同库主题、重启七表/订单/两账号车、共享图字节。种子故障回滚未跑。 |
| STEP02 | TST-04/05/31基础子项 | PASS | stage-A.json；stage-B.json | run_review.py（A–F）；补充见commands.md | 登录密码正反、CSRF/状态码、共享资源与文本转义抽查；组件/错误探针未穷举。 |
| STEP03 | TST-01–04/33 | PASS | stage-B.json；stage-supplement.json | run_review.py（A–F）；补充见commands.md | 首页排序、主题类型/排序分页、命中及空搜索、详情相册、草稿/售罄、游客文案。 |
| STEP04 | TST-05–07/18/31/39身份 | PASS | stage-A.json；stage-final-checks.json | run_review.py（A–F）；补充见commands.md | 双Cookie、退出隔离、Auth先CSRF、双端禁用/1微秒/1秒戳、错角色、他人车403/订单404。内部确认删除时点未直接观测。 |
| STEP05 | TST-25–28顺序子项 | PASS | stage-E.json；stage-C.json | run_review.py（A–F）；补充见commands.md | 分类增改删引用、商品资料/上下架、增量补货、旧表单409；并发与故障未跑。 |
| STEP06 | TST-04/40顺序子项 | 存疑 | stage-E.json；stage-supplement.json | run_review.py（A–F）；补充见commands.md | 增改删/父版本/跨父/末图回封面通过；缺版本实测409，TST-40文字标准400，该子项按标准FAIL。原排序工具FAIL补证通过，原记录不改。 |
| STEP07 | TST-08–11/17车子项 | PASS | stage-B.json；stage-persistence.json | run_review.py（A–F）；补充见commands.md | 加改删/同SKU合并、99/20边界、失效全行SUM徽标、版本409、持久性；失效改量409文档缺项。 |
| STEP08 | TST-11–13 | PASS | stage-C.json | run_review.py（A–F）；补充见commands.md | 85确认无DB写、令牌替换/车价变409、字段400保留、短PT2S实例实等3秒过期409；未实等默认10分钟。 |
| STEP09 | TST-12–19/30核心 | PASS | stage-C.json；stage-supplement.json | run_review.py（A–F）；补充见commands.md | 新85单1+2明细、10/12→8/11、version+1、清车/徽标0/303、顺序重放一次、篡改金额身份无效、历史快照。 |
| STEP10 | TST-18–22/34部分 | PASS | stage-D.json | run_review.py（A–F）；补充见commands.md | 失败NULL三字段、成功MOCK首次凭证/时间、重放不改；两明细取消返库一次/保留下架/不回填车；U09拒绝分支。 |
| STEP11 | TST-19/22/29/30 | PASS | stage-E.json；stage-F.json | run_review.py（A–F）；补充见commands.md | 新单CI完整号/状态/userId过滤、首次发货/重复/非法409、双端快照/北京时间。 |
| STEP12 | TST-37–39主库子项 | PASS | stage-E.json；stage-final-checks.json | run_review.py（A–F）；补充见commands.md | 五统计/卡片与SQL、仅CUSTOMER、启停幂等/单调戳/旧会话失效、正常重登。空库/错误配置未重跑。 |

P0：TST-01–35、37–40；P1：TST-36。映射和各步留STEP13部分见[checklist.md](checklist.md)。PASS仅限本轮已执行子项，缺参版本子项按现有标准FAIL，不以改标准消除差异。

## 新跑结果与证据入口

- 正式主流程 **364 条HTTP、996 条检查断言**；原始断言1项FAIL为A10重复标记工具误报，独立补充已说明并重跑通过。断言数量不是TST用例数量。
- A/B/C/D/F、supplement、persistence、final-checks 的结构化阶段均PASS；E原始FAIL保留，不能改写成一次无失败执行。首次attempt1在身份阶段因外部工具错误中断，旧轮38条请求完整保留，不继承其通过项。
- 新85元订单：`CSU-7df1c3e8521677d7043e92066497667f`（最终SHIPPED）；独立取消单：`CSU-6a124d4369e78aa809a309373a609d09`（CANCELLED）。各1主单+2明细，金额85，库存/返库/版本/清车/重放见[db-checks.md](db-checks.md)。
- [http.jsonl](http.jsonl)保存逐POST七表完整有序行摘要；[sql.jsonl](sql.jsonl)保存SQL及安全字段结果；[checks.jsonl](checks.jsonl)保存真实断言；阶段结束先写小结后进入下一阶段。
- 两端clean verify输出 `BUILD SUCCESS` / `No tests to run.`，不以构建成功代替HTTP/SQL业务正确。进程/端口/JDBC真实UTC和页面北京时间动态对照见[environment.md](environment.md)、stage-F、environment/。
- 8张原始关键截图见[screenshots/index.json](screenshots/index.json)，已目视检查。实际捕获宽度748/763/1264，未冒称指定双桌面视口全验。截图06包含明确虚构收货字段；其他抓取文本未记录收货/联系原值。

## 问题清单

| 编号/严重度 | 现象 | 复现 | 证据 | 建议 |
|---|---|---|---|---|
| REV-01 / P1 | 本轮实际操作者为Codex AI；真人本人独立执行/真实姓名签署条件尚未完成，组员互评未实施。 | 查看本轮执行声明与所有脚本/工具记录；没有真人签署记录。 | checklist.md；review.json | 本人按清单人工抽验并实名签署；不要将本轮写成组员或真人已复核通过。 |
| REV-02 / P2 | A10缺失productVersion实测409 PRODUCT_IMAGE_VERSION_REQUIRED；TST-40标准写400。按该文字标准此子项FAIL，STEP06存疑。 | ADMIN登录，POST /products/61/images，仅提交合法imagePath、sortOrder及CSRF，省略productVersion。 | http.jsonl 原E缺版本请求；doc-audit/audit.json；stage-E.json | 后续统一产品与用例/文档决定；本轮不改实现或标准。 |
| REV-03 / P2 | 有有效版本的失效商品实际改量返回409；需求“改量”行未明列该原因。 | B把车商品设DRAFT，提交新数量与有效条目版本，409且七表零写。 | http.jsonl B invalid product quantity actual 409；doc-audit/summary.md | 文档补齐失效改量及同值幂等条件。 |
| REV-04 / P2 | 游客U03真实链接“登录后加购”，提示回本页由本人确认；规格未规定该链接精确标签。 | 游客GET /products/1（上架有货夹具）；检查data-login-to-add。 | http/0098-B.html；screenshots/03-U03-guest-login.jpg | 后续交互文案统一/记录；流程符合先登录再手动加购。 |
| REV-05 / P2 | README当前阶段已写M2，后文仍写购物车/订单后续版本、下一步STEP08；测试导语仍称TST39待实施；首页路由当前行为句过时。 | 读取当前README第100/130行、测试文档业务用例导语和首页路由行。 | doc-audit/audit.json；doc-audit/summary.md | STEP13前更新当前说明，保留历史实测原文身份。 |
| REV-06 / P2 | Word仍称M0已完成、M1尚未开工/仅主题初始化，与当前实现不符。 | 只读解包Word document.xml读取前言；SHA前后相同。 | doc-audit/audit.json word；doc-audit/summary.md | 本人复核后更新Word，本轮保持不动。 |
| REV-07 / P2 | 402条含失败轮HTTP中226条body_sha256是写盘前文本摘要，Windows换行后不等于归档原始字节；176条直接相等。 | 运行integrity/capture_bytes.py并比较原索引和原文件字节。 | capture-byte-audit-final.json；quality-final.json | 使用新增raw_file_sha256补偿索引校验所有原文件；原正文/索引不改。后续工具直接哈希写盘字节。 |
| REV-08 / P2 | STEP02–11受测SHA到当前基线产品diff非空，是后续业务实现；只有最新STEP12到基线为空，不能称历史所有步骤源码此后未变。 | integrity/verify_integrity.py重算各步清单与受测blob，再git diff各SHA..基线 --产品路径。 | evidence-integrity.json；integrity/stage-G-summary.md | STEP13对最终SHA整体验收，不能以旧记录结论替代。 |

未观察到本轮已执行范围的P0产品缺陷；这不证明未验证范围安全。REV-01是人工验收身份门槛，其他注明为契约/文档/证据工具或覆盖事项。

## 原失败、工具问题与独立补证

- 首轮attempt1：双端Cookie容器错误共用一个CSRF缓存导致用户退出403，随后预期状态码被当data参数触发TypeError，退出1；保留attempt1代码、响应、checks及error。修正新工具后从A完整重跑。
- E排序：原选择器把每张图article和两个form都计入data-image-id，得到每ID三次，原FAIL保留。supplement用article行与独立SQL新跑且复读原归档图行均一致。
- 捕获字节：402条含失败轮记录，176 raw摘要直接匹配、226存在换行转换。原文件/索引不改，新增[capture-byte-audit-final.json](capture-byte-audit-final.json)给全部实际raw SHA，逐条可精确对应；不能再称原body_sha256全为归档字节摘要。
- C封面陈述：C最初提交的是相同placeholder路径，该阶段小结“改封面”过强；独立supplement实际换成`images/review-missing-cover.svg`，两表整行及双端旧图片src保持快照。合法缺图路径是新夹具，不改素材文件。
- 汇总SQL工具曾用保留字LINES作为别名，1064退出1，尚未生成报告；原脚本及失败摘要在tools-failures/。改别名line_count后新查询成功，未改产品或旧证据。
- 环境初次PowerShell解析、MySQL沙箱权限、inspect.py命名冲突、reference路径守卫误拒绝及完整性诊断脚本错误均保留，细节见environment.md/integrity/。不把这些工具错误记为产品缺陷。

## 证据身份与完整性

- 历史13目录、4764归档文件的大小/SHA与-text新重算全部匹配；37运行清单/4461条目可从受测Git blob仅重建对应行尾精确匹配。原始Git严格字节、行尾重建、当前工作区差异分开记录。[evidence-integrity.json](evidence-integrity.json)。
- 旧步骤到当前HEAD有后续业务实现变化，最新STEP12→本轮基线产品diff为空。不能声称每步历史源码此后全部未改；本轮重新执行是当前结果依据。
- 当前199运行输入及双JAR无漂移，产品/旧README+docs/Word/旧证据相对基线差异为空，见[quality-final.json](quality-final.json)、[delivery-checks.json](delivery-checks.json)。本轮新增资料最终字节清单见artifacts.sha256（不含自身）。

## 未验证范围

- 并发/竞争：TST-17、24、28并发、35末件、并发启停/相册/发货及锁等待交错。顺序重放不等于并发证明。
- 故障注入：TST-16/23、种子提交前故障、部分写入/连接失败回滚；本轮无此类注入。
- P1/TST-36确认收货未选做；REST仅预留；真实支付/退款/物流不在项目范围。
- 性能、压力、全量安全攻击、完整可访问性/浏览器矩阵、1366×768和1920×1080双视口全量回归未做。截图实际尺寸见screenshots/index.json。
- TST-37空业务库控制台与自然错误配置页面本轮未重跑（结构库DDL/CHECK已跑，不能替代页面）。
- 默认PT10M未实等10分钟，过期机制通过同一JAR独立PT2S实例实等3秒验证。
- Tomcat内部确认属性删除的具体时点未直接读会话；仅观察禁用旧POST302、旧身份不复活、重登旧确认409，并结合当前源码。
- 未穷举TST-01–40所有边界：%/_/!正向字面搜索、金额上溢、双礼盒数量2的独立链、全部字段长度/路径边界、错误探针全部方法等；不得把核心抽查扩大为整条用例全验。
- TST-32技术持久性子项已新跑，但“另一位真人组员复现”及本人实名签字尚未完成。

## 环境与复现

Windows 11 / China Standard Time(UTC+08:00)；Microsoft JDK21.0.12.1、根Wrapper Maven3.9.16、MySQL8.4.9/InnoDB。全新datadir/UUID/59315，禁止开发库。用户8080、管理8081；JDBC+00:00，订单显示Asia/Shanghai。完整初始/重启PID、版本输出、启动/停止状态见[environment.md](environment.md)。

复现必须先重建新的隔离实例并导入原SQL，配置一个临时connection JSON（字段见common.py与环境脚本，不提交口令）。根运行 `python -X utf8 docs/evidence/2026-11-15-review/run_review.py <临时connection.json>`；A–D结束等待输入，确认小结后Enter执行E/F。脚本不是幂等重置工具，不得在开发库或本轮已变数据库直接重放85元起点断言。补充脚本/重启配合顺序见[commands.md](commands.md)。

本轮成果供STEP13最终SHA整验与Word更新使用；不改原台账结论，不替本人签字。


## 处理结果（2026-11-15 文档收口）

本节是从复核提交 `a4dc041` 创建 `fix/review-closeout` 后追加的处理说明；上方原结论、原问题表、原失败与未验证范围按复核当时事实保留。此次仅统一现行文档，不重跑业务、不把原 FAIL/存疑改写成新的实测通过，不改台账、不替本人签字、不改 Word。

| 问题 | 本次处理 | 对应文档 / 后续范围 |
|---|---|---|
| REV-01 | 未处理；本人抽验与真实姓名签署待完成。 | 不修改原声明及台账；由本人实际抽验签署后另轮处理。 |
| REV-02 | 文档口径已统一：缺失/空白/旧 `productVersion` 返回 409 并提示重新载入；非整数/负数/溢出版本返回 400。原 STEP06 标准差异及本轮复核当时的 FAIL/存疑保留。 | [TST-40 现行标准](../../测试与验收用例.md#管理端补充功能)、[A10 路由/SSR/事务](../../系统设计与路由.md#管理端路由)、[BR-17](../../需求与业务规则.md#br-17-相册资源归属与版本)、[A10 页面反馈](../../页面清单与原型.md#管理端页面)。产品代码未改。 |
| REV-03 | 补齐实际改量不可购/库存不足 409 且保留车；有效版本相同数量幂等成功不写库，失效行同样适用。仅原数量超库存的行可改至库存内数量。 | [需求改量/移除](../../需求与业务规则.md#加购改量与移除)、[SSR 改量/移除](../../系统设计与路由.md#ssr-表单与结果契约)。 |
| REV-04 | 明确游客有货详情的“登录后加购”链接、登录后自行加购及无游客 POST 加购表单。售罄仍按原规格禁用购买。 | [U03 页面及操作反馈](../../页面清单与原型.md#用户端页面)。 |
| REV-05 | 更新当前阶段、构建运行后的根页行为及测试导语：STEP01–12 已交付，当前复核收口与 STEP13 准备，最终整体验收待执行；用户端 U01 目录首页 / 管理端 A02 控制台。 | [仓库 README](../../../README.md#当前阶段)、[测试导语](../../测试与验收用例.md#业务用例)、[首页路由](../../系统设计与路由.md#用户端路由)、[页面清单](../../页面清单与原型.md)。历史实测原文身份保留。 |
| REV-06 | 未处理；Word 更新延期。 | 本人抽验签署后，由下一轮单独更新 Word；此次不修改 Word 或台账。 |
| REV-07 | 归档原始字节以对应补偿索引的 `raw_file_sha256` 为准，写盘前 `body_sha256` 仅保留原身份。旧正文、HTTP 索引、失败记录及补偿索引均不改。 | [实际字节摘要](capture-byte-audit-final.json)；规则已加入[STEP13 发布门槛](../../测试与验收用例.md#结果记录与发布门槛)。 |
| REV-08 | 历史步骤后续源码演进不抹去；最终整体验收必须按 STEP13 最终受测 SHA 执行，不由旧步骤结果推定通过。 | [STEP13 门槛与步骤对照](../../测试与验收用例.md#结果记录与发布门槛)。本轮未执行 STEP13 并发或故障注入。 |

此次 README 追加是本轮明确授权的文档说明例外，追加前的原字节前缀保持不变。旧 `artifacts.sha256` 仍对应 `a4dc041` 的归档版本；核对其中 README 条目时使用该提交的 Git blob（或当前文件中同长度的原始前缀），不为本次追加重写旧清单。其他旧证据与 `review.json` 原样保留。本次修改范围、历史段保留与搜索校验见[收口说明](closeout/README.md)和[验证结果](closeout/validation.json)。


## 本人执行记录（2026-11-15）

- 执行人：**高宇弘**；执行日期：**2026-11-15**。本人已在本会话逐步反馈并明确确认真实姓名、日期及“本次抽验无异常”，授权按以下分工整理执行与签署记录。
- 环境：Windows 11；固定 Microsoft JDK21.0.12.1、根 Maven Wrapper3.9.16、MySQL8.4.9；用户端8080、管理端8081；新隔离MySQL端口50070，数据库 `csucampuscraft_personal_20261115`，UUID `9e69ebaa-e090-11f1-96eb-005056c00001`。两端JAR的当前源码/199输入与SHA一致，按明确允许复用，未重复构建。详见[个人抽验环境](closeout/个人抽验环境.md)。
- 抽验范围：85元下单→支付→后台发货→U08联动；禁用与重启用后的旧会话失效、重新登录；CSRF/他人订单越权；A02五项计数；A10缺失 `productVersion` 返回409。
- 操作分工：**第1–5、7步由高宇弘本人操作和观察；第6步由AI执行curl演示，高宇弘本人观察输出并确认。** 隔离环境、2件方格本+1件礼盒的85元SQL车夹具及A02 SQL计数由AI准备/查询，不写成本人手工加购或手工SQL操作。

| 步骤 | 本人确认的结果 | 操作与证据身份 |
|---|---|---|
| 1 | PASS：结算页2种3件、85.00。 | 本人打开并观察；车来源为AI SQL夹具。 |
| 2 | PASS：进入订单详情、待支付、85.00、2条明细。 | 本人提交；用户确认已跳转，未单独报告Network303观测。 |
| 3 | PASS：页面待发货、MOCK、CSUPAY-凭证、首次支付时间已显示。 | 本人操作模拟支付并观察；PAID实际标签“待发货”，不硬记作页面显示“已支付”。 |
| 4 | PASS：管理端已发货及首次发货时间；用户端刷新亦已发货；A02待发货数减少1。 | 本人查单、发货和双端刷新；本人未提供具体时间原值或发货前五项绝对数。 |
| 5 | PASS：禁用后旧标签需登录；重新启用后旧标签仍需登录；重新登录新订单仍在、车为空。 | 本人操作启停与旧/新会话。空车为85元下单清车后的正常状态。 |
| 6 | PASS：本人已观察确认302／403／404。 | AI curl演示，匿名管理根302、公开登录POST缺CSRF403、bob已登录访问alice单404；[实际HTTP记录](closeout/personal-check/step6-security-demo-attempt2.json)。不写成本人亲自执行curl。 |
| 7 | PASS：本人提交A10请求得到409与重新载入提示；A02五项54／6／2／2／1与SQL一致。 | 本人操作A10及对照页面；[只读SQL参照](closeout/personal-check/step7-sql-reference.json)由AI查询，AI未代发A10请求。 |

- 本人反馈原话与身份/日期确认：[human-confirmations.json](closeout/personal-check/human-confirmations.json)。本人没有提供截图路径或支付/发货时间的具体原值，不补造这些观察。
- 关联订单号：`CSU-cd330329fee6ff92bb7963911a6a8fc4`（AI从本次库唯一新单只读定位，非补填本人原话）。清理前SQL补证为SHIPPED、85.00、一主单两明细，alice启用且购物车0，A02为54／6／2／2／1，商品5相册仍0且版本0；见[最终安全SQL状态](closeout/personal-check/final-sql-state.json)。该补证不替代上表的本人观察。
- 异常：**本人确认本次抽验无异常。** 准备工具的版本初值误判及第6步临时目录权限失败按原事实保留（后者未发出HTTP），不抹去，也不冒充本人看到的产品失败；独立新准备/演示结果另存。
- 结论：**本人已按上述范围执行并确认；未覆盖项（并发、竞争、故障注入、P1及其他未验证范围）见STEP13/未实施说明。** 不写成组员互评或“组员复核通过”；上方历史自动复核与文档收口状态保持当时身份，REV-01的当前状态以本节和收口表为准。
- 签署：**高宇弘，2026-11-15**（按本人在本会话的明确确认与授权整理写入）。

本次环境停止与临时目录清理结果另存[cleanup-result.json](closeout/personal-check/cleanup-result.json)，由后续清理实际结果填写；不改台账或Word，REV-06继续待下一轮Word更新。


清理实际完成：`2026-11-15T12:18:45.4965732+08:00`，cleanup **PASS**；双端PID16916/18400及MySQL父/子PID15428/7356均已退出，本次监听无残留，精确临时目录及连接指针已删除。MySQL正常shutdown退出0，Java显式停止的实际进程码为-1，按原值记录。独立复查亦PASS，见[cleanup-verification.json](closeout/personal-check/cleanup-verification.json)。旧复核实例目录与开发库未被此清理操作触及。
