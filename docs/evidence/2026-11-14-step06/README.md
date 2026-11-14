# STEP06 后台商品相册实测证据

- 受测完整 Git SHA：`1aa6ad0c4a7546c5bfba7ed65ef05f5913132027`；基线：`75e4339266968edc212f160b1119ac720965c408`。
- 受测分支：`feat/step06-admin-images`；源码工作区为空（`attempt2/git-input-status.txt`）；源码、SQL、静态素材、两端JAR图片的执行前后摘要未变化。
- 结论：**PASS（自动验收，组员复核待补）**；成功轮次 `attempt2`，此前失败轮次如有保留原始证据，不能视为通过。
- attempt1产品HTTP、原生Service与浏览器各项观测通过，但最终读取浏览器JSON时验收脚本漏设UTF-8，触发Windows GBK UnicodeDecodeError，**该轮整体FAIL原样保留**。只修验收工具编码后，attempt2在新隔离库完整复跑通过，同一源码SHA。若失败图与成功图字节相同，原stage不改，归档由artifact-references.json给出原path→可直接查看的成功图path及完整SHA，避免双份PNG。
- 环境：JDK21、Wrapper Maven3.9.16、MySQL 8.4.9；隔离库 `csucampuscraft` 端口 `57460`，Java监听127.0.0.1:8080/8081。版本实际输出见 `attempt2/versions.txt`；JAR摘要、运行输入摘要见 result.json / runtime-inputs.sha256。
- 两端真实 `mvnw.cmd -f <module>/pom.xml verify` 均退出0并有BUILD SUCCESS；原始日志保存在该轮次 build-user.log/build-admin.log。只依赖已有运行时，无新增测试框架或业务探针路由。

## 覆盖与原始记录

- HTTP 149 条，POST 71 条；**每一POST（含登录、游客、CSRF/角色拒绝）**均有7表before/after行数和有序原始行SHA、目标父商品所有资料/状态/封面/库存/version/时间字段与相册行前后记录，见 `attempt2/database-writes.jsonl` 与 `http-post-coverage.json`。账户、地址及订单行只留摘要，未公开敏感明文。
- A10读页、入口、创建、排序/替代文本编辑、同排序按ID、重复path允许、空alt回商品名；新增/修改/删除仅真实变化增父version，同值编辑303且全部状态不变；移除最后图片后用户详情回封面，封面缺失浏览器回占位。
- 跨商品/不存在image404，父不存在优先404；旧/缺失/空version409，格式/负数/Long溢出400；路径/排序/替代文本边界400；缺/错CSRF403、错角色403、未登录302。拒绝POST无数据变化。
- MAX父版本真变更在容量校验阶段409零写入，同值可303；这是上溢拒绝观测，**不是**后段故障注入或并发回滚实验。
- 旧A05表单在相册增版后409；旧相册表单在补货后409。封面独立；其余5表（含历史快照）最终与种子完全一致。
- 实际JAR Service原生串行调用 + MyBatis拦截观测：操作者SELECT FOR UPDATE为首个SQL，随后父商品锁，RC事务和单连接；版本验证早于图片归属查找，同值无DML；身份失效/错角色在业务表前拒绝。源码及输出见 `attempt2/AlbumWriteProbe.java` 与 native-probe.log。没有实现并发、生产故障钩子或测试HTTP端点。
- 两端同path200的Content-Type/字节/SHA与assets一致，见 static-resources.jsonl；缺资源**原始404**与浏览器占位资源**200**分别留证，不能把缺文件写成200。
- 24张PNG（1366×768、1920×1080各12张），含A10多图/空态/缺封面、A04/A05入口、用户详情联动，见 `attempt2/browser/`；浏览器仅GET，不触发写库。result.json记录截图尺寸、SHA、真实HTTP以及占位资源事件。
- HTTP正文脱敏后gzip去重，http.jsonl索引记解压后SHA。sensitive-data-scan.json实际解压并检查正文、CSRF值、会话、Cookie、BCrypt和已知教学密码。evidence-files.json对除自身外全部文件给出字节SHA。

## 口径与尚未覆盖

1. 当前任务明确缺失/空productVersion为409，历史TST-40表原标准为400；本轮按任务覆盖，原标准保留，由项目文档实测差异说明。
2. 用户“4条写路由”实际列3条POST和1条GET；只验证列出的3条POST，无新增第4条。
3. 写入路径比BR-17和用户图片片段更严：拒任意`..`子串、冒号、百分号、反斜杠、查询/片段、控制字符和独立`.`段；合法Unicode/空格/缺文件/重复路径通过，用户片段未改。
4. TST-40并发/故障注入和订单快照写入留STEP13；本轮仅证明已有历史快照不受相册写影响。Word指导书未修改，M1统一更新待评估。
5. 负责人：本人姓名待填（Codex生成初稿，本人核对与验证）；复核人：组员姓名待填（组员复核待补，M3前完成）。AI执行单元的自动验收不代替组员签字。

## 运行与停机

验收脚本 verify_step06.py、verify_browser.cjs 与 AlbumWriteProbe.java 原文归档在成功轮次；执行环境变量只传受测SHA、构建日志目录及秘密，秘密未进入命令参数/证据。隔离DB先导入后授权，app仅SELECT/LOCK TABLES、product_image DML与product UPDATE，其他表无DML权限。每个独立SQL连接先设UTC。

`tracked_processes_stopped=true` 证明此次受控Java/MySQL进程全部退出；私有运行目录与临时认证文件不进归档。cleanup.json另记私有目录清理。

## 独立复核与复查入口

- `source-publication.json`：本轮十个管理端源码/资源文件及完整 SHA-256；`source-review.json`：独立静态复核，不能代替运行观察。
- `ui-visual-review-attempt2.json`：24 张图逐图检查与完整 SHA；两轮图完全相同，引用第一次已查看的同字节图片，保留两轮检查事实。
- `independent-observation-review.json` 与 `review_observations.py`：独立重读成功轮原始记录，149 HTTP 中的 71 POST 均一一关联七表对照；56 次拒绝无写入，11 次相册变化仅触及请求父商品及其单个图片并使父版恰增 1，2 次同值编辑无写。另两次成功 POST 为登录和 STEP05 补货联动，不算相册写入。
- 128 个运行输入的清单 SHA-256：`11ce2a3046bccc5ca6f135f59bb81f6868b549ae0c06831b150daa29d45be9f6`；结束及文档归档前继续核对无漂移。文档/证据提交另行记录，不能替换受测代码 SHA。
- 命令原始字节使用 `attemptN/commands.jsonl.gz` 无损保存，解压 SHA/长度见 `compressed-text-index.json`；HTTP 正文索引的 SHA 对应脱敏后解压内容。复查脚本 `audit_evidence.py` 默认目录可由环境变量 `STEP06_EVIDENCE_DIR` 指定。
- 双端 Wrapper 在主验收前由新 PowerShell 进程构建；实际脚本 `images-build-fresh.ps1` 保留完整参数、JDK/独立 Maven 缓存及无 Maven PATH 设置，分别用 `-Module user` / `-Module admin` 执行。`build-user.json` / `build-admin.json` 记录真实退出 0，构建日志见成功轮次。脚本中的本机工作路径仅用于说明此次执行环境，其他机器需替换路径。

命令原始JSONL以`attemptN/commands.jsonl.gz`无损压缩归档，`compressed-text-index.json`保存原字节数与解压后完整SHA，原stage命令文件未修改；敏感/hash审计同样解压检查。
