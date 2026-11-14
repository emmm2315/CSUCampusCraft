# STEP07 双方独立实现比较与合并取舍

本报告先对固定本地 Git 对象做只读比较，再按本轮明确范围选择性移植。比较阶段未改仓库源码或任何 Git 引用，未联网。静态推断、两边旧实测与本轮新实测分别记录，不把它们拼接为一个新 PASS。

## 比较基线与证明对象

| 对象 | 完整 Git SHA / 原始身份 | 说明 |
| --- | --- | --- |
| 共同基线与 main | `a1d4f3523f557af63fc77ea883986c099edcd93e` | 两份 STEP07 平行开发；本次禁止改 main。 |
| 本地 Starmetor 分支 tip | `dda8f8254eec3f63e9c3bede397131cbe55c6179` | 原受测代码 `3bc5629bcbcbeefa6cbc8f655e8cb4d790c81b77`，干净工作区。 |
| 组员 emmm2315 分支 tip | `221dfb6dfa4fe93d69ffe1eecda97e98705406e1` | 只读本地已 fetch 的 `origin/feat/step07-cart`；原记录为未提交工作区受测，之后 publication 关联功能汇总 `ceb4059717d59020b999d1479a7ef5f647a89e14`，不冒称最终 tip 重新实测。 |

两者共同祖先是 main，上下游均不是快进关系。比较的是两个 tip 的真实文件，不只比较各自相对基线的新增行。细节、双边源码行号、Git blob SHA 与 DOM 标记集合见 `backend-comparison.json`、`frontend-auth-comparison.json`、`evidence-comparison.json`。

## 逐项差异及取舍

| 项目 | 本地实现 | 组员实现 | 统一实现与理由 |
| --- | --- | --- | --- |
| CartService / CartPage API | read / quantityFor；quantity、validSubtotal、invalidCount 等模型。 | getCart / quantity；total、checkoutAllowed、totalQuantity。 | 保留本地 API 与页面模型，避免超出限定移植范围的 DTO/模板整体改名。 |
| CartItem / CartLine | 持久实体含时间；单独当前商品投影提供 invalidCode、publicProduct、valid、subtotal。 | CartItem 同时承载 JOIN 商品字段；Service 构造 CartLine record，并做空值回退。 | 保留本地结构与已有可核对字段；不混用两个不兼容模型。 |
| CartItemMapper / 品种查询 | 读取本人有界整车并取行数；商品普通 SELECT。 | 单行查询及 countKinds COUNT(*)；商品 SELECT FOR UPDATE。 | 保留本地实现。组员 COUNT 只用于 SKU 种类，不能误判成徽标错误。 |
| CustomerWriteGuard 位置 | auth 包，经 StoreUserMapper 锁用户。 | cart 包，经 CartItemMapper 锁用户。 | 保留 auth 包，便于后续结算/订单复用，避免认证查询与车 Mapper 耦合。 |
| 守卫与事务 | MANDATORY，要求已有 RC 写事务；首 SQL 锁操作者并复验状态、角色、微秒 authStamp。 | 同样要求 RC 写事务并锁操作者复验。 | 共同约束保留；新验收在实际 JAR 入口重新观测，不借用旧结论。 |
| 商品行锁 | 购物车校验商品时普通 SELECT，不预留库存。 | 加购、改量使用商品 FOR UPDATE。 | **不移植商品 FOR UPDATE**。按本轮要求，仅用用户行锁协调车写；商品与后台写不必因购物车预览校验互相阻塞，成交时再做库存事务。 |
| 实际改量商品不可用 | 与加购共用 available，返回404。 | 返回409 CART_PRODUCT_UNAVAILABLE。 | **移植实际改量409**，稳定 code 为 CART_PRODUCT_UNAVAILABLE，提示“请移除该条目后继续选购”。车条目仍存在，商品状态变化属于可恢复冲突。 |
| 加购未知/DRAFT | 404。 | 404，具体 code 名称不同。 | 保留本地404及原稳定 code，不改加购矩阵。 |
| 同值、失效行、MAX | 所有者和有效版本后立即同值成功，早于商品可用性及版本容量检查。 | 商品锁/可用性/库存检查后才同值成功。 | **保留本地同值提前返回**；不能整段搬组员改量方法。有效版本同值303、零写零增版，失效仍保留、仍阻结算。 |
| 归属、版本与移除 | 非本人403、目标不存在404、旧版409；条件写绑定 user/id/version，检查影响行数；失效行和MAX可移除。 | 核心归属、版本及失效移除约束相近。 | 保留本地实现和全部验证标记，避免无必要改动。 |
| CartController / 原提交回显 | CartForm 保留原 quantity/version；仅失败动作回显，其他表单当前版；摘要有唯一锚点。 | 主要保留 quantityInput；冲突可禁用 fieldset，隐藏版取当前行。 | 保留本地原版本，避免失败页悄悄用新版本重试旧操作；不移植整套 Controller/模板模型。 |
| 加购失败恢复 | 可公开商品在U03回显；其他保持原HTTP失败由通用页处理。 | 部分失败回本人U05。 | 保留本地恢复路径，不扩大本轮路由/页面取舍。 |
| 常规游客 U03 | 游客也有 POST 表单，依靠后端302登录。 | 有货游客显示登录链接；售罄游客显示不可购买。 | **移植游客登录链接**：不渲染游客 POST 表单，登录后回商品 GET，由本人手动加购；已登录用户表单及 min/max/CSRF 原样保留。 |
| 直接构造游客POST | 从单个正 Long productId 导出固定商品 GET，其他车写回/cart，不重放POST。 | 非GET登录回跳默认首页。 | 保留本地后端防御。UI改登录链接不等于撤销直接请求的身份、CSRF及固定回跳保护。 |
| AuthFilter 角色/CSRF | +10身份；购物车POST错角色延后到+20 CSRF后的 MVC preHandle，早于参数。 | +10直接拒绝错角色，早于CSRF。 | 保留本地 身份→CSRF→角色→参数 次序；同为403不能证明顺序相同，新验证核对稳定错误码。 |
| PageModelAdvice 徽标 | COALESCE SUM仅按本人；含失效行；直接错误页可重查身份；技术失败为不可用状态。 | 正常SUM相同；依赖request用户，错误态flag及异常处理方式不同。 | 保留本地 SQL、模型名与错误页处理。双方正常SUM均正确，不做公共模型重构。 |
| 失败再认证 | 清身份时同步将已构建页面徽标归0。 | 未同步重置旧徽标模型。 | 保留本地修复。旧徽标风险是静态推断，未另执行组员失败实验，不能写成组员旧验收失败。 |
| U05 / data-* / CSS | 既有 item-count、quantity、invalid-count、行原因、金额和 action 标记。 | 另一组 total/checkout-allowed/valid/form 标记及 CSS。 | 保留本地 U05、原DOM标记和CSS。已登录 data-add-cart 保留；游客新增 data-login-to-add，仅标识新登录入口。 |
| 文案与无障碍 | 已有唯一label/id、字段错误、刷新恢复入口。 | 有商品名 aria-label 等小改进。 | 本轮不作额外页面/CSS重构；仅在新增游客入口上提供可读标签和说明，避免扩大审查面。 |

