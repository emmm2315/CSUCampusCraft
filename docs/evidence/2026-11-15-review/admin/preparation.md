# E 执行器准备记录

本文件只记录执行器准备，不是阶段E已运行结论。`admin_review.py` 的 `run(r)` 必须在阶段A–D完成、主代理交接同一 `Review` 对象及新生成的 `paid_order`、`cancelled_order` 后调用。

准备时只读取当前源码/模板，未发送HTTP或业务SQL。已执行：

```powershell
python -X utf8 -c "import ast,pathlib; p=pathlib.Path('docs/evidence/2026-11-15-review/admin/admin_review.py'); ast.parse(p.read_text(encoding='utf-8')); print('AST_OK; no HTTP/SQL execution')"
```

退出0，输出 `AST_OK; no HTTP/SQL execution`。Python启动器仍打印real-location提示，未阻止解析。

准备过程中首次猜测的模板路径 `dashboard.html`、`orders/list.html`、`customers/list.html` 不存在，`Get-Content` 报错；随后 `rg --files csucampuscraft-admin/src/main/resources/templates` 列出真实位置为 `home.html`、`orders/index.html`、`customers/index.html`。另一次 `rg` 误用单数目录 `order/customer` 报不存在，随后改用已枚举出的完整路径读取。上述均为检查命令路径错误，未运行产品，不当作产品失败，也不删除这段记录。

执行范围：顺序HTTP和SQL，所有正式结果由公共 `Review.req/check/finish` 写入HTTP、SQL、检查和 `stage-E.*`；独立新增分类与商品只落隔离数据库，不改seed文件。后台启停会使旧用户session失效，脚本结束前恢复alice启用并重新登录更新 `r.u`。补货只绑定quantity；通过补货后的旧商品表单409验证版本，不错误要求补货自身传version。

空库、错误配置、并发、竞争和故障注入不在此脚本内；不可根据准备、源码静态检查或旧证据改写为已通过。
