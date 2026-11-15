# STEP13 状态与确认令牌边界补验

受测 d577179e4468354552d3f5f48d624a4296ee3cfb。这是 TST-13/20/21/29 指定边界的独立补验，不是39项完整验收或四条复合用例全覆盖。

69条真实HTTP、28次POST，333项业务断言0失败，四个有界子矩阵项均PASS。覆盖COMPLETED发货重放；PAID取消拒绝；CANCELLED两种模拟支付拒绝；SHIPPED/COMPLETED成功重放保持首次凭证、失败拒绝；U09 pending200金额、本人非pending409、他人404及游客302。跨会话同账号和跨账号提交原确认令牌都使用当前CSRF并409；原持有会话仍用同一令牌到达U06字段400且保留令牌，独立证明未被其他会话消费。

原attempt1 result.json保持FAIL：原因仅为进程已停后的Python rmtree PermissionError，原HTTP、七表、333项断言和原清理失败记录未改写。随后核对自有绝对路径、PID停止及18080/18081/62964无监听，PowerShell仅删除该补验runtime，独立cleanup-retry.json为PASS。请按“补验业务及子矩阵PASS＋原清理失败后重试PASS”引用，不把原整体结果改成PASS。

私有MySQL62964；观察8080/8081实际占用后使用18080/18081。199个运行输入结束无漂移。敏感扫描64份文本、34份解压正文、30个已知私密值，0发现。购物车准备动作单独记账，其余状态/令牌边界逐次七表零写；订单、支付、库存和快照未被补验改变。源脚本与新harness快照、真实运行输入、HTTP、前后数据库记录和artifacts.sha256均在evidence/attempt1；新汇总见delivery-summary.json。本人/组员未新增人工执行或签署。
