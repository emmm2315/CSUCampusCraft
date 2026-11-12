# CSUCampusCraft 校园文创商城

CSUCampusCraft 是《软件开发架构平台》实验一的双端商城项目，以中南大学地标和院系为商品设计题材。当前版本提供两个独立的 Spring Boot 工程，通过 MyBatis-Plus 读取同一个 MySQL 数据库，并用 Thymeleaf 渲染校园主题。

| 工程目录 | Maven 项目 | 本机首页 | 会话 Cookie |
| --- | --- | --- | --- |
| `csucampuscraft-user` | `csucampuscraft-user` | http://127.0.0.1:8080/ | `CSUCAMPUSCRAFT_USER_SESSION` |
| `csucampuscraft-admin` | `csucampuscraft-admin` | http://127.0.0.1:8081/ | `CSUCAMPUSCRAFT_ADMIN_SESSION` |

## 当前阶段

M0 工程初始化与 STEP02 公共页面和安全基础已完成，STEP03/STEP04 业务功能待开发。两个应用已分别启动，根页 `GET /` 能读取同一 MySQL 库的一级主题，两个端口也能读取同一份共享图片。登录、购物车、订单和后台业务按后续步骤开发。P0 管理端包括真实控制台、分类维护、商品资料、上下架、增量补货、商品相册、普通顾客查询与启停、关联订单以及查单发货；REST 接口仅作设计预留。新增需求已进入文档，尚未实现。

MySQL 8.4（InnoDB）是项目数据库基线。首版范围与交付标准见[项目立项与范围](docs/项目立项与范围.md)。

## 准备环境

使用 JDK 17 或 21、Maven 3.6.3 或更高版本，以及 MySQL 8.4 和 `mysql` 客户端。代码按 Java 17 编译。两个工程都使用 Spring Boot 3.5.15、Spring MVC、Thymeleaf 和 MyBatis-Plus 3.5.7。两个 POM 显式加入 spring-security-crypto，由 Spring Boot 管理版本，供后续登录用 BCryptPasswordEncoder(10) 校验种子散列。可在 IntelliJ IDEA 中分别导入两个 `pom.xml`，或在命令行独立构建。确认 `mvn -v` 使用预期的 JDK。

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

带数据脚本包含教学账号 `alice`、`bob`、`disabled`、`admin`，教学密码为 `CSUCampusCraft123!`。这些是供后续登录模块使用的商城账号。JDBC 连接使用 MySQL 应用账号的口令。双端 JDBC 会话统一使用 UTC，页面的业务时间按 Asia/Shanghai 展示。

## 构建和启动双端

在仓库根目录分别构建。

```powershell
mvn -f csucampuscraft-user/pom.xml verify
mvn -f csucampuscraft-admin/pom.xml verify
```

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

打开上表两个首页。导入演示数据后，用户端和管理端分别显示自己的应用标识，并展示数据库中的「校园地标、学院风采、社团活动、校园运动、毕业纪念」。导入结构版时，两端展示空目录。详情、账号登录、购物车和订单属于后续版本。

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

M0 已完成本地独立目录复现与 INIT-01 至 INIT-05 核对，详细版本、环境和观察见[M0 结项记录](docs/测试与验收用例.md#m0-结项记录)。本次通过范围为工程初始化，登录、购物车、交易及后台业务仍按计划开发。

推送前用 `git status --short` 核对两端源码、SQL、共享素材、七份文档、指导书与归档证据均纳入提交。`docs/evidence/` 下经过检查的 `.log` 属于验收资料；构建 `target/`、本机口令文件和普通运行日志继续忽略。提交后可记录新的完整 SHA，保留本轮「基线 SHA + 工作区快照」证据的原始身份，不把它改写成该新提交已测试。

STEP02 已完成基础设施交付，组员可按计划并行认领 STEP03 的公开目录和 STEP04 的身份模块。新成员先按 README 在自己的环境复现 STEP01，并阅读下方 STEP02 交接约定；后台及交易写入口须等 STEP04 鉴权通过。

## STEP02 工具链与公共基础交接

STEP02 受测代码提交为 `5d9271d7e32634f947eb9f6077e7a4f3d98806a7`，验证使用 Microsoft JDK 21.0.12.1、Maven 3.9.16，Java 编译目标继续为 17。先在 PowerShell 设置 JDK 并核对 Maven 的 Java 与版本，再执行上面的双端 `verify`。Maven 3.9.16 需已加入本机 PATH。

```powershell
$env:JAVA_HOME = 'C:\Users\Starmetor\.jdks\ms-21.0.12.1'
$env:Path = "$env:JAVA_HOME\bin;$env:Path"
java -version
mvn -v
```

两端 `foundation/` 下提供异常映射、字段校验、303 响应、密码库和会话级 CSRF。公共模板约定为 `layout::page(pageTitle,pageContent)`、`fields::text(id,name,label,value,errors)`、`fields::number(id,name,label,value,min,max,step,errors)`、`fields::csrf`、`alerts::summary(errors)` 和 `images::image(path,altText)`。调用带错误摘要的字段时使 `id` 与 `name` 相同，错误 Map 键使用同一名称，摘要链接才能定位输入。普通文本用 `th:text`，字段值用 `th:value`；密码不回显。

POST 表单复用 `fields::csrf`，可加 `data-submit-state` 启用「处理中」反馈。成功写后使用 `HttpResponses.seeOther(readPath)` 返回 303。`BusinessException` 的消息只放可展示文案，技术异常交给通用 500。`InputChecks.money` 默认检查完整有符号 DECIMAL(12,2) 列范围，返回两位小数且不舍入；价格正值等业务限制由调用方传入 min/max。用户导航 `cartQuantity` 当前固定为 0，STEP07 再接查询。

日常启动使用默认 profile，验证专用入口不会注册。复现本步探针时，在已经设置同库环境变量的两个终端分别运行：

```powershell
java -jar csucampuscraft-user/target/csucampuscraft-user-0.0.1-SNAPSHOT.jar --spring.profiles.active=verification
java -jar csucampuscraft-admin/target/csucampuscraft-admin-0.0.1-SNAPSHOT.jar --spring.profiles.active=verification
```

每个终端只执行对应端命令。`GET /__verification/foundation` 展示公共片段，`GET /__verification/errors/{status}` 检查错误页，`POST /__verification/submit` 只增加非持久化计数并返回 303，不操作业务表。运行与脱敏证据见[STEP02 基础设施实测记录](docs/测试与验收用例.md#step02-基础设施实测记录)。

本轮按任务要求对所有非 GET 请求先校验会话级表单 `_csrf`，HEAD/OPTIONS 也包括在内。现有 HLD/BR-01 对未来未登录业务写请求规定先进入登录页，两者的身份/CSRF 顺序留在 STEP04 接入时协调；STEP02 没有实现这些业务入口。返回地址白名单仅约束跳转，不注册未来 GET 路由。
