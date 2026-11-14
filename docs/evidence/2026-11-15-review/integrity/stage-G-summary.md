# 阶段 G：证据归档完整性小结

本小结仅覆盖 G 的证据与受测源码身份部分；路由/文档/Word 现状由主执行者另录。本轮执行人为 Codex AI，不能代替用户的人工复核或签名。以下结论来自本轮实际重算，不采用历史业务用例的 PASS 句。

**归档字节核对 PASS；“各旧受测 SHA 之后产品源码均未变”不成立，已逐步记录后续实现差异。**

- 13 个 STEP02–12 目录（含 STEP07 原本地、组员导入、合并后）均有 README；12 个有顶层 result，组员导入按原结构无顶层 result，具有 summary/http84/probe/browser 的分项结果，未补造。
- 本轮按旧归档索引独立读取 4,764 个文件，SHA-256/字节数全部匹配，0 缺失/不匹配；同 4,764 路径逐项 `git check-attr` 均为 `text: unset`。
- 37 份 runtime 清单（含每个正式 attempt 和补充，组员版为 before/after JSON）共 4,461 个文件条目重新核对。所有已声明清单摘要匹配；组员 before/after 的 files、JAR 摘要及规范 JSON inputs_digest 自一致。
- 原运行输入有 LF、CRLF、混合换行；不能把 Git LF blob 哈希直接当原运行字节，也不能把当前 checkout 字节等同历史运行字节。所有 4,461 条都能从各自受测 Git blob（组员使用后来 publication 关联代码提交）只改变行尾精确重建原 SHA。STEP06 的 3 处、STEP11/12 CSS 的 2 处混合换行另有独立诊断，保留严格原字节不匹配计数，不把它改成“逐字节全等”。这证明文本内容可关联，不是重新运行历史代码。
- 各现存 attempt 目录与 result 均有独立清单；失败 attempt 原文件随归档 SHA 一并通过重算。STEP02 attempt1 与 STEP11 attempt1 的原 result 保留历史 raw `PASS`，与后来整轮否决记录不是一个口径；本轮仅登记原标签，不把它们认作完整通过，不改写旧结果。
- 从各受测 SHA 到本轮基线 `0329c9810c4ad2719c4ae95190ff516d1d21a9ed`，仅 STEP12 的产品源码/SQL/POM/Wrapper/assets diff 为空。STEP02–11 有后续新增或修改，详见下表和各 detail JSON。不能据旧证据推出当前整库所有功能通过；本轮新跑检查以及 STEP13 仍必要。
- 本轮检查时，以上旧证据目录相对本轮基线的工作区差异为空；未修改旧证据或源码。

| 归档 | 原受测/发布关联 SHA | 受测 SHA→本轮基线产品差异路径数 |
| --- | --- | ---: |
| STEP02 | 5d9271d7e32634f947eb9f6077e7a4f3d98806a7 | 155 |
| STEP03 | ad43f8f213d858b2d7b15b0676ed2e438051ebb2 | 133 |
| STEP04 | 74e6272e5b60ac1604964f7e50909f4a1490086f | 116 |
| STEP05 | 93f3c461163ff09f54b667299360068d450ca254 | 95 |
| STEP06 | 1aa6ad0c4a7546c5bfba7ed65ef05f5913132027 | 86 |
| STEP07 原本地 | 3bc5629bcbcbeefa6cbc8f655e8cb4d790c81b77 | 71 |
| STEP07 组员 | 原实测未提交；后来关联 ceb4059717d59020b999d1479a7ef5f647a89e14 | 86 |
| STEP07 合并后 | 9e61c3e88761519fc63a4d99cafb006a51eacfa5 | 69 |
| STEP08 | 54d6b007eb1317c14be090016ea75aec02ead6c5 | 63 |
| STEP09 | 1399c311f34c98907ee80c812cfe71606b9820c7 | 45 |
| STEP10 | b0253a5ecc920dfa862eec0eb8358f301ac41c10 | 36 |
| STEP11 | 39c96aaaad18c58dce9d57450e14317a75c29b3d | 22 |
| STEP12 | 03384367c87147f1c29859c799f3c464b016b760 | 0 |

证据：`../evidence-integrity.json` 为结构化总表；本目录每个 step JSON 包含全部文件条目和实际摘要、差异列表；`commands.json` 为真实 Git 命令/退出码；`run-result.json` 为最终审计 stdout/stderr/退出 0；`commands.md` 保留首次警告和一次临时诊断工具失败。复现：先运行 `verify_integrity.py`，再运行 `newline_diagnostic.py`，最后再次运行主脚本复核混合换行诊断。重算不会改变原文件。

当前 review 运行输入另存 `review-runtime-inputs.sha256`，供本轮结束时复核；它不替代任何旧清单，也不为当前业务验收提供通过结论。归档完整性证明只覆盖已有清单所列文件与 Git 对象，无法证明失败瞬间是否另外存在未归档文件。
