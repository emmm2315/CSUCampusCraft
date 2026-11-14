# STEP10 模拟支付与待支付取消实测证据

2026-11-14，从已合并STEP09的干净main `dc2033da0ee52eb478999031c4f6838d6434d70b` 创建 `feat/step10-payment`。受测源码 **`b0253a5ecc920dfa862eec0eb8358f301ac41c10`**。**同一源码修正验证工具后，新私有库attempt2全量自动验收通过；台账待复核。** 不改main、不push，组员实名与交叉复核待补。

## 轮次和工具修复

attempt1整体FAIL保留：[原结果](attempt1/result.json)、[诊断](attempt1-diagnostic.json)。该轮HTTP状态矩阵和24张浏览器图、真实点击通过；原生探针仅9项前置检查通过，随后外部Trace将MyBatis严格ParamMap当普通Map，get缺失键抛BindingException，包装为MyBatisSystemException。原轮native前后七表对照未归档，不追补、不宣称已证明该阶段零写。空SQL trace与失败位置只是代码/诊断推断。离线用真实ParamMap重现后，仅给外部工具加containsKey防护与8项结构回归；生产源码和两个JAR均不变。[工具诊断](native-tool-diagnostic/)保留原字节与日志；修正编译和结构结果在[native-preflight-fixed](native-preflight-fixed/)。

attempt2重新创建私有实例、导入种子、完整运行HTTP/浏览器/native；不继承首轮通过结论。[完整结果](attempt2/result.json)、[轮次摘要](attempts-summary.json)、[分类指标](delivery-metadata.json)、[独立复核](independent-observation-review.json)。新工具在判断native退出前先写前后对照，避免再次漏采失败观察。

成功轮168个运行输入，清单SHA-256 `443291ac2bfd32c5ff0fe4b9f50ff584956753dca870c879304a03c44af07ca9`，起测干净，结束未漂移。[清单](attempt2/runtime-inputs.sha256)、[源码变更](source-publication.json)。[100个受保护文件比对](step09-source-preservation.json)确认STEP09订单/结算/身份Java、管理端、SQL、Wrapper和素材与本轮起点一致。

## 构建、运行与证据入口

Microsoft JDK21.0.12.1、Wrapper Maven3.9.16、MySQL8.4.9/InnoDB。两端实际Wrapper verify均BUILD SUCCESS/退出0（用户端3.548秒、管理端1.709秒），复用已有离线settings/cache，Maven不在子终端PATH。[原始命令及构建日志](builds/)。没有新依赖或测试框架。私有MySQL失败轮60661、成功轮53912，各自UUID/datadir核验；SQL连接UTC，用户/管理JAR同库csucampuscraft，在8080/8081核验监听PID。[成功库身份](attempt2/database-identity.json)、[启动](attempt2/launches.jsonl)、[监听归属](attempt2/listener-ownership.jsonl)、[版本](attempt2/versions.txt)。原开发库未触及。

HTTP原始索引：[attempt2/http.jsonl](attempt2/http.jsonl)；逐请求七表有序全字段摘要与安全行状态：[database-writes](attempt2/database-writes.jsonl.gz)；动作前后：[action-observations](attempt2/action-observations.jsonl)。收货字段只留SHA，HTML/截图遮挡，不保存密码、Cookie/CSRF/确认原值或完整收货信息。模拟支付凭证可按本任务记录，不是真实支付凭据。

## 状态机与七表观察

支付/取消均在READ_COMMITTED事务内首先CustomerWriteGuard锁当前用户并复验ENABLED/CUSTOMER/UTC微秒authStamp，再按order_no+user_id锁本人订单。未知、格式不符和他人统一404；本人资源定位后解析result，缺失/非法/重复400，然后判状态409。CSRF403和无身份302沿用原过滤器。

PENDING_PAYMENT模拟FAILURE是合法303，七表不变，支付三字段NULL，详情闪存提示仍待支付可重试/取消。首次SUCCESS只改订单status/payment_method/payment_no/paid_at/updated_at，MOCK+CSUPAY-32hex共39字符，数据库CI唯一键兜底；paid_at取GREATEST(CURRENT_TIMESTAMP(6),created_at)。PAID/SHIPPED/COMPLETED重复SUCCESS保留原凭证、原时间和整行；这些状态FAILURE/取消409；CANCELLED任何合法支付结果409。所有支付不读改商品库存，金额只取成交订单，客户端金额/凭证/时间/user_id均不采信。

取消只允许本人PENDING_PAYMENT；取不可变明细，按product_id升序锁全部商品，先检查所有库存/版本溢出，再按原数量在当前stock上加值、version+1，逐条核对影响1行，最后同事务写CANCELLED/cancelled_at。原DRAFT状态及名称、价格、封面保持，快照/明细/购物车不改。重复取消整七表无写，保留首次取消时间；PAID及后续状态409。测试先为现购物车另加不同SKU一件，取消后该行数量/version及徽标1原样，不把购入商品放回车，也不清后来加入的条目。[非空购物车对照](attempt2/nonempty-cart-cancel.jsonl)。

