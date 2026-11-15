# STEP13 本轮最终技术验收证据

父级[result.json](result.json)按五组**本轮新运行**的59个必要片段，汇总39个P0编号的技术PASS；没有把原始失败轮改成成功。逐编号见[p0-matrix.md](p0-matrix.md)，原始分段和字节追溯见[parent-traceability-validation.json](parent-traceability-validation.json)。TST-32另一位真人复现及组员互评未实施；高宇弘原2026-11-15本人签署仅对应原七项范围，未扩张为本轮真人操作。P1 TST-36未选做。

## 源码、制品与环境

- 完整受测SHA：`d577179e4468354552d3f5f48d624a4296ee3cfb`，分支`feat/step13-acceptance`；产品源码未修改，未改main、未push。
- 用户端JAR SHA-256：`6b6027b67f381cfcc012cd3fc79bc940ad546c9acc2ae46fbf9ac13a71d42700`。
- 管理端JAR SHA-256：`1a8bf9ded1a535876a96b991659596fa82c01bf2bebccef45c755fe8e8820586`。
- JDK Microsoft **21.0.12.1**、Maven Wrapper **3.9.16**、MySQL **8.4.9**。两端真实`clean verify`均BUILD SUCCESS，Maven日志总时长分别3.599s、3.126s；离线隔离settings/cache、无Maven PATH的实际命令见[用户构建](build-user.json)、[管理构建](build-admin.json)。Wrapper不提供JDK，本轮`JAVA_HOME=C:/Users/Starmetor/.jdks/ms-21.0.12.1`。
- 五组均绑定同199项运行输入及同两JAR。运行组清单SHA为`e0f5ea7765eb1b97e889866f80d8af69f00b29004575235c21094735c3b0789a`；根清单与运行组清单的条目集合完全相同，各原文件哈希分别保留。
- 主5独立MySQL端口**56969**；新6并发/故障独立端口**64927**。补验组端口56542/62964/57725，均有独立UUID与数据目录。两应用只监听本机8080/8081，实测冲突的补验改用18080/18081。

当前管理端根页是需ADMIN登录的A02真实控制台。初始化、同库、共享图片、结构空库、ADMIN-only空业务和双JAR重启技术子项均本轮重测；M0历史“双端根页主题页”的原验收记录保持原义，不冒充当前A02标准。

## 五组来源与采纳边界

| 组 | 原整体结果 | 本轮采纳范围 |
|---|---|---|
| [主5](attempt5/result.json) | **FAIL保留** | HTTP序号**1–787**的顺序/空库/安全技术片段、20张真实图、双JAR重启。788–817属后来失败C1的准备，不采作并发成功；C1 stdout解码前未归档，不能追认响应胜负。 |
| [新6](attempt6/result.json) | PASS | 新私库全部**8C＋5D**，1260项断言0失败、291次HTTP；仅10个P0编号的13分段，不单独宣称39项完整通过。 |
| [首页筛选徽标补验](home-filter-supplement/attempt1/result.json) | PASS | 首页边界、联合筛选、含失效行徽标，共3个限定片段。 |
| [状态/令牌补验](state-token-supplement/attempt1/result.json) | **FAIL保留** | 333项业务断言0失败、69次HTTP、4个限定片段PASS；原失败仅清理PermissionError，[独立清理重试](state-token-supplement/cleanup-retry.json)通过，未改原结果。 |
| [DDL元数据补验](ddl-metadata-supplement/attempt1/result.json) | PASS | 本轮初始化DDL/约束等限定元数据片段。 |

85元主线单号：**`CSU-3132fed968806dbdeb89e41063f992b9`**。主5 HTTP363真实成交`2×18.00＋49.00=85.00`，一主单两明细，确认车清除，库存10/12→8/11且两商品version各＋1；随后模拟支付为PAID、后台发货为SHIPPED，双端仍读成交快照，另一账号购物车和重启持久化另有对照。后续截图重新准备过购物车，不把截图车非空说成下单未清车。

## 并发：真实HTTP与锁等待

各案用独立演示schema、两独立HTTP worker和共同latch起点；外部只读锁门控释放后由真实Service完成。每窗口保存共同七表前后，不对并发POST虚构独立零写归因。[原始窗口](attempt6/concurrency/raw.jsonl)、[场景索引](concurrency/results.jsonl)。

