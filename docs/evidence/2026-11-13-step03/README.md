# STEP03 用户端目录与毕业专区验收证据

最终完整通过为 attempt3，精确受测实现提交 `ad43f8f213d858b2d7b15b0676ed2e438051ebb2`，分支 `feat/step03-catalog`；顶层 result.json 是该轮原字节副本。基线 main 为 `f9fd249b7a8c0a6ea6111133062d9e701096ef9d`，Maven Wrapper 独立先行提交为 `17a57809946099edaedd67e466518ad0aaf412e8`。后续文档/证据另行提交，不把归档提交冒充受测代码 SHA。

## 独立轮次

| 轮次 | 结论 | 原因与范围 |
| --- | --- | --- |
| attempt1 | FAIL | 空库与演示库首页观察通过后，验证器参考 SQL 的 CONVERT 默认排序规则与 code 列的 as_ci 混合，ERROR 1267。diagnostic-attempt1 保存独立复现的确切 SQL/stderr。只修验证器，失败原证据不覆盖。 |
| attempt2 | FAIL | 同一旧生产提交 68244c371e5522f590d340459b7e4b679cc2abac。非空 q 的真实 HTTP 返回 500。独立实 JAR CatalogService 诊断确认所有非空 q 均因 MyBatis 对 record 派生 likePattern 属性映射失败；不是 emoji 特有问题。diagnostic-attempt2 保存实际异常栈。 |
| attempt3 | PASS | 修复后的新实现提交在全新隔离 MySQL 上重新完成全部 HTTP、SQL、浏览器与零写入核对。Mapper 通过显式 bind 传递派生 LIKE 值；搜索框移除 UTF-16 maxlength，服务端仍严格按码点校验 120 字符，页面给出关联提示。 |

## 实际观察与边界

两端 Wrapper verify 构建退出 0；构建来源为根目录 fresh PowerShell，PATH 不含 Maven，实际命令与退出码见构建 JSON/脚本及日志。Wrapper 固定 Maven 3.9.16，使用本机已存在缓存，不声称重新下载；只解决 Maven，不提供 JDK。环境为 Microsoft OpenJDK 21.0.12.1、MySQL 8.4.9，实际数据库端口见 attempt3/result.json 与 launches.jsonl。应用端口为 8080/8081。

每轮都建立新的私有 MySQL 数据目录，先核对 UUID/端口再导入未改动的两份 SQL。结构库和演示库分别测试，应用仅获两库 SELECT 权限；原有 MySQL 服务与开发库未参与验证。空库首页/列表正常空态，详情 404。演示库物理总量 60，公开 ON_SALE 为 54，DRAFT 为 6；公开总数不写成 60。

本轮覆盖首页主题排序、新品与精选数量/顺序、二级入口规范化与毕业横幅；主题/类型/字面关键词联合筛选；四种固定排序完整 54 项序列；count/list 一致；分页保留条件、条件变化回首页、越界页有效回退；合法 Long 但不存在/非一级主题返回 404，非整数/越界/非法枚举与长度返回 400；Long.MAX_VALUE 页不会乘法溢出；DRAFT 不公开、售罄仍可浏览。详情核对名称、SKU、价格、库存、父子面包屑、相册排序、无相册回退封面、缺图占位和禁用加购入口。后台仅回归原首页与未实现路径 404。

字面 `%`、`_`、反斜杠和 `!`、XSS 文本及缺失 GRADUATION 代码以私有库临时夹具验证，单独记录在 fixtures.jsonl；只有验证器 root SQL 临时修改数据，应用仍为 SELECT only。夹具每次恢复，并核对七表有序全字段行的行数与 SHA-256；只归档汇总，不保存用户散列、订单地址或原始行。结构空库也留存前后摘要。

62 张截图覆盖 1366×768 与 1920×1080 视口，fullPage 图片高度可能超过视口。screenshots.json 记录尺寸及 SHA-256，screenshots.md 给出索引。浏览器使用真实 Edge 正常 GET，检查图片实际加载/缺图回退、无横向溢出、label/id 关联、类型/分页状态、禁用购买、转义文本与无 GET CSRF 字段；不把直接 GET 当成真人输入动作或未开发的加购/身份验证。

## 审计与复现

commands.jsonl 记录实际外部命令退出码与耗时；http.jsonl 索引脱敏响应，启动请求轮询不属于业务验收响应。源码清单为 runtime-inputs.sha256，JAR 摘要、Git 状态与全 SHA 在对应 result.json/launches.jsonl。浏览器工具与 case 清单从最终轮开始各自快照；前两轮仍保留当时 Python 工具和原始部分截图。

所有归档响应先收集并移除已知会话/CSRF 值，URL 会话矩阵参数也脱敏；不含 Cookie/Set-Cookie 原值、数据库随机口令、BCrypt 实值、完整收货信息、私有初始化 SQL、JAR、缓存或数据库目录。执行进程均已停止。工具依赖本机外部运行目录，复测应指定新的 attemptN 与完整 STEP03_TESTED_CODE_SHA，不直接在归档目录运行。

本步只证明 REQ-02/REQ-03 公开浏览与相关基础校验。TST-01–04/TST-33 中购物车、登录及写入部分仍待后续步骤，不记为完整业务通过。交叉复核及组员实名仍须按项目台账补齐。

## 独立首页状态补充

全量 attempt3 不变。复核发现结构空库同时缺少主题和商品，且种子首页两栏未展示零库存，因此额外建立全新的私有数据库，在同一 `ad43f8f213d858b2d7b15b0676ed2e438051ebb2` 与相同 JAR 上执行 `supplement-home-states`。该补充 146 项检查通过，记录 9 条 HTTP 和 4 张截图，数据库端口 61857。

第一场景仅以 root SQL 将商品 1 库存设为 0，精选仍含该卡片并显示“售罄”；第二场景暂时将全部 60 商品状态改为 DRAFT，5 个主题、毕业入口与搜索表单仍保留，两栏分别显示无可售商品空态，各主题及全局/关键词列表均为 200/总数 0。每个场景在夹具写入后和应用读取后比较七表摘要，均无应用写入；每次恢复后与原始摘要一致。应用仍只有 SELECT 权限，全部进程停止。supplement-screenshots.json/md 单独索引新增 4 图，不把它们混入原全量 62 图或覆盖旧结果。

## 最终复核与变更位置

本次新增的[变更清单](changed-files.md)、[代码与证据独立复核](code-review.json)、[66 图逐图视觉复核](visual-review/README.md)、[真实 JDBC 参数绑定回归](parameter-binding/fixed-binding-result.json)与[文档范围核对](document-scope-review.json)均为 AI 辅助复核资料，不替代人类组员复核。开发台账 STEP03 标为“待复核”：代码与自动实测完成，姓名待填，M3 前补齐组员关键业务抽验。

运行输入在受测开始/结束与最终归档前均按 85 个文件核对；文档、证据及归档属性规则不属于运行输入。新增文档/证据后单独提交，归档提交不是新的运行受测身份。SQL 执行计划仅记录当前小型数据集观察，不宣称全部查询同时命中两条商品索引或已完成大数据量性能验收。
