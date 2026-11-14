# 2026-11-15 复核环境

执行者：Codex AI；人工复核人：本人（真实姓名待填）。本页记录新跑的环境事实，不构成人工签字。

| 项目 | 本轮实测 |
| --- | --- |
| 仓库与基线 | `D:\Github Projects\CSUCampusCraft`；`0329c9810c4ad2719c4ae95190ff516d1d21a9ed`；分支 `feat/review-2026-11-15` |
| OS / 时区 | Windows 11，NT `10.0.26200.0`；`China Standard Time`，UTC+08:00，无夏令时；日期按 Asia/Shanghai |
| 固定 JDK | `C:\Users\Starmetor\.jdks\ms-21.0.12.1`；Microsoft OpenJDK `21.0.12.1+1-LTS`，64bit |
| Maven | 根 `mvnw.cmd`；Apache Maven `3.9.16`；实际输出确认运行 JDK 21.0.12.1 |
| MySQL / 客户端 | `D:\MySQL\bin\mysqld.exe` / `mysql.exe`；`8.4.9`；InnoDB |
| 隔离实例 | `127.0.0.1:59315`；独立全新 datadir `C:\Users\Starmetor\AppData\Local\Temp\csucampuscraft-review-20261115-b53811e5a70e42d792037669ec7cad67\data` |
| 实例 UUID | `8323950c-e04c-11f1-bb8f-005056c00001`，由本轮全新初始化产生 |
| MySQL PID | Start-Process 返回监督父 PID **36524**；实际 59315 监听子 PID **29576**，二者进程树均落盘 |
| 应用账号 | `review_app@127.0.0.1`，仅 `csucampuscraft.*` 的 SELECT/INSERT/UPDATE/DELETE；随机临时口令仅存临时文件 |
| 用户端 | `http://127.0.0.1:8080`，PID **36828**，独立 `CSUCAMPUSCRAFT_USER_SESSION`；默认确认 TTL **PT10M** |
| 管理端 | `http://127.0.0.1:8081`，PID **36332**，独立 `CSUCAMPUSCRAFT_ADMIN_SESSION` |
| 连接参数 | 两端继承 `CSUCAMPUSCRAFT_DB_URL=jdbc:mysql://127.0.0.1:59315/csucampuscraft`、`CSUCAMPUSCRAFT_DB_USER=review_app`、临时 `CSUCAMPUSCRAFT_DB_PASSWORD` |
| JDBC 时区 | performance_schema 实际读到两端各10个连接均为 **+00:00**；通过 processlist 客户端端口与 TCP PID 映射到两个 Java 进程 |
| 页面时区 | 当前双方 SalesOrder 与管理 CustomerProfile 从 UTC 转 `Asia/Shanghai`；页面动态时间对照由主流程另记录，静态配置不能代替动态比对 |

上述PID为初次启动身份。持久化复核阶段按主流程要求，在保留同一MySQL及业务数据的条件下，核对原PID/JAR SHA/监听归属后重启两个主应用。当前用户端PID **37480**、管理端PID **3936**，同一JAR、同一环境连接、同一8080/8081端口；旧PID36828/36332已停止。新用户根页200、管理根页302到登录、管理登录200。命令、旧新身份及日志见 `environment/restart1-*.json/log` 与 `restart-main.ps1`。重启脚本不写业务库；数据与临时主题的重启前后核对由主流程 `persistence_review.py` 独立记录。应用仍运行，无自然退出码，因此结果中 `processExitCode=null`，不伪记为0。

两个 Maven `clean verify` 退出码均 **0**，日志均 `BUILD SUCCESS`，且明确 `No tests to run.`。因此这里只证明构建成功，不推断业务验收通过。构建前沙箱可见进程清单未见 java/mysqld；沙箱清单不能证明宿主机没有其他进程。本轮没有停止任何旧进程，两个 clean 均实际成功，无 target 文件锁错误。

演示 SQL 从原始 `database/02-schema-with-demo.sql` 导入本轮空库，退出 **0**。七表顺序 `store_user/category/product/product_image/cart_item/sales_order/sales_order_item`：**4/15/60/100/10/10/20**。另在 `review_schema` 空库导入 `01-schema.sql`，退出 **0**，七表全 **0**。两库各 **35** 个 CHECK、均 ENFORCED=YES，实时规范化谓词完全一致；两份源 SQL 的 CHECK 名称与实际库匹配。失败种子回滚和非法写入故障场景本环境阶段未执行。

| 当前实际构建 JAR | SHA-256 |
| --- | --- |
| user，30,093,096 bytes | `c8a1bea5305186af82cb5f505f67cbce8600f424103f79cc2f825a0a709eb868` |
| admin，30,095,071 bytes | `1dba0cfacee7186afe9933a325945fb4689612b4992de656be2619f083eb4c4d` |

