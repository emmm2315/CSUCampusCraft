# STEP07 持久购物车自动验证证据

2026-11-14，本步自动验证通过，实名组员复核待补。基线 main：`a1d4f3523f557af63fc77ea883986c099edcd93e`。受测对象为 `feat/step07-cart` 的未提交工作区，不把基线当作购物车代码提交。137 个运行输入与双端 JAR 前后无变化，摘要见 `runtime-inputs-before.json` / `runtime-inputs-after.json`。

| 文件或目录 | 内容 |
| --- | --- |
| `summary.json` | 本步范围、工具版本、真实数量与限制。 |
| `build-user-final.log`、`build-admin.log` | JDK21 / Wrapper3.9.16 双端构建退出0；构建自身没有单元测试。 |
| `http84/result.json`、`http84-attempt1.log` | MySQL8.4.13；590断言、73顺序POST+4双请求并发组，七表哈希及车/商品明值；400/409 HTML已脱敏。 |
| `probe/` | 真实Service31项、Model18项，源码、结果和日志；包括用户锁等待期间禁用再授权及最大版本。 |
| `browser/result.json`、PNG、`visual-review.json` | 463检查、30页面截图、2联系表；每张记录真实HTTP/视口/页面/摘要，完成目视核对。 |
| `instance.json`、`mysql84-source.json` | 全新隔离实例身份及官方分发包完整性来源，不含应用密码。 |
| `application-lifecycle.json` | 真实应用重启的PID与JAR摘要，持久车重登恢复。 |
| `scripts/` | 外部验收与隔离生命周期脚本。脚本记录本机路径；在其他机器复现时替换工具/仓库路径，使用新label创建隔离目录。 |
| `audit.json`、`sensitive-data-scan.json`、`cleanup.json` | 独立归档核对、敏感值扫描及受控临时进程清理。 |

复现顺序：在仓库运行 README 的双端 Wrapper 构建；用 `scripts/manage_mysql.py start --base <MySQL8.4根目录> --label <新轮次>` 创建独立实例，取得私有环境文件；`serve_app.py <instance.json> 18080` 启动应用。为 `verify_cart.py` 设置 STEP07_MYSQL、STEP07_DB_PORT、STEP07_DB_NAME、STEP07_INSTANCE、STEP07_BASE、STEP07_OUT（新输出目录）。HTTP完成后顺序跑 ServiceProbe、浏览器夹具和浏览器脚本，避免互相改变全表哈希。私有口令只在进程环境/私有文件使用，不进入输出；最后先停止受控应用，再由 manage_mysql.py 按UUID/datadir核验后停库。

统计限制：81个响应只指被记录的购物车POST，不包括所有GET/登录/退出；并发组有真实时间重叠，但不扩大到订单竞争。SQL客户端未逐连接显式设置UTC。STEP08结算、订单和下单清车均未实现，空车/失效车只判定购物车展示与就绪阻断；不把这些计成完整TST-11或订单用例通过。

代码/HTTP/SQL/浏览器的AI复核不替代真实姓名的组员交叉复核。M1保持待复核，Word指导书暂不更新。最终代码未提交、未合并、未推送。
