# CSUCampusCraft 校园文创商城

CSUCampusCraft 是《软件开发架构平台》实验一的双端商城项目，以中南大学地标和院系为商品设计题材。当前版本提供两个独立的 Spring Boot 工程，通过 MyBatis-Plus 读取同一个 MySQL 数据库，并用 Thymeleaf 渲染校园主题。

| 工程目录 | Maven 项目 | 本机首页 | 会话 Cookie |
| --- | --- | --- | --- |
| `csucampuscraft-user` | `csucampuscraft-user` | http://127.0.0.1:8080/ | `CSUCAMPUSCRAFT_USER_SESSION` |
| `csucampuscraft-admin` | `csucampuscraft-admin` | http://127.0.0.1:8081/ | `CSUCAMPUSCRAFT_ADMIN_SESSION` |

## 当前阶段

M0 与 M1（STEP02–06）已通过各自范围自动实测，组员实名和交叉复核待补。STEP07 用户端持久购物车、U03 加购和全站导航徽标的本步结果为 通过（attempt1；仅本步购物车范围，组员复核待补）；当前阶段以本页及对应实测记录为准。用户端支持本人车持久化、同 SKU 合并、版本改量与移除；管理端保持 STEP06 交付。结算确认、下单与订单页面尚未开发，控制台在 STEP12，REST 仅预留。

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

打开上表两个首页。用户端可公开浏览；管理端未登录先进入登录页，用本端管理员教学账号登录后显示应用标识及「校园地标、学院风采、社团活动、校园运动、毕业纪念」。仅结构库没有种子账号：用户端公开页展示空态，管理端可打开登录页但没有可用教学账号；日常身份联调应使用演示库。用户端公开详情已实现，可从首页主题或毕业专区进入列表和详情；登录/退出见下方 STEP04 交接，购物车和订单属于后续版本。

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

M0 已完成本地独立目录复现与 INIT-01 至 INIT-05 核对，详细版本、环境和观察见[M0 结项记录](docs/测试与验收用例.md#m0-结项记录)。M0 结项证明工程初始化；当前目录和身份交付范围见本页「当前阶段」，购物车、交易及后台业务按后续步骤验证。

推送前用 `git status --short` 核对两端源码、SQL、共享素材、七份文档、指导书与归档证据均纳入提交。`docs/evidence/` 下经过检查的 `.log` 属于验收资料；构建 `target/`、本机口令文件和普通运行日志继续忽略。提交后可记录新的完整 SHA，保留本轮「基线 SHA + 工作区快照」证据的原始身份，不把它改写成该新提交已测试。

STEP02–STEP05 已通过各自范围自动实测；STEP06 构建通过，正式验收结论见上方「当前阶段」及[STEP06 实测记录](docs/测试与验收用例.md#step06-实测记录)。M1 组员复核仍待补；STEP07 购物车实际覆盖见当前阶段，下一步为 STEP08 整车确认。新成员仍须在自己的环境复现 STEP01，并阅读下方公共基础与身份交接；后台和交易写不能只依赖入口过滤器授权。

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

## STEP07 持久购物车与导航徽标交接

用户端 `GET /cart`（U05）只读当前会话 CUSTOMER 的数据库购物车；`POST /cart/items` 加购，`POST /cart/items/{itemId}/quantity` 改量，`POST /cart/items/{itemId}/remove` 移除，均带 CSRF，成功固定 303 回 `/cart`。U03 已有真实加购表单，售罄仍可浏览但禁用购买控件。游客提交先 302 到登录，允许的商品详情作为读回跳地址；登录后由本人重新点击，绝不自动重放 POST。

所有车写 Service 均 READ COMMITTED，事务首个数据库操作是 `CustomerWriteGuard.lock(actor)`：锁 `store_user` 并复验 ENABLED、CUSTOMER 与 UTC 微秒认证戳，之后才读本人车、条目和商品当前状态。身份失效清本端身份与确认并 302 登录；已认证错角色按细化矩阵 403。三条 cart POST 的入口顺序为 AuthFilter(+10) 身份 → CsrfFilter(+20) → MVC CartRoleConfiguration.preHandle 角色 → 参数绑定；事务内复验不被入口检查替代。其他既有保护路径不扩展业务。

加购数量 1–99、每人最多 20 种（含失效行），同 SKU 合并；新增条目由数据库自增回填 ID，版本从 0 起，数量实际变化才增版。更新/删除绑定本人条目、提交版本并检查受影响行数。有效版本的相同数量直接无 DML 成功，包括版本到上限或商品已失效的原值；它不会解除失效结算阻断。实际改量仍检查商品可用性及库存；旧版本、数量冲突、版本上溢均拒绝。移除不增版，版本上限的条目仍可正常移除；加购、改量、移除均不改库存或商品版本。

徽标统一为 `SELECT COALESCE(SUM(quantity),0) FROM cart_item WHERE user_id=?`，参数只取当前认证的 CUSTOMER，包含下架、售罄、超库存行，不 JOIN 过滤有效性，不以种类 COUNT 替代。PageModelAdvice 向全部用户端布局注入，303 目标页重新读，游客和失效身份为 0；直接错误页亦重查身份。只有实际查询故障的通用错误状态显示“—”表示暂不可用，不伪造已登录空车，也不因为数据库技术异常清除合法身份。失败再认证清身份时同步重置旧模型的徽标为 0。没有前端加减或跨账号缓存。

U05 用当前单价与 BigDecimal 重算，只把有效行计入小计；下架、售罄、超库存行保留并给出原因，仍可移除。含失效行明确标注“有效条目小计”并阻止整车结算。正常车的结算入口本步也暂不开放，不注册或链接 `/checkout`、`/orders`。400/409 只回显本人失败表单的允许字段及原版本；重新载入由用户确认，不悄悄替换失败版本。公开详情的参数/库存冲突尽可能回显 U03，非本人条目 403 不暴露他人车。

受测源码 `3bc5629bcbcbeefa6cbc8f655e8cb4d790c81b77`，起测工作区干净；双端构建 用户端和管理端均 BUILD SUCCESS、退出 0；实际 `mvnw.cmd -o -s <isolated settings> -Dmaven.repo.local=<isolated cache> -f <module>/pom.xml verify` 在无 Maven PATH 的新进程执行，完整参数见证据根 `cart-build-fresh.ps1`，元信息 `build-user.json` / `build-admin.json`，日志见 attempt1；真实 HTTP、数据库、徽标、重启与浏览器结果 通过（attempt1；仅本步购物车范围，组员复核待补）。见[STEP07 实测记录](docs/测试与验收用例.md#step07-实测记录)及[证据入口](docs/evidence/2026-11-14-step07/README.md)。TST-08–11 和 TST-17 只按本步购物车范围判定，TST-11 有效确认仍留 STEP08，真实并发/旧确认及交易留 STEP13。管理端、DDL、POM、共享素材及 Word 本轮不改。