## 两边旧证据与文档的区别

| 项目 | 本地原记录 | 组员原记录 | 本轮处理 |
| --- | --- | --- | --- |
| 受测身份 | 干净提交3bc5629，140运行输入。 | 未提交工作区，137输入，事后publication关联功能提交。 | 原始身份与限制原样保留；本轮固定新SHA、干净起点、140及以上运行输入重新验收。 |
| 工具链 | JDK21.0.12.1 / MySQL8.4.9；每SQL连接显式UTC。 | JDK21（安装目录标记21.0.7.6）/ MySQL8.4.13；原说明辅助SQL未逐连接显式UTC。 | 不把环境差异写成失败；新轮记录真实工具版本、端口、库UUID并逐连接UTC。 |
| HTTP覆盖 | 335 HTTP、154全部POST逐次七表；native50，browser302。 | 73顺序购物车POST及4双请求并发组共81 cart POST，590断言；Service31、Model18，browser463；不覆盖全部GET/登录/退出的逐POST审计。 | 数量和范围不可直接相加。旧并发观察不证明统一代码并发已验收；本轮重新执行要求内全部流程。 |
| 图片与视口 | 24图，1366/1920。 | 30页面图及2联系表，含390移动视口。 | 旧图原字节保留；新轮另产20–30图，含1366/1920及真实游客登录/手动加购过程。 |
| 文档 | 本地STEP07原实测和台账。 | 独立台账、publication及原限制说明。 | 不覆盖任一旧记录；新增“合并说明与最终验证”，实名继续待填，注明组员参与。 |

组员原目录从固定 tip 的 `docs/evidence/2026-11-14-step07/` 逐 Git blob 原字节导入 `../2026-11-14-step07-member/`，96个原文件均核对原blob与SHA；新增导入说明及清单不改原文件。本地 `../2026-11-14-step07/` 及所有既有证据不动。导入只读扫描未发现已知口令、BCrypt、实际CSRF/会话/Cookie值。

## 合并方式与新验收边界

1. 从本地 feat/step07-cart 创建 feat/step07-cart-merged。
2. 严格执行 `git merge --no-ff -s ours origin/feat/step07-cart`。这是 ours **合并策略**，保留两条提交历史，整体保留本地树；不是 `-X ours` 的逐文件冲突偏好。随后只提交上述两个选择性功能变化。
3. 不改 main，不改原本地 feat/step07-cart，不改任何 origin引用，不push、不force、不删分支。新合并提交记录父SHA及树一致性。
4. 两端Wrapper新构建、新私有MySQL、双端同库、新受测SHA与运行输入清单；不得借用两边旧结果。重新核加购/改量/移除/徽标/1–99与20种边界/跨账号/禁用与重登/真实游客登录后手动加购及其他表不变。
5. “禁用中途”额外用实际JAR Service在用户行锁等待期间由私有root夹具禁用推进认证戳，观察锁内复验拒绝；记录真实等待，不把此认证场景扩大称为订单并发或故障注入。

本文件在只读比较完成时形成；合并后实际提交与新的运行结果见本目录 README、result.json 和“合并说明与最终验证”，旧记录不会被改写。本目录名按任务指定为2026-11-15，执行时间保留真实时钟与时区，不据目录名伪造日期。
