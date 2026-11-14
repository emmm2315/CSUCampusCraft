# STEP07 合并后持久购物车与导航徽标实测证据

- 实际受测完整 Git SHA：`9e61c3e88761519fc63a4d99cafb006a51eacfa5`；main 基线：`a1d4f3523f557af63fc77ea883986c099edcd93e`；分支 `feat/step07-cart-merged`。
- 结论：**PASS（自动验收，组员实名复核待补）**，成功轮 `attempt2`。起测工作区干净，见 `attempt2/git-input-status.txt`。运行输入 140 个，清单 SHA-256 `c5f13d7ad5e1fc42ef45b19bdcb246788df5add2e5baad2830d8a50cb5ef9fbb`，结束逐项确认无漂移。
- JDK 21、Wrapper Maven 3.9.16、MySQL 8.4.9；独立库 `csucampuscraft` 端口 `53954`；双端 JAR 监听127.0.0.1:8080/8081。版本原输出、库UUID/私有目录与监听PID见成功轮 versions.txt / database-identity.json / listener-ownership.jsonl。
- 两端真实Wrapper verify均BUILD SUCCESS、退出0；完整本机执行参数在 `cart-build-fresh.ps1`，新终端不含Maven PATH，固定JDK与独立缓存；两端元信息在build-user/admin.json，日志在成功轮，未新增依赖或测试框架。

本目录名 `2026-11-15-step07-merged` 按用户指定的合并批次；执行时间使用系统真实时钟，见 result.json 的 date，未伪造未来日期。双方旧结果分别见[本地原记录](../2026-11-14-step07/README.md)和[组员原字节记录](../2026-11-14-step07-member/README.md)，它们都不代替本轮新 SHA 的新测试。

## 覆盖与可复核记录

- 主工具 2851 项断言通过；HTTP 346 条、POST 157 次，每一POST有自动七表前后对照。`attempt2/database-writes.jsonl.gz`保存本人完整车行id/user/product/quantity/version/时间、商品现价/库存/状态/version及全7表有序原始行SHA；敏感账号/订单只保留表摘要。
- TST-08：身份→CSRF→角色→格式→锁当前用户复验→商品状态→合并数量/品种/库存。覆盖无身份302、缺错CSRF403、错角色403、参数400、未知/下架404、售罄/库存/合并超99/第21种409。单次1/99成功，同SKU一行、新行version0，实际改量增1。
- TST-09：首页、列表、详情、购物车、登录、400/403/404/409/500错误页及游客均核对本人全部SUM(quantity)，包括失效行；不按行数、商品状态或库存过滤。退出、重新登录、全新客户端与实际同JAR重启后购物车恢复；bob只读本人车。失败重新认证后的匿名页面徽标归0。
- TST-10/17购物车顺序部分：跨账号条目403、不存在404、旧版本409；同值有效版本303且零DML，MAX版本同值可303、实际变更409、移除MAX版本仍可成功；20种中失效行仍计数，已有SKU在满20种时可加量。
- TST-11本步部分：读取当前价格并以BigDecimal计算有效条目小计，清种子车后2×18.00+49.00=85.00；后台SQL夹具下架/售罄/减库存后车行保留并分别说明原因，不计入有效小计，仍可移除。整车结算按钮本步始终禁用，未注册/链接checkout/orders。
- 所有拒绝POST表摘要相同；每个成功购物车写仅允许本人cart_item变化，其余六表（包括产品库存/version、已有订单快照）不变。根SQL夹具独立记录于fixtures.jsonl，结束恢复原产品/账号全部受控字段，不能当作后台业务入口。
- 实际合并用户JAR原生Service补充（91项） `CartWriteProbe.java` / native-probe.log：先操作者FOR UPDATE、写事务READ COMMITTED、同连接；缺身份/旧戳/禁用/错角色在车表前拒绝；有效同值无DML，数量变化带version条件；真实徽标SQL为SUM且无JOIN/COUNT。各写SQL跟踪另断言商品读取无FOR UPDATE。独立root连接持有用户行，P_S data_lock_waits真实确认Service等待后禁用并推进微秒认证戳提交，Service锁内拒绝且车/商品无变；重启用旧戳仍拒绝。AUTH_LOCK_WAIT原始日志及auth-lock-wait.json记录真实连接/等待/时间，不是两HTTP抢购或订单并发。
- 本轮先在default profile执行购物车矩阵及同JAR重启；随后仅为复用STEP02既有400/403/404/409/500 GET错误探针重启到verification profile，另核库存/车数据无变化。不增加生产测试端点，不做业务故障注入。
- 28张PNG：`attempt2/browser/`保留24张两桌面视口只读检查，`attempt2/journey/`另有4张真实游客流程图（1366）。游客详情没有POST表单，只显示登录后加购链接；实际点击→登录303返回详情（0件、无自动重放）→本人手动点击一次真实加购→303购物车（1件），两次真实浏览器POST都由仅本机工具observer逐请求记录七表前后、与所有HTTP同一索引；不是生产探针。每图有完整SHA/尺寸/视口，28张全部是本次新生成。
- http.jsonl的正文经脱敏后gzip去重，索引记解压后SHA；最终sensitive-data-scan.json解压每一正文和命令日志检查CSRF/Cookie/会话/BCrypt/已知教学口令。evidence-files.json列除自身外所有文件字节SHA。

