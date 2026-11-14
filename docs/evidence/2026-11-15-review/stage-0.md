# 阶段 0 环境与基线小结

完成时间：2026-11-15（Asia/Shanghai）；执行者：Codex AI。

- 新跑根 Wrapper/JDK21 `clean verify` 两端退出0；新 JAR 哈希已固定，未把构建成功当成业务通过。
- 独立 MySQL8.4.9 新datadir/UUID/59315；原SQL导入退出0，七表4/15/60/100/10/10/20。结构库七表0；两库各35个ENFORCED CHECK，规范化谓词相同。
- 用户8080 PID36828、管理8081 PID36332均启动；隔离数据库监听PID29576（监督父36524）。两端实际JDBC连接按端口/PID映射均UTC；页面Asia/Shanghai待主流程动态对照。
- 同JAR短TTL辅助18080 PID2276（PT2S）另记，默认8080仍PT10M。
- 原始沙箱初始化失败、脚本编码解析失败和辅助工具命名失败均保留并说明；未动开发库、未改产品、未停止旧进程。
- 环境准备已完成，后续身份/目录/交易/后台逐阶段由主流程运行。INIT-01/02/03/05仅本轮已列子项可作为证据；重启持久化、共享资源字节、故障注入与完整INIT不能由本小结扩大判为PASS。

证据入口：[environment.md](environment.md)、[commands-environment.md](commands-environment.md)、[environment/inspection-result.json](environment/inspection-result.json)、[environment/ownership-summary.json](environment/ownership-summary.json)。
