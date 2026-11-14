# STEP08 整车结算确认实测证据

2026-11-14，受测源码 `54d6b007eb1317c14be090016ea75aec02ead6c5`，分支 `feat/step08-checkout`。从干净 main `993b2ee184a1a05af40a1943970276ffb14cfac0` 创建，起测工作区干净。**本步范围自动验收通过；台账待复核。** STEP07 既有状态和证据保持不变，实名组员交叉复核待补（M3 前）。本目录只归档本轮新运行，不复用旧结果。

入口：[摘要 result.json](result.json)、[完整 attempt1/result.json](attempt1/result.json)、[HTTP 索引](attempt1/http.jsonl)、[独立观察复核](independent-observation-review.json)、[字段/令牌观察](attempt1/confirmation-observations.jsonl)、[敏感扫描](attempt1/sensitive-scan.json)、[视觉复核](ui-visual-review.json)。attempt1 首次完整运行通过，无被覆盖的失败轮。

## 环境与构建

Windows 11；Microsoft JDK 21.0.12.1；仓库 Wrapper Maven 3.9.16；MySQL 8.4.9。新建私有数据库 `csucampuscraft` 监听 `58660`，用户端 `127.0.0.1:8080`、管理端 `127.0.0.1:8081` 同库启动且实际核对监听 PID；未接触原开发库。[数据库 UUID/UTC](attempt1/database-identity.json)、[启动参数](attempt1/launches.jsonl)、[监听归属](attempt1/listener-ownership.jsonl)、[版本](attempt1/versions.txt)。

两端在 Maven 不在 PATH 的新 PowerShell 中以固定 JDK 运行 `./mvnw.cmd -o -s <隔离 settings> -Dmaven.repo.local=<已有缓存> -f csucampuscraft-user/pom.xml verify` 与管理端对应命令，均 `BUILD SUCCESS`、退出码 0。[原始构建日志和脚本](builds/)保留实际字节，隔离 settings/cache 只复用已下载依赖，没有修改 POM/Wrapper。用已安装 Maven 3.9.16 的成员也可按 README 常规构建。

147 个运行输入逐项冻结，清单 SHA-256 `e23e25c23afb45c22474833685506d5086ab9193f253920b70b818673a39bec2`；[实际清单](attempt1/runtime-inputs.sha256)涵盖两端 POM/src、SQL、共享素材及 Wrapper，结束逐项不漂移；两个 JAR SHA 在 attempt1/result.json。管理端、SQL、依赖、素材未改。[源码文件清单](source-publication.json)和[受测差异](attempt1/implementation-diff.patch)。

## 实际结果与边界

- 2249 项主断言、247 条 HTTP、209 份逐请求七表自动对照；其中 82 次结算确认请求（含两次浏览器跟随登录跳转）与 86 次 POST /orders 全部七表有序全字段摘要相同，车条目/version、商品库存/version、历史订单均未写入。浏览器跳转保存 requested_path、实际响应 path 和 302 链，不将游客最终登录页 200 误记成结算页 200。[逐请求对照 gzip](attempt1/database-writes.jsonl.gz)、[摘要算法与脚本](attempt1/verify_step08.py)、[原始种子摘要](attempt1/database-original.json)、[最终摘要](attempt1/database-final.json)。
- 真实购物车 HTTP 移除 alice 全部种子车，再加入 2 本 18.00 元方格本和 1 盒 49.00 元毕业礼盒，U06 为两种三件、85.00 元；独立复核重读 86 份金额页面，与该请求前 SQL 的本人全车、价格、数量、条目版本逐项一致。购物车准备写入仍只允许 cart_item 变化，其他六表不变；它们不属于 STEP08 下单写入。
- 空车/下架/售罄/超库存拒绝409；每行金额和总价分别检查 DECIMAL(12,2)，单行溢出和仅总价溢出都拒绝。额外客户端 total/amount/unitPrice/userId/productId 字段不能决定服务端金额、清单或归属。
- 缺/错 CSRF 403；游客及失效身份先302登录，无 POST 自动重放。新令牌替换旧令牌；同账号另一会话和他人令牌409；过期通过真实 `PT1S` 用户 JAR 重启证明，随后恢复默认 `PT10M`。退出、禁用/重新启用和重新认证后，旧确认不能复活。跨会话无效提交只影响提交会话当前确认，不影响原持有人会话。
- 三个字段分别覆盖缺失、空白、1 字符、50/30/255 上限、超长、首尾 Unicode 空白及 emoji 码点。400 保留仍有效令牌可修正；脚本字符串作为 input/textarea 普通文本，HTML 转义且无注入脚本。收货字段只在同次响应回填，不进会话；证据 HTML 结构化脱敏，截图遮盖这些字段，因此脚本原文字面证明来自真实 DOM 断言而非遮罩截图。
- 同账号另一会话通过真实购物车 POST 改量、往返改量导致 version 改变、新增和移除，都使旧确认409，车仍保留。改价、下架、售罄、减库存是独立 root SQL 夹具，明确记录于 [fixtures.jsonl](attempt1/fixtures.jsonl)，不冒充后台 HTTP。夹具结束恢复受控商品和账号字段；单独商品 version 变化、库存变化后仍足量不单独作废确认，因为本步不预留库存。
- 原生补充 [NativeCheckoutProbe.java](attempt1/NativeCheckoutProbe.java) 使用受测 JAR 实际类，130 项通过；受控对象检查不可变拷贝、序列化、32 字节随机输入、128 个不同令牌观察、精确过期边界及字段顺序；现场 private-DB Service 捕获两条本人车商品 JOIN 查询，均在只读事务，未执行 FOR UPDATE 或 DML。[原生日志](attempt1/native-probe.log)。这不替代 HTTP，也不证明未来下单并发或原子性。
- 浏览器 302 项断言，36 次真实导航/提交均有前后摘要，24 张新 PNG。完整视觉复核逐图查看；两视口检查表单标签、字段定位、85.00、徽标、错误反馈、静态图和无页面横向溢出。fullPage 截图高度可超过视口高度，原始 viewport 与 PNG 尺寸单独保存。

