# 个人抽验制品复用依据（AI 准备）

当前分支 `fix/review-closeout`，HEAD `d9ed79c1546128beb8b5924e01f55970b44fa767`。本次独立重算199个运行输入，全部与原确切清单匹配；当前产品工作区相对HEAD无差异，原受测 `0329c98` 到当前HEAD的产品源码/SQL/POM/Wrapper/素材差异为空。

两端现存 JAR 的原始字节摘要与上次真实构建制品精确一致：

| 端 | 字节数 | SHA-256 |
|---|---:|---|
| user | 30093096 | `c8a1bea5305186af82cb5f505f67cbce8600f424103f79cc2f825a0a709eb868` |
| admin | 30095071 | `1dba0cfacee7186afe9933a325945fb4689612b4992de656be2619f083eb4c4d` |

本次使用固定 `JAVA_HOME=C:/Users/Starmetor/.jdks/ms-21.0.12.1` 新跑 `java -version` 与根 `mvnw.cmd -v`，实际退出码均0，确认 Microsoft OpenJDK21.0.12.1、Maven3.9.16。输出保存在 `artifact-versions.log`。

因此允许复用上述确切制品，本次未重复构建。本文件只证明制品身份与工具链，未启动应用或访问数据库，也不代表本人已执行任何购物/支付/发货/安全抽验。逐文件摘要、Git差异命令与退出码详见 `artifact-provenance.json`。
