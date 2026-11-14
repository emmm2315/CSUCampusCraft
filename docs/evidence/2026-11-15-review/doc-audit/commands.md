# 本子任务实际命令

工作目录：`D:\Github Projects\CSUCampusCraft`。执行者：Codex AI 文档检查单元。以下均为只读源材料检查，输出只写新证据目录。

1. `git branch --show-current`：输出 `feat/review-2026-11-15`。
2. `rg --files csucampuscraft-user/src/main/java csucampuscraft-admin/src/main/java | Sort-Object`：枚举当前源码。
3. 首次大范围 `rg -n 'Mapping\(|登录|改量|失效|缺失|productVersion|STEP0|STEP1' ...` 同时传入不存在的 `csucampuscraft-user/src/main/resources/templates/catalog`，退出1，并报告路径不存在；输出过长被截断。这是检查命令路径错误，不是产品失败。后续改为实际 `templates/products/detail.html`，定向读取，并用下述可重跑脚本完整抽取。
4. `Get-Content csucampuscraft-user/src/main/resources/templates/products/detail.html -Encoding UTF8 | Select-Object -Skip 31 -First 39`：读取游客选购模板，观察“登录后加购”。
5. `Get-Content csucampuscraft-user/src/main/java/org/csucampuscraft/storefront/cart/CartService.java -Encoding UTF8 | Select-Object -Skip 90 -First 115`：读取改量/移除的当前实现。
6. `Get-Content csucampuscraft-admin/src/main/java/org/csucampuscraft/admin/catalog/ProductImageService.java -Encoding UTF8 | Select-Object -Skip 94 -First 34`：读取缺失父版本409的分支。
7. `Get-Content docs/系统设计与路由.md -Encoding UTF8 | Select-Object -Skip 63 -First 34`：读取用户端表及查询契约。
8. 用 Python `zipfile.ZipFile` 读取 Word 的 `word/document.xml`，以 `xml.etree.ElementTree` 抽取382个段落，筛选阶段文本；没有调用任何Word写入工具。
9. 完整新跑、可重现命令：

   ```powershell
   python -X utf8 docs/evidence/2026-11-15-review/doc-audit/audit_docs.py
   ```

   退出0；实际输出用户端17/文档17、管理端28/文档28，差集均空；5项文档问题；Word前后SHA-256相同。Python启动时打印 `Failed to find real location of ...python.exe`，但解释器继续执行脚本且退出0，该启动器提示如实保留。

10. `git diff --name-only`：当时已跟踪文件只见主代理获授权修改的 `.gitattributes`；`git status --short -- docs/evidence/2026-11-15-review/doc-audit` 显示本子目录为新建，未改旧文档。

准确的确定性抽取/比较逻辑全部位于 `audit_docs.py`，运行结果位于 `audit.json`，静态差集另存 `routes.json`。没有将静态读取写作HTTP已通过。