## 实现决策与 STEP09 交接

令牌为 SecureRandom 32 字节、Base64URL 无填充，绑定本端会话和 userId；UTC Instant 创建/到期时间，默认10分钟，可配置 `csucampuscraft.checkout.confirmation-ttl`。不可变会话快照存整车 itemId/productId/quantity/itemVersion/unitPrice、服务端总价及显示资料，不含收货字段。到期即不可用，下一次校验清除或新 GET 替换；没有后台清理定时器。会话结束、退出、重新认证和清身份沿用 SessionSupport 清理。

保守失效策略：提交缺失/错误/旧/跨会话令牌时409并清除提交会话的当前确认，所以 A 被 B 替换后再提交 A，会使 B 也需重新确认。字段400和CSRF403保留仍有效确认。全部校验通过的 **409 `ORDER_SUBMISSION_PENDING`** 明确“下单将在 STEP09 接入”，不产生任何订单，保留有效确认；它不是成功提交。

GET /checkout 和本轮 POST /orders 都只读数据库，不调用 CustomerWriteGuard，不持用户/商品业务行锁；Java 会话监视器仅协调本端确认状态。STEP09 替换占位时必须建立 READ COMMITTED 原子事务：先锁用户复验身份，再核对整车/确认，按商品 ID 升序锁商品重查价格状态库存，订单及明细、扣库/version、已确认条目清理同一提交；成功消费令牌并303至本人订单。TST-11–13只登记本步确认/字段/旧确认部分，真实下单留STEP09，竞争和故障回滚留STEP13。

## 截图索引

全部收货输入遮挡；令牌与会话值未出现在可见截图。

| 场景 | 1366×768 视口 | 1920×1080 视口 |
| --- | --- | --- |
| u01-live-badge | [1366](attempt1/browser/u01-live-badge-1366.png) | [1920](attempt1/browser/u01-live-badge-1920.png) |
| u03-live-badge | [1366](attempt1/browser/u03-live-badge-1366.png) | [1920](attempt1/browser/u03-live-badge-1920.png) |
| u05-valid-checkout-entry | [1366](attempt1/browser/u05-valid-checkout-entry-1366.png) | [1920](attempt1/browser/u05-valid-checkout-entry-1920.png) |
| u06-csrf-403 | [1366](attempt1/browser/u06-csrf-403-1366.png) | [1920](attempt1/browser/u06-csrf-403-1920.png) |
| u06-empty-cart-409 | [1366](attempt1/browser/u06-empty-cart-409-1366.png) | [1920](attempt1/browser/u06-empty-cart-409-1920.png) |
| u06-fields-400 | [1366](attempt1/browser/u06-fields-400-1366.png) | [1920](attempt1/browser/u06-fields-400-1920.png) |
| u06-guest-login | [1366](attempt1/browser/u06-guest-login-1366.png) | [1920](attempt1/browser/u06-guest-login-1920.png) |
| u06-invalid-cart-409 | [1366](attempt1/browser/u06-invalid-cart-409-1366.png) | [1920](attempt1/browser/u06-invalid-cart-409-1920.png) |
| u06-replaced-token-409 | [1366](attempt1/browser/u06-replaced-token-409-1366.png) | [1920](attempt1/browser/u06-replaced-token-409-1920.png) |
| u06-script-literal-400 | [1366](attempt1/browser/u06-script-literal-400-1366.png) | [1920](attempt1/browser/u06-script-literal-400-1920.png) |
| u06-valid-85 | [1366](attempt1/browser/u06-valid-85-1366.png) | [1920](attempt1/browser/u06-valid-85-1920.png) |
| u06-validated-pending-409 | [1366](attempt1/browser/u06-validated-pending-409-1366.png) | [1920](attempt1/browser/u06-validated-pending-409-1920.png) |

## 归档完整性与停机

原始 stage 记录不改；仅归档副本的 commands.jsonl 和 database-writes.jsonl 无损 gzip，解压字节 SHA 见 [压缩索引](compressed-text-index.json)。HTTP 正文按脱敏后字节 SHA 去重压缩，独立复核逐条解压核对。敏感扫描实际检查167份文本、132份gzip正文、108个已知私密值，零命中；最终包还会逐文本/gzip做结构化检查。构建日志、源码、脚本、PNG、JSON 逐字节摘要见 evidence-files.json（不包含自身）。不归档私有密码、原始 Cookie/CSRF/确认令牌、完整收货信息、JAR、class、依赖缓存或 MySQL 数据目录。

所有本轮创建进程已停止；范围校验后的私有目录清理见 cleanup.json。main、既有分支/远端引用及3385份旧证据保持原样，后续仅在本功能分支提交三份文档和新证据，不push。AI静态/自动/视觉复核不能代替组员实名签字。

归档预检补记：首次最终范围核对因 Git 默认转义中文文档路径而误判；这是发布工具问题，未发生业务验收失败或源码变更。明确使用 `git -c core.quotepath=false` 后，原引用、3385份旧证据及允许路径核对通过。旧工具字节与修正版本均保留，详见 publication-verification.json。