## 边界、差异与轮次

- 加购未知/DRAFT仍404；现有车条目的实际改量不可用按本轮指定409，两个场景分开。已认证错角色403，身份/状态/认证戳失效清身份并302登录。
- 有效版本同值改量不写数据，所以即使商品已失效或version为MAX仍可成功；实际改量下架/不可用为409，原生异常验证稳定code CART_PRODUCT_UNAVAILABLE，页面提示移除后继续选购；售罄或不足仍409。删除不加版，可删除MAX版本行。没有把购物车有效性检查当作库存预留。
- TST-08–10只按本轮真实分支覆盖；TST-11的有效结算确认/下单、TST-17并发/旧确认/订单清车留后续STEP08/09/13；认证锁等待是本轮实际补充，只证明等待期间禁用后的事务内复验；不把它当作购物车双请求、订单竞争或后段故障回滚证明。
- 轮次：attempt1工具超时整体FAIL原样保留；attempt2使用新私有库完整重跑PASS，详见本页末尾和attempt1-diagnostic.json。
- 姓名待填；负责人（Codex生成初稿，本人核对与验证）、组员复核待补（M3前完成）。AI执行单元不代替组员签字。

## 运行与停机

验收脚本、native源码、浏览器脚本归档在成功轮。应用账号仅获SELECT/LOCK TABLES与cart_item的INSERT/UPDATE/DELETE，其他六表无DML权限；账号、商品变化仅私有库root夹具。每个SQL连接先设UTC，生产数据库未触及。`tracked_processes_stopped=true`确认受控进程均退出，cleanup.json记录经绝对路径范围校验后的私有目录清理；秘密文件不进入归档。

命令和逐请求数据库前后原始JSONL分别以 `attemptN/commands.jsonl.gz`、`attemptN/database-writes.jsonl.gz` 无损压缩归档；`compressed-text-index.json` 保存每份原字节数与解压后完整SHA，原stage文件未改、内容未删减，敏感/hash审计实际解压核对。

原生认证锁等待使用独立 root 事务制造用户锁与禁用变更，详见 `CartWriteProbe.java`、`native-probe.log` 和 `auth-lock-wait.json`；这是非 HTTP 补充，不计入 157 次 HTTP POST。其外层前后对照在完整恢复私有账号/产品夹具后执行；HTTP 每次 POST 的“其余六表不变”独立成立。HTTP 场景的 root 夹具另存于 fixtures.jsonl。

浏览器真实导航见 HTTP 序号 142–147，POST 为 144（登录）与146（手动加购），均有 automatic_all_posts 七表记录和具名语义记录。Chrome 对303跳转正文不可读取，索引明确 `body_available=false`，记录真实状态/Location与空采集正文；GET 正文均实际读取，正文 SHA 指脱敏后采集字节。

attempt1 因 mysql 客户端不变量快照调用 TimeoutExpired 而整体 FAIL，原 result/log/脚本保留；错误包含负剩余 timeout，计时/主机中断原因尚未证实，不能当作通过。`attempt1-diagnostic.json` 给出原结果字节 SHA 与观察限制。attempt2 使用相同产品 SHA、全新私有库完整重跑后 PASS，没有产品修复，也没有复用旧通过结论。失败轮4张旅程图与成功轮逐字节相同，仅归档副本按 `artifact-references.json` 引用成功图；原 stage 四图不动，成功28图均可直接查看。

## 双方合并与独立复核入口

- `comparison.md` 是合并前形成的逐项比较与取舍；双边源码行号、Git blob 和验证标记见三份 comparison JSON。`merge-record.json` 保存 ours 策略的双亲提交及合并树与原本地树相等的证明；之后仅修改 `source-publication.json` 列出的两个源码文件。
- 原本地证据仍在 `../2026-11-14-step07/`；组员96份原文件逐 Git blob 原字节导入 `../2026-11-14-step07-member/`，该目录新增导入说明/清单。`member-import-review.json` 核对其原字节与敏感值，不将原组员结果当作新验收。
- `source-review.json`、`backend-candidate-review.json`、`ui-static-check.json` 为限定移植静态复核；`ui-visual-review-attempt2.json` 为28张新图逐图检查。它们不能代替实名组员签字。
- `independent-observation-review.json` / `review_observations.py` 独立重读新轮346 HTTP和157 POST：70个非303请求零写；27次新增版本0、5次真实改量版本+1、37次移除、3次同值零写；所有应用POST其他六表不变，100条徽标观察与实际HTML/SQL对照。
- 独立复核还解析实际游客导航HTML及登录/手动加购两POST对照，确认游客无POST表单、登录后车仍为空、本人提交才新增；核对原生不可用409稳定code、无商品FOR UPDATE与P_S等待日志。4ms是首次确认阻塞的偏移，20ms是补充总时长，不称精确锁等待时长。
- 原始引用快照在 `original-refs.json`；本轮只新增/提交合并分支，main、原本地STEP07和全部origin引用保持原SHA，不push、不删分支、不重写组员历史。目录批次名按任务为2026-11-15，真实执行时间保留2026-11-14的原始时间戳。
