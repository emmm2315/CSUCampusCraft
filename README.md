# CSUCampusCraft 校园文创商城

CSUCampusCraft 是《软件开发架构平台》实验一的双端商城项目，以中南大学地标和院系为商品设计题材。当前版本提供两个独立的 Spring Boot 工程，通过 MyBatis-Plus 读取同一个 MySQL 数据库，并用 Thymeleaf 渲染校园主题。

| 工程目录 | Maven 项目 | 本机首页 | 会话 Cookie |
| --- | --- | --- | --- |
| `csucampuscraft-user` | `csucampuscraft-user` | http://127.0.0.1:8080/ | `CSUCAMPUSCRAFT_USER_SESSION` |
| `csucampuscraft-admin` | `csucampuscraft-admin` | http://127.0.0.1:8081/ | `CSUCAMPUSCRAFT_ADMIN_SESSION` |

## 当前阶段

项目处于文档定稿和 M0 工程初始化。两个应用已分别启动，根页 `GET /` 能读取同一 MySQL 库的一级主题，两个端口也能读取同一份共享图片。登录、购物车、订单、后台业务和预留 REST 接口按后续里程碑开发。

MySQL 8.4（InnoDB）是项目数据库基线。首版范围与交付标准见[项目立项与范围](docs/项目立项与范围.md)。

## 准备环境

使用 JDK 17 或 21、Maven 3.6.3 或更高版本，以及 MySQL 8.4 和 `mysql` 客户端。代码按 Java 17 编译。两个工程都使用 Spring Boot 3.5.15、Spring MVC、Thymeleaf 和 MyBatis-Plus 3.5.7。可在 IntelliJ IDEA 中分别导入两个 `pom.xml`，或在命令行独立构建。确认 `mvn -v` 使用预期的 JDK。

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

分别在两个终端设好数据库环境变量后启动。也可以把各端命令单独运行，另一端没有启动时仍可访问本端首页。

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
| [开发计划与任务](docs/开发计划与任务.md) | 里程碑、任务依赖、分工、风险与协作。 |
| [测试与验收用例](docs/测试与验收用例.md) | INIT 实测、TST 计划、取证和交付门槛。 |

配套材料为[实验一 CSUCampusCraft 校园文创商店实验指导书](<docs/实验一 CSUCampusCraft 校园文创商店实验指导书.docx>)。指导书的 CSU-V 编号可在《测试与验收用例》中找到对应 TST。