礼盒独立购买2盒98元后取消，只返礼盒2盒、该商品version加1，组成单品不联动。stock=INT_MAX、product.version=LONG_MAX等自然边界409零写，不把预检查拒绝称为中途故障回滚。商品改名/改价/换封面/下架是明确root SQL夹具，支付仍按原订单金额、成交快照不变；不是后台业务入口。

原生[NativePaymentProbe](attempt2/NativePaymentProbe.java)/[日志](attempt2/native-probe.log)调用真实PaymentService，记录Spring/JDBC RC、同一物理连接、首用户锁→本人订单锁→取消商品升序锁、全部商品锁先于返库DML、条件更新和影响行数，以及失败/重放无DML。两张目标单由HTTP创建，native只执行状态动作，不创建订单，动作统计与HTTP分开。新单明细本就由STEP09升序插入，不虚构逆序明细测试。没有做并发、竞争或故障注入。

独立重读实际归档HTTP、SQL安全行和PNG摘要，复验首次支付的唯一凭证/原快照、所有支付商品不变、取消精确返库及各类无写分支。[独立结果](independent-observation-review.json)记录实际数量，不合并不同层次断言冒充业务用例数。

## 浏览器与截图

通过轮直接提供24张新PNG，分别1366×768和1920×1080视口；有真实按钮点击的失败支付→成功支付→303详情，以及展开取消提示后确认提交。实际POST303与目标GET分别采集，不能读取的跳转正文标body_available=false，不伪造正文。两视口使用不同新订单；所有截图来自新轮，不复用失败图。[实际视觉检查](ui-visual-review.json)。收货遮罩图不单独证明字段内容；fullPage高度可以超过视口。

| 场景 | 1366视口 | 1920视口 |
| --- | --- | --- |
| journey-cancelled-no-cart-restore | [1366](attempt2/browser/journey-cancelled-no-cart-restore-1366.png) | [1920](attempt2/browser/journey-cancelled-no-cart-restore-1920.png) |
| journey-failure-still-pending | [1366](attempt2/browser/journey-failure-still-pending-1366.png) | [1920](attempt2/browser/journey-failure-still-pending-1920.png) |
| journey-success-first-receipt | [1366](attempt2/browser/journey-success-first-receipt-1366.png) | [1920](attempt2/browser/journey-success-first-receipt-1920.png) |
| u08-cancel-confirmation | [1366](attempt2/browser/u08-cancel-confirmation-1366.png) | [1920](attempt2/browser/u08-cancel-confirmation-1920.png) |
| u08-cancelled | [1366](attempt2/browser/u08-cancelled-1366.png) | [1920](attempt2/browser/u08-cancelled-1920.png) |
| u08-paid-receipt | [1366](attempt2/browser/u08-paid-receipt-1366.png) | [1920](attempt2/browser/u08-paid-receipt-1920.png) |
| u08-shipped-first-receipt | [1366](attempt2/browser/u08-shipped-first-receipt-1366.png) | [1920](attempt2/browser/u08-shipped-first-receipt-1920.png) |
| u09-CSRF-403 | [1366](attempt2/browser/u09-CSRF-403-1366.png) | [1920](attempt2/browser/u09-CSRF-403-1920.png) |
| u09-foreign-404 | [1366](attempt2/browser/u09-foreign-404-1366.png) | [1920](attempt2/browser/u09-foreign-404-1920.png) |
| u09-pending-teaching | [1366](attempt2/browser/u09-pending-teaching-1366.png) | [1920](attempt2/browser/u09-pending-teaching-1920.png) |
| u09-state-conflict | [1366](attempt2/browser/u09-state-conflict-1366.png) | [1920](attempt2/browser/u09-state-conflict-1920.png) |
| u09-unknown-404 | [1366](attempt2/browser/u09-unknown-404-1366.png) | [1920](attempt2/browser/u09-unknown-404-1920.png) |

失败轮24张原图未删，归档副本改用[无损ZIP](attempt1/browser/screenshots.zip)保存，避免把两轮48张图混作同一验收图集；[迁移索引](artifact-references.json)逐图给原路径、ZIP条目和原始字节SHA。原stage的PNG及原browser/result.json不动，ZIP解压后逐字节一致。两轮单号/时间不同，不声称图片同SHA去重。成功轮24张已逐张视觉复核，失败图只作为原轮历史。

## 范围与完整性

TST18–22/34只覆盖本步支付、取消、快照、权限和独立礼盒；管理端订单详情/发货留STEP11。开发计划STEP10原有故障注入文字保留，但本轮按用户明确边界将TST23/24及同步竞争/中途失败回滚留STEP13，不声称已验证。真实支付、退款、物流、发货、确认收货均未实现。

两轮原始stage记录保持原字节；仅归档副本commands/database-writes无损gzip，见[压缩索引](compressed-text-index.json)。HTTP正文按脱敏字节SHA核对，原轮敏感扫描分别保存；最终包逐文本、gzip及ZIP条目复核，evidence-files.json列除自身外字节摘要。不归档JAR/class/cache或MySQL数据目录。

全部本轮进程已停；两私有目录经绝对路径范围验证后清理见cleanup.json。main、原分支/远端引用、3905份旧证据保持原样。STEP07/08/09台账仍待复核，STEP10同样待组员实名复核（M3前）；AI执行与自查不能替代组员签字。