| 场景 | 同时JDBC等待数 | 两请求实际HTTP | 本次最终数据 |
|---|---:|---|---|
| C1 两账号抢末件 | 2 | alice303 / bob409 | 仅新增1主单1明细；stock1→0、version＋1；败者车保留且旧确认已失效。 |
| C2 买2与补3 | 2 | 下单303 / 补货303 | 初始10，最终11；version＋2，一笔36.00订单，确认车清除。 |
| C3 同确认重复提交 | 1 | 请求1为409 / 请求2为303 | 仅一笔36.00订单，库存减2、version＋1；旧令牌不删除后来新加车。 |
| C4 支付与取消 | 2 | 支付409 / 取消303 | 本次取消胜出：CANCELLED、支付三字段空；两商品按原数量仅返一次库存，各version＋1。 |
| C5 支付与发货 | 2 | 支付303 / 发货303 | 本次付款先行，最终SHIPPED；首次凭证/支付时间保留，无库存或快照修改。门控实际采用同order_no唯一索引。 |
| C6 编辑与相册 | 2 | 资料303 / 相册409 | 资料胜出，父version仅＋1；失败方无新增相册行。 |
| C7 禁用与在途下单 | 2 | 下单303 / 禁用303 | 本次下单先完成：新增1主单1明细、库存减1、version＋1；禁用后旧会话受保护请求302，重新启用不复活。 |
| C8 同用户购物车 | 2＋2 | 加1/加2均303；再加2为303/旧版设4为409 | 第一窗口仅1行quantity3/version1；第二窗口最终quantity5/version2，无丢更新。 |

C3是**HTTP并发、共享服务器会话、应用monitor串行进入业务事务**，只要求并实测1个JDBC等待者，不称两个业务事务同时进库。C8有两个分别同步的子窗口，因此8个场景共9个窗口、18次并发HTTP响应。这里只证明本次实际合法序列，不宣称枚举了全部线程调度。

## 故障：条件触发器与整体回滚

五案各用隔离schema，以条件BEFORE触发器`SIGNAL SQLSTATE 45000 / errno1644`，由真实HTTP进入事务；没有产品故障开关。各案实际均为**500通用错误页**，响应不含注入marker、SQL或堆栈；七表有序全字段摘要及安全逐行状态相同。只证明已提交行数据回滚，不声称回收自增分配器空洞。

| 场景 | 注入位置 | 实际先行写入证据 | HTTP / 七表 / 清理 |
|---|---|---|---|
| D1 | 首条订单明细INSERT前 | 主单INSERT已执行，affected1 | 500；七表相同；DROP后0残留 |
| D2 | 第二商品扣库存UPDATE前 | 主单＋2条明细＋第一商品扣库已执行 | 500；七表相同；DROP后0残留 |
| D3 | 第二车行DELETE前 | 主单＋2条明细＋两商品扣库＋第一车行删除已执行 | 500；七表相同；DROP后0残留 |
| D4 | 取消时第二商品返库前 | 第一商品返库UPDATE已执行，affected1 | 500；七表相同；待支付/取消时间不变；DROP后0残留 |
| D5 | 订单转PAID的UPDATE前 | 实际1644事件，支付状态写入未成功 | 500；七表相同；支付三字段仍空；DROP后0残留 |

[故障索引](faults/results.jsonl)、[实际先行语句](attempt6/faults/intermediate-statements.jsonl)、[触发器创建/删除](attempt6/faults/triggers.jsonl)只记录应用线程区间、归一化digest与affected rows，不存SQL_TEXT或私密参数；[限定独立复核](cd-final-readonly-audit.json)另核对212项证据条件。

## 工具失败、修正与复测

原attempt1–5的整体FAIL及其原索引全部保留；这些工具修正均未改变产品源码。

