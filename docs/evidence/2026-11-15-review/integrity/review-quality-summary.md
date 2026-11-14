# 本轮新证据独立质量审计

执行者：Codex（AI）；仅检查新证据，未改任何产品源码、原 HTTP/SQL/检查日志或原阶段小结。初审为 `review-quality.json`，后续扫描快照为 `review-quality-followup.json`。本报告不构成人工签名。

## 已发现并保留的问题

1. **P2：新 HTTP 正文摘要索引的字节口径错误。** `common.py` 在 Windows `write_text` 转换行尾之前计算 `body_sha256`。该字段不是所有归档 HTML 文件的原始字节摘要；非空正文常见 CRCRLF。新建 `../capture-byte-audit.json` 对每条 HTTP 提供实际 `raw_file_sha256`、原声明、只逆转一次 CRLF 的内存重建摘要，不改原文件或索引。审计快照含主轮 HTTP 1–340 与失败 attempt1 的 1–38，共 378 条；166 条原字节直接匹配、212 条原字节不匹配，378 条全部直接匹配或逆一次 CRLF 后精确匹配。原始失败与字节差异均保留。后续 HTTP 应另生成增量/最终索引，不能把本快照写成覆盖未来请求。
2. **P2：E 的相册排序断言收集了重复嵌套标记。** 原 `E A10 SQL order` 失败保留；每图 article 与两个 form 都带 `data-image-id`，原实际六个标记不能直接比两行 SQL。新 `supplement.py` 真实增删两图并按 article 行比较 SQL，通过；还按同样行口径重读原已归档响应，得到与原 SQL 一致的两行。没有覆盖原 FAIL。
3. **P2：C 原小结的“封面变更”表述超出当时实际。** C 提交的封面与原封面同为 placeholder，不能证明变化后的快照。新补充真实换成合法站内但不存在的另一封面路径，独立比较订单两表完整行不变，U08/A07 的 src 仍为原快照；原小结保留，补充小结明确纠正。缺图路径不等于第二个真实资源文件。
4. **覆盖缺口已补：正向商品名搜索。** B 原检查仅有无结果关键词，不足以证明正向匹配。新补充用实际独立商品全名搜索，比较返回商品 ID 及总数 1。`%/_/!` 字面匹配与更多搜索边界未据此扩大为通过。

`supplement-result.json` 新 41 项检查无失败，`original_failure_retained=true`。这不改变 E 原阶段 FAIL。补充另验证全 60 个种子 SKU 的库存公式，以及独立新增商品 4+3=7。

## 脱敏审计

从本轮隔离库只读查询得到已知教学联系、收货字段与 BCrypt 散列，仅存扫描进程内存；读取临时配置中的随机应用口令同样只作内存匹配，未归档原值或片段。已知集合计数：联系值 4、收货值 9、散列值 4、临时口令值 1；收货字段无长度小于 3 的值，因此当前 `sanitize(len>=3)` 的短姓名风险本数据未触发，但不能推广为通用可靠脱敏器。

后续快照扫描新证据 466 个捕获文本文件，未发现已知邮箱、电话、收货字段上下文、散列或临时口令泄露；HTML 中 `_csrf`/`confirmationToken` 非空原值、非空 password 回显、URL 会话标记和 BCrypt 形态扫描均 0 项。可执行工具内 README 已公开教学口令常量及明确虚构测试输入按复现用途保留，不把它们当临时数据库口令。

已知字符串扫描有两文件命中（共十处），独立逐 JSON 键定位后全部仅为账号安全 `display_name` 字段，其文本恰好与某种子收货人相同，**不是收货/联系字段泄露**。以下只列键，不列值：

- `checks.jsonl`：733 行 `detail.before.display_name`、`detail.after.display_name`；737 行 `detail.actual.display_name`、`detail.expected.display_name`；742 行 `detail.before.display_name`、`detail.after.display_name`。
- `sql.jsonl`：114、118、119、120 行各 `rows[0].display_name`。

主轮 HTTP 1–340（182 POST）与失败 attempt1（38 HTTP、15 POST）编号连续且不重复；每条 POST 均有真实七表 before/after。HTML 文件原字节索引问题按上方 P2 处理，不误写为正文丢失或产品失败。GET 的 `before=None` 不是零写入证明。

## 结论边界

- A 从恢复原认证戳仍302证明身份已清；未直接读取服务端会话里的结算确认属性，重新登录后旧确认拒绝不能单独证明登录前已移除此属性。A 原小结已明确该限制，最终汇总应保留。
- F 的时间/支付字段 SQL 不是所有 CHECK 谓词穷举；35 个 CHECK 元数据与负库存代表拒绝仅按实际覆盖解释。
- 空业务控制台、错误配置、并发/竞争/故障注入、真实支付/物流、性能、P1 与独立人类组员复现不能据本轮顺序抽查声明完成。重启持久性由主执行者另建 `persistence` 阶段运行，此扫描快照尚未观察其最终结果。
- 阶段 A–F 均明确 AI 执行；清单明确人工姓名、亲自操作和签名尚待用户。不得将“本人（真实姓名待填）”写成已由人完成此次操作。
- 短 TTL 记录已逐条核对：HTTP 180 GET 登录、181 POST 登录、182 GET 确认、183 POST 下单409，与补充说明编号一致；这些是18080辅助实例，不是实等默认10分钟。
- 本轮结束时，当前运行输入、产品源码、旧文档/Word/旧证据保护，以及新增 HTTP/截图的最终扫描仍需主执行者收口。

复现实际命令：`python -X utf8 docs/evidence/2026-11-15-review/integrity/capture_bytes.py`（退出0）；`python -X utf8 docs/evidence/2026-11-15-review/integrity/audit_review_quality.py`（初审退出0）。后续快照通过加载同一只读模块并把 OUT 指向独立 `review-quality-followup.json` 运行，初稿未覆盖。
