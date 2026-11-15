# CSUCampusCraft 交付后 UI 重设计证据

变体：standard，浅纸 / 墨字 / 黄块强调 / 本地 Saira；默认浅色、手动深色与本端 localStorage 记忆。
主视觉：校园品牌、原商品和五项真实计数，没有游戏资产或外部字体请求。
页面：U01–U09、A01–A10、毕业专区、空态及两端 400/403/404/409/500；业务验收冻结。

## 版本、环境与结论

基线 `e2bdeb9df9cc7888383ef7afa28d5fbe94f29696`；最终 UI 受测 `d22433c2abf87b1a996c6a18467fd7a9a5a43372`，工作区干净。UI 代码提交为 `a14df9dc9fc96ad5985edd5abdb1292a66fec0bc` 与最终修正 `d22433c2abf87b1a996c6a18467fd7a9a5a43372`；本目录和收口文档另提交，不能当成重跑后的新代码结论。main 未改，不 push、不合并。

Windows / Microsoft JDK21.0.12.1 / Maven Wrapper3.9.16 / MySQL8.4.9。两端8080/8081，JDBC UTC、页面Asia/Shanghai。before2 MySQL55497、final after4 MySQL57665、theme supplement5 MySQL58382，各自独立 datadir/UUID。PID、监听归属、命令与完整环境见各轮 `versions.txt`、`database-identity.json`、`launches.jsonl`、`commands.jsonl[.gz]` 和最终 [清理记录](cleanup.json)。

双端改前和最终改后均执行 `./mvnw -f csucampuscraft-user/pom.xml clean verify` / admin同命令（Windows实际用 `mvnw.cmd`），均 BUILD SUCCESS、退出0。各轮构建原日志为 `attemptN/build-user.log` / `build-admin.log`。最终两JAR SHA256：user `b87bfd7a5e9eec981d053fbcc5ad471ca4a9f890e697f0cfccb621a90031e676`；admin `47d8326f13e8b7facd537d6f7174bad3d9d1281138b15348f75cd74dfe602712`。209个运行输入起末稳定，[原始清单](attempt4/runtime-inputs.sha256)。

最终 after4：678 项主检查、0失败，197条审计HTTP、144次浏览器导航；no-JS键盘补充另13项、两个真实POST均303，整批七表不变。前后规范化业务结果精确相同，[对照](paired-comparison.json)。PASS只覆盖本次UI及代表性业务回归，不把它写成重做STEP13全部并发/故障试验。

## 业务与 DOM 保留

[selector-preservation.json](selector-preservation.json) 对比46模板、963原契约元素，原data/id/name/action/method/Thymeleaf绑定缺失或改变0，原业务文案缺失0；**业务 DOM 契约未变**。原始 [before](selectors-before.json) / [after](selectors-after.json) 清单均保留。仅新增html视觉属性 `data-ef-variant` / `data-theme`、主题脚本/字体preload绑定及无障碍包裹层，不是业务参数。

[源码保留](source-preservation.json)逐文件核对：Java、SQL、POM、Wrapper、Word、原历史实测文件及6971份既有证据不变。两端原JS IIFE完整保留，新脚本仅主题/导航标示/摘要焦点。[JAR保留](jar-business-preservation.json)逐项核222/217个class及依赖条目，变更0。完整本轮UI文件清单见[changed-files.txt](changed-files.txt)，主要为46模板、两端CSS/JS/theme、Saira/OFL和轮廓资源、UI规范与两个文档入口；`.gitattributes`仅追加本证据目录 `-text`。

| 回归 | 新库真实观察 |
| --- | --- |
| 85元主线 | 清Alice车→2×18.00+1×49.00→85.00→303建单，1主单2明细、库存10/12→8/11、版本各+1、清车及U08徽标0→MOCK支付→admin发货→双端SHIPPED |
| 逐请求身份 | 禁用后旧保护会话302；启用不复活旧会话；公开目录仍可访问 |
| 权限/边界 | 游客302、他人订单404、CSRF403、A10缺productVersion409；原状态码与跳转保留 |
| 控制台 | 五项原计数与独立SQL一致，售罄仍属于上架统计；原链接不变 |
| 无JS/键盘 | 原生登录Enter→303；同数量改量Enter→303且版本/七表不变；不依赖前端金额或自动重放POST |

七表观察、HTTP状态与Location见各轮 `http.jsonl` 和 `db-writes.jsonl.gz`。U09成对截图选另一张待支付种子单 `DEMO-202611-AL-01`（74.60），以固定同状态；85元主线支付是另一张本轮新建订单，见 `attempt4/business-order-public.json`、HTTP和U08/A07，不能将74.60图片说成85元付款过程。

## 截图与可访问性

