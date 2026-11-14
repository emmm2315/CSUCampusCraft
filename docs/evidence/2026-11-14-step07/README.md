# STEP07 持久购物车与导航徽标实测证据

- 实际受测完整 Git SHA：`3bc5629bcbcbeefa6cbc8f655e8cb4d790c81b77`；main 基线：`a1d4f3523f557af63fc77ea883986c099edcd93e`；分支 `feat/step07-cart`。
- 结论：**PASS（自动验收，组员实名复核待补）**，成功轮 `attempt1`。起测工作区干净，见 `attempt1/git-input-status.txt`。运行输入 140 个，清单 SHA-256 `606956a7a7ff516732e9c3484b3573386899fdb346d4210ec93c5addf9e1f5a9`，结束逐项确认无漂移。
- JDK 21、Wrapper Maven 3.9.16、MySQL 8.4.9；独立库 `csucampuscraft` 端口 `60324`；双端 JAR 监听127.0.0.1:8080/8081。版本原输出、库UUID/私有目录与监听PID见成功轮 versions.txt / database-identity.json / listener-ownership.jsonl。
- 两端真实Wrapper verify均BUILD SUCCESS、退出0；完整本机执行参数在 `cart-build-fresh.ps1`，新终端不含Maven PATH，固定JDK与独立缓存；两端元信息在build-user/admin.json，日志在成功轮，未新增依赖或测试框架。

## 覆盖与可复核记录

- 主工具 2775 项断言通过；HTTP 335 条、POST 154 次，每一POST有自动七表前后对照。`attempt1/database-writes.jsonl.gz`保存本人完整车行id/user/product/quantity/version/时间、商品现价/库存/状态/version及全7表有序原始行SHA；敏感账号/订单只保留表摘要。
- TST-08：身份→CSRF→角色→格式→锁当前用户复验→商品状态→合并数量/品种/库存。覆盖无身份302、缺错CSRF403、错角色403、参数400、未知/下架404、售罄/库存/合并超99/第21种409。单次1/99成功，同SKU一行、新行version0，实际改量增1。
- TST-09：首页、列表、详情、购物车、登录、400/403/404/409/500错误页及游客均核对本人全部SUM(quantity)，包括失效行；不按行数、商品状态或库存过滤。退出、重新登录、全新客户端与实际同JAR重启后购物车恢复；bob只读本人车。失败重新认证后的匿名页面徽标归0。
- TST-10/17购物车顺序部分：跨账号条目403、不存在404、旧版本409；同值有效版本303且零DML，MAX版本同值可303、实际变更409、移除MAX版本仍可成功；20种中失效行仍计数，已有SKU在满20种时可加量。
- TST-11本步部分：读取当前价格并以BigDecimal计算有效条目小计，清种子车后2×18.00+49.00=85.00；后台SQL夹具下架/售罄/减库存后车行保留并分别说明原因，不计入有效小计，仍可移除。整车结算按钮本步始终禁用，未注册/链接checkout/orders。
- 所有拒绝POST表摘要相同；每个成功购物车写仅允许本人cart_item变化，其余六表（包括产品库存/version、已有订单快照）不变。根SQL夹具独立记录于fixtures.jsonl，结束恢复原产品/账号全部受控字段，不能当作后台业务入口。
- 实际用户JAR原生串行Service补充 `CartWriteProbe.java` / native-probe.log：先操作者FOR UPDATE、写事务READ COMMITTED、同连接；缺身份/旧戳/禁用/错角色在车表前拒绝；有效同值无DML，数量变化带version条件；真实徽标SQL为SUM且无JOIN/COUNT。
- 本轮先在default profile执行购物车矩阵及同JAR重启；随后仅为复用STEP02既有400/403/404/409/500 GET错误探针重启到verification profile，另核库存/车数据无变化。不增加生产测试端点，不做业务故障注入。
- 24张PNG：1366×768与1920×1080各12张。85元有效车、失效车、bob空车、目录/详情/游客及错误页徽标见 `attempt1/browser/`，每图记录完整SHA/尺寸/视口/HTTP状态；浏览器只GET，两批前后数据库均不变。
- http.jsonl的正文经脱敏后gzip去重，索引记解压后SHA；最终sensitive-data-scan.json解压每一正文和命令日志检查CSRF/Cookie/会话/BCrypt/已知教学口令。evidence-files.json列除自身外所有文件字节SHA。

## 边界、差异与轮次

- 用户验收段将下架统列409，但本轮核心契约/SRS/HLD/原TST-08矩阵明确加购DRAFT为404；按细化矩阵执行。身份存在且错角色403，只有身份/状态/戳失效才清身份并302登录。
- 有效版本同值改量不写数据，所以即使商品已失效或version为MAX仍可成功；实际改量下架404、售罄或不足409。删除不加版，可删除MAX版本行。没有把购物车有效性检查当作库存预留。
- TST-08–10只按本轮真实分支覆盖；TST-11的有效结算确认/下单、TST-17并发/旧确认/订单清车留后续STEP08/09/13；不把原生串行调用算并发或后段回滚证明。
- 本轮只有 attempt1 一个真实验收轮次并完整通过，没有 live FAIL 轮次；准备期静态自检不代替真实 HTTP 结果。
- 姓名待填；负责人（Codex生成初稿，本人核对与验证）、组员复核待补（M3前完成）。AI执行单元不代替组员签字。

## 运行与停机

验收脚本、native源码、浏览器脚本归档在成功轮。应用账号仅获SELECT/LOCK TABLES与cart_item的INSERT/UPDATE/DELETE，其他六表无DML权限；账号、商品变化仅私有库root夹具。每个SQL连接先设UTC，生产数据库未触及。`tracked_processes_stopped=true`确认受控进程均退出，cleanup.json记录经绝对路径范围校验后的私有目录清理；秘密文件不进入归档。

命令和逐请求数据库前后原始JSONL分别以 `attemptN/commands.jsonl.gz`、`attemptN/database-writes.jsonl.gz` 无损压缩归档；`compressed-text-index.json` 保存每份原字节数与解压后完整SHA，原stage文件未改、内容未删减，敏感/hash审计实际解压核对。

## 独立复核入口

- `source-publication.json` 列出本轮20个用户端源码/资源文件及完整SHA；`source-review.json`、`ui-code-review.json` 为独立静态复核，不代替运行结果。
- `ui-visual-review-attempt1.json` 记录24张图逐图查看事实、完整SHA和视口；不是实名组员签字。
- `independent-observation-review.json` 与 `review_observations.py` 独立重读全部原始HTTP和逐POST数据库记录：154次POST一一关联七表对照，70次非303请求零写入；购物车26次新增版本0、5次改量版本恰增1、36次移除、3次同值无写。所有变更只涉及本人单行，其余六表保持。
- 95条徽标观察另核实际响应HTML、解压正文SHA及记录的SQL全车SUM，包含失效行、游客及错误页。并发、旧确认、结算/下单和后段故障注入不在本轮证明范围。
