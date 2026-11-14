# STEP07 后端只读差异比较

本地 `dda8f8254eec3f63e9c3bede397131cbe55c6179`；组员 `221dfb6dfa4fe93d69ffe1eecda97e98705406e1`；共同基线 `a1d4f3523f557af63fc77ea883986c099edcd93e`。本报告只比较 Git 对象，未修改仓库，尚不宣称合并后验收通过。

| 项目 | 本地实现 | 组员实现 | 合并取舍与原因 |
| --- | --- | --- | --- |
| Service/页面 API | read(userId)、quantityFor(userId)；CartPage 暴露 quantity/validSubtotal/invalidCount/itemCount/empty/hasInvalidItems/allValid。 | getCart(userId)、quantity(userId)；CartPage 暴露 total/checkoutAllowed/totalQuantity/empty。 | 保留本地 API。HTTP 路由相同，但 Java/模板模型不兼容；本轮只允许限定移植，不做全栈 DTO 重命名。 |
| CartItem 与读模型 | CartItem 仅持久字段，含 createdAt/updatedAt；AUTO 主键回填并检查 ID；CartLine 为独立当前商品投影，提供 invalidCode/publicProduct/valid/subtotal。 | CartItem 同时承载车行和 JOIN 商品字段；CartLine 是 Service 创建的 record，Service 做缺失商品/封面回退。 | 保留本地实体和读模型。保留时间与生成 ID 的可核对性、既有 U05 字段和 data-* 状态标记；组员的空值回退不在本轮指定移植范围。 |
| 商品查询与种类统计 | 先读取本人至多 20 行车，再按 productId 查找已有行；商品用普通 SELECT；种类用读取行数。 | 按 userId/productId 查单行，另 countKinds COUNT(*)；商品用 FOR UPDATE。 | 保留本地查询策略，不移植商品锁或 countKinds 重构。COUNT(*) 在组员代码只用于 SKU 种类检查，并非徽标错误；两种有界读法均能表达 20 种规则。购物车不预留库存，按需求只锁用户行即可，避免无必要地与后台商品写互相阻塞。 |
| 写守卫位置与首锁 | auth.CustomerWriteGuard 经 StoreUserMapper.selectForUpdate 锁操作者。 | cart.CustomerWriteGuard 经 CartItemMapper.lockUser 锁操作者。 | 保留 auth 包和 StoreUserMapper。两边均 MANDATORY，要求已有 READ_COMMITTED 写事务，并复核 ENABLED、CUSTOMER、完整 authStamp；本地位置更便于后续结算/订单复用，避免认证查询耦合到购物车 Mapper。 |
| 改量不可用商品状态 | 实际改量调用与加购共用 available(product)，不存在/DRAFT 为 404 PRODUCT_NOT_AVAILABLE。 | 实际改量用 409 CART_PRODUCT_UNAVAILABLE，提示下架/不可用后移除；加购仍 404 CART_PRODUCT_NOT_FOUND。 | 仅为本地实际改量分支移植 409 CART_PRODUCT_UNAVAILABLE，文案按本轮指定“请移除该条目后继续选购”。已有本人车条目仍存在，商品状态变化属于恢复性冲突；加购未知/DRAFT 继续维持原矩阵 404，不改其他稳定 code。 |
| 同值与失效语义 | 所有者与版本校验后，同 quantity 立即成功返回，早于商品状态/库存与版本上限检查。 | 先锁商品并校验状态、库存，再判断同 quantity 无操作。 | 保留本地同值规则；不可整段移植 member changeQuantity。本轮明确有效版本同值仍 303、零写、零增版，包括已失效行和 MAX 版本；成功无操作不解除购物车失效/结算阻断。 |
| 版本、归属和移除 | 条目不存在404、非本人403、旧版409；更新/删除绑定 userId/id/version 并检查行数；移除不读商品状态。 | 同样使用归属404/403、旧版409、条件更新/删除及影响行数；失效行可移除，删除不增版。 | 保留本地实现。核心约束等价；本地已保留 MAX 版本移除及原始数量/版本证据，避免不必要差异。 |
| Controller 原值与冲突恢复 | CartForm 保留 quantity 和提交 version；失败动作单独回显原值，其他行使用当前版本；错误摘要映射 item-<id>-<field>。 | 主要保留 quantityInput，模板隐藏 version 取当前行；cartConflict 提供刷新提示。 | 保留本地 CartForm、原版本及错误锚点。避免失败页把旧提交悄悄替换为新版本后再次提交；保持当前 data-* 与审核工具约定。 |
| 加购失败页面 | 能公开读取商品时在 U03 回显；非法 ID 或已不可用商品时保持原 POST 失败，由通用错误页处理。 | 无法重读公开详情时回本人 U05，同时保留失败状态。 | 保留本地失败回显分支。本轮只取指定游客 UX 和改量409，不扩展失败页路由/模型；双方都不应泄露不可公开或他人商品/车数据。 |
| 角色与 CSRF 次序 | AuthFilter +10 对 cart POST 错角色仅设标记，CsrfFilter +20 后由 MVC preHandle 拒绝角色，再解析参数。 | AuthFilter +10 直接拒绝错角色，早于 CsrfFilter +20。 | 保留本地入口顺序。符合原 STEP07 明确的 身份→CSRF→角色→参数 次序；组员版本也返回403，但不能据同状态码认为次序相同。 |
| 游客 POST 防御回跳 | CartRequestNavigation 从单个合法正整数 productId 生成固定商品 GET；其他车写回 /cart；白名单校验，不自动重放。 | AuthFilter 对非 GET 统一回 /。 | 保留本地防御性 POST 行为；常规游客 UI 将另按指定改为登录链接。游客不再有详情 POST 表单，但直接构造请求仍须安全、可恢复且不自动重放。 |
| 徽标 SQL 与错误态 | quantityFor 使用 COALESCE(SUM(quantity),0) 仅按 user_id；PageModelAdvice 可重查直接错误页身份，失败标记防重复查询，显示不可用而非0。 | quantity 使用同一 SUM 口径；PageModelAdvice 依赖现有 request.currentUser，捕获 DataAccessException/TransactionException 并用 cartQuantityAvailable 标志显示不可用。 | 保留本地徽标 SQL、模型名与直接错误页处理。两边正常 SUM 均含失效行且没有商品联表/过滤；不可用标志命名与行为不同，不做未授权公共模型重构。 |
| 失败重新认证的旧徽标 | LoginController 清会话身份后，同时将已构建模型的 cartQuantity 归0并清不可用标志。 | 清 currentUser/authenticated，但未同步重置此前 PageModelAdvice 的 cartQuantity。 | 保留本地重新认证衔接。静态上存在匿名失败页残留旧徽标的可能，不能将此推断写成组员旧实测失败；新合并验收需再次验证。 |

