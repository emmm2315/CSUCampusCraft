# STEP05 后台分类、商品与补货验收证据

最终完整通过为 attempt3。受测代码 93f3c461163ff09f54b667299360068d450ca254，分支 feat/step05-admin-catalog，main基线 a8438b72493fba108577e0ba4918e61b043b8916已含STEP04。测试起点工作区干净，121项运行输入摘要 bb0cd1144b5d2b09ddc4e4d29ff381416066a6f8afbafcc804f287644623d591在结束与归档前复核无漂移。顶层result/runtime/versions为完整轮原字节副本，文档与证据随后提交，其新SHA不冒充源码受测提交。

## 结果和环境

1273项主工具断言、201条主HTTP，83份主轮写前后记录（82份HTTP + 1份Native Service补充），浏览器280项检查和28张两视口关键图，原生Service事务探针通过。断言有包含关系，不是独立业务用例数量。双端实际Maven Wrapper verify退出0，JDK21.0.12.1、Maven3.9.16、MySQL8.4.9，数据库端口58353，HTTP8080/8081。SQL、POM、assets与用户端源码未改。

所有运行只用新私有MySQL数据目录。先核对server UUID/端口与本轮datadir，再导入原演示SQL；两个JAR显式127.0.0.1，监听OwningProcess核对本轮创建PID后才发业务POST。应用只在category/product有INSERT/UPDATE/DELETE，其余5表无DML权限；另有全库SELECT及支持锁读的LOCK TABLES。原开发库与服务未参与。

## 覆盖与数据库对照

分类：21字符一级编码生成32字符二级，22/空编码400；大小写重复code、同父同名/同类型409；不存在父404、非一级父409、非法type400。编辑忽略code/parent/type篡改，只更新name/sort；有子分类和草稿商品引用的删除409，空分类删除303。AUTO回填ID经HTTP createdId及独立Service返回均按主键查到同一行。

商品：新建DRAFT和默认字段、CI SKU冲突、名称/价格/summary/UTF8 description65,535字节/封面255字符等边界；仅合法二级类目。编辑忽略SKU/stock篡改，version条件更新，合法同值编辑version及updated_at均不变；旧版409。上/下架精确状态与版本；礼盒49.00/12库存按独立SKU演示上下架，公开读同步可见/不可见。增量10+3=13、重复合法补货独立加值，旧资料表单409，非法增量和库存/version上溢拒绝零行变化。历史订单快照未动。列表count/list与独立SQL参考一致，根/叶分类、状态、字面字符%/_/反斜杠/!、分页和超页均覆盖。写回跳只接受/products固定读上下文，保留全部合法5条件和字面搜索；外部地址回退。

每个业务Service写HTTP的前后七表有序全字段摘要及category/product变化行在 database-writes.jsonl。长summary/description只存字符/字节数和SHA，不重复存大文本。拒绝分支摘要相同；其他5表（用户、相册、购物车、订单、明细）全轮原始/最终摘要相同。成功category/product修改是预期变化，没有伪装为整库不变。主轮最初3个未认证POST仅有即时前后摘要相等断言，没有保存逐次原始delta；不把该缺口隐藏成完整ledger。新增的独立游客补测另存3份完整逐次对照，不能回填或冒充主轮旧请求。Native真实Service补充合法补货与新增分类单列为一次补充记录，不冒称主HTTP。

## 事务内部补充

ActorWriteProbe从实际受测admin JAR提取类/依赖，启动临时本机上下文，直接调用真实Spring代理ProductService.restock和CategoryService.create；没有新增生产路由、依赖或注入故障Hook。Executor观察器只记录占位SQL、事务隔离及同连接布尔，不修改SQL/结果。SQL_TRACE证实首条Mapper业务SQL是锁ADMIN，后锁目标，RC且同连接；stock/version增量SQL与提交值一致。缺身份、旧stamp、CUSTOMER及临时禁用ADMIN拒绝且无目标写。Native临时root状态夹具保存/恢复同一UTC原值；最终store_user摘要与原始相同。它不是并发/订单购买/后台启停接口验收。

TST25/26的本步分类与商品范围通过；TST27用真实补货增版制造旧资料409，只证明本步部分；TST28只证明顺序增量与溢出，用户购买2并发补3最终11、故障回滚留STEP13。相册、控制台、订单和顾客模块未实现。

