# STEP04 双端登录与访问控制验收证据

完整通过为 attempt4，实际受测代码 `74e6272e5b60ac1604964f7e50909f4a1490086f`，分支 `feat/step04-auth`。main基线 `f5372631f24dc265abda7eeeb2711584417abfe9`已含STEP03。开始工作区干净，103个运行输入清单SHA-256为 `e4f937e512c9e2f3f526a6645e45966bb371793843fa162de842d8606d377194`，结束再次确认无漂移。顶层result/versions/runtime-inputs/git-input-status为完整轮原字节副本。后续文档归档提交不替代受测SHA。

## 结果与范围

主工具920项检查通过、192条脱敏HTTP；浏览器另416项检查、56张两视口截图；两端原生session探针各27项检查。这些是断言计数，主工具包含对子工具的通过断言，不能合称独立业务用例数。

环境为Microsoft OpenJDK21.0.12.1、Maven3.9.16、MySQL8.4.9。双端实际Wrapper verify退出0，附离线设置/缓存参数，完整命令见构建JSON/脚本和日志。新私有MySQL目录端口59448，应用8080/8081，共用csucampuscraft，应用仅SELECT，不连接现有开发库。SQL未改，本轮导入演示版。七表仅归档行数及有序全字段SHA，不存散列/收货原始行。

覆盖双端GET/login；错误/不存在/禁用/错端角色统一提示，另验密码原样；缺字段400、密码清空；登录缺/错CSRF403、成功303；同host同Cookie jar及真实浏览器双端登录，两Cookie名称独立、session ID变化仅记boolean，双向退出隔离，CSRF保留。管理GET/未认证302、认证后初始化主题页，用户目录公开200；未来保护路径未认证302、认证且合法CSRF后未实现路径404；无身份POST先登录，有效身份错CSRF403；合法GET returnUrl保留、非法回/、POST不重放。管理退出固定303到/login，没有扩大ReturnUrlPolicy。

root SQL夹具模拟禁用、GREATEST单调启用、错角色及只加1微秒updated_at。旧会话不复活的本轮证明是已被清除的身份仍不可用，另测1微秒戳变化；不宣称后台启停API、双会话/竞争/真实同微秒写已完成。TST-39留STEP12，其他业务表写仍未实现。

原生探针从精确受测JAR提取classes/已有依赖，在临时端口启动相同应用类的Tomcat上下文；没有新增HTTP路由。真实GET/POST登录后从原生session manager读取SessionIdentity，与只读JDBC UTC原值比较，固定非零微秒123456未截断；只输出boolean。探针还验证旧stamp/不存在ID清身份与结算占位、合法CSRF失败重登清旧身份/确认、错CSRF保留身份、退出失效。它是相同JAR类的补充验证，不冒充主8080/8081的额外业务接口。

## 夹具与零写入

夹具root SQL单独记录，所有独立mysql客户端连接显式UTC。启用用GREATEST推进；role测试只恢复role并保留stamp。原始seed状态/role/stamp只在全部HTTP、探针和浏览器结束、即将关闭进程时统一恢复，之后不再发送验收HTTP。每个夹具内读取前后摘要一致；最终七表与原始完全相同。最终fixture_cleanup_succeeded为实际摘要比较，进程均停止。

## 失败与复测

- attempt1整体FAIL：HTTP39正确为400登录表单/字段错误，工具误要求正文出现数字400。修为允许内联字段400并保留HTTP状态及技术信息排除检查。
- attempt2整体FAIL：UTC读取TIMESTAMP，恢复新连接却用SYSTEM+08，账号1/4的updated_at偏-480分钟。独立复制失败私有数据后，只有store_user摘要不同；副本仅修两行timestamp便七表全等。原EV与原datadir未改。早两轮cleanup=true仅表示恢复SQL执行完，不能当作值已恢复；最终轮改为实际七表比较。
- 时区诊断最早未指定UTF8客户端，摘要字节/系统区名解码不可靠，不用于产品判断。后续UTF8诊断查询与七表比较完成并写PASS结果，最后控制台打印因Windows GBK编码退出1。原结果/工具快照保留，成功读取结果文件，不宣称诊断一次启动至退出无错。
- attempt3整体FAIL：主192 HTTP及两端session探针通过；已认证登录页有退出和登录两个合法CSRF输入，宽泛locator触发strict mode。只收窄登录form的错误token注入，另建attempt4。旧browser/result在提前异常时只反映已做断言，没有完成标记，不能当完整PASS。
- attempt4同源码、第四套全新私有库完整PASS；browser明确completed=true且exit0，不拼接失败局部结果。

## 截图、脱敏与复现

[screenshots.md](screenshots.md)索引完整56图；旧attempt3的25图独立保留。浏览器真实填表提交，字段400用noValidate绕HTML5以测试服务端；错误CSRF仅修改登录form。截图前密码字段必须为空、无value回显；没有横向溢出/URL会话重写，图片实际加载。成功POST303截图为跟随后的目标读页，JSON status是触发响应。逐图AI复核由另一执行单元追加，不替代组员人工交叉复核。

HTML先收集并移除会话/CSRF值；命令不输出秘密环境或POST字段值；Cookie只存名称/存在性，ID变化只记boolean。BCrypt实值、数据库随机口令、会话/CSRF原值、完整收货信息、JAR、依赖、私有DB目录不归档。工具依赖本机外部目录，复测指定新的attemptN与STEP04_TESTED_CODE_SHA，不直接在归档目录运行。TST-05/06/07/31仅本步身份覆盖；TST-39留STEP12。实名待填，组员M3前交叉复核。

## 独立逐图复核

[视觉复核](visual-review/README.md)记录56/56逐张view_image检查，绑定各图SHA、视口和观察。旧失败轮interim独立保留。此为AI辅助审查，组员真人交叉复核和姓名仍待补。原生JAR输入、完整轮result原字节和最终七表摘要已在归档前再核对。

## 最终复核与变更

[工程/文档文件清单](changed-files.md)、[跨端源审查](cross-code-review.json)、[受测源码审查](committed-source-review.json)、[独立原始证据审查](final-evidence-review.json)、[文档审查](final-document-review.json)和[文档范围守卫](document-scope-review.json)均已保留。所有复核为AI辅助，不替代姓名待填的组员人工交叉复核；开发台账保持待复核，M3前抽验关键业务。

私有datadir仅在诊断时复制并校正副本，原失败证据未改；取证结束后清理本轮临时运行目录，清理结果另档。旧轮部分浏览器JSON的PASS不能覆盖父轮FAIL，完整通过只认attempt4 completed=true/exit0与最终七表恢复。8个文档/归档属性文件随后提交，受测SHA仍为74e6272e5b60ac1604964f7e50909f4a1490086f。