## 源码定位

- ours_noop: `dda8f8254eec3f63e9c3bede397131cbe55c6179:csucampuscraft-user/src/main/java/org/csucampuscraft/storefront/cart/CartService.java:95`
- ours_change_product_read: `dda8f8254eec3f63e9c3bede397131cbe55c6179:csucampuscraft-user/src/main/java/org/csucampuscraft/storefront/cart/CartService.java:96`
- member_noop: `221dfb6dfa4fe93d69ffe1eecda97e98705406e1:csucampuscraft-user/src/main/java/org/csucampuscraft/storefront/cart/CartService.java:108`
- member_change_unavailable: `221dfb6dfa4fe93d69ffe1eecda97e98705406e1:csucampuscraft-user/src/main/java/org/csucampuscraft/storefront/cart/CartService.java:104`
- member_product_lock: `221dfb6dfa4fe93d69ffe1eecda97e98705406e1:csucampuscraft-user/src/main/java/org/csucampuscraft/storefront/cart/CartItemMapper.java:48`
- ours_product_read: `dda8f8254eec3f63e9c3bede397131cbe55c6179:csucampuscraft-user/src/main/java/org/csucampuscraft/storefront/cart/CartItemMapper.java:37`
- ours_guard: `dda8f8254eec3f63e9c3bede397131cbe55c6179:csucampuscraft-user/src/main/java/org/csucampuscraft/storefront/auth/CustomerWriteGuard.java:26`
- member_guard: `221dfb6dfa4fe93d69ffe1eecda97e98705406e1:csucampuscraft-user/src/main/java/org/csucampuscraft/storefront/cart/CustomerWriteGuard.java:30`
- ours_badge: `dda8f8254eec3f63e9c3bede397131cbe55c6179:csucampuscraft-user/src/main/java/org/csucampuscraft/storefront/cart/CartItemMapper.java:24`
- member_badge: `221dfb6dfa4fe93d69ffe1eecda97e98705406e1:csucampuscraft-user/src/main/java/org/csucampuscraft/storefront/cart/CartItemMapper.java:32`

组员证据中的既有成功/并发声称应按原 SHA 独立保留；本报告未将它们当作合并后结果。