## 失败与权限诊断

attempt1在产品启动前失败：表尚未导入时授表级DML，MySQL1146；调整工具顺序，不改产品。attempt2在首次分类非法输入请求返回500：测试账号对store_user只有SELECT，锁读被MySQL1142拒绝。该轮七表未变，原FAIL保留。

在attempt2私有datadir的独立副本复现：普通SELECT成功，FOR UPDATE拒绝；只增加schema LOCK TABLES后相同锁读成功。原失败目录未被诊断改写。MySQL8.4的FOR UPDATE除SELECT还要求至少一种相关锁/写权限，参见[MySQL官方锁读文档](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking-reads.html)。本轮选择LOCK TABLES，使其他5表仍无DML；README开发账号原本已有全库DML，本来满足条件。attempt3同源码、新私有库完整通过，不拼接失败局部结果。

## HTTP正文、截图和隐私

http.jsonl的body_file为脱敏原文的gzip按内容SHA去重，body_encoding=gzip；redacted_body_sha256对应解压后的UTF8脱敏正文，evidence-files.json另校验压缩文件原字节。复核与敏感扫描必须先解压，不能跳过.gz。少数runner中文断言标签受Windows管道编码影响，结果JSON/HTML和数据库证据均显式UTF8并为准，原控制台记录未改写。

[screenshots.md](screenshots.md)索引28图；浏览器真实提交负面表单，noValidate用于观察服务端400/409，限定具体表单的CSRF避免误选退出表单。拍摄前滚动触发原有lazy图片、等待实际加载，保持原路径/回退行为；没有改业务前端。密码为空、Cookie/CSRF/散列/教学密码无原值归档，长文本边界不含完整收货隐私。逐图AI复核不替代组员人工交叉复核，实名与M3抽验仍待补。

工具依赖当前机器外部运行目录。复测需新的attemptN与完整STEP05_TESTED_CODE_SHA，不在归档目录直接重跑；不要把准备阶段编译/辅助诊断当成业务通过。所有跟踪进程已停止，私有数据目录/依赖提取缓存不归档。

## 私有运行清理

所有attempt的进程停止后，按绝对路径逐一核对在本验证目录内，清理5个私有数据/依赖提取目录；见private-runtime-cleanup.json与cleanup_private.py。诊断时未改原datadir，随后只清理私有运行目录，不删除任何旧EV。原始失败与完整通过文件均保留。根目录final-input-recheck.json额外重算121项当前源码、顶层result原字节及28 PNG摘要。

## 独立游客拒绝补测

supplement-guest-rejections使用同一源码SHA与完全相同的JAR摘要、新私有演示库（MySQL端口63571），仅启动实际admin 8081并验证监听PID；user JAR仅核摘要，本小补测没有重复运行用户端或整套业务。三个新游客POST分别为/categories、/products、/products/1/restock，均302到本端登录且不重放原POST。每个请求分别保存7表原始before/after摘要、category/product全部关键行before/after及空delta；最终7表仍等新库初始。36项检查、3条HTTP、3份写记录、0图，121输入稳定，进程停止。它补充路径拒绝行为的新观测，不证明或重建旧seq4/5/6已丢失的原始逐次测量。原attempt3和顶层主结果原字节未改。

## 最终独立复核与变更

[变更清单](changed-files.md)、[源码静态复核](cross-code-review.json)、[实际提交输入复核](committed-source-review.json)、[解压原始证据复核](final-evidence-review.json)、[文档复核](final-document-review.json)、[文档范围守卫](document-scope-review.json)和[28图逐图视觉复核](visual-review/README.md)已留档。它们都是AI辅助，不替代组员实名/人工复核；台账待复核，M3前补齐关键业务抽验。

A04长名/最大价边界图操作列文字折行，但完整可读，无覆盖/页面横溢，作为非阻断UI密度观察保留，受测源码未为此改变。原始83记录精确为82HTTP+1Native；另3游客拒绝补测完整前后对照，独立成目录，不回填主轮。压缩body的SHA、敏感扫描均按解压后内容核对；归档文件本身另有字节SHA清单。
