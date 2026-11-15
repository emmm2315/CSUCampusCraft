# STEP13 本轮P0技术验收分段清单

本表按原编号列出39行，直接追溯本轮同一源码的新运行片段；TST-36为P1，未选取。自动化技术部分的PASS不代表真人签字或组员交叉复现。

| 编号 | 本轮核对内容 | 技术结论 | 原始分段来源 |
|---|---|---|---|
| TST-01 | 公开目录与数据库对照 | PASS | [主5:serial](attempt5/p0-matrix.json) |
| TST-02 | 首页两栏排序与边界 | PASS | [主5:serial](attempt5/p0-matrix.json)；[首页补验:home-edges](home-filter-supplement/attempt1/p0-matrix.json) |
| TST-03 | 筛选、字面搜索与分页 | PASS | [主5:serial](attempt5/p0-matrix.json)；[首页补验:combined-filters](home-filter-supplement/attempt1/p0-matrix.json) |
| TST-04 | 详情、错误与图片回退 | PASS | [主5:serial](attempt5/p0-matrix.json)；[主5:browser](attempt5/p0-matrix.json) |
| TST-05 | 双端登录与凭据保护 | PASS | [主5:serial](attempt5/p0-matrix.json) |
| TST-06 | 双端会话隔离 | PASS | [主5:serial](attempt5/p0-matrix.json) |
| TST-07 | 退出与失效身份拦截 | PASS | [主5:serial](attempt5/p0-matrix.json) |
| TST-08 | 加购判定与响应矩阵 | PASS | [主5:serial](attempt5/p0-matrix.json) |
| TST-09 | 持久购物车和SUM徽标 | PASS | [主5:serial](attempt5/p0-matrix.json)；[主5:restart](attempt5/p0-matrix.json)；[首页补验:invalid-badges](home-filter-supplement/attempt1/p0-matrix.json) |
| TST-10 | 购物车归属、版本与同值 | PASS | [主5:serial](attempt5/p0-matrix.json) |
| TST-11 | 失效车保留并阻止整车结算 | PASS | [主5:serial](attempt5/p0-matrix.json) |
| TST-12 | 收货字段与服务端金额 | PASS | [主5:serial](attempt5/p0-matrix.json) |
| TST-13 | 确认令牌、跨会话和整车变化 | PASS | [主5:serial](attempt5/p0-matrix.json)；[状态补验:edge](state-token-supplement/attempt1/p0-matrix.json) |
| TST-14 | 85元原子下单主线 | PASS | [主5:serial](attempt5/p0-matrix.json) |
| TST-15 | 锁内价格、状态、库存拒绝 | PASS | [主5:serial](attempt5/p0-matrix.json) |
| TST-16 | 下单三处故障整体回滚 | PASS | [新6:D1](attempt6/p0-matrix.json)；[新6:D2](attempt6/p0-matrix.json)；[新6:D3](attempt6/p0-matrix.json) |
| TST-17 | 重复确认与购物车并发 | PASS | [新6:C3](attempt6/p0-matrix.json)；[新6:C8](attempt6/p0-matrix.json) |
| TST-18 | 本人订单权限 | PASS | [主5:serial](attempt5/p0-matrix.json) |
| TST-19 | 成交快照双端不变 | PASS | [主5:serial](attempt5/p0-matrix.json) |
| TST-20 | 支付状态、重放与故障 | PASS | [主5:serial](attempt5/p0-matrix.json)；[新6:D5](attempt6/p0-matrix.json)；[状态补验:edge](state-token-supplement/attempt1/p0-matrix.json) |
| TST-21 | 待支付取消与状态边界 | PASS | [主5:serial](attempt5/p0-matrix.json)；[状态补验:edge](state-token-supplement/attempt1/p0-matrix.json) |
| TST-22 | 下架商品按成交数量返库 | PASS | [主5:serial](attempt5/p0-matrix.json) |
| TST-23 | 返库中途失败整体回滚 | PASS | [新6:D4](attempt6/p0-matrix.json) |
| TST-24 | 支付与取消竞争 | PASS | [新6:C4](attempt6/p0-matrix.json) |
| TST-25 | 后台分类与商品录入 | PASS | [主5:serial](attempt5/p0-matrix.json) |
| TST-26 | 分类引用与删除限制 | PASS | [主5:serial](attempt5/p0-matrix.json) |
| TST-27 | 商品旧版本与资料保护 | PASS | [主5:serial](attempt5/p0-matrix.json) |
| TST-28 | 补货增量与购买竞争 | PASS | [主5:serial](attempt5/p0-matrix.json)；[新6:C2](attempt6/p0-matrix.json) |
| TST-29 | 后台发货状态与竞争 | PASS | [主5:serial](attempt5/p0-matrix.json)；[新6:C5](attempt6/p0-matrix.json)；[状态补验:edge](state-token-supplement/attempt1/p0-matrix.json) |
| TST-30 | 双端订单精确筛选与分页 | PASS | [主5:serial](attempt5/p0-matrix.json) |
| TST-31 | CSRF、转义及写入响应 | PASS | [主5:serial](attempt5/p0-matrix.json)；[主5:admin-security](attempt5/p0-matrix.json) |
| TST-32 | 初始化、同库主线与重启技术复现 | PASS；真人复现另列未实施 | [主5:empty-demo](attempt5/p0-matrix.json)；[主5:restart](attempt5/p0-matrix.json) |
| TST-33 | 毕业专区导航和筛选 | PASS | [主5:serial](attempt5/p0-matrix.json) |
| TST-34 | 礼盒独立SKU交易 | PASS | [主5:serial](attempt5/p0-matrix.json) |
| TST-35 | 两个账号争抢最后一件 | PASS | [新6:C1](attempt6/p0-matrix.json) |
| TST-37 | 真实控制台统计及空态错误态 | PASS | [主5:serial](attempt5/p0-matrix.json)；[主5:empty-demo](attempt5/p0-matrix.json) |
| TST-38 | 顾客安全资料与关联订单 | PASS | [主5:serial](attempt5/p0-matrix.json) |
| TST-39 | 启停认证戳、旧会话和竞争 | PASS | [主5:serial](attempt5/p0-matrix.json)；[新6:C7](attempt6/p0-matrix.json) |
| TST-40 | 相册路径、父版本与竞争 | PASS | [主5:serial](attempt5/p0-matrix.json)；[新6:C6](attempt6/p0-matrix.json) |

TST-32真人组员独立复现：**未实施**。本轮仅由Codex AI验证初始化、同库运行、演示主线与持久重启等技术子项；旧人审仅保留原记录范围，不能扩写成本轮39项组员验收。组员交叉复核及负责人/复核人实名登记仍待补。

主5原整体FAIL仅采纳已完成片段，失败C1不进入并发结论。新6才是全部8个并发场景和5处故障回滚来源。各原始FAIL保持不变，详见[证据说明](README.md)和[逐段验证](parent-traceability-validation.json)。
