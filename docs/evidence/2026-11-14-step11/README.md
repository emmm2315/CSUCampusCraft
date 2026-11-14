# STEP11 后台订单查询与模拟发货实测

2026-11-14，从已包含STEP10的干净main `8dd7794e5b84fbc9a95069b76a74b761218e6d0a` 创建 `feat/step11-admin-orders`。实际受测源码 **`39c96aaaad18c58dce9d57450e14317a75c29b3d`**。本步范围自动验收通过、组员实名复核待补；不修改main，不push。各实际轮次与结果以[result.json](result.json)、[原始轮次清单](original-attempt-inventory.json)为准，旧STEP07–10台账不改变。

## 轮次与外部工具审计

attempt1原工具记录PASS，业务HTTP/七表/native/浏览器观察保留，原result.json和所有原字节不追改为FAIL。事后[工具独立审计](tool-audit.json)发现两个断言局限：原始响应的BCrypt检测正则双转义，正常形状散列未被命中；归档scrub会遮盖散列，归档后扫描不能追补原响应未泄漏的证明。另外首发提示只查整页“发货”不足，且CI小写POST后工具跟随规范大写单号GET，没有按实际小写Location消费Spring FlashMap。

只修外部验证器：先用合成数据核对正确散列模式的正反例，再对脱敏前可得原响应扫描；303原样跟随Location并在role=status全局提示中核对完整首发/重复反馈。生产源码、183个运行输入和两个JAR不变；attempt2新私有库从种子完整重跑，最终结论只依新轮，不继承首轮断言。旧26图只在归档副本无损ZIP保留，stage原图及历史视觉报告不动。不能把首轮原PASS改称整轮失败，也不能将旧脱敏响应恢复为不存在的原始证明。

## 环境、输入与复现入口

Microsoft JDK21.0.12.1、根Maven Wrapper3.9.16、MySQL8.4.9/InnoDB，SQL连接UTC，页面Asia/Shanghai。本轮私有MySQL端口65113，用户JAR8080、管理JAR8081同库csucampuscraft；核对私有datadir/UUID/监听PID，未接触已有开发库。[数据库身份](attempt2/database-identity.json)、[版本](attempt2/versions.txt)、[监听归属](attempt2/listener-ownership.jsonl)。

两端真实Wrapper verify退出0、BUILD SUCCESS，用户端4.342秒、管理端4.150秒；新子终端没有Maven PATH，显式使用JDK21与已有离线settings/cache，不新增依赖或测试框架。[构建脚本](builds/build-fresh.ps1)、[用户日志](builds/build-user.log)、[管理日志](builds/build-admin.log)、[退出码](builds/build-exits.json)。

受测起点干净，183个运行输入，清单SHA-256 `eca6993a4cdffd98594ebaa48e093ec1e520d603eff407cb3747a698629822cb`；运行结束逐项不漂移。[输入清单](attempt2/runtime-inputs.sha256)、[17个源文件](source-publication.json)、[源码独立审查](source-review.json)、[149个既有保护文件](protected-source-preservation.json)。全部用户端代码、既有后台Java、两端POM、SQL、Wrapper与静态素材保持不变。新增CSS仅管理端A06/A07使用，原CSS字节前缀保留。

## 实际结果与七表边界

[本轮完整结果](attempt2/result.json)、[分类统计](delivery-metadata.json)、[HTTP索引](attempt2/http.jsonl)、[逐请求七表对照](attempt2/database-writes.jsonl.gz)、[独立重读结果](independent-observation-review.json)。HTTP、原生Service、浏览器检查分别计数，准备订单的用户端下单/支付也单独核对，不充当后台发货次数。

成功轮2136项主断言、0失败，202条捕获HTTP、53次POST、176份自动七表审计（含语义重复共218份）。17次发货POST=3次首次发货+3次无写成功+11次拒绝零写；原生另175项、22条SQL、12个有SQL的串行事务阶段（null actor另验证无SQL）。浏览器255项、26张新图，28个捕获文档响应是实际请求的子集。4条主HTTP成功发货链完整核对实际Location大小写和全局完整反馈；2条浏览器首发由实际DOM/PNG核对完整反馈。原响应扫描只覆盖已捕获可得的200份正文；2份303正文不可读，另2个浏览器A07跟随GET未捕获、未扫描，不扩大计数。

