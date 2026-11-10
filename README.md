# CSUCampusCraft 校园文创商城

CSUCampusCraft 是《软件开发架构平台》实验一的双端商城项目，以中南大学地标和院系为商品设计题材。当前版本提供两个独立的 Spring Boot 工程，通过 MyBatis-Plus 读取同一个 PostgreSQL 数据库，并用 Thymeleaf 渲染校园主题。

| 工程目录 | Maven 项目 | 本机首页 | 会话 Cookie |
| --- | --- | --- | --- |
| `csucampuscraft-user` | `csucampuscraft-user` | http://127.0.0.1:8080/ | `CSUCAMPUSCRAFT_USER_SESSION` |
| `csucampuscraft-admin` | `csucampuscraft-admin` | http://127.0.0.1:8081/ | `CSUCAMPUSCRAFT_ADMIN_SESSION` |

购物车、交易和后台维护的开发范围见[项目需求与双端设计](docs/项目需求与双端设计.md)。

## 准备环境

使用 JDK 17 或 21、Maven 3.6.3 或更高版本，以及 PostgreSQL 16 或更高版本和 `psql`。代码按 Java 17 编译。两个工程都使用 Spring Boot 3.5.15、Spring MVC、Thymeleaf 和 MyBatis-Plus 3.5.7。可在 IntelliJ IDEA 中分别导入两个 `pom.xml`，或在命令行独立构建。确认 `mvn -v` 使用预期的 JDK。

## 初始化共享数据库

启动本机 PostgreSQL，用数据库管理角色连接 `postgres` 库。示例采用默认管理角色 `postgres`。已有应用角色时可复用，建库时把 `OWNER` 改为实际角色。

```powershell
psql -X -h 127.0.0.1 -p 5432 -U postgres -d postgres -W
```

在 `psql` 中为开发环境创建应用角色和空库。`\password` 会提示输入本机数据库口令。

```sql
CREATE ROLE csucampuscraft LOGIN;
\password csucampuscraft
CREATE DATABASE csucampuscraft OWNER csucampuscraft ENCODING 'UTF8' TEMPLATE template0;
```

退出管理客户端，从仓库根目录用应用角色导入一份脚本。双端联调使用演示数据版。

```powershell
$env:PGCLIENTENCODING = 'UTF8'
psql -X -h 127.0.0.1 -p 5432 -U csucampuscraft -d csucampuscraft -W -v ON_ERROR_STOP=1 -f database/02-schema-with-demo.sql
```

仅创建表结构时，将末尾的文件替换为 `database/01-schema.sql`。两份脚本各自在空库中独立执行，统一使用 `public` schema。已初始化的库直接连接使用。应用正常启动时关闭自动 SQL 初始化。

两端读取同一组环境变量。分别启动时，在两个终端或两个 IDEA 运行配置里使用同一套连接信息。

| 变量 | 默认值或说明 |
| --- | --- |
| `CSUCAMPUSCRAFT_DB_URL` | `jdbc:postgresql://127.0.0.1:5432/csucampuscraft` |
| `CSUCAMPUSCRAFT_DB_USER` | `csucampuscraft` |
| `CSUCAMPUSCRAFT_DB_PASSWORD` | 应用角色在 PostgreSQL 中的本机口令，默认空值 |

带数据脚本包含教学账号 `alice`、`bob`、`disabled`、`admin`，教学密码为 `CSUCampusCraft123!`。这些是供后续登录模块使用的商城账号。JDBC 连接使用 PostgreSQL 应用角色的口令。

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

两端构建都从 `assets/` 打包共享素材。可以分别打开两端的 `/images/catalog-placeholder.svg`，检查占位图是否加载。PostgreSQL 迁移和双端初始化结果见[初始化实测记录](docs/验收与联调清单.md#初始化实测记录)。

## 项目文档

- [实验一 CSUCampusCraft 校园文创商店实验指导书](<docs/实验一 CSUCampusCraft 校园文创商店实验指导书.docx>)
- [项目需求与双端设计](docs/项目需求与双端设计.md)
- [系统架构与共享数据契约](docs/系统架构与共享数据契约.md)
- [开发任务与版本路线](docs/开发任务与版本路线.md)
- [组内开发协作指南](docs/组内开发协作指南.md)
- [验收与联调清单](docs/验收与联调清单.md)
