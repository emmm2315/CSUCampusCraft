"""Generate STEP12 guide from the actual final run and precise observation boundaries."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;RAW=HERE/'verification/evidence'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
attempts=sorted([p for p in RAW.glob('attempt*')if p.is_dir()and(p/'result.json').exists()],key=lambda p:int(p.name[7:]))
run=read(attempts[-1]/'result.json');assert run['overall']=='PASS'
name=attempts[-1].name;date=read(HERE/'verification/evidence-date.json');meta=read(HERE/'verification/delivery-metadata.json')
br=read(attempts[-1]/'browser/result.json');assert br['overall']=='PASS'
review=read(HERE/'ui-visual-review.json');assert review['overall']=='PASS'
shots='\n'.join('- ['+x['path']+']('+name+'/browser/'+x['path']+')'for x in br['screenshots'])
text=f'''# STEP12 普通顾客管理与真实控制台实测

批次日期{date['evidence_date']}（Asia/Shanghai），首次正式起测见[evidence-date.json](evidence-date.json)。从已含STEP11的干净main `a899cce263526926292afec8ed55d6757aed0597` 创建 `feat/step12-admin-customers`；实际受测源码 **`{run['tested_code_sha']}`**。本步范围自动验收通过，组员实名复核仍待补；main未修改、不push。旧STEP07–11台账保留。每轮原始身份、结果与当前原字节清单见[result.json](result.json)、[original-attempt-inventory.json](original-attempt-inventory.json)，不补造缺失观察。

## 工程、构建与输入

Microsoft JDK21.0.12.1、Maven Wrapper3.9.16、MySQL8.4.9/InnoDB，SQL连接UTC、页面Asia/Shanghai。实际构建在2026-11-14 23:53:58 +08:00完成，两端均clean verify/BUILD SUCCESS/退出0：用户4.641秒、管理4.482秒。测试在次日本地日期启动，不把构建时间倒填为次日。[真实构建脚本](builds/build-fresh.ps1)、[用户日志](builds/build-user.log)、[管理日志](builds/build-admin.log)、[退出码](builds/build-exits.json)。复用已有离线settings/cache，无新依赖或测试框架；clean用于避免删除的旧初始化HomeController.class残留。

[JAR根路由检查](jar-root-route-review.json)实际确认旧初始化控制器已移除、新DashboardController已打包，没有重复GET /。用户端源码不改；160个既有受保护文件与基线一致，见[源码保护](protected-source-preservation.json)。本步22个变更路径（13个新Java、明确删除旧根类、8个资源）见[source-publication.json](source-publication.json)。[Root静态读审](source-review.json)、[作者静态审查](backend-review.json)、[UI静态检查](ui-static-review.json)均不能代替实测。

{run['runtime_file_count']}个运行输入，SHA-256清单 `{run['runtime_manifest_sha256']}`；起测工作区干净、结束逐项无漂移。[运行输入]({name}/runtime-inputs.sha256)、[版本]({name}/versions.txt)、[数据库身份]({name}/database-identity.json)。本轮MySQL端口{run['mysql_port']}，用户端8080/管理端8081；datadir、UUID和监听PID均核对，未访问已有开发数据库。

## 结果与复核入口

[完整原结果]({name}/result.json)、[分层统计](delivery-metadata.json)、[HTTP索引]({name}/http.jsonl)、[逐请求七表]({name}/database-writes.jsonl.gz)、[独立重读](independent-observation-review.json)。主HTTP、浏览器和原生Service断言分层计数，不相加冒充不同业务用例。所有POST均有真实七表前后摘要；浏览器重定向GET如果只有after观察，会明确before=None，不伪称具有前后或零写证明。

本轮2688项主断言、0失败；272条HTTP、59次POST全部完整审计。数据库记录总310条=302份真实before/after（含264自动审计及具名/原生观察）+8份明确after-only，不把310都说成成对。28次状态POST=5次禁用+5次启用+2次无写重放+16次拒绝零写；原生另225项/31条SQL/18个有SQL阶段，浏览器另243项/38响应/6POST/24图。264个捕获可读原正文在脱敏前扫描，8个302/303正文不可读如实标注；归档敏感扫描143文本/85份解压正文/55个已知私密值，0发现。Root独立重读65份A08、20份A09、14份A02、12条完整反馈链，启停3类结果及原生目标3仅戳推进2微秒均通过。

七表均按主键有序、全字段作SHA摘要；账号安全行仅保留教学显示字段和credential/contact不可逆摘要。启停真实改变只允许目标store_user.status/updated_at变更，其他用户、角色、密码、联系方式及六张业务表保留。同状态成功和拒绝分支按七表完整摘要核对无变化。界面中的收货、邮箱和电话在归档正文/截图遮盖；密码、Cookie/CSRF/确认原值不入证据。

## A08/A09 与启停

顾客查询固定role=CUSTOMER，q strip后≤50码点，按用户名的字面包含匹配。绑定LIKE参数，先!→!!、%→!%、_→!_，SQL ESCAPE '!'；反斜杠为普通字符。status=ALL/ENABLED/DISABLED、按ID升序、默认10条/1–50，list/count同条件，过滤重置第一页、分页保留条件，超页空态给有效页。格式或重复字段400；未知/ADMIN详情404。受控特殊用户名和无订单顾客是明确root INSERT夹具，没有新增账号业务路由，原种子4人和夹具后的总数分别记录。

A09只读安全教学资料，空联系方式显示未填写；不读/输出密码散列。订单链接带userId，A06继续按同一CUSTOMER与单号/状态AND组合；A07可返回该顾客资料。表单只含targetStatus与CSRF。额外role/password/资料参数不绑定、不写入，不能修改ADMIN、角色、密码或历史数据。

CustomerService.changeStatus显式READ_COMMITTED，第一数据库操作AdminWriteGuard.lock(actor)复核ENABLED/ADMIN/原UTC微秒authStamp，随后锁目标用户行、复核CUSTOMER，再校验唯一目标状态。未知或ADMIN目标404优先于非法状态组合；非法ID/缺失/重复/非法状态400。真实改变用角色/旧状态/旧原值戳条件更新并检查影响1行，显式updated_at=GREATEST(CURRENT_TIMESTAMP(6),updated_at+INTERVAL 1 MICROSECOND)。相同状态直接无DML成功，保留整行与原时间；成功303到数据库重读的A09，完整固定提示在全局status区。

## 双端会话与历史保留

隔离库把alice.updated_at设未来一小时是明确root夹具，再正常登录取得多份会话。真实HTTP禁用、启用在该下界条件下各恰好推进1微秒；同状态不变。这不是两HTTP发生于同一墙钟微秒，也没有修改系统时钟。

旧会话分别覆盖车、确认、本人订单和写请求；禁用后下一保护请求清身份并302，先于CSRF/参数校验。禁用再启用期间未访问的旧会话也因戳不一致而失效。公开目录仍可游客浏览；重新正常登录后原车/订单/成交快照可读，旧确认令牌配当前CSRF仍409，未生成订单或扣库。启停本身不取消订单、不返库、不清车；禁用顾客的既有PAID订单仍按管理员正常发货动作处理，该动作与启停分别留七表对照。

HTTP顾客无法建立管理员身份，用户端Cookie不认证管理端，按302处理；原生有效CUSTOMER actor的403另由真实写守卫证明，不混为HTTP已认证错角色。

## 真实控制台与三种配置

DashboardMapper一次SELECT包含五个独立COUNT子查询：ON_SALE、DRAFT、PAID、CUSTOMER ENABLED和CUSTOMER DISABLED。售罄仍计上架，管理员不计顾客，无财务数据。五卡分别链接规定状态列表；每次上下架、模拟支付、禁用后发货、启停后刷新，与独立SQL及卡片目标列表计数对照。

空业务场景使用独立csucampuscraft_empty schema，只保留一个可登录ADMIN，CUSTOMER及其他六表为空，五卡0；不称七表字面全空时HTTP仍可登录。自然错误场景使用同一JAR和另一受限应用数据库账号，可读store_user完成登录但无业务表SELECT权，控制台500、GET重试链接可用，无数字兜底。各HTTP/SQL记录标明schema和应用账号配置；不能拿主库快照替代空库或错误配置观察，也没有生产故障注入开关。

## 原生事务、工具预检和截图

原生工具调用受测JAR的真实CustomerService/DashboardService，记录RC、同物理连接、ADMIN行锁→目标锁、角色/旧状态/原戳条件UPDATE影响1、幂等/拒绝无DML；每次DashboardService只有一条含五COUNT的Mapper SELECT。直接JDBC诊断读数另列，不冒充生产SQL。null actor在SQL前拒绝，不虚构无SQL分支的连接观测。

正式起测前发现的外部Native参数名断言已修：实际StoreUserMapper用id、CustomerMapper用userId；preflight1原件保留，preflight2实际Mapper注解/ParamMap回归13项通过。生产源码不改，未创建失败产品轮次。[预审](tool-preflight-review.json)、[最后工具调整读审](tool-final-freeze-review.json)、[Native预检](native-tools/preflight2/metadata.json)。正确BCrypt原响应扫描及合成回归沿用；只对实际捕获且可读正文作脱敏前检查，不补造不可读重定向正文。

{len(br['screenshots'])}张新原PNG，两个视口1366×768/1920×1080，覆盖A02/A08/A09及空业务/权限错误配置；全部实际逐图查看并绑定原字节SHA：[视觉复核](ui-visual-review.json)。fullPage高度可大于视口，收货和教学联系方式遮罩不单独证明字段原文。截图不能替代SQL/HTTP/微秒时序证据，AI复核不替代实名组员签字。

{shots}

## 收口与范围

仅归档副本commands/database-writes无损gzip，见[压缩索引](compressed-text-index.json)。若存在早轮，原结果身份保留、旧图可无损ZIP并逐条映射：[artifact-references.json](artifact-references.json)；原stage字节不改。[原轮清单](original-attempt-inventory.json)如实记录归档时字节，不倒填为历史封存时刻。final-audit.json复核HTTP/PNG/源代码/文档和私密结构，evidence-files.json列除自身外原始字节摘要，新目录Git设-text。既有4608份证据、原分支和远端引用保护见baseline-preservation.json。

本轮进程已停，限定本轮私有runtime/attemptN的绝对路径和停止状态核验后清理，结果见cleanup.json。不归档数据目录、JAR/class/cache或私密原值。M2代码与逐步自动验收闭环仍须组员实名复核；TST-37/38/39、TST-07/30仅按本步实际覆盖登记。并发启停/交易竞争及中途故障回滚留STEP13，P1确认收货未实现，无ADMIN账号管理、账号创建删除、改密改角色或财务功能。Word指导书本轮不改，建议M2复核后统一更新实施指引，再在M3实测后补最终验收记录。
'''
(HERE/'evidence-README.md').write_text(text,encoding='utf-8')
print(json.dumps(dict(readme='evidence-README.md',attempt=name,screenshots=len(br['screenshots']),date=date['evidence_date'])))