全部实际POST先后保存store_user/category/product/product_image/cart_item/sales_order/sales_order_item的有序全字段摘要与安全行状态；拒绝和无写成功逐请求核对七表不变。首次发货只允许目标主单status、shipped_at及数据库维护的updated_at改变；支付凭证、paid_at、总额、收货及商品快照、库存、商品version、购物车、明细保持原值。收货内容只保存不可逆摘要，HTML与截图遮盖原文。

用户端清空种子车后通过真实HTTP建立2本18元方格本+1盒49元礼盒的85元订单，完成模拟支付；管理员A06按完整单号CI/状态/顾客ID组合查到，A07模拟发货，再读取用户U08。双端读取同一主单的SHIPPED与首次发货时间，快照仍为成交值。后续当前商品资料改动是明确的隔离库root SQL夹具，不冒充后台业务操作；两个页面仍从原明细/收货快照展示。新增准备订单与native目标均由HTTP建立，native不造订单。

## 查询、授权与写事务

A06订单号strip后≤40码点、绑定等值SQL，按原列utf8mb4_0900_as_ci比较，不使用LIKE；空串不限。status为ALL或五种状态；可选userId空白为不限，非正整数/格式或Long越界400，未知或ADMIN404，停用CUSTOMER仍可查历史。orderNo/status/userId为AND条件，list/count同一WHERE，固定created_at/id倒序；默认size10、1–50，page小于1整数归1，非法/重复字段400，超末页及超大OFFSET200空态且保留条件和有效页链接。

A07全站详情只投影安全账号标签，不把密码散列放入页面；明细不JOIN当前商品代替成交值。仅PAID渲染带CSRF的发货确认，先显示订单号并要求核对收货快照；其他状态说明门槛，未知/格式不符路径404。顾客资料入口为文字占位，STEP12再接通。

发货Service显式READ_COMMITTED，首个数据库操作AdminWriteGuard锁操作者并复核ENABLED/ADMIN/原始UTC微秒authStamp，随后按订单号FOR UPDATE锁主单。PAID条件更新为SHIPPED，shipped_at=GREATEST(CURRENT_TIMESTAMP(6),paid_at)，影响必须为1行。SHIPPED/COMPLETED直接返回已处理，零DML保留原首次时间和整行；PENDING_PAYMENT/CANCELLED409；未知404。成功及幂等均303到详情、固定flash反馈。冲突页提供本单及列表恢复入口，无额外状态变更或真实物流。

游客/失效ADMIN先身份校验而302，缺错CSRF403。顾客在管理端登录统一失败，其用户端Cookie不能建立后台身份（302）；本轮未伪造已认证CUSTOMER后台会话。实际已认证错角色403由外部原生工具调用真实AdminWriteGuard验证，两者证据边界分开。

原生[NativeAdminOrderProbe.java](attempt2/NativeAdminOrderProbe.java)与[日志](attempt2/native-probe.log)记录受测JAR真实Spring事务、RC、同一物理连接、先ADMIN锁再订单锁、唯一发货条件UPDATE与影响1行；无商品/明细锁或DML。串行幂等、非法状态和旧认证戳等按实际日志核对。外部工具先用真实MyBatis ParamMap验证containsKey保护，见[native预检](native-tools/preflight1/metadata.json)。null actor在SQL前被拒绝，不冒称该分支测得连接隔离级别。没有并发、竞争或故障注入。

## 截图与真实浏览器请求

26张本轮新PNG，1366×768与1920×1080视口，均实际逐图查看：[视觉复核](ui-visual-review.json)。fullPage实际高度可大于视口。浏览器POST303真实采集，2份重定向正文明确body_available=false。两个后续A07 GET未分配route ID、未归档网络正文，其实际状态和完整首发提示由DOM断言/截图证明；下一条已捕获同路径请求是8080的U08，绝不替代8081的A07响应。主HTTP4条成功链另有真实A07正文完整反馈。[捕获边界](verification/tool-fix/browser-capture-boundary.json)。不造缺失响应或将其混入200份已捕获正文扫描。截图中的收货值用浏览器遮罩，截图本身不证明被遮盖字段原文；业务字段另由内存校验和SHA/安全SQL对照证明。