## 短 TTL 辅助实例

同一用户端 JAR 另启 `http://127.0.0.1:18080`，PID **2276**，仅命令行覆盖 `--server.port=18080 --csucampuscraft.checkout.confirmation-ttl=PT2S`；连接本轮隔离库。用于等待超过2秒后真实 HTTP 验证过期。默认8080实例与源码配置保持 PT10M，辅助结果不能称为实等10分钟。辅助10个 JDBC 连接也实际为 +00:00。主流程完成短TTL真实HTTP测试后，已核对PID命令行和18080监听归属并单独停止该辅助；停止后进程数和18080监听数均0，见 `environment/short-ttl-stop-result.json`。主8080、8081与MySQL继续保留。

## 库存核对专用参照库

阶段F需要原始种子库存参照时，在同一隔离实例另外新建 `review_reference`，原样导入 `database/02-schema-with-demo.sql`；建库、导入和计数退出码均0，七表为4/15/60/100/10/10/20。执行前使用 `@@port/@@datadir/@@server_uuid` 再核对确为本轮隔离实例。源SQL SHA-256 `6871082e148e1aed9d0da74d4aa49d98de18d48960544a597bbc94fad96103bd`，未改SQL，主业务库不重置。完整命令/结果见 `environment/import-reference.ps1` 与 `reference-*`。

参照库首次外部工具的路径守卫因 MySQL batch 默认把反斜杠转义成双反斜杠而拒绝继续，当时没有执行建库/导入。原失败输出保留 `reference-attempt1-guard-error.log`；改为 `--raw` 读取目标后核对成功再建库，非产品故障。

## 保留的失败与限制

1. `powershell`（Windows PowerShell 5.1）对无 BOM UTF-8 脚本按 ANSI 解析，运行前 ParserError。使用 `pwsh` 重跑，构建与后续执行才发生；失败输出重现保存于 `environment/attempt0-parser-error.log`，未将其算作产品失败。
2. 沙箱临时目录首次 MySQL initialize 退出 **1**，InnoDB redo rename 报 OS error **5**。失败目录未删除，原日志 `environment/mysql-initialize.log` 保留。经授权沙箱外运行，在另一全新临时目录初始化退出 **0**，见 `mysql-initialize-attempt2.log`；没有使用现有开发库。
3. 外部辅助工具初名 `inspect.py` 与 Python 标准库模块重名，导致 requests 循环导入；未发起该轮 HTTP/SQL。保留错误日志，改名为 `inspect_environment.py` 后成功，四组 SQL 退出均0。
4. MySQL `@@system_time_zone` 原始输出包含服务器中文编码损失；未美化原字节。OS Get-TimeZone 与实际会话 +00:00 分别记录。

实际命令见 [commands-environment.md](commands-environment.md)，启动脚本、原始输出、CHECK/索引、UUID、JDBC与PID交叉映射见 [environment/](environment/)。未归档口令、会话值或 CSRF 原值。

## 最终停止状态

主流程全部HTTP/SQL完成后，已核对当前用户37480、管理3936的JAR命令与8080/8081监听归属，再停止这两个本轮进程。隔离MySQL再次以 `@@port/@@datadir/@@server_uuid` 和监督36524/监听29576的命令行、父子关系、59315监听交叉核对，随后使用本轮临时root.cnf执行 `mysqladmin shutdown`，真实退出码 **0**；未对其他MySQL或开发实例发停止操作。最终四个本轮进程与8080/8081/18080/59315监听均无残留，结果 **PASS**。MySQL数据目录、root/app临时defaults文件与private-state均保留，未执行删除。

最终停止脚本本身退出0；Java由显式 `Stop-Process` 终止，取回的两个实际进程退出码均为 **-1**，没有改写成自然退出0。MySQL监督与监听子进程均正常退出 **0**，服务器原日志有 `Received SHUTDOWN from user root`、`Normal shutdown` 和 `Shutdown complete`。

停止前后身份、各进程实际退出码、mysqladmin输出和剩余监听检查分别见 `environment/final-stop-before.json`、`final-stop-result.json`、`final-stop-mysqladmin.log`，执行脚本 `final-stop.ps1` 和命令表已保存。上文初次启动与重启后的PID均为历史运行身份，当前服务已停止。

环境目录及本页、stage-0、commands-environment 已用临时随机应用口令做精确匹配，并检查会话Cookie、CSRF和确认令牌原值模式；扫描未检出。扫描报告仅记录数量和类别，不含原值，见 `environment/sensitive-scan-result.json`。公开种子教学密码在复现源脚本中出现属于已公开教学夹具，非随机数据库口令。
