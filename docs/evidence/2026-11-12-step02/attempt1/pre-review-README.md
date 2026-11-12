# STEP02 基础设施独立验收证据

2026 年 11 月 12 日在 Windows 本地独立初始化 MySQL 数据目录，使用实际仓库已构建的双端 JAR 验证。正式运行 attempt1 的 134 项检查全部通过。此前基础设施编译阶段的探针 switch 语法错误保留为 build-user-initial-failure.log 与 build-admin-initial-failure.log；修正后才产生本轮实际受测实现，不将编译失败混入一次成功运行。

## 受测版本与环境

- M0 基线：022f50196ceb7b89880dabe1c369360e8f6136c3。
- 受测实现提交：b35b0a48a0fb0e60919a41ddfe4496c96ee236b0，分支 feat/step02-foundation。启动验收时工作区干净；后续文档与证据另行提交，不回写成实现提交本身。
- runtime-inputs.sha256 固定两工程 POM、src、共享 assets 与 SQL 的实际输入，清单摘要 dfc8ba211e5e9832bc0f090fc0a5c79cae0e6138e4f814ff66e643b6db2d4374；运行结束再次核对逐项没有漂移。result.json 记录各 JAR 摘要。
- 实测 Microsoft OpenJDK 21.0.12.1、Maven 3.9.16、MySQL 8.4.9；原始版本输出在 versions.txt。双端用 8080/8081，MySQL 使用 result.json 中的临时端口。
- 数据库是新建的私有数据目录，服务 UUID 和端口与该目录一致后才执行导入与授权。原有 MySQL 服务与开发库不参与本次验证。

## 实际观察

1. 两端在结构空库返回原 M0 空态；在演示库 GET / 返回各端标识、五个一级主题及原 data 标记。默认 profile 下未知路径、所有本轮探针入口和尚未实现的登录/目录/分类/购物车/订单入口均为 404。
2. 仅启用 verification profile 后注册 /__verification 路径：错误探针分别返回 400/403/404/409/500；500 页面没有技术哨兵、SQL或堆栈。文本脚本和引号按转义文本输出，字段 label/id、错误摘要、aria 关联及唯一 CSRF hidden 片段可读。
3. CSRF 缺失、错误、另一会话、重复表单值、只放 header、只放 query 均为 403；HEAD、OPTIONS、PUT、PATCH、DELETE 缺 CSRF 也为 403。每次拒绝后独立读取计数器未增加。有效会话加表单 token 的 POST 返回 303 和本端首页 Location，计数器只增加一次。
4. database-before.json 与 database-after.json 对七张表记录有序全字段行的汇总摘要和行数，前后完全相同；文件不保存账号散列或完整行内容。验证 POST 只增加内存计数器，不包含业务写入或业务事务实现。
5. 两端 CSS 响应等于各自源码且两份内容完全相同；共享 SVG 响应字节仍等于 assets 唯一源文件。Microsoft Edge 与捆绑 Playwright 的 10 项检查通过，包含 1366/1920 视口、16px 正文/28px 标题、无横向溢出、2px 焦点线、字段标签、缺图回退和错误页。browser/ 保存截图及结果。
6. FoundationChecks.java 从实际 JAR 提取的 classes/lib 调用生产 PasswordService、ReturnUrlPolicy、InputChecks：用户端 75 个、管理端 79 个断言通过。验证四个实际种子散列的正反匹配、新 cost10 编码、72字节边界；返回地址允许/拒绝/编码绕过及 fallback；整数/长整数溢出、Unicode 字符长度、枚举和 DECIMAL(12,2) 范围与两位精度。

## 证据文件和安全处理

result.json 与 verification-summary.json 为结构化结果；http.jsonl 按序索引 112 个 .body 响应；commands.jsonl 保存外部命令、退出码及耗时，launches.jsonl 保存启动参数、连接目标和口令存在性。构建、HTTP、Java 类探针与浏览器输出均单独保存。

HTTP 记录是脱敏响应，不是未经处理的网络转储：Cookie/Set-Cookie 值不存储，CSRF hidden 原值与已知会话值替换为 [REDACTED]。实际数据库口令运行时随机生成，仅通过私有进程环境传递；种子密码与散列只存在于验证内存或私有临时文件中，文件在结束时删除。二次扫描未发现 CSRF 原值、真实 Cookie 或实际 BCrypt 散列。归档没有 cookiejar、私有初始化 SQL、JAR、缓存或数据库目录。

verify_step02.py、FoundationChecks.java、verify_browser.cjs 是实际验证工具源。工具采用外部 verification/runtime 布局和本次本机绝对依赖路径，保留用于审阅，不应直接在仓库证据目录执行；复跑须在新的 attemptN 目录准备环境和实际 JAR。默认探针不生效这一点已实际通过 HTTP 验证。

本轮所有跟踪的 Java 与隔离 MySQL 进程均已停止，result.json 的 tracked_processes_stopped 为 true。该验收只证明 STEP02 基础设施；TST-04、TST-05、TST-31 的业务部分仍待实施，尚无商品详情、身份授权、交易或后台业务通过记录。