| 场景 | 1366视口 | 1920视口 |
| --- | --- | --- |
| a06-CUSTOMER-page2-preserves-filter | [1366](attempt2/browser/a06-CUSTOMER-page2-preserves-filter-1366.png) | [1920](attempt2/browser/a06-CUSTOMER-page2-preserves-filter-1920.png) |
| a06-CUSTOMER-status-exact-order | [1366](attempt2/browser/a06-CUSTOMER-status-exact-order-1366.png) | [1920](attempt2/browser/a06-CUSTOMER-status-exact-order-1920.png) |
| a06-after-ship-filter | [1366](attempt2/browser/a06-after-ship-filter-1366.png) | [1920](attempt2/browser/a06-after-ship-filter-1920.png) |
| a06-allsite-orders | [1366](attempt2/browser/a06-allsite-orders-1366.png) | [1920](attempt2/browser/a06-allsite-orders-1920.png) |
| a06-empty-intersection | [1366](attempt2/browser/a06-empty-intersection-1366.png) | [1920](attempt2/browser/a06-empty-intersection-1920.png) |
| a06-invalid-query-400 | [1366](attempt2/browser/a06-invalid-query-400-1366.png) | [1920](attempt2/browser/a06-invalid-query-400-1920.png) |
| a06-outofrange-recovery | [1366](attempt2/browser/a06-outofrange-recovery-1366.png) | [1920](attempt2/browser/a06-outofrange-recovery-1920.png) |
| a07-completed-keeps-first-shipped-time | [1366](attempt2/browser/a07-completed-keeps-first-shipped-time-1366.png) | [1920](attempt2/browser/a07-completed-keeps-first-shipped-time-1920.png) |
| a07-missing-CSRF-403 | [1366](attempt2/browser/a07-missing-CSRF-403-1366.png) | [1920](attempt2/browser/a07-missing-CSRF-403-1920.png) |
| a07-paid-confirm-before-ship | [1366](attempt2/browser/a07-paid-confirm-before-ship-1366.png) | [1920](attempt2/browser/a07-paid-confirm-before-ship-1920.png) |
| a07-unknown-order-404 | [1366](attempt2/browser/a07-unknown-order-404-1366.png) | [1920](attempt2/browser/a07-unknown-order-404-1920.png) |
| journey-admin-first-shipped | [1366](attempt2/browser/journey-admin-first-shipped-1366.png) | [1920](attempt2/browser/journey-admin-first-shipped-1920.png) |
| journey-user-same-shipped-snapshot | [1366](attempt2/browser/journey-user-same-shipped-snapshot-1366.png) | [1920](attempt2/browser/journey-user-same-shipped-snapshot-1920.png) |

## 完整性、范围与收口

只归档新轮观察，既有4232份证据及原分支/远端引用的保护结果见[baseline-preservation.json](baseline-preservation.json)。压缩只在归档副本进行，commands/database-writes无损gzip见[压缩索引](compressed-text-index.json)；原轮结果保留，旧图无损ZIP映射在[artifact-references.json](artifact-references.json)。原stage未改写。HTTP正文摘要、PNG摘要、原轮完整清单、文档/源码冻结和脱敏结构由final-audit.json复核，evidence-files.json列除自身外原始字节摘要；新目录Git设-text避免换行转换。原轮known-private扫描保留，最终结构扫描不重建已丢弃私密输入。

本轮进程已停，路径范围严格核对后才清理本轮私有runtime/attemptN；实际结果见cleanup.json。不归档MySQL数据目录、密码、Cookie/CSRF/确认原值、完整收货信息、JAR/class/cache。TST-29/30仅登记本步后台查询、模拟发货和双端新单/快照联查；TST-39顾客管理留STEP12，同步竞争和中途故障回滚留STEP13。未实现后台支付/取消/确认收货、真实支付、退款、物流或控制台。AI执行与复核不能代替M3前组员实名签字。
