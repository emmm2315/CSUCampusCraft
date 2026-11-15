# CSUCampusCraft 校园文创商城

CSUCampusCraft 是《软件开发架构平台》实验一的双端商城项目，以中南大学地标和院系为商品设计题材。当前版本提供两个独立的 Spring Boot 工程，通过 MyBatis-Plus 读取同一个 MySQL 数据库，并用 Thymeleaf 渲染校园主题。

| 工程目录 | Maven 项目 | 本机首页 | 会话 Cookie |
| --- | --- | --- | --- |
| `csucampuscraft-user` | `csucampuscraft-user` | http://127.0.0.1:8080/ | `CSUCAMPUSCRAFT_USER_SESSION` |
| `csucampuscraft-admin` | `csucampuscraft-admin` | http://127.0.0.1:8081/ | `CSUCAMPUSCRAFT_ADMIN_SESSION` |

## 当前阶段

M0、M1 的原始实测，以及 STEP07–11 各自受测 SHA 和待复核台账保留。STEP12 顾客列表/详情、启停与 A02 真实控制台已实现，受测 `03384367c87147f1c29859c799f3c464b016b760`，本步验证：通过（全新私有库正式attempt1，本步范围自动验收通过；台账待实名组员复核）。顾客页只读安全字段，真实启停单调推进认证戳，同值不写；控制台一条 SQL 读取五项真实计数，失败显示重试错误。STEP01–12 已交付，复核与 STEP13 进行中（当前为复核文档收口与整体验收准备，STEP13 整体、并发和故障验收尚待执行）；本人抽验签署待完成，各步原实测与待复核台账保留。P1 收货未选做，REST 仅预留。处理进展见[复核收口说明](docs/evidence/2026-11-15-review/closeout/README.md)。

MySQL 8.4（InnoDB）是项目数据库基线。首版范围与交付标准见[项目立项与范围](docs/项目立项与范围.md)。

## 准备环境

准备 JDK 21、MySQL 8.4 和 `mysql` 客户端。仓库根目录的 Maven Wrapper 固定 Maven 3.9.16，无需先安装 Maven 或把它加入 PATH。Wrapper 只解决 Maven，不包含 JDK，仍需将 `JAVA_HOME` 指向自己的 JDK 21；本机示例为 `C:/Users/Starmetor/.jdks/ms-21.0.12.1`，其他组员按自己的安装路径替换。代码继续按 Java 17 编译。两个工程都使用 Spring Boot 3.5.15、Spring MVC、Thymeleaf 和 MyBatis-Plus 3.5.7。两个 POM 显式加入 spring-security-crypto，由 Spring Boot 管理版本，供登录模块用 BCryptPasswordEncoder(10) 校验种子散列。可在 IntelliJ IDEA 中分别导入两个 `pom.xml`，或在命令行独立构建。在仓库根目录用 `.\mvnw.cmd -v`（PowerShell）或 `./mvnw -v`（bash）确认 Maven 3.9.16 与预期 JDK。

## 初始化共享数据库

启动本机 MySQL。在 PowerShell 用具备建库、建表和授权权限的账号连接。示例使用本机 `root`，客户端以提示方式读取密码。

```powershell
mysql --host=127.0.0.1 --port=3306 --user=root --password --default-character-set=utf8mb4
```

在 MySQL 客户端创建空库和仅供双端应用连接的账号。把示例口令替换成本机开发口令。已有合适账号时复用其连接配置。

```sql
CREATE DATABASE csucampuscraft CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_ci;
CREATE USER 'csucampuscraft'@'127.0.0.1' IDENTIFIED BY '替换为本机开发口令';
GRANT SELECT, INSERT, UPDATE, DELETE ON csucampuscraft.* TO 'csucampuscraft'@'127.0.0.1';
```

退出客户端，在仓库根目录用管理账号对已选空库导入一份脚本。双端联调选择演示版。

```powershell
mysql --host=127.0.0.1 --port=3306 --user=root --password --default-character-set=utf8mb4 --batch --database=csucampuscraft --execute="SOURCE database/02-schema-with-demo.sql"
```

仅验证表结构时将路径换为 `database/01-schema.sql`。两个脚本各自在预先创建的空库执行一次。导入出错时检查客户端错误，确认目标库状态，并在新的空库重试。建表语句分别提交，演示数据在一个事务内提交。应用正常启动关闭自动 SQL 初始化。

两端读取同一组环境变量。分别启动时，在两个终端或两个 IDEA 运行配置里使用同一套连接信息。

| 变量 | 默认值或说明 |
| --- | --- |
| `CSUCAMPUSCRAFT_DB_URL` | `jdbc:mysql://127.0.0.1:3306/csucampuscraft` |
| `CSUCAMPUSCRAFT_DB_USER` | `csucampuscraft` |
| `CSUCAMPUSCRAFT_DB_PASSWORD` | MySQL 应用账号的本机口令，默认空值 |

带数据脚本包含教学账号 `alice`、`bob`、`disabled`、`admin`，教学密码为 `CSUCampusCraft123!`。这些是两端登录模块使用的商城账号。JDBC 连接使用 MySQL 应用账号的口令。双端 JDBC 会话统一使用 UTC，页面的业务时间按 Asia/Shanghai 展示。

## 构建和启动双端

在仓库根目录分别构建。PowerShell 使用：

```powershell
.\mvnw.cmd -f csucampuscraft-user/pom.xml verify
.\mvnw.cmd -f csucampuscraft-admin/pom.xml verify
```

bash 使用：

```bash
./mvnw -f csucampuscraft-user/pom.xml verify
./mvnw -f csucampuscraft-admin/pom.xml verify
```

已安装 Maven 3.9.16 也可直接用 `mvn -f <模块>/pom.xml verify`。首次运行 Wrapper 会从 Apache Maven 官方仓库取得固定版本，后续复用 `~/.m2/wrapper/dists` 下的缓存。仓库根没有聚合 POM，两个模块仍各自构建。若下载不可达，保留失败输出；本机已验证的 Maven 绝对路径回退为：

```powershell
& 'C:/Users/Starmetor/.m2/wrapper/dists/apache-maven-3.9.16/0daed3be3ebd1c706f0e69e8b07c6b73f5cc4ea3dfce72a8d0ec2e849ca2ddb0/bin/mvn.cmd' -f csucampuscraft-user/pom.xml verify
```

其他成员应替换成自己的 Maven 3.9.16 路径。Wrapper 的缓存复用与本轮实际结果见 STEP03 验收记录。

分别打开用户端和管理端两个 PowerShell 终端，在两个终端中各执行一次以下连接设置，再执行各端启动命令。需要改端口或库名时修改 URL；账号与口令须对应前面创建的 MySQL 应用账号。口令从交互输入读取，不写进配置文件或命令历史。

```powershell
$env:CSUCAMPUSCRAFT_DB_URL = 'jdbc:mysql://127.0.0.1:3306/csucampuscraft'
$env:CSUCAMPUSCRAFT_DB_USER = 'csucampuscraft'
$env:CSUCAMPUSCRAFT_DB_PASSWORD = [System.Net.NetworkCredential]::new('', (Read-Host '输入本机 MySQL 应用账号口令' -AsSecureString)).Password
```

这些设置只对当前终端及其启动的 Java 进程生效，重新打开终端后需要重新设置。每个应用可以独立运行。

用户端终端运行下面的命令。

```powershell
java -jar csucampuscraft-user/target/csucampuscraft-user-0.0.1-SNAPSHOT.jar
```

管理端终端运行下面的命令。

