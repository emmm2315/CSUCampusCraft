# Word 指导书定向更新验证

本次由 AI 按用户授权做文档状态收口；不是新增实测或代替本人签署。高宇弘于 2026-11-15 的本人七项抽验与签署，见 [本人执行记录](../../../README.md#本人执行记录2026-11-15)。

更新文件：`docs/实验一 CSUCampusCraft 校园文创商店实验指导书.docx`。

| 项目 | 更新前 | 更新后 |
| --- | --- | --- |
| SHA-256 | `1202242524c1e3947de820761b9a976376d8410615b43118202f1de69ff21f93` | `85d3e052f82c3a79f1bd7259b84ceb229ed4c8fd5526d980c0412e4c0cae7c4d` |
| 文件大小 | 57,480 B | 57,753 B |
| Word 实际分页 | 19 | 19 |
| 主体段落 / 表格 | 319 / 2 | 319 / 2 |

只改五个段落的文字节点（主段落从零编号 3、19、37、51、292）：前言当前阶段、实际分工、账号段的 M0 历史身份、STEP01 预期段的历史身份，以及联调演示导语。STEP01–14 的操作指引、表格、原实测内容保留；M0 根页显示五主题的操作条目保留为历史复现指引，不作为现行双端首页行为。

ZIP 中仅 `word/document.xml` 的上述文字变化；样式/版式 XML 骨架、所有表格 XML 及其余 ZIP 成员均保持原字节。已重新打开验证 ZIP CRC、全部 XML/关系文件可解析、python-docx 可读取及 STEP01–14 标题存在。详见 [结构与文本验证](word-update-validation.json)。

实际使用 **Microsoft Word 16.0 COM（只读，不保存输入）导出 PDF，再以 bundled pypdfium2 转为 144 dpi PNG**。更新前后均 19 页；第 1、2、3、4、18 页因授权文字修改而变化，其余 14 页 PNG 像素摘要完全一致，见 [分页与像素对照](word-render-comparison.json)。AI 逐页打开原尺寸 PNG 完成目视检查：本子任务查看 1–10、18 页，主任务查看 11–17、19 页；所有页文字、表格、页眉页脚无裁切、重叠或缺字，未验内容保留为操作指引。此目视检查属于 AI 文档版式校验，不冒充高宇弘新增人工操作。

打包的 `render_docx.py` 已实际尝试：首次因 sandbox Temp 权限失败；改用本轮 workspace 临时目录后明确报告 `LibreOffice soffice.exe was not found on PATH`，日志分别保存在 [首次日志](canonical-render.log)、[workspace Temp 复测日志](canonical-render-workspace-temp.log)。Bundled Windows runtime 未提供 LibreOffice，未调用用户桌面 LibreOffice。Word COM 在 sandbox 内初始化时报访问拒绝，获得本轮已授权的主机执行后可用；第一次传入斜杠路径时 Word 把路径解释为 URL，返回找不到文件，规范为 Windows 路径后基线与更新稿均只读导出成功。保留这些工具失败事实，不作为产品缺陷或本人抽验异常。

实际成功命令使用 bundled Node/Python，路径由 workspace dependency loader 返回：

```powershell
$dep = 'C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies'
# 首次 Word 编辑前成功执行一次，退出码 0
& "$dep/node/bin/node.exe" 'C:/Users/Starmetor/.codex/plugins/cache/openai-primary-runtime/documents/26.1112.11011/skills/documents/container_tools/mark_artifact_operation_started.mjs' --operation-kind edit --expected-output-count 1 --output-format docx
& "$dep/python/python.exe" -X utf8 'docs/evidence/2026-11-15-review/closeout/owner-review-docs/word/update-word.py'
# 更新前后分别调用；InputPath 同为目标指导书，输出 before.pdf / after.pdf
& 'docs/evidence/2026-11-15-review/closeout/owner-review-docs/word/render-word.ps1' -InputPath 'D:/Github Projects/CSUCampusCraft/docs/实验一 CSUCampusCraft 校园文创商店实验指导书.docx' -OutputPdf 'D:/Github Projects/CSUCampusCraft/docs/evidence/2026-11-15-review/closeout/owner-review-docs/word/_qa/after.pdf'
& "$dep/python/python.exe" -X utf8 'docs/evidence/2026-11-15-review/closeout/owner-review-docs/word/render-pdf-pages.py'
```

更新脚本内置更新前 SHA 门槛，禁止对已更新文件重复套用。临时 `_qa` 内的 DOCX/PDF/PNG 仅作内部校验，完成后清理，不提交大量中间文件；各页摘要和实际导出元信息保存在上述 JSON。REV-06 本轮 Word 更新完成；STEP13 整体/并发/故障验收待执行，P1 未选做，不生成其通过结论。
