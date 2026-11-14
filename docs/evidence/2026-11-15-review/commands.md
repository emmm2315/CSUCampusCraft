# 真实命令索引

所有路径相对仓库根目录。脚本为本轮新建复核工具，不属于产品实现；每次运行的 stdout/stderr、退出码和 HTTP/SQL 事件另存。会话值、CSRF、结算令牌与临时 DB 口令不归档原值。

## 开始与阅读

已执行：`Get-Location`；`git status --short`（空）；`git branch --show-current`（main）；`git rev-parse HEAD`（0329c9810c4ad2719c4ae95190ff516d1d21a9ed）；`rg --files -g AGENTS.md -g '!**/target/**' -g '!**/node_modules/**'`（未发现）；`Get-ChildItem -Force`。

`git switch -c feat/review-2026-11-15` 首次因 .git 沙箱只读失败（cannot lock ref / Permission denied）；同一命令在允许写 .git 的执行权限下退出0，成功切分支。未推送。

按清单顺序执行 `Get-Content <文件> -Encoding UTF8`，长文件分段 `Select-Object -Skip N -First M`；`rg -n '^##|^对应验收|^目标|^验收|STEP0[1-9]|STEP1[0-2]' docs/开发计划与任务.md`；测试文档通过新运行的 Python 解析分节读取各步范围；历史 README/result 只作结构及受测SHA核对，不继承其结论。完整性/文档审计的可重跑脚本和命令在各自目录。

环境探测：`Get-Command java,python,mysql,mysqld,node -ErrorAction SilentlyContinue`；`Get-ChildItem C:/Users/Starmetor/.jdks`；`Get-ChildItem 'C:/Program Files/MySQL'`；`Get-CimInstance Win32_Process` 在普通沙箱返回“无法从客户端中访问 CIM 资源”，未以该失败输出推断无进程。Python launcher 曾打印 Failed to find real location 警告但脚本运行退出0，后续用实际解释器。

## 后续执行

环境命令见 `commands-environment.md`（准备完成后生成）；HTTP/SQL主流程命令逐次追加在此。

## 已实际执行的主流程与补充

以下命令实际使用解释器 `C:/Users/Starmetor/AppData/Local/Python/pythoncore-3.14-64/python.exe -X utf8`。临时连接指针为 `C:/Users/Starmetor/AppData/Local/Temp/review-connection.json`，仅保存文件位置/端口/PID，口令只在独立临时配置内。脚本内部每个HTTP和SQL、请求结果与检查均逐次写入jsonl；不得从旧步骤工具结论填入。

1. `python -X utf8 docs/evidence/2026-11-15-review/run_review.py <临时连接JSON>`：首次退出1（CSRF缓存/参数位置工具错误，完整保留attempt1）；修正新工具后同命令从A重新运行，A–D结束在终端等待，审阅阶段小结后向该进程输入换行，执行E/F，实际进程退出0。脚本会保留失败断言而继续，因此退出0不代表没有失败：E有1个原始排序选择器FAIL，后续独立补证，不改原FAIL。
2. `python -X utf8 docs/evidence/2026-11-15-review/supplement.py <临时连接JSON>`：退出0，stdout/stderr见supplement-run.log，命令/实际退出码见supplement-command.json。相册article选择器、新封面路径、正向搜索、全60库存参照公式为新请求/查询。
3. `python -X utf8 docs/evidence/2026-11-15-review/persistence_review.py <临时连接JSON>`：临时主题改名并记录完整七表摘要，在RESTART_READY等待；由environment/restart-main.ps1核对PID后重启双端，同进程接收换行继续，实际退出0。重启后重新登录，七表、订单和alice/bob非空车重新验证；主题恢复原名和原时间戳。
4. `python -X utf8 docs/evidence/2026-11-15-review/final_checks.py <临时连接JSON>`：退出0，真实stdout/stderr见final-checks-run.log，命令/实际退出码见final-checks-command.json。补充有效旧确认禁用后POST302、重新启用不复活、重登原令牌409；全库状态/时间配套SQL新查。
5. `python -X utf8 docs/evidence/2026-11-15-review/write_db_report.py <临时连接JSON>`：首次只读汇总SELECT把LINES作为别名导致1064/退出1，保留tools-failures下原脚本与失败摘要（明确不是重建stdout）；新工具改line_count后重跑退出0，输出db-checks.md、db-report-run.log。
6. `python -X utf8 docs/evidence/2026-11-15-review/finalize_review.py`：实际退出0，只读Git与本轮证据，生成README、review.json、199个当前运行输入摘要及交付差异记录，不读旧结论替代本轮结果。

上述“实际进程退出码”来自工具返回或PowerShell `$LASTEXITCODE`，不是根据PASS字样推断。主交互流程终端stdout没有另存完整原始transcript；逐条实际检查保存在checks.jsonl，原请求响应和逐POST七表前后保存在http.jsonl，不伪造终端回放。两端clean verify原始构建输出另完整归档。

## 图形界面与截图

使用computer-use插件的cua_repl，仅访问本轮localhost。真实UI：U01→毕业专区→U03游客登录链接→alice登录→购物车；后台admin登录→A02→商品查询“复核商品”→A10。按界面真实状态采集8张原始JPEG，未编辑截图。两次用户登录中间的E启停使浏览器旧会话失效，重登后查看新85元已发货快照。浏览器登录是单独的只改会话动作，未称为http.jsonl捕获的HTTP记录，也未作产品数据库写入。

截图API：`tab.screenshot({fullPage:true})`，通过`fs.writeFile`写入本目录screenshots；文件原始尺寸/SHA在screenshots/index.json。截图06仅含本轮脚本声明的虚构收货字段，不含真实私人资料，未声称其收货区已经遮盖。目视核查通过contact sheet辅助展示（派生图只存本机可视化临时目录，未冒充原截图）。

## 完整性和收口

历史完整性与当前质量的真实命令、退出码见integrity/commands.md、commands.json、quality-final.json；换行字节补偿工具为integrity/capture_bytes.py，新增capture-byte-audit-final.json提供归档文件实际字节摘要，原body/index不改。

实际执行 `git diff --exit-code 0329c9810c4ad2719c4ae95190ff516d1d21a9ed -- <产品路径>` 和旧README/docs（排除本新目录）均退出0，记录于delivery-checks.json。本轮进程停止、mysqladmin shutdown和最终端口/PID核对见environment/final-stop-*；MySQL正常退出0，Java显式停止实际进程码-1均如实记录。datadir及临时凭证保留，不删除开发资源。


## 暂存检查

已实际git add仅暂存本目录与.gitattributes；暂存607个文件时路径守卫全部符合允许范围，606个新目录文件text属性全为unset。git diff --cached --check将受保护的CR/原始响应行尾报告为尾随空白（退出及数量见staging-validation.json）；保留字节，不为消除该警告改写原始响应。仅.gitattributes的空白检查退出0，产品diff退出0。提交命令为git commit -m "docs: record independent STEP01-12 review evidence"，实际提交SHA以会话最终回复与Git记录为准；不push、不合并。
