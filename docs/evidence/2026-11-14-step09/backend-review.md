# STEP09 后端自检与交接

受测源码由主执行单元固定为 `f8b01088b5f4b9e335d3ee86587e2695ffba0e7a`。本记录由后端初稿作者执行静态自检，不能替代独立组员复核或新运行验收。14 个候选 Java 文件在主执行单元发布前用 JDK21 `javac --release 17` 私有编译通过；主执行单元另已执行真实双端 Wrapper 构建，完整日志以新证据为准。

`OrderSubmissionCoordinator` 在本端 Java 会话监视器内调用单独 Spring 代理的 `OrderService.submit`；代理真正提交或回滚后才返回。Service 显式 READ COMMITTED，第一个数据库操作为 `CustomerWriteGuard.lock(actor)`。之后才读最新确认与当前整车、校验收货字段，按商品 ID 升序锁所有商品、锁内重算价/状态/库存/版本及金额，第一条 INSERT 前再调用 `CheckoutService.requireCurrent` 校验同一确认仍为本会话本人最新且未过期。该最后检查不访问数据库，使用既有 UTC Clock。

主单初态 PENDING_PAYMENT，支付三字段 NULL。名称、SKU、封面和价格来自锁内商品，收货值来自服务端长度校验并规范化的本次请求。每条小计与合计均 BigDecimal 两位小数、正数、不超 DECIMAL(12,2)。16 字节安全随机值编码为32位十六进制，冠 `CSU-` 后36字符，匹配既有返回路由白名单；数据库原唯一索引提供大小写不敏感的最终冲突判断，冲突不自动重放。

全部插入、生成ID、库存/version条件扣减与确认车精确删除均检查影响行数；删除含 userId/itemId/productId/quantity/version 条件，不按 userId 删除整车。任意异常整体回滚。字段400保持有效确认，业务409清当前确认，其他技术异常由通用500处理；提交成功后才条件清会话确认，已结束会话的清理不影响已提交订单结果。Java会话同步不替代数据库用户锁和商品锁。

U07 查询固定本人，完整号 trim 后0–40码点，普通绑定等值SQL沿用列的CI排序规则，状态/页码/条数服务端校验；count/list同WHERE，固定创建时间及ID倒序。不可表示或超过末页的OFFSET返回200空页。U08未知、格式不符或他人单号统一404；明细只按已核对归属的主单读取历史快照，不JOIN当前商品。时间原值为UTC LocalDateTime，只在显示getter转换北京时间；空状态时间getter返回null。

未新增依赖、SQL、管理端或支付/取消/发货入口。`ORDER_SUBMISSION_PENDING`已从当前生产入口移除；历史文档与旧证据应继续保留并注明旧阶段语义。本步用户端U08与SQL可以核对成交快照，但管理端订单详情尚未实现，完整双端HTTP对照留STEP11。TST-16/17/35的并发和故障注入继续留STEP13，顺序重放或源代码检查不能代替它们。
