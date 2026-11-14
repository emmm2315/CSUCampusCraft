# G 文档、路由与 Word 只读核对

执行者：Codex AI；不代表本人或组员完成了人工复核。

受测源码：`0329c9810c4ad2719c4ae95190ff516d1d21a9ed`。结论来自本次读取当前树、抽取Controller注解及Word XML，不引用旧证据结论。

## 当前路由静态对照

| 端 | 实际P0 SSR路由 | 文档P0 SSR路由 | 源码独有 | 文档独有 |
| --- | --- | --- | --- | --- |
| user | 17 | 17 | [] | [] |
| admin | 28 | 28 | [] | [] |

排除 verification profile 的10个非持久探针、P1 receipt、未来REST预留。静态一致不替代HTTP实测。完整方法/路径/源文件行号见 audit.json。

## 问题与待统一事项

### DOC-01 · P2 · 文档缺项

需求改量表的失败列未明确下架/不可用商品改量返回409；BR-04已有上架校验总则。当前实现先处理有效版本同值数量（无写入成功），真实改量再查商品状态并409。

后续文档更新补齐409及同值幂等条件；运行态以本轮B阶段HTTP为准。

- `docs/需求与业务规则.md` line 81: 一账号与一商品组合唯一，重复加购累加。每个 SKU 合计数量为 1–99 的整数，整车至多 20 种 SKU。添加和修改时校验上架状态及当前库存，修改或移除校验条目版本。已失效的条目可以移除。写车时锁住当前用户行，并在锁后复核启用状态与会话 `authStamp`，同账号并发加购不会生成重复记录，旧版本拒绝覆盖。
- `docs/需求与业务规则.md` line 192: | 改量 | 按本人 `itemId` 提交新的 `quantity` 和当前 `version`。 | 数量实际变化时递增条目版本。值相同且版本有效时保留原行与版本。 | 非整数和范围错误返回 400，旧版本或库存不足返回 409，提示刷新当前购物车。 |
- `csucampuscraft-user/src/main/java/org/csucampuscraft/storefront/cart/CartService.java` line 94:             // A valid same-value request does not modify an invalid row or consume a version.
- `csucampuscraft-user/src/main/java/org/csucampuscraft/storefront/cart/CartService.java` line 95:             if (current.getQuantity() == quantity) return;
- `csucampuscraft-user/src/main/java/org/csucampuscraft/storefront/cart/CartService.java` line 98:                 throw new BusinessException(HttpStatus.CONFLICT, "CART_PRODUCT_UNAVAILABLE",
- `csucampuscraft-user/src/main/java/org/csucampuscraft/storefront/cart/CartService.java` line 99:                         "商品已下架或不可用，请移除该条目后继续选购。");

### DOC-02 · P2 · 文案待统一

U03游客有货时为登录链接，模板文案“登录后加购”；提示要求返回本页由本人确认。符合先登录再手动加购流程，但规格中的“加入购物车”动作描述未规定链接的确切标签。

记录当前真实文案；后续统一交互措辞，不判为功能失败。

- `csucampuscraft-user/src/main/resources/templates/products/detail.html` line 65:                     <a th:if="${product.stock > 0}" class="button" data-login-to-add
- `csucampuscraft-user/src/main/resources/templates/products/detail.html` line 66:                        th:href="@{/login(returnUrl=${'/products/' + product.id})}" aria-describedby="guest-purchase-help">登录后加购</a>
- `csucampuscraft-user/src/main/resources/templates/products/detail.html` line 69:                        th:text="${product.stock == 0 ? '商品已售罄，暂不可购买。' : '请先登录，返回本页后由本人选择数量并确认加购。'}">购买说明</p>
- `docs/页面清单与原型.md` line 13: | U03 商品详情 `/products/{productId}` | 公开，REQ-03、REQ-05 | 面包屑、封面、相册、名称、SKU、价格、库存和纯文本设计说明。输入数量后加购，游客先登录。 | 无相册回退封面，资源缺失显示占位图。售罄显示库存状态并禁用加购。下架或不存在时返回可继续浏览的 404。 |
- `docs/页面清单与原型.md` line 48: | U03 | 数量默认 1，界面提示可售上限，展示名称、SKU、单价、封面及可选相册。 | 游客前往本端登录，成功后返回详情再手动加购。登录用户加购成功 303 进入 U05 并按全车数量和读取徽标。格式或数量范围错误 400，商品未知或下架 404，售罄、超库存、合并超 99 或第 21 种 SKU 409，均保留原车。会话无效先本端重登，错角色或 CSRF 403。页面给出对应字段、刷新详情或购物车入口。 |