before2 / after4各92张核心配对图，36场景×4视口均有DOM观察；桌面1366×768、1920×1080，每页都有截图，关键页另390×844/430×932。after4额外14张 `extra-fullpage-*` 检查目录、车/结算、订单详情、控制台、商品与相册长页；after5额外两张深色1366实拍，不冒充before配对图。原图均保留磁盘字节及SHA。

| 示例 | 改前 | 最终改后 |
| --- | --- | --- |
| U01 首页 | [1366](attempt2/browser/main/U01-home-1366.png) | [1366](attempt4/browser/main/U01-home-1366.png) |
| U02 目录 | [1366](attempt2/browser/main/U02-products-1366.png) | [1366整页补充](attempt4/browser/main/extra-fullpage-U02-products-1366.png) |
| U05 手机购物车 | [390](attempt2/browser/main/U05-cart-390.png) | [390](attempt4/browser/main/U05-cart-390.png) |
| A02 控制台 | [1366](attempt2/browser/main/A02-dashboard-1366.png) | [1366](attempt4/browser/main/A02-dashboard-1366.png) |
| A10 相册 | [1920](attempt2/browser/main/A10-images-1920.png) | [1920](attempt4/browser/main/A10-images-1920.png) |

深色实拍：[U01](attempt5/theme-visual-supplement/U01-dark-1366.png)、[A02](attempt5/theme-visual-supplement/A02-dark-1366.png)。它们来自第五个新演示库，不复用after4交易夹具，首页徽标8是该库的种子车，不能与after4重加车后的3件或成交后0件混为同一时点。

final4所有导航：document横向溢出0、可见无标签字段0、失效aria引用0、无caption表格0、caption窄竖列0。真实点击主题按钮、aria-pressed、localStorage和重载持久化通过；暗色paper rgb(25,25,25)、正文rgb(237,237,237)，正文对比15.0177。reduced-motion长动效0，Tab可见2px实线焦点。观察和媒体记录见 `attempt4/browser/*/result.json`、`browser-summary.json` 与checks；这是轻量自动检查，不等同完整辅助技术认证。

实际AI目检范围见 [root记录](root-visual-review.json)、[后台记录](admin-visual-review.json)、[共享样式记录](implementation-audit/after4-scoped-visual-review.json)，均有原图SHA，不把未查看图片写成已目检。已修移动caption、真实行序、五统计首屏与四列筛选。手机后台宽表保留局部横向滚动；个别价格末位在窄列可折行，数值完整，可作后续视觉细化。A05–A09并非全部有手机PNG，均有390/430 DOM和溢出观察；部分A05/A07屏外区域没有人工逐元素视觉确认。未做真机或完整屏幕阅读器认证。

## 失败、复测、隐私与归档

attempt1为工具UTF8/GBK解码失败；attempt2新私库完整before通过。attempt3默认浅色页面不会因OS dark自动切换，旧工具假设导致整体FAIL，原92图和FAIL保留；同时真实目检发现移动caption问题。修CSS并修工具后，最终d224在新私库attempt4完整通过，attempt5仅补两端真实暗色图和七表零写证明。原失败不追认、不改写，不记作产品业务失败。

原敏感扫描按轮保留；新目录最终扫描和截图遮罩另记录。口令、Cookie/CSRF/确认原值、完整收货信息未归档；收货/登录输入等截图区域已遮罩。所有执行和视觉核对均为AI，不编造新增真人验收或签署。

为控制体积，大JSONL在**归档副本**中做gzip(mtime=0)，原生成物未改。每轮 `packing.json`给出原文件SHA/长度与压缩后实际磁盘SHA/长度，解压逐字节相同；原manifest原样保存在 `source-artifacts.sha256`，相应[验证](attempt4/source-byte-verification.json)。新的 `artifacts.sha256`始终散列磁盘实际保存字节，不把解压逻辑字节冒充磁盘字节。所有PNG原图未转换。

5轮自有库已在核UUID、完整命令/PID创建时间、路径边界及非reparse后清理，相关监听0；[cleanup](cleanup.json)与[清理后原manifest复核](post-cleanup-integrity.json)。不会删除原证据、系统MySQL或其他项目目录。

## 来源与维护

全局技能 `C:/Users/Starmetor/.agents/skills/endfield-ui`，来源commit `96702a36317b4c76538d1a20ed6beaae4e6067e2`；技能不进入仓库，运行包不读取它。Saira/OFL按原字节打包。上游OFL第22行自带尾随空格，空白检查仅排除两份原许可；项目自身UI差异检查通过。没有新依赖/前端构建链、CDN或游戏素材。

规范见 [UI设计规范](../../UI设计规范.md)。完整最终状态见 [result.json](result.json)；此目录交付提交与测试提交分开，最终Git提交SHA见外层回复与Git历史。