```powershell
java -jar csucampuscraft-admin/target/csucampuscraft-admin-0.0.1-SNAPSHOT.jar
```

打开上表两个首页。当前用户端为 U01 公开目录首页，提供主题、新品、精选和毕业专区；管理端未登录先进入登录页，用本端管理员教学账号登录后进入 A02 真实控制台。M0 双端主题初始化页的历史行为见原始实测证据。仅结构库没有种子账号：用户端公开页展示空态，管理端可打开登录页但没有可用教学账号；日常身份联调应使用演示库。用户端可从首页主题或毕业专区进入列表和详情；双端登录、购物车、结算、订单、支付取消及后台管理已按 STEP01–12 交付，当前复核与 STEP13 进度见本页「当前阶段」。

两端构建都从 `assets/` 打包共享素材。可以分别打开两端的 `/images/catalog-placeholder.svg`，检查占位图是否加载。MySQL 与双端初始化实测结果见[初始化实测记录](docs/测试与验收用例.md#初始化实测记录)。

## 项目文档

| 文档 | 用途 |
| --- | --- |
| [项目立项与范围](docs/项目立项与范围.md) | 目标、范围和阶段验收口径。 |
| [需求与业务规则](docs/需求与业务规则.md) | REQ、BR 和可测试的通过标准。 |
| [页面清单与原型](docs/页面清单与原型.md) | 双端页面、空态和错误态、低保真线框与界面变量。 |
| [数据库设计](docs/数据库设计.md) | ER 图、七表字典、约束、索引与写入边界。 |
| [系统设计与路由](docs/系统设计与路由.md) | 分层、模块、SSR 路由与未来 REST 映射。 |
| [开发计划与任务](docs/开发计划与任务.md) | 按 STEP01 至 STEP14 推进的工作顺序、前置条件、具体任务、交付与核对。 |
| [测试与验收用例](docs/测试与验收用例.md) | INIT 实测、TST 计划、取证和交付门槛。 |

配套材料为[实验一 CSUCampusCraft 校园文创商店实验指导书](<docs/实验一 CSUCampusCraft 校园文创商店实验指导书.docx>)。指导书与开发计划共用 STEP01 至 STEP14，并引用 INIT/TST 用例。先按《开发计划与任务》找到当前步骤，再按指导书完成操作，用《测试与验收用例》记录结果；已有初始化通过不代表待开发业务通过。

## 本轮文档与初始化核对

需求新增 REQ-14 至 REQ-16、规则新增 BR-16 至 BR-18；管理端页面扩展至 A10。TST-37 至 TST-40 对应控制台、顾客查询、顾客启停与相册维护。一级分类编码上限为 21 字符，生成二级编码后最长 32；加购失败状态、全车数量徽标及全部 35 个命名 CHECK 的判定在对应需求、页面、路由、数据库与测试文档中保持一致。

2026 年 11 月 11 日的新一轮隔离初始化验证将基线 Git SHA、未提交运行源码清单及其 SHA-256 分开保存，见[测试与验收用例](docs/测试与验收用例.md#初始化实测记录)。历史记录未保存精确 SHA 的部分保留原事实，不反推成当前提交的验收结果。

## M0 完成与开工入口

M0 已完成本地独立目录复现与 INIT-01 至 INIT-05 核对，详细版本、环境和观察见[M0 结项记录](docs/测试与验收用例.md#m0-结项记录)。M0 结项仅证明当时工程初始化，历史实测保持原身份；当前 STEP01–12 已交付，目录、身份、购物车、交易及后台范围见本页「当前阶段」，最终整体验收按 STEP13 执行。

推送前用 `git status --short` 核对两端源码、SQL、共享素材、七份文档、指导书与归档证据均纳入提交。`docs/evidence/` 下经过检查的 `.log` 属于验收资料；构建 `target/`、本机口令文件和普通运行日志继续忽略。提交后可记录新的完整 SHA，保留本轮「基线 SHA + 工作区快照」证据的原始身份，不把它改写成该新提交已测试。

STEP01–12 已交付，复核与 STEP13 进行中；各步原实测和待复核台账保持原样，本人抽验与签署待完成。STEP06 缺失/空白商品版本的 409 文档口径已统一，处理说明见[复核记录追加小节](docs/evidence/2026-11-15-review/README.md#处理结果2026-11-15-文档收口)；最终整体验收仍按 STEP13 的最终 SHA 执行。新成员仍须在自己的环境复现 STEP01，并阅读下方公共基础与身份交接；后台和交易写不能只依赖入口过滤器授权。

## STEP02 工具链与公共基础交接

STEP02 受测代码提交为 `5d9271d7e32634f947eb9f6077e7a4f3d98806a7`，验证使用 Microsoft JDK 21.0.12.1、Maven 3.9.16，Java 编译目标继续为 17。先在 PowerShell 设置 JDK，再用 Wrapper 核对 Java 与 Maven 版本并执行上面的双端 `verify`。使用 Wrapper 不要求 Maven 已加入 PATH。

```powershell
$env:JAVA_HOME = 'C:\Users\Starmetor\.jdks\ms-21.0.12.1'
$env:Path = "$env:JAVA_HOME\bin;$env:Path"
java -version
.\mvnw.cmd -v
```

两端 `foundation/` 下提供异常映射、字段校验、303 响应、密码库和会话级 CSRF。公共模板约定为 `layout::page(pageTitle,pageContent)`、`fields::text(id,name,label,value,errors)`、`fields::number(id,name,label,value,min,max,step,errors)`、`fields::csrf`、`alerts::summary(errors)` 和 `images::image(path,altText)`。单个表单可使 `id` 与 `name` 相同，字段错误 Map 使用 `name`；同页多行表单须给 `id` 加唯一前缀，并将摘要另映射到完整 `id`，A10 的具体约定见下方 STEP06 交接。普通文本用 `th:text`，字段值用 `th:value`；密码不回显。

POST 表单复用 `fields::csrf`，可加 `data-submit-state` 启用「处理中」反馈。成功写后使用 `HttpResponses.seeOther(readPath)` 返回 303。`BusinessException` 的消息只放可展示文案，技术异常交给通用 500。`InputChecks.money` 默认检查完整有符号 DECIMAL(12,2) 列范围，返回两位小数且不舍入；价格正值等业务限制由调用方传入 min/max。用户导航 `cartQuantity` 已由 STEP07 接入本人全部车条目数量和，具体查询与错误态见下方交接。

日常启动使用默认 profile，验证专用入口不会注册。复现本步探针时，在已经设置同库环境变量的两个终端分别运行：

```powershell
java -jar csucampuscraft-user/target/csucampuscraft-user-0.0.1-SNAPSHOT.jar --spring.profiles.active=verification
java -jar csucampuscraft-admin/target/csucampuscraft-admin-0.0.1-SNAPSHOT.jar --spring.profiles.active=verification
```

每个终端只执行对应端命令。STEP04 起管理端验证路径也受 ADMIN 身份保护，先在管理端登录，再手动访问对应探针路径。`GET /__verification/foundation` 展示公共片段，`GET /__verification/errors/{status}` 检查错误页，`POST /__verification/submit` 只增加非持久化计数并返回 303，不操作业务表。运行与脱敏证据见[STEP02 基础设施实测记录](docs/测试与验收用例.md#step02-基础设施实测记录)。

STEP02 的 CsrfFilter 继续校验所有非 GET 请求；STEP04 已在它之前接入 AuthFilter，受保护请求先检查身份，再进入 CSRF。公开登录 POST 仍需 CSRF，HEAD/OPTIONS 的非 GET 校验口径保持原有实现。返回地址白名单仅约束跳转，不注册未来 GET 路由。


## STEP03 公开目录交接

用户端入口为 `/`、`/products`、`/products/{productId}`，毕业专区复用列表。演示库为 60 件物理商品、54 件公开上架商品；售罄仍可浏览，草稿返回 404。STEP07 已将详情加购接入真实购物车表单；售罄仍禁用，目录与相册沿用原契约。代码与验收身份、失败复测及桌面截图见[STEP03 实测记录](docs/测试与验收用例.md#step03-实测记录)和[证据目录](docs/evidence/2026-11-13-step03/README.md)。

列表只绑定 categoryId/type/q/sort/page/size。categoryId 只接受一级主题，二级入口已转换为父主题 ID+类型；直接传二级 ID 返回 404。关键词去首尾空白，服务端按 Unicode 码点限 120；LIKE 使用 `ESCAPE '!'` 并显式绑定转义值。排序固定四段白名单；默认 6 条，允许 1–50。过滤改变回第 1 页，分页保留条件，超页仍返回 200 空态。

STEP04 已实现下述身份过滤顺序，参见后面的正式交接。后续数据库业务写须在操作者用户行锁内复验身份；入口过滤器不替代事务授权。姓名与组员交叉复核仍需在 M3 前补齐。


## STEP04 双端身份交接

两端 GET /login 公开，POST /login 校验表单 CSRF、用户名和密码；启用 CUSTOMER 仅能登录用户端，启用 ADMIN 仅能登录管理端。错误凭证/禁用/错端角色使用同一失败提示，密码字段不回显；登录成功更换会话 ID，CSRF 保留，303回合法returnUrl或/。POST /logout先过身份与CSRF，用户端303回/，管理端303回固定/login；两个Cookie独立。

AuthFilter为HIGHEST_PRECEDENCE+10，CsrfFilter仍为+20。公开基础路径为/login、/error、/css/**、/js/**、/images/**；用户GET/和/products及子路径公开，其余预留/cart、/checkout、/orders及子路径与POST/logout受保护，未知普通路径仍404。管理端除白名单外全部受保护。未认证302至/login，已认证但错角色403；不存在的未来受保护GET在认证后404。外部/动作/非法returnUrl回退/，不自动重放POST。

会话只存SessionIdentity(userId,authStamp)，authStamp为数据库updated_at的UTC微秒LocalDateTime原值；每次受保护请求查库以equals比较，不格式化或截断。失效清本端身份与结算确认；公共目录遇旧身份失效按游客继续。模型仅放安全AuthUser；cartQuantity已由STEP07接入本人全部车条目数量和。两端Cookie名保持原值，tracking-modes=cookie，不再把会话ID写入链接。真实通过范围、失败复测及截图见[STEP04实测记录](docs/测试与验收用例.md#step04-实测记录)和[证据目录](docs/evidence/2026-11-14-step04/README.md)。

STEP05 已接入受保护后台分类、商品及补货，详见下方交接。数据库业务写继续要求事务内操作者锁，入口过滤器不替代事务授权；初始化主题页不是控制台，root SQL夹具不是后台启停接口，TST-39留STEP12。


## STEP05 后台分类、商品与补货交接

ADMIN登录后使用/categories及/products，分类按两级维护，商品新增DRAFT、编辑保留SKU/库存、上下架按版本、补货按增量。表单POST带CSRF，成功303回列表；旧版409需手动重新载入。相册入口已由 STEP06 接入 A10，具体边界见下方交接。用户端代码、初始化SQL、POM、Wrapper和共享素材保持原状。

每个写Service声明READ_COMMITTED，第一步调用AdminWriteGuard.lock(SessionIdentity)。该守卫要求已有写事务，先锁store_user操作者，再复核ENABLED、ADMIN及LocalDateTime.equals(authStamp)，之后才触业务目标。会话失效清本端身份/确认并302登录；角色错误403。商品资料和状态UPDATE带id/version条件并检查行数，真实变化增版；同值资料不更新。补货直接SQL stock=stock+quantity，数据库当前值为基准，库存/version上溢拒绝。

产品写后的返回上下文只接受固定/products及五个重新绑定的查询参数；允许q里合法字面反斜杠等字符，不把它作为任意returnUrl，也不放宽登录回跳白名单。管理端新增样式仅服务A03/A04/A05，原公共Token不改。真实覆盖、失败配置诊断及28图见[STEP05实测记录](docs/测试与验收用例.md#step05-实测记录)和[证据目录](docs/evidence/2026-11-14-step05/README.md)。TST-25–28只按本步覆盖判定，真实购买、并发与故障注入留STEP13。

正常开发按前文数据库授权即可支持锁读。隔离验收账号限制其他五表无DML时，额外授schema级LOCK TABLES以允许store_user的FOR UPDATE，实测不会写操作者行；这属于测试角色配置，未改变初始化SQL。权限要求参考[MySQL8.4官方说明](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking-reads.html)。


## STEP06 后台商品相册交接

A04 商品列表和 A05 商品编辑页可进入管理端 `GET /products/{productId}/images`（A10）。页面展示名称、SKU、独立封面、当前 `productVersion` 以及按 `sort_order ASC, id ASC` 排列的相册；提供返回编辑、重新载入和查看用户端详情入口。新增、编辑、移除分别使用 `POST /products/{productId}/images`、`POST /products/{productId}/images/{imageId}`、`POST /products/{productId}/images/{imageId}/remove`。本轮按枚举实现 1 个 GET 与 3 个 POST，不增设第四个写动作；每个写表单都有 CSRF 与父版本，成功 303 回固定 A10，不接受请求传入的跳转地址。

`ProductImageService` 的三个写方法均在 READ COMMITTED 事务内先调用 `AdminWriteGuard.lock(actor)`，再锁父商品、校验父版本，编辑/移除随后按父商品及图片 ID 查询归属。真实新增、内容变化或移除与父商品 `version + 1` 在同一事务中完成；同值编辑不写入、不改版本，即使版本已到上限仍可无变化成功。真实变化在版本上限被拒绝，异常回滚覆盖图片行和父版本。相册不修改独立封面、库存、SKU、状态或历史快照；移除仅删除相册行。用户端源码、初始化 SQL、POM、Wrapper、共享素材都未改动。

`imagePath` 去首尾空白后限 1–255 个 Unicode 码点，以 `images/` 开头，拒绝 `..` 子串、独立 `.` 路径段、协议冒号、反斜杠、`%`、`?`、`#` 和 ISO 控制字符。允许 Unicode、空格、路径复用及合法但暂缺的文件；缺图交由既有片段显示占位。`altText` 去空白后可空且最多 120 个码点，空值在展示时回退商品名；排序是非负整数、空值为 0。此校验采用既有渲染片段可接受路径的安全子集，不检查文件存在，也不写文件系统。

400/409 在 A10 保留失败动作原始输入及原 `productVersion`，其他表单使用当前版本，409 提供明确重新载入链接。不会悄悄以新版本重放旧操作。每行输入 `id` 使用 `image-<id>-<field>`，新增使用 `add-<field>`；`fieldErrors` 仍按字段名绑定，摘要 `errorAnchors` 映射到完整唯一 ID。旧版本且目标图片已消失时只展示原提交摘要，不生成不存在记录的写表单。商品不存在 404；归属检查后的图片不存在或跨商品 404；旧版本和本轮要求的缺失/空白版本为 409，非整数、负数、溢出或重复版本字段为 400。旧 TST-40 对缺失版本写 400 的差异在本轮实测记录单列，原表不改。

「查看用户端详情」默认指向 `http://127.0.0.1:8080/products/{id}`。本机用户端使用其他基址时，可在管理端启动参数设置 `--csucampuscraft.user-base-url=http://127.0.0.1:8080` 并替换为实际可信基址；该值来自服务端配置，末尾斜杠会去除，仅拼服务端商品 ID，既不是表单 `returnUrl`，也不会放宽登录回跳白名单。

受测代码为 `1aa6ad0c4a7546c5bfba7ed65ef05f5913132027`。双端 Wrapper `verify` 已退出 0；正式 HTTP/SQL/截图与敏感扫描结果为 通过（attempt2；本步范围，组员复核待补），见[STEP06 实测记录](docs/测试与验收用例.md#step06-实测记录)及[证据目录](docs/evidence/2026-11-14-step06/README.md)。TST-40 只记录本轮顺序相册维护/版本部分，TST-04 只记录本轮静态资源与回退部分；真实下单竞争、并发及故障注入留 STEP13。Word 实验指导书本轮不改，M1 复核后再按完整 STEP02–06 交付统一更新，不能以自动验收代替实名组员复核。

> 2026-11-15 现行口径补充：以上保留 STEP06 当时的交接与标准差异事实。缺失/空白/旧 `productVersion` 为 409 并提示重新载入，非整数/负数/溢出版本为 400；当前 TST-40 主表已统一，不改写原实测与原证据。

## STEP07 持久购物车与导航徽标交接

用户端 `GET /cart`（U05）只读当前会话 CUSTOMER 的数据库购物车；`POST /cart/items` 加购，`POST /cart/items/{itemId}/quantity` 改量，`POST /cart/items/{itemId}/remove` 移除，均带 CSRF，成功固定 303 回 `/cart`。已登录用户在 U03 使用真实加购表单；游客详情不渲染加购 POST 表单，显示“登录后加购”链接到 `/login?returnUrl=/products/{id}`，登录后返回商品读页，由本人手动加购，不自动重放。售罄仍可浏览但不可购买；直接构造的游客购物车 POST 仍由后端先要求登录并选择允许的 GET 回跳。

所有车写 Service 均 READ COMMITTED，事务首个数据库操作是 `CustomerWriteGuard.lock(actor)`：锁 `store_user` 并复验 ENABLED、CUSTOMER 与 UTC 微秒认证戳，之后才读本人车、条目和商品当前状态。身份失效清本端身份与确认并 302 登录；已认证错角色按细化矩阵 403。三条 cart POST 的入口顺序为 AuthFilter(+10) 身份 → CsrfFilter(+20) → MVC CartRoleConfiguration.preHandle 角色 → 参数绑定；事务内复验不被入口检查替代。其他既有保护路径不扩展业务。

加购数量 1–99、每人最多 20 种（含失效行），同 SKU 合并；新增条目由数据库自增回填 ID，版本从 0 起，数量实际变化才增版。更新/删除绑定本人条目、提交版本并检查受影响行数。有效版本的相同数量直接无 DML 成功，包括版本到上限或商品已失效的原值；它不会解除失效结算阻断。实际改量仍检查商品可用性及库存；商品已下架或不可用时改为 409 `CART_PRODUCT_UNAVAILABLE`，提示“请移除该条目后继续选购”。加购不存在或 DRAFT 仍为 404，条目不存在仍为 404。旧版本、数量冲突、版本上溢均拒绝。移除不增版，版本上限的条目仍可正常移除；加购、改量、移除均不改库存或商品版本。

徽标统一为 `SELECT COALESCE(SUM(quantity),0) FROM cart_item WHERE user_id=?`，参数只取当前认证的 CUSTOMER，包含下架、售罄、超库存行，不 JOIN 过滤有效性，不以种类 COUNT 替代。PageModelAdvice 向全部用户端布局注入，303 目标页重新读，游客和失效身份为 0；直接错误页亦重查身份。只有实际查询故障的通用错误状态显示“—”表示暂不可用，不伪造已登录空车，也不因为数据库技术异常清除合法身份。失败再认证清身份时同步重置旧模型的徽标为 0。没有前端加减或跨账号缓存。

U05 用当前单价与 BigDecimal 重算，只把有效行计入小计；下架、售罄、超库存行保留并给出原因，仍可移除。含失效行明确标注“有效条目小计”并阻止整车结算。正常车的结算入口本步也暂不开放，不注册或链接 `/checkout`、`/orders`。400/409 只回显本人失败表单的允许字段及原版本；重新载入由用户确认，不悄悄替换失败版本。公开详情的参数/库存冲突尽可能回显 U03，非本人条目 403 不暴露他人车。

双方独立实现后以 `git merge --no-ff -s ours origin/feat/step07-cart` 保留组员历史：合并提交 `457d77a0a2a9920262175663d6f5a480c719d38f` 的两个父提交为本地 `dda8f8254eec3f63e9c3bede397131cbe55c6179` 和组员 `221dfb6dfa4fe93d69ffe1eecda97e98705406e1`，随后仅选择性移植上述游客登录链接、实际改量不可用 409 及允许的文案/无障碍改进。保留本地页面模型、data-* 标记、角色/CSRF 顺序与原版本回显；不移植组员商品行 `FOR UPDATE`。购物车不预留库存，仍只先锁用户行，再读取当前商品，避免无必要地阻塞后台写。逐项取舍见[合并差异报告](docs/evidence/2026-11-15-step07-merged/comparison.md)。

本地原受测 `3bc5629bcbcbeefa6cbc8f655e8cb4d790c81b77` 的[旧实测与证据](docs/evidence/2026-11-14-step07/README.md)不改；组员 `221dfb6dfa4fe93d69ffe1eecda97e98705406e1` 的[原始证据副本](docs/evidence/2026-11-14-step07-member/README.md)按 Git blob 原字节保存，96 个文件的来源与哈希见[导入说明](docs/evidence/2026-11-15-step07-merged/member-import-review.json)。组员原记录按其原受测 SHA 理解，不将旧并发、三视口或其他观察自动继承为新结论。

本轮统一受测源码为 `9e61c3e88761519fc63a4d99cafb006a51eacfa5`，源码预检工作区干净；两端已重新执行 Wrapper `verify`，均 BUILD SUCCESS、退出 0，完整新命令与日志已在本轮证据归档。新的运行输入及摘要 起测工作区干净，140 个输入，清单 SHA-256 `c5f13d7ad5e1fc42ef45b19bdcb246788df5add2e5baad2830d8a50cb5ef9fbb`；结束及归档前逐项未漂移；私有库端口与环境 Windows/JDK21.0.12.1/Wrapper3.9.16/MySQL 8.4.9；成功轮私有端口 53954、库 csucampuscraft，双端127.0.0.1:8080/8081；库UUID、私有datadir、监听PID、两JAR SHA及真实UTC/本地时间均在 attempt2 原始记录，SQL连接逐次UTC；执行实际日期为2026-11-14，不改为目录批次日期；新 HTTP/SQL/徽标/浏览器结论 通过（全新私有库 attempt2；本步范围自动验收通过，台账仍待复核），见[STEP07 合并说明与最终验证](docs/测试与验收用例.md#合并说明与最终验证)和[新证据入口](docs/evidence/2026-11-15-step07-merged/README.md)。不得复用两边旧结果冒充本轮重跑。

台账继续待复核，负责人及复核人实名待填；组员参与的 Git 作者为 `emmm2315`，实名另补，Codex 参与集成和初稿整理，不能代替组员签字。TST-08–11、TST-17 仍只按购物车本步覆盖，结算确认留 STEP08、下单留 STEP09，未覆盖的真实购物车并发、旧确认和后段故障回滚留 STEP13。本轮新增身份中途禁用交错检查的实际结果亦须新证据证明，不扩张为所有并发通过。管理端、DDL、POM、Wrapper、共享素材和 Word 不改。

新目录名按本轮指定为 `2026-11-15-step07-merged`；准备阶段实际时钟日期是 2026-11-14，执行日期与时间以新 result、HTTP 和命令原始时间戳为准，不将日志改写成目录日期。


## STEP08 整车结算确认交接

> 以下保留 STEP08 当时的交接与受测事实。STEP09 起 `POST /orders` 已替换为真实事务，`ORDER_SUBMISSION_PENDING` 只作为历史说明保留；当前行为见本页 STEP09 交接与对应实测。

U05 仅在购物车非空且全部有效时显示到 `GET /checkout` 的整车结算链接，空车或存在失效条目时继续阻止结算。U06 重读本人整车及现价，展示全部条目、单价、小计、总价和模拟配送表单；空车、下架、售罄、超库存或金额超过 `DECIMAL(12,2)` 范围均 409 并提供购物车入口。当前可购库存只用于校验，不预留、不扣减。

`CheckoutConfirmation` 保存在用户端会话的 `SessionSupport.CHECKOUT_CONFIRMATION_ATTRIBUTE`：32 字节 `SecureRandom` 生成的不透明令牌、UTC `Instant` 创建和到期时间、userId、不可变全车行（itemId/productId/quantity/itemVersion/unitPrice，另含展示所需名称、SKU、封面和小计）及服务端 `BigDecimal` 总价。每个会话只保留最新一份；重开替换，重新登录、清身份、退出或会话结束清理；到期即不可用，并在下一次校验或重新确认时清理/替换。服务端配置 `csucampuscraft.checkout.confirmation-ttl` 默认 `PT10M`，例如启动参数 `--csucampuscraft.checkout.confirmation-ttl=PT10M`；临时短 TTL 只用于隔离验收。

`POST /orders` 本步是显式校验占位：沿用身份/CSRF 过滤后，依次验证本会话本人最新令牌与时效、当前整车的条目/商品/数量/条目版本/单价及可购状态，再校验收货人、电话、地址。三项使用 `InputChecks` 去首尾空白并按 Unicode 码点限定 1–50 / 1–30 / 1–255。字段错误 400，同一响应以 Thymeleaf 转义回填本人可修正内容并保留仍有效确认；收货内容只存在于本次请求，不存会话快照、不进日志或证据。浏览器总价、单价和 userId 等额外字段不参与计算或归属判断。

缺失、错误、重复、过期、被替换或跨会话/账号的确认统一 409；不读取或泄露他人的确认。采取保守清理：无效令牌也会结束提交会话内当前确认，因此提交旧标签 A 后，新标签 B 也需重新确认。整车或价格变化、当前库存不足同样作废确认并保留购物车；仅商品版本变化或库存变化后仍足量，不会单独造成确认失效。全部校验通过仍返回 **409 `ORDER_SUBMISSION_PENDING`**，说明“下单将在 STEP09 接入”，不伪造成功、不建立订单、不扣库存、不清车；因为没有成功提交，此占位保留仍有效的确认。CSRF 失败由既有过滤器 403 拒绝，不消耗确认。

本步只使用普通只读 SQL，不调用 `CustomerWriteGuard`，不持用户或商品业务行锁；Java 会话监视器只协调本端令牌替换/校验。它不能代替真实下单授权和事务。STEP09 必须替换占位，在 READ COMMITTED 事务内先锁当前用户并复核认证戳，再重验确认/整车，按商品 ID 升序锁商品后校验与扣减，主单、明细、库存/version 和已确认车条目清理一并提交，成功后消费令牌并 303 至本人订单详情。

受测 `54d6b007eb1317c14be090016ea75aec02ead6c5`；两端均用固定 JDK 21 和根 Maven Wrapper 3.9.16 执行 verify，真实输出 BUILD SUCCESS，user/admin 退出码均为 0。attempt1 主验收 2249 项断言、0 失败，247 条真实 HTTP；209 组逐请求七表自动对照，连同具名重复观察共 234 组。82 次 GET /checkout（含浏览器两次游客重定向）与 86 次 POST /orders 均有七表零写入证据。独立响应/SQL/截图摘要重放为 PASS，86 个金额页面与 SQL 当前整车逐项一致。另有原生补充 130 项、浏览器 302 项观察、36 条真实浏览器 GET/POST、24 张截图；这些补充按各自层次归档，不以相加计数代替业务覆盖。敏感扫描 167 个文本、132 个解压缩正文、108 个已知私密值，发现 0 项 详见 [STEP08 实测记录](docs/测试与验收用例.md#step08-实测记录)及[证据目录](docs/evidence/2026-11-14-step08/README.md)。TST-11–13 只确认本步浏览/确认/校验部分；真实订单金额落库、库存扣减、清车和订单页面待 STEP09，并发/故障回滚待 STEP13。STEP07 台账保持待复核，Word 本轮不改。


## STEP09 原子下单与本人订单交接

本节保留STEP09当时的下单/只读订单交付与实测事实。STEP10已接入下方模拟支付/取消说明，不能把本节“动作留后续”当作当前未实现。

受测源码 `1399c311f34c98907ee80c812cfe71606b9820c7`，分支 `feat/step09-orders`。修复源码1399c311f34c98907ee80c812cfe71606b9820c7下，两端均重新使用固定Microsoft JDK21.0.12.1与Maven Wrapper3.9.16执行verify，真实BUILD SUCCESS、退出0；用户端3.663秒、管理端1.680秒，完整命令和日志归档。 成功attempt2有1865项主断言、0失败，226条HTTP；88次POST均有七表自动前后对照，共184份自动审计、含具名重复观察共258份。49次POST /orders中3次303成交、46次拒绝且七表零变化（302×2、400×20、403×4、409×20）。独立重读确认3张HTTP新单与1张原生新单、31份U07及10份U08数据和SQL一致。原生真实Service另70项、14条SQL；金额受控补充另13项；浏览器326项、28次真实导航/提交、24张PNG。各层断言与记录分别计数，不合并充当业务用例数。成功轮敏感扫描159份文本、120份解压正文、148个已知私密值，0发现。 详见[STEP09 实测](docs/测试与验收用例.md#step09-实测记录)和[新证据](docs/evidence/2026-11-14-step09/README.md)。STEP07/08 台账仍待复核；未用本步自动验证替代实名组员签字。

轮次与修复：首次attempt1受测f8b01088b5f4b9e335d3ee86587e2695ffba0e7a：85元下单及U08已成功，但GET /orders列表500导致整轮FAIL；该失败GET七表无变化，之前独立成功请求的订单不是此读请求的部分写入。根因是MyBatis按原方法名识别record派生getOffset，#{query.offset}缺少offset()访问器。仅新增offset()并让getOffset委托，形成1399c311f34c98907ee80c812cfe71606b9820c7；原FAIL和诊断保留，新私有库attempt2从头完整重跑PASS，新的85元成交由本轮实际请求产生，不复用旧通过项。 `backend-review.json`为首次运行前的作者静态自检，不能当最终通过证明；修复后的源码比对见`final-source-fix-review.json`，运行结果各按所属SHA和attempt读取。

`POST /orders` 沿用会话身份和 CSRF。`OrderSubmissionCoordinator` 在当前 Java 会话监视器内调用独立 Spring 代理 `OrderService.submit`，让令牌替换、校验与提交的本端会话边界保持一致。真实 Service 声明 READ COMMITTED，其第一个数据库操作是 `CustomerWriteGuard.lock(actor)`：先锁当前 store_user 并按原始 UTC 微秒认证戳复验 ENABLED/CUSTOMER，之后才重新读取本人最新确认、当前整车及收货字段。字段错误400保留仍有效确认并回填可修内容，不写订单。

随后按商品 ID 升序锁所有涉及商品，使用锁内当前价、状态、库存和 version 重算每行小计及整车总价；金额均 BigDecimal 两位小数且不超 DECIMAL(12,2)。确认条目、数量、车版本或价格变化以及下架、缺库存、商品版本上溢均409，保留车并清当前确认。商品名称、SKU、封面快照从锁内当前商品取得，不从客户端或以后可变商品 JOIN 取得。商品锁等待后、第一条订单 INSERT 前再次检查确认仍属于本会话本人、仍为最新且未过期。

单号使用 `CSU-` 加16随机字节的32位十六进制，共36字符，符合 `[A-Za-z0-9_-]{1,40}` 和既有 ReturnUrlPolicy。数据库现有不区分大小写的唯一键负责最终唯一性，冲突整单回滚，不自动重放。事务先写一张 PENDING_PAYMENT 主单（支付方式、凭证、支付时间均NULL）与全部商品/收货快照，再逐SKU用 `stock=stock-quantity, version=version+1` 且 `id/stock>=quantity/version` 条件更新，最后只删除本次确认且本人/itemId/productId/quantity/version相符的车行。每次插入、扣库、删除都检查影响行数；任一失败由同一事务回滚。

会话不是数据库事务资源，因此确认在事务代理成功返回（数据库提交完成）后才条件消费；已结束会话的清理不会把已提交订单误报成回滚。409清确认，字段400保留有效确认；技术异常清旧确认并由通用500处理，用户先查看本人订单和购物车，不自动重发。成功303到 `/orders/{orderNo}`，目标页重新查全车 SUM 徽标。被清理的只是确认车行，后续新加购不应被整车 DELETE 清掉。

`GET /orders`（U07）固定按当前会话本人过滤，完整 `orderNo` 去空白后0–40码点、普通绑定等值SQL按数据库列排序规则大小写不敏感，空值不限；状态 ALL 或5个业务状态，默认10条、1–50，页码整数小于1按1，创建时间/ID倒序，list和count共用where。超末页200空态并给有效页入口；巨大页码不计算溢出的OFFSET。`GET /orders/{orderNo}`（U08）未知、格式不符或他人单号统一404，省略其订单资料；详情只读保存的快照，时间从数据库UTC转换到北京时间展示。待支付只显示状态，支付/取消按钮与路由留STEP10。

本步可验证新订单、明细、库存/version、车、徽标和用户端历史快照；管理端尚无订单详情且禁止本步修改admin，故“管理端HTTP详情同样显示快照”的完整联查留STEP11，本轮使用用户端U08和数据库快照对照，不声称已跑通管理端页面。TST-12–19/30/34只登记实际覆盖部分；TST-16/17/35并发与故障注入留STEP13，支付取消留STEP10。


## STEP10 模拟支付与取消交接

本节保留 STEP10 当时的模拟支付、取消和实测事实；其中“后台发货尚未实现”是该步历史边界。当前后台订单与发货入口见下方 STEP11 交接，旧实测记录和证据不改写。

本人待支付单可从U08进入 `GET /orders/{orderNo}/payment`（U09），显示订单号、成交总额和教学模拟标识，两个按钮提交SUCCESS/FAILURE。只有待支付订单提供支付表单，其他本人状态GET支付页409并给回详情入口；未知/格式不符/他人订单GET与写请求统一404，不暴露金额/收货资料。U08待支付操作区提供模拟支付和取消确认，取消前说明“库存返还、商品不会回购物车”；已付款显示原凭证与首次时间，历史种子状态仍只读，不新增发货/收货入口。

新增PaymentService的pay/cancel均显式READ_COMMITTED，首个数据库操作必须是CustomerWriteGuard.lock(actor)，复验ENABLED/CUSTOMER及完整UTC微秒authStamp；随后按订单号+user_id锁本人订单。支付在归属核对后绑定唯一result字段，缺失/非法/重复400；组合输入采用归属优先，因此未知/他人单即使result非法仍404。身份/CSRF沿用现有过滤器，游客302，缺错CSRF403；订单号大小写按现有MySQL列的排序规则精确匹配。

待支付FAILURE无DML，303回详情的globalError明确仍待支付、可重试或取消。首次SUCCESS只把主单改为PAID，写MOCK、SecureRandom16字节生成的`CSUPAY-`+32位hex（39字符）及首次paid_at；现有不区分大小写唯一键兜底，冲突整笔回滚，不自动重试写。PAID/SHIPPED/COMPLETED重放SUCCESS无DML，保留首次凭证、时间和updated_at；这些状态FAILURE409，CANCELLED的任何合法模拟支付409。付款金额只读订单总额，客户端amount/userId等不参与计算或授权，所有支付分支均不锁/写商品库存。

首次取消仅PENDING_PAYMENT：锁订单后按不可变明细的product_id升序锁全部商品，先核对库存INT上限、版本BIGINT上限，再以当前库存+原明细数量返库、version+1，检查每条更新影响1行；最后同事务写CANCELLED及首次cancelled_at。返库SQL带锁内version和库存/版本溢出条件，不覆盖旧页面库存，保留商品其他所有字段，DRAFT返库后仍DRAFT。重复CANCELLED直接303不再读/写商品、不返第二次、不改首次时间；PAID及后续状态取消409。新Service不改cart_item或sales_order_item，不回填购物车，不改成交商品/收货/金额快照，也不主动修改结算确认；身份失效清理仍沿用既有基础设施。

支付/取消时间用数据库UTC微秒时间并以created_at为下界，符合状态配套字段与时间链CHECK；页面沿用Asia/Shanghai展示。合法写动作完成均303回本人详情，flash只保存固定反馈文字，不保存收货信息、令牌或客户端金额。所有新SQL隔离在payment包，STEP09的OrderService/Coordinator/Mapper/Controller/Query与checkout逻辑未改。

受测 `b0253a5ecc920dfa862eec0eb8358f301ac41c10`。环境与构建：两端均用固定JDK21和根Maven Wrapper3.9.16执行verify，实际带已有离线settings/cache参数，真实BUILD SUCCESS、退出0；用户端3.548秒、管理端1.709秒。仅验证工具修复，第二轮复用相同受测JAR，SHA逐轮记录，不假称重构建了生产代码。 Windows11；Microsoft JDK21.0.12.1、Maven Wrapper3.9.16、MySQL8.4.9/InnoDB。成功attempt2私有端口53912，失败attempt1端口60661，两个独立UUID/目录均有身份核对；用户端8080与管理端8081同库csucampuscraft，SQL连接UTC。进程已停止；私有目录是否已删除以cleanup.json实际归档为准。

输入冻结：受测源码起测工作区干净；168个运行输入，清单SHA-256为443291ac2bfd32c5ff0fe4b9f50ff584956753dca870c879304a03c44af07ca9，结束逐项未漂移。STEP09既有order/checkout/auth Java及admin/SQL保持原字节，文档与新证据随后另提交。

本轮结果：成功attempt2有1786项主断言、0失败，224条HTTP、93次POST均有七表自动前后对照；187份自动审计，连同具名重复观察共266份。47次支付/取消POST分为3次首次付款、5次首次取消、8次无写入处理和31次拒绝零写（302×3、400×5、403×6、404×5、409×12）；不把状态码303等同于首次业务写入。10张订单仅用于既有STEP09真实HTTP建单准备；native只对其中两张bob订单执行独立动作，不新建订单。原生133项/25条SQL、浏览器237项/32次导航/8次POST/24张新PNG分别计数；6个实际浏览器303响应的正文不可读取时已明确标记，不补造正文。独立重读HTTP/SQL按同一分类复核通过。成功轮敏感扫描129份文本、93份解压正文、49个已知私密值，0发现。

轮次与工具修复：首次attempt1使用同一生产源码b0253a5ecc920dfa862eec0eb8358f301ac41c10，生产HTTP动作和24图浏览器检查均通过，但外部Native Trace.safeNumbers对缺失可选键调用MyBatis ParamMap.get，抛出BindingException，整轮FAIL保留。原生只完成9项前置检查、SQL事件为空，旧工具没有归档该native调用的七表前后对照，不重建或声称原生零写入。离线实际原工具重现缺键异常，仅用containsKey守卫修复外部工具并通过8项结构检查；生产源码、受测SHA及JAR未改。attempt2使用全新私有库从种子完整重跑HTTP、浏览器和真实Service原生阶段后PASS，不能继承旧通过结论。旧24张原始PNG按无损ZIP保存在attempt1/browser/screenshots.zip，artifact-references.json登记各图原始字节与映射；stage原文件不动，成功轮24张直接查看。

TST-18–24/34只按本轮支付、正常取消、幂等和拒绝分支登记；TST-23恢复首项后故障回滚及TST-24同步竞争留STEP13，不把串行支付/取消或重复请求当成竞争证明。真实支付、退款、物流和后台发货均未实现。详见[STEP10实测记录](docs/测试与验收用例.md#step10-实测记录)、[新证据](docs/evidence/2026-11-14-step10/README.md)。


## STEP11 后台订单与模拟发货交接

本节保留 STEP11 当时的交付和实测事实；其中顾客入口、控制台留 STEP12 是历史边界。当前实现见下方 STEP12 交接，旧记录不改写。

管理端 `GET /orders`（A06）要求启用 ADMIN，可按完整订单号、状态和可选普通顾客 ID 组合查询。订单号去首尾空白后最多 40 码点，用绑定等值 SQL 按原 MySQL 排序规则不区分大小写匹配；空串不限，不作模糊查询。状态为 ALL 或既有五种状态，默认每页 10 条、允许 1–50，按创建时间、ID 倒序，列表和 count 共用条件。页码整数小于 1 按 1，超末页或不可表示的巨大 OFFSET 返回 200 空态并提供有效页入口。筛选变化回第 1 页，翻页保留所有条件。

`userId` 未提交或去空白后为空表示不限；非正整数、非整数或超出 Long 范围返回 400。指定顾客必须存在且角色为 CUSTOMER，禁用顾客仍可筛选历史订单；未知 ID 或 ADMIN ID 返回 404。本步只提供订单关联筛选，不实现顾客资料页。未知、格式无效的订单路径统一 404；列表字段格式错误和重复参数返回 400。

`GET /orders/{orderNo}`（A07）显示全站订单的成交商品、收货和金额快照、支付凭证与状态时间；商品明细不 JOIN 当前商品替代快照。列表和详情中的账号名称仅用安全字段读取，不把带密码散列的账号实体放入页面模型。管理端 DTO、Mapper 独立位于 `org.csucampuscraft.admin.order`，不依赖用户端工程。管理导航增加订单入口，用户端代码不变。

`POST /orders/{orderNo}/ship` 使用既有身份过滤与 CSRF。`AdminOrderService.ship` 声明显式 READ_COMMITTED，首个数据库操作是 `AdminWriteGuard.lock(actor)`，锁当前 ADMIN 并复核启用、角色和原始 UTC 微秒 authStamp；随后只锁目标订单行。锁内 PAID 才改为 SHIPPED，以 `GREATEST(CURRENT_TIMESTAMP(6),paid_at)` 写首次发货时间，并检查条件更新影响 1 行。SHIPPED/COMPLETED 重放直接成功且无 DML，保留首次时间和 updated_at；待支付或取消单 409。成功或重放均 303 回详情并用固定 flash 文案反馈；冲突页给详情和列表恢复入口。

发货路径不读或锁商品、不写库存、明细、购物车、支付凭证和成交快照，不接入真实物流。技术写冲突整笔回滚并显示稳定 409，不自动重试。缺错 CSRF 返回 403；游客、顾客未能建立管理端身份或仅携带用户端 Cookie 时，HTTP 返回 302 登录。原生 Service 的有效 CUSTOMER actor 则由事务内角色复核返回 403；HTTP 与原生补充各按自己的入口登记，不能混为一种角色用例。

受测 `39c96aaaad18c58dce9d57450e14317a75c29b3d`。环境与构建：Windows11；Microsoft JDK21.0.12.1、Maven Wrapper3.9.16、MySQL8.4.9/InnoDB。最终attempt2私有端口65113，原attempt1端口54774，分别使用独立数据目录与UUID；用户端8080和管理端8081共用csucampuscraft，SQL连接UTC。 受测39c96aaaad18c58dce9d57450e14317a75c29b3d下，两端用固定JDK21和根Maven Wrapper3.9.16执行verify，真实BUILD SUCCESS、退出0；用户端4.342秒，管理端4.150秒。两轮复用同一对受测JAR并核对SHA，仅外部工具更正，不虚构生产代码修复或重新构建。

输入冻结：受测源码起测工作区干净；183个运行输入，清单SHA-256为eca6993a4cdffd98594ebaa48e093ec1e520d603eff407cb3747a698629822cb，起测和结束逐项未漂移。用户端、初始化SQL、两端POM与Wrapper保持原字节，文档与新证据随后另提交。

本轮结果：最终attempt2有2136项主断言、0失败，202条已捕获HTTP，53次POST均有七表前后审计；176份自动对照，含具名重复观察共218份。17次发货POST分为3次首次SHIPPED、3次无写入重放、11次拒绝零写（302×3、403×4、404×1、409×3）。原生175项、22条SQL，浏览器255项、26张新PNG，各层分别计数，不当作不同业务用例数。成功轮敏感扫描150份文本、107份解压正文、36个已知私密值，0发现。Root另独立重读HTTP/SQL和截图元数据，复核同一3/3/11发货分类、47份A06、18份A07、原生仅两PAID单变更及两类反馈证明，结论通过。 两轮受控应用和私有MySQL进程均已停止；确认路径位于本轮专属runtime后，两个私有数据目录均已删除，cleanup.json实际结果PASS，未触碰生产数据库。

捕获边界：28条浏览器文档响应是已捕获子集，4次真实POST中2次303正文不可读；另有2次实际跟随的管理端A07 GET未分配捕获ID，网络正文未归档、未做raw扫描，不能用后续用户端U08记录161/175冒充。浏览器首次发货提示由真实DOM完整文字检查及PNG证明；主HTTP客户端4条成功/重放链有实际Location到A07 GET及精确全局提示。修正的原始正文散列检测只覆盖200份已捕获且可读响应，0命中；不含上述2个未捕获GET和2个不可读303，不补造缺失字节。

轮次与边界：首轮attempt1的result原记录PASS，保留该身份与业务观察，不改写为FAIL。独立工具审计发现原始HTTP正文BCrypt正则双重转义、发货反馈仅查整页常驻词的验证局限；CI发货后人工GET又改了303目标订单号大小写。仅修外部工具，9项合成正反例回归通过，按实际Location原样随访并核对全局提示完整文字；生产源码、受测SHA及JAR不变。最终用全新私有库attempt2从种子完整重跑，不继承旧通过结论；浏览器捕获局限另由browser-capture-diagnostic.json登记，不重写两轮原始结果。 TST-29/30 只登记本步后台查询、模拟发货和新单双端快照联查；TST-39、顾客资料和关联入口留 STEP12，并发、竞争和故障注入留 STEP13。顺序重放不能当作竞争证明，AI 自动及视觉检查不能代替组员实名复核。详见 [STEP11 实测记录](docs/测试与验收用例.md#step11-实测记录)、[新证据](docs/evidence/2026-11-14-step11/README.md)。


## STEP12 普通顾客与真实控制台交接

管理端 `GET /customers`（A08）固定查询 CUSTOMER，`q` 去首尾空白后最多 50 码点，按用户名包含匹配；状态缺省 ALL，可选 ENABLED/DISABLED。SQL 显式 `ESCAPE '!'`，关键词中的 !、%、_ 依次转义，绑定参数中的反斜杠本身为字面字符。默认每页 10 条、允许 1–50，按 ID 升序，列表与 count 共用条件。页码小于 1 的整数归 1，非法/重复查询字段 400；超末页或巨大 OFFSET 返回 200 空态并提供有效页入口，筛选变更回第一页，翻页保留条件。

`GET /customers/{userId}`（A09）只展示普通顾客 ID、用户名、显示名、状态、教学邮箱/电话及创建时间；邮箱电话空值显示未填写。详情使用独立 CustomerProfile 安全投影，列表、详情和目标行锁 SQL 都不查询密码散列，页面不接收 StoreUser 实体。未知或 ADMIN 目标 404，非法路径 ID 400。A09 的订单入口带 `userId` 进入 A06，A07 反向进入该 CUSTOMER 详情；无订单顾客仍可读详情，关联订单交集为空时正常空态。

`POST /customers/{userId}/status` 只绑定 `targetStatus` 与既有 CSRF，其他角色、密码或资料参数不参与写入。CustomerService 声明显式 READ_COMMITTED，首 SQL 为 AdminWriteGuard.lock(actor)，锁当前 ADMIN 并复核 ENABLED、角色和原始微秒 authStamp；然后锁目标用户安全投影、复核 CUSTOMER，再校验唯一必填的 ENABLED/DISABLED。未知或非 CUSTOMER 404 优先于目标状态校验；合法目标缺失/重复/非法状态 400。同状态直接 303 无 DML，真实切换仅更新 status 及 `GREATEST(CURRENT_TIMESTAMP(6),updated_at+INTERVAL 1 MICROSECOND)`，带锁内旧状态和原戳条件并检查影响 1 行；时间上溢或写冲突回滚为稳定 409，不自动重试。

成功 303 回 A09，固定提示说明真实更新或已处于目标状态；400/409 页提供修正/刷新恢复入口。禁用后下一次受保护请求清本端旧身份和结算确认，启用不会恢复旧会话，包括禁用期间未访问的会话，须正常重新登录。购物车、订单、成交快照、库存和支付数据保留；管理员仍可按既有订单状态发货。HTTP 无本端管理员身份时 302，缺错 CSRF 403；原生角色拒绝与 HTTP 会话边界分开记录，不把顺序快速切换当作竞争证明。

`GET /`（A02）由 DashboardController 替换旧初始化根路由，仍要求 ADMIN。DashboardMapper 用一条 SELECT 的五个独立 COUNT 子查询读取上架商品、草稿商品、PAID 待发货单、启用 CUSTOMER、禁用 CUSTOMER；售罄上架仍计上架，ADMIN 不计顾客。卡片带对应 status 进入列表；空业务表得到真实 0，SQL 查询失败返回 500 dashboard-error，固定说明与 GET 重试，无统计数字兜底。旧 Category 链路保留给分类业务，M0/早期初始化主题页证据是历史验收，未被改写。

受测 `03384367c87147f1c29859c799f3c464b016b760`。环境与构建：Windows11；Microsoft JDK21.0.12.1、Maven Wrapper3.9.16、MySQL8.4.9/InnoDB，私有端口56528。正式运行于2026-11-15 00:10:11至00:14:53，用户端8080和管理端8081同库csucampuscraft，SQL连接UTC；另用独立csucampuscraft_empty和仅允许store_user读取的受限应用账号分别验证空业务与自然查询失败。 两端固定JDK21和根Maven Wrapper3.9.16执行clean verify，真实BUILD SUCCESS、退出0；用户端4.641秒、管理端4.482秒，构建于2026-11-14 23:53:58完成，未改写成15日。clean清除删除旧HomeController可能遗留的class；实际管理JAR无旧Home且有唯一根路由DashboardController，随后正式运行使用此对受测JAR。

输入冻结：受测源码起测工作区干净；199个运行输入，清单SHA-256为353ae2c704f160fcff7a7ad5ec624ad7e7a7b8a1ed7a41ef5b46dd10ca98a85f，起测及结束逐项未漂移。用户端、初始化SQL、POM与Wrapper保持原字节，文档和新证据随后另提交。

本轮结果：正式attempt1有2688项主断言、0失败，272条已捕获HTTP、59次POST均有完整七表前后审计。数据库记录共310条：302份成对观察（含264份自动对照与具名重复观察）及8份after-only。28次状态POST分为禁用5次、启用5次、同态2次、拒绝零写16次（404×2、400×10、403×2、302×2）。原生225项/31条SQL、浏览器243项/38条响应/6次POST/24张PNG分别计数，不冒充不同业务用例数；敏感扫描143份文本、85份解压正文、55个已知私密值，0发现。 2026-11-15 00:23:05确认受控进程停止、路径位于本轮专属runtime后，已删除唯一attempt1私有运行目录，cleanup.json实际PASS；未触碰生产数据库，脱敏证据保留。

轮次与捕获边界：本轮只有正式attempt1，完整通过且无生产源码修复。首次live之前的外部工具预审修正actor参数id/userId提取、旧确认搭配当前CSRF、禁用顾客后既有PAID单发货顺序和控制台原GET序号绑定；原预检与各自SHA保留，这些不是失败业务轮，不改写为生产缺陷修复。正式冻结工具和受测源码在运行中未擅改。 已捕获272条响应中264份可读原始正文在脱敏前扫描，0散列命中；8个重定向响应正文不可读取，明确不补造。另8个跟随重定向GET使用after-only数据库记录：before=None，不计完整前后审计、不声称该GET已观测零写。所有59次POST均有真实七表before/after；浏览器重定向网络正文、精确全局反馈与数据库观察分别登记。

TST-37–39 只登记本轮实际范围；M2 代码和本步自动验收闭环仍需组员实名复核，不能代替 STEP13 并发、故障与全链路验收。Word 指导书本轮不改，建议 M2 组员复核后、STEP13 整验前集中同步；P1 收货由小组另行确认。详见 [STEP12 实测记录](docs/测试与验收用例.md#step12-实测记录)、[新证据](docs/evidence/2026-11-15-step12/README.md)。
