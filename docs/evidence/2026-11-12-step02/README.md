# STEP02 基础设施验收归档

## 最终结论

仅 attempt4 构成本轮完整 STEP02 验收通过。顶层 result.json 是 attempt4/result.json 原字节副本，summary.json 汇总四轮状态，旧结果没有覆盖或重新解释成一次连续成功。

M0 基线为 022f50196ceb7b89880dabe1c369360e8f6136c3。首次实现提交 b35b0a48a0fb0e60919a41ddfe4496c96ee236b0 在复核中发现两个问题，修复后的精确受测实现提交为 5d9271d7e32634f947eb9f6077e7a4f3d98806a7，分支 feat/step02-foundation。后续文档和证据另行提交。运行输入清单摘要为 9b10df92681a3761c6ce35948b86bb30db9bca81971b7c3b524191da0591fce1，运行结束逐项核对未漂移。

使用 Microsoft OpenJDK 21.0.12.1、Maven 3.9.16、MySQL 8.4.9。每轮都建立新的私有 MySQL 数据目录与空库，验证服务 UUID 和端口后再初始化。attempt4 的数据库端口为 62983，两端应用为 8080/8081。原有 MySQL 服务和开发库未参与本次验证。

## 四轮记录与缺陷复测

| 记录 | 自动化结果 | 完整验收结论 |
| --- | --- | --- |
| attempt1 | 原 134 项自动化检查为 PASS，原 result.json 保留 | 复核判未通过。20 个非 HEAD CSRF 拒绝实际返回 JSON，字段错误 p 虽有 ID 但正文为空。见 attempt1/review-findings.json 和指向的脱敏响应。 |
| attempt2 | FAIL | 修复产品代码后，强化 HTTP 已通过，但新增浏览器提交中验证工具等待未完成导航超时。后续 DB-after 和 Java 类探针未执行，不能算完整通过。 |
| attempt3 | FAIL | 同一生产提交，调整工具路由匹配后仍在等待导航的组件截图阶段超时；原 result/error/部分图片及当时浏览器工具快照保留。 |
| attempt4 | PASS | 改为在 window 冒泡阶段由验证器阻止导航、检查原生表单事件的提交中状态；真实 POST 的 303 另由实际 HTTP 验证。全套重新在新隔离库完成。 |

产品修复为：CSRF 拒绝直接渲染 403 Thymeleaf 视图，保持 text/html、403 和本端标记，不受 Accept 内容协商影响；字段错误读取使用动态 Map.get(name) 并显示实际文案。工具超时记录不归因于新的产品故障，原始错误、原有自动化事实及修复后的新结果均独立保存。编译准备阶段曾有探针 switch 语法错误，两份 initial-failure 构建日志也单独保留，其后受测源码才进入上述实现提交。

## attempt4 观察范围

- 284 项自动化检查、200 条脱敏 HTTP 响应、12 项真实 Edge 浏览器检查通过。
- 两端独立构建实际 JAR 可运行。结构空库保留原 M0 空态，演示库显示各端标识和五个主题。默认 profile 下探针、未知路径和尚未实现的业务路径均为 404。
- 验证 profile 的 400/403/404/409/500 状态与页面正确；500 不含哨兵、SQL 或堆栈；脚本文本按转义普通文本输出。
- 字段错误正文为预期文案，label/id、aria-invalid、aria-describedby 和摘要链接真实关联。
- 缺、错、跨会话、多值、只 header、只 query 的 CSRF，以及 HEAD/OPTIONS/PUT/PATCH/DELETE 缺 token，均被拒绝。每个场景按 Accept 缺省、text/html、application/json 分组，除 HEAD 无实体外全部为 SSR 403 HTML。计数器未增加；合法表单 POST 则为 303 且仅增加一次内存计数器。
- 七表有序全字段行的汇总摘要与行数前后完全相同。仅保存汇总，不保存账号散列或完整行。
- 双端 CSS 响应等于源码、两份 CSS 字节一致，共享 SVG 字节仍等于 assets 唯一源。浏览器覆盖 1366/1920 视口、16px 正文、28px 标题、2px 焦点线、无横向溢出、缺图回退和表单错误。提交中检查标记 navigationPreventedByVerifier=true，只检查前端组件，不冒充服务端实际提交。
- 从实际 JAR 提取的生产类验证用户端 75、管理端 79 个断言，包括四个种子密码正反校验、cost10 新编码、72 UTF8字节、返回地址允许/拒绝和编码绕过、整数/长整数、Unicode 长度、枚举与 DECIMAL(12,2) 两位范围。

## 文件与复核方式

顶层提供最终结果、版本、构建、源码清单和按工程分组的 changed-files.md，attempt1 至 attempt4 提供独立响应、命令、启动信息、结果和截图。commands.jsonl 记录已完成外部命令的退出码及耗时；超时在对应 result.error 中记录，不虚构退出码。http.jsonl 索引脱敏 .body。attempt1/pre-review-* 保留首次归档候选中的工具及说明，须结合 review-findings 阅读；attempt3/4 保存当时实际浏览器工具快照。attempt2 未独立保留浏览器源码快照，以其原始超时和部分图记录为准。

所有 HTTP 证据已移除 Cookie/Set-Cookie 值，CSRF 原值与已知会话值替换为 [REDACTED]；包括 Servlet 可能生成的 session URL 参数。密码和散列只在私有进程环境、内存或临时文件使用，不进入日志、页面或归档。二次扫描没有真实 Cookie、CSRF 原值或实际 BCrypt 散列。归档不含 cookiejar、私有初始化 SQL、JAR、缓存或数据库目录。

verify_step02.py、FoundationChecks.java、verify_browser.cjs 是最后一轮验证工具源，依赖本机外部 verification/runtime 布局与已构建仓库 JAR，不应直接在证据目录运行。新一轮需选择新的 attemptN 并显式设置 STEP02_TESTED_CODE_SHA 为完整受测实现 SHA。所有本次跟踪 Java 和隔离 MySQL 均已停止。

本步只证明 STEP02 基础设施。TST-04、TST-05、TST-31 的商品/登录/业务写入部分仍待实施，不将无业务探针当作这些完整用例通过。