### DOC-03 · P2 · 契约不一致

TST-40标准把缺失父版本列为400；当前requireVersion缺失/空白返回409 PRODUCT_IMAGE_VERSION_REQUIRED。

运行态由E阶段重跑确认；后续明确采用400还是409并统一契约。

- `docs/测试与验收用例.md` line 494: | TST-40 | REQ-03、REQ-16、BR-03、BR-11、BR-12、BR-15、BR-17 | 在 `/products/{productId}/images` 对测试商品新增、编辑路径/替代文本/排序及删除。覆盖相同值提交、旧/缺失父版本、其他父商品的 `imageId`、非法路径/排序、删最后一图，并发相册与商品编辑或库存变更。用同一已有素材请求两端静态资源。 | 列表按排序值/ID 升序，新增 ID 由库产生。每次真实相册变更与父 `version+1` 原子提交，相同值且有效版本不增版。先锁操作者并复核认证，再锁父商品校验 `productVersion`，旧版本 409，格式缺失 400，跨商品图片 404。任一失败无部分写入。删末图保留封面与文件，详情回封面、缺图再占位；历史订单快照不变。两端同一路径 HTTP 200、类型及字节一致。 | 操作请求、父版本与图片记录前后值、冲突结果、排序和回退截图、历史封面快照、两端及源文件哈希。 |
- `docs/测试与验收用例.md` line 544: | TST-40 | 路径覆盖合法 `images/` 文件、空串、超过 255 字符、外部 URL、盘符、`..` 穿越；`altText` 超过 120 字符、负数/非整数排序、缺失/非法 `productVersion`。 | 语法或字段错误返回 400，父版本和图片行不变。合法站内路径的文件暂缺可显示占位图，记录元数据和实际静态文件可用性是两项证据。 |
- `csucampuscraft-admin/src/main/java/org/csucampuscraft/admin/catalog/ProductImageService.java` line 108:         if (raw == null || raw.isBlank()) {
- `csucampuscraft-admin/src/main/java/org/csucampuscraft/admin/catalog/ProductImageService.java` line 109:             throw new BusinessException(HttpStatus.CONFLICT, "PRODUCT_IMAGE_VERSION_REQUIRED",
- `csucampuscraft-admin/src/main/java/org/csucampuscraft/admin/catalog/ProductImageService.java` line 110:                     "缺少商品版本，操作未提交，请重新载入相册页。",

### DOC-04 · P2 · 文档过时

README当前阶段已写M2闭环，但后文仍把购物车/订单写作后续版本、下一步STEP08；测试文档业务用例导语仍写TST-39继续待实施；路由表用户首页仍称当前主题读取页。

仅登记，STEP13/指导书更新时同步清理当前口径；历史实测段落不改写。

- `README.md` line 12: M0、M1 的原始实测，以及 STEP07–11 各自受测 SHA 和待复核台账保留。STEP12 顾客列表/详情、启停与 A02 真实控制台已实现，受测 `03384367c87147f1c29859c799f3c464b016b760`，本步验证：通过（全新私有库正式attempt1，本步范围自动验收通过；台账待实名组员复核）。顾客页只读安全字段，真实启停单调推进认证戳，同值不写；控制台一条 SQL 读取五项真实计数，失败显示重试错误。M2 代码与各步已登记的本步范围自动验收闭环，仍待实名组员复核；STEP13 整体、并发和故障验收尚待执行，P1 收货未选做，REST 仅预留。
- `README.md` line 100: 打开上表两个首页。用户端可公开浏览；管理端未登录先进入登录页，用本端管理员教学账号登录后显示应用标识及「校园地标、学院风采、社团活动、校园运动、毕业纪念」。仅结构库没有种子账号：用户端公开页展示空态，管理端可打开登录页但没有可用教学账号；日常身份联调应使用演示库。用户端公开详情已实现，可从首页主题或毕业专区进入列表和详情；登录/退出见下方 STEP04 交接，购物车和订单属于后续版本。
- `README.md` line 130: STEP02–STEP05 已通过各自范围自动实测；STEP06 构建通过，正式验收结论见上方「当前阶段」及[STEP06 实测记录](docs/测试与验收用例.md#step06-实测记录)。M1 组员复核仍待补；STEP07 购物车实际覆盖见当前阶段，下一步为 STEP08 整车确认。新成员仍须在自己的环境复现 STEP01，并阅读下方公共基础与身份交接；后台和交易写不能只依赖入口过滤器授权。
- `docs/测试与验收用例.md` line 429: 以下表格保留完整验收标准。STEP03 浏览及 STEP04 双端身份已覆盖的部分见上方对应实测记录。TST-05/06/07/31 只确认 STEP04 已覆盖的身份/CSRF 部分，TST-25–28 的 STEP05 顺序维护/版本/补货部分见实测，购买、并发与故障注入留 STEP13；未覆盖业务仍待实施；TST-04 的加购、TST-31 后续业务写及 TST-39（STEP12）继续待实施，TST-36 另须先确认选做。每条写入验证记录请求和业务数据前后值。无副作用的断言在独立连接读取已提交数据。
- `docs/系统设计与路由.md` line 67: | `GET /` | U01 首页 | 公开。当前为主题读取页，业务阶段展示导航、新品、推荐和毕业入口。 | REQ-01、REQ-02 |

### DOC-05 · P2 · 待更新

Word前言仍为M0已完成、M1尚未开工，当前实现仅主题初始化；与README的M2代码闭环不一致。

Word待本人完成复核后统一更新，本轮不改。

- `docs/实验一 CSUCampusCraft 校园文创商店实验指导书.docx` XML paragraph 4: M0 工程初始化已完成，M1 业务开发尚未开工。已在本地独立目录和隔离 MySQL 自动复现双端构建、独立启动、同库读取、重启保留与共享图片，记录见《测试与验收用例》。以下业务步骤为待开工计划，预期结果是完成标准。
- `docs/实验一 CSUCampusCraft 校园文创商店实验指导书.docx` XML paragraph 97: M0 已独立复现双端单独及同时运行、同库改名、重启保留和共享图片。本步保留给新成员复现；当前实现仅到主题读取与初始化，规划页面待开发。
- `docs/实验一 CSUCampusCraft 校园文创商店实验指导书.docx` XML paragraph 283: STEP12 顾客管理与真实控制台
- `docs/实验一 CSUCampusCraft 校园文创商店实验指导书.docx` XML paragraph 338: 本页在 P0 功能开发后使用。M0 仅完成初始化，尚不具备完整交易页面；不能把以下步骤写成已演示。所有分支使用隔离测试库恢复初值，前一分支的变更不得隐含成为后一分支的夹具。

## 版本与边界

Word SHA-256：`1202242524c1e3947de820761b9a976376d8410615b43118202f1de69ff21f93`，本轮只读前后相同。
台账未修改；STEP02为通过，STEP03–12仍待复核。Word状态登记待更新。

运行命令：`python -X utf8 docs/evidence/2026-11-15-review/doc-audit/audit_docs.py`。
