# M0 独立复核证据

2026年11月11日在独立目录从实际仓库重新复制源码，单独构建两个工程，在新的隔离 MySQL 数据目录执行初始化和双端运行验证。此轮全部正式检查第一次通过，没有合并旧实测结果。复核仅覆盖工程初始化，不证明登录、购物车、订单或新增后台业务已实现。

版本为基线 Git SHA ae6f47f995fef790b5a2f513574ed2129e4409b3，加 runtime-input-diff.patch 中的两个未提交 POM 依赖变更。runtime-inputs.sha256 固定实际构建源文件，完整清单摘要为7675b25acb6544a13e37cf5187cedfd0ff372613e2442f30772a8a882df772b1。文档及构建产物不计入该清单。结束时逐项确认原仓库源文件摘要仍相同，不能把本次称作干净提交验证。

result.json 是原始 init-result.json 结构化结果的归档副本；run.log 为实际验证输出；build-user.log / build-admin.log 和 build-exits.json 为两次独立 Maven verify 及退出码。运行时使用隔离设置文件与预先准备的 Maven 缓存，缓存不属于项目交付物。两次构建使用 Microsoft JDK21.0.12.1、Maven3.9.16，应用编译目标保持Java17。MySQL为8.4.9，端口58333。versions.txt保存工具原始版本输出。

INIT01至INIT05覆盖独立JAR、七表空库与演示库导入、预期数据、演示种子事务失败回滚、两端分别和同时运行、两个端口各自的空目录、同库主题变更、重启数据保留及恢复、两端共享SVG字节一致。http.jsonl索引每次保存的HTTP响应，http-*.body是原始响应字节。启动时等待首页可访问用于初始化就绪判断，不属于业务故障恢复验收。

csucampuscraft-checks.tsv 与 csucampuscraft_structure-checks.tsv 保存两个库的35项约束完整元数据，按表名与约束名排序。名称集合与实际01-schema.sql一致、ENFORCED全部为YES，且两个库的名称、完整谓词和启用状态逐字节一致。DDL与数据库设计表的语义对照另由文档审核负责。该结果不等同于每个CHECK的非法DML测试。

实际从两端JAR提取的spring-security-crypto-6.5.11分别验证4个真实种子BCrypt散列的正、误密码，并验证新cost10编码。M0MapperProbe.java启动当前实际应用的Spring上下文，通过实际CategoryMapper插入分类，核对回填ID等于同连接LAST_INSERT_ID及按ID回读；用户端503、管理端504，两个JDBC会话时区均为+00:00。测试事务回滚，七表行数恢复为4/15/60/100/10/10/20。该受控数据探针不证明尚未开发的管理端分类HTTP功能通过。

commands.jsonl保存受控子命令、退出码和耗时，launches.jsonl保存实际双端启动参数及连接目标，口令仅记录存在性。SQL通过标准输入执行，随机数据库口令未写入归档。源工具verify_init.py及M0MapperProbe.java保留供审阅，基于本次外部runtime布局运行，不应直接在仓库证据目录执行。日常复现按仓库README及INIT用例，在全新隔离目录运行工具时先准备源码和独立构建产物。

所有本次启动的Java与MySQL进程均已停止，私有口令初始化文件已删除；结果中的tracked_processes_stopped为true。现有MySQL服务的数据目录未使用或修改。