| 原记录 | 外部工具问题与后续处理 |
|---|---|
| attempt1 | SQL字面量排序规则不匹配，业务HTTP前停止；保留FAIL后在新私库重跑。 |
| attempt2 | CONVERT表达式coercibility导致夹具查询不匹配；独立literal预检验证修正，再新私库重跑。 |
| attempt3 | parse_qs忽略合法空q=，错误断言分页；修观察器后新私库重跑。 |
| attempt4 | 浏览器调用方误传JSON文本而非夹具文件路径；扫描又命中工具源码中的固定虚构电话。两类原失败保留，改参数和随机夹具后新5重跑。 |
| attempt5 | 首次C1 Java stdout默认GBK，Python严格UTF-8解码失败且未存原stdout，不推断该C1胜负。改显式UTF-8 JSON字节，实际中文/emoji default/GBK/UTF8离线回归及隐私预检后，新6独立重跑全部8C/5D；解析前记录输出长度/hash/UTF8判断。 |
| 独立重读初版 | 主5浏览器207断言实际在browser/result，而非主checks的TST04标签；state用户U08用“模拟发货”dt/dd，而非管理端data-shipped-time。两份误报原件保留，按实际组件/模板重读，分别4235和375项检查通过；无业务重跑或产品修复。 |
| 清理工具 | state原PermissionError保留、独立重试成功。统一清理首版误读retry.overall而实际为passed=true，在任何删除前停止，原报告保留；修字段核对后清理与独立验证成功。 |

C5门控在首次正式C/D运行前改为同order_no唯一索引，原工具版本保留；预检调整不冒充业务失败或运行结论。轮次说明见[child-delivery-summary.json](child-delivery-summary.json)、[工具原版本](tool-versions/)、[UTF8诊断](tools-final/stdout-encoding-diagnostic.json)。

## 图片、清理、归档与人工边界

- 主5[20张原始PNG及浏览器结果](attempt5/browser/)覆盖1366×768和1920×1080，[AI视觉复核](browser-visual-review.json)实际逐张查看。浏览器24条导航是after-only元数据、207断言；整批七表前后证明只读，不冒称每个导航都归档/扫描原始响应体，不用截图替代主HTTP状态证据。收货、联系、口令及令牌在交付中遮盖。
- [统一清理](cleanup-all-runtime.json)实际删除9个自有运行目录、另1个已不存在；[新进程独立复核](cleanup-verification.json)确认14相关端口无监听、无本轮进程，1312份原证据/结果/保留日志字节不变。原清理预检FAIL见[保留记录](cleanup-all-runtime-attempt1.json)，非本轮MySQL未触碰。
- [archive-transforms.json](archive-transforms.json)的27项xz/gzip仅作用于**交付副本**，原stage证据不改；解压字节必须等于logical_sha256。子目录原artifacts.sha256仍索引原始逻辑字节，须按映射解压核对。父目录最终artifacts.sha256按最终存盘文件直接计算，包含压缩文件本身；原body gzip不重新压缩。两层索引语义分别保留。
- 本轮Codex AI执行、独立重读和视觉检查不代替人审。TST-32另一组员独立复现、组员交叉复核及实名登记均未实施；原有人审只保留原覆盖子集，未扩写。P1未选，旧STEP证据不充当本轮实测；自动化技术闭环与人工验收门槛分别记录。

## 最终文档与离线核对

最终指导书保留原310个非授权段落及2张原表，仅9槽定向修改、追加15段；实际Word COM16/PDFium渲染21页全部逐页检查。原包渲染器因缺LibreOffice失败日志保留。见[word核对](word/word-update-validation.json)、[视觉检查](word/word-render-review.json)、[渲染临时件清理](word/word-qa-cleanup.json)、[最终文档清单](documents-manifest.json)。实验报告和答辩脚本随docs单独交付，Word页面PNG/PDF仅作QA后已清理；本目录只含20张浏览器截图。

存储校验：根artifacts.sha256直接针对本目录最终写盘文件字节；归档变换仅是无损xz/gzip，原阶段文件未改。可用标准Python运行 `python restore_evidence.py --output <不存在的外部临时目录>` 恢复逻辑JSONL/完整重放报告，再按原child索引核对；此命令只复制与解压，不连接数据库或调用业务。目录中缺失的逻辑.jsonl文件按archive-transforms.json查找同内容.xz。源码与5506份既有证据保护见[source保护](source-preservation-before-publication.json)；本地文档/归档提交晚于受测源码，最终提交身份见Git历史和交付回复，不回填成已测试源码。

主5已采纳顺序请求的原索引无损存为[http.jsonl.xz](attempt5/http.jsonl.xz)，新6索引为[http.jsonl](attempt6/http.jsonl)；原主5逻辑索引可用restore_evidence.py恢复后按原SHA核对。
