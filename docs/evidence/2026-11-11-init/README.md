# 2026 年 11 月 11 日初始化验证证据

本目录保存 M0 初始化与密码库可用性验证，不代表业务模块已实现或通过。
受测源码基线为 ae6f47f995fef790b5a2f513574ed2129e4409b3，附加两端 POM 的未提交 spring-security-crypto 依赖变更。runtime-inputs.sha256 列出实际构建输入，result.json 给出清单摘要和两个受测 JAR 摘要；文档与构建产物不计入运行输入清单。该状态不能表述为干净提交的验收。

result.json 与 run.log 是在新隔离数据库完成的独立成功运行。first-attempt-result.json 与 first-attempt-run.log 保留此前脚本失败：改主题的 UPDATE 未选择数据库，验证在该处停止。修正脚本后在另一个新 datadir 独立重跑，失败不归因于业务应用。构建准备阶段还曾因本地缺失 Thymeleaf 依赖而离线解析失败，之后使用中央仓库补齐；该准备阶段未保留独立原始构建日志。build-user.log 与 build-admin.log 对应实际成功构建。

check-constraints.tsv 和 check-audit-result.json 来自随后对同一隔离 datadir 的独立只读元数据核对。35 个命名 CHECK 与结构脚本名称集合一致且 ENFORCED 全为 YES。未执行全套非法 DML 用例。

verify_init.py 和 check_constraints.py 是实际使用的验证工具源文件。它们基于外部暂存目录的 runtime/ 布局运行，包含受测 JAR、源码和独立 MySQL datadir；此处保留用于审阅操作逻辑，不能直接在此证据目录运行。日常重现按项目 README 与 INIT 用例操作。脚本中的口令在运行时随机生成，证据不包含数据库口令。完成后本次跟踪的双端进程和隔离 MySQL 均已停止。
