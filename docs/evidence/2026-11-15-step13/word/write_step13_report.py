"""Create the report and optional demonstration script from observed final STEP13 facts."""
import importlib.util
import json
import pathlib
import sys

STAGE=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('guide_builder',pathlib.Path(__file__).with_name('build_step13_documents.py'))
guide=importlib.util.module_from_spec(spec);spec.loader.exec_module(guide)

def table(rows):
    def cell(text):return str(text).replace('|','\\|').replace('\n',' ')
    return '\n'.join('| '+' | '.join(cell(c) for c in row)+' |' for row in rows)

def main():
    summary=json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8-sig'));guide.gate(summary)
    for case in summary['concurrency']+summary['faults']:
        assert case.get('observed') and case.get('evidence'), 'Require actual observations and archived evidence link'
    evidence=summary['evidence_path'].removeprefix('docs/')
    history=summary.get('attempt_history_text','原始失败轮与最终有效分组分别归档，具体工具诊断、输入与退出信息见本轮证据索引。主5的串行、空库、重启和20张新图完成，但后续C1外部工具解码失败使其整体结果仍为FAIL，缺失原始输出不追认；并发与故障在新的隔离库补齐。父汇总按同一最终源码、两端JAR和199项运行输入逐格引用实际有效段，不把任何原叶结果改写为通过。')
    concurrency=table([['场景','本轮观察','结果与证据'],['---','---','---']]+[[x['name'],x['observed'],f"{x['status']}；[{x.get('id',x['name'])}]({evidence}/{x['evidence']})"] for x in summary['concurrency']])
    faults=table([['故障阶段','本轮独立连接观察','结果与证据'],['---','---','---']]+[[x['name'],x['observed'],f"{x['status']}；[{x.get('id',x['name'])}]({evidence}/{x['evidence']})"] for x in summary['faults']])
    report=f'''# CSUCampusCraft 校园文创商城实验报告

项目负责人：高宇弘。项目实现与资料整理使用 AI 辅助。本轮 STEP13 由高宇弘授权 Codex 执行自动验收，报告由 AI 根据实际记录整理，提交前需本人核对。2026-11-15 已有本人抽验签署只对应原七项确认，本报告不把本轮自动动作写成新增真人执行或组员签署。组员互评及另一位真人独立复现未实施。

## 项目范围与本轮结论

我们把课程宠物商店题材改为中南大学校园文创商城，采用真实校园地标与院系分类，首版突出毕业专区和成品礼盒。商品以独立 SKU 管理；礼盒扣自身库存，不拆分其中单品。项目采用两个独立 Spring Boot 工程，共用 MySQL，分别承载顾客选购交易和管理端商品、履约与顾客管理。

本轮最终受测提交为 `{summary['source_sha']}`。39 项 P0（TST-01–35、TST-37–40）在该版本的分组自动验收中通过；TST-36 确认收货为 P1，未选做。各有效组使用相同源码、两端JAR及199项运行输入，父结果逐格记录来源，不要求或伪称某一原叶完整通过全部39项。初始化、同库、共享图片、结构空库、保留 ADMIN 的空业务及重启技术子项也已通过。M0原INIT-03双根页五主题标准保留历史身份；当前管理端根页需登录并显示A02，不以现行A02声称重现该历史页面。八项真实 HTTP 并发、五项隔离库触发器故障注入结果见后文与原始证据。M3 分组自动验收通过；该结论不替代尚未开展的组员互评。

真实支付、物流、退款售后、上传、对象存储、新用户注册、管理员账号管理、REST 接口和 P1 确认收货未实现；性能压测、生产部署和生产安全审计未验证。

## 架构与双端边界

用户端为 `csucampuscraft-user`，提供公开主题目录、商品详情、登录、持久购物车、确认、本人订单及教学模拟支付与取消。管理端为 `csucampuscraft-admin`，提供分类商品、增量补货、相册、全站订单和模拟发货、普通顾客启停及五项真实统计。两端从同一库读取已提交数据，不共享浏览器会话。

```mermaid
flowchart LR
  U[用户端浏览器] --> UC[用户端 Controller]
  A[管理端浏览器] --> AC[管理端 Controller]
  UC --> US[Service 事务与业务校验]
  AC --> AS[Service 事务与业务校验]
  US --> UM[MyBatis Mapper]
  AS --> AM[MyBatis Mapper]
  UM --> DB[(共享 MySQL InnoDB)]
  AM --> DB
```

Controller 负责参数绑定、页面模型及 SSR 结果；成功写操作以 303 指向可读页。Service 承担身份复验、状态机、金额和归属校验、事务边界及行锁顺序。Mapper 只执行绑定参数的查询和条件写入，数据库以唯一键、外键、CHECK 和 InnoDB 事务形成最后约束。Thymeleaf 以转义文本展示商品设计说明、用户名和错误反馈。

用户端 Cookie 名为 `CSUCAMPUSCRAFT_USER_SESSION`，管理端为 `CSUCAMPUSCRAFT_ADMIN_SESSION`；只记录标识名称，不记录值。身份过滤早于 CSRF，逐请求检查账号启用、角色及原始微秒认证戳。写事务第一条数据库操作再次锁定操作者并复验，避免入口认证和实际写入之间的状态变化。顾客真实启停单调推进认证戳，使旧会话在重新启用后仍需登录；同状态操作不写时间。

## 环境与复现方式

{summary['environment_text']}。本轮用 JDK21 和仓库 Maven Wrapper 3.9.16 分别执行双端 `clean verify`，代码继续按 Java17 编译。Wrapper 固定 Maven，不提供 JDK；其他成员须将 `JAVA_HOME` 设置为自己的 JDK21。MySQL JDBC 会话采用 UTC，业务页面按 Asia/Shanghai 展示。

SQL01 在新结构空库验证两端启动与空态，不额外造账号，因此管理端不可登录。另建仅有 ADMIN 的空业务库，验证五项真实统计均为0以及列表空态和详情404。SQL02 演示库初始七表数依次为 `4/15/60/100/10/10/20`，对应 `store_user/category/product/product_image/cart_item/sales_order/sales_order_item`。这三种库状态分别记录，不能把 ADMIN-only 状态称为所有表都空。

从新隔离库进行实际交易、发货、顾客启停、相册与统计核对，再重启双端核对数据保留。本轮复现由 AI 自动执行，未把课程模板中的“另一位组员”写成已实施事实。

## 工具失败与分组汇总

{history}

## 一次真实85元订单

本轮订单号为 `{summary['demo_order_no']}`，只引用业务单号，不记录收货字段。操作先清空 alice 全部种子车，再加 `CSU-LMK-NOTE-01` 数量2和 `CSU-GRAD-BOX-01` 数量1；直接在种子车追加会累加已有数量或受到失效条目影响。

1. HTTP 客户端 GET 确认页，服务端重读本人整车，按当前价格计算 `18.00 × 2 + 49.00 = 85.00`，会话中保存随机确认令牌和条目、数量、版本、单价快照。GET 不扣库、不预留库存；客户端金额不参与计算。后续浏览器只读截图是单独阶段，不冒充浏览器完成了本轮下单。
2. POST 下单先通过身份与 CSRF，进入 READ COMMITTED 事务后第一步锁当前 CUSTOMER 并复验；再校验有效确认、收货字段与当前车，按商品 ID 升序锁商品，在锁内重新检查可售状态、价格、库存和版本。
3. 同事务写入一张 `PENDING_PAYMENT` 主单和两条成交明细。名称、SKU、封面、单价、数量与小计固定为快照；每 SKU 按当前版本与库存条件扣减并核对影响行数，删除本次确认且版本相符的车条目。失败整体回滚，成功后确认失效并 303 到本人订单详情。
4. 本轮实际得到两明细小计36.00和49.00，总额85.00；库存由10/12变8/11，两商品版本各加1，确认车清空，目标详情页徽标重新查询为0。支付和发货不重复扣库。
5. 下单后、支付与发货前，本轮修改过当前商品名、价、封面和上下架；订单仍保留原成交快照与85元总额，历史订单两表未随商品资料变化。随后模拟支付仍按原订单金额成功，写 `MOCK`、唯一凭证与首次支付时间；后台按完整单号查单并发货，用户端同一订单为 `SHIPPED`。

购物车徽标从本人全部车条目 `SUM(quantity)` 得到，包含失效行；游客为0，不能用商品行数或前端推算代替。取消只对待支付订单按原成交数量返库并推进商品版本，不回填购物车；重复取消不二次返库。模拟支付重复成功保留首次凭证和时间。

## 并发竞争的实际结果

各场景使用两个独立线程与共同同步起点发真实业务 HTTP，等待响应后用独立数据库连接读取已提交状态。除 C3 同一确认双提交必须共享同一服务端会话外，其他请求使用独立会话。C3 的两个 HTTP 请求确实并发，应用的会话 monitor 串行业务事务入口；不把它说成两个同时持有数据库事务的线程。同步工具或数据库锁探针仅补充解释，不能代替业务请求。以下观察来自本轮记录，不从单次顺序操作推断。

{concurrency}

各并发窗口的七表前后与版本数量对照另见[实际数据库记录]({evidence}/{summary['cd_evidence_subpath']}/db-writes.jsonl.xz)，同步时间及真实HTTP响应见[并发原始记录]({evidence}/{summary['cd_evidence_subpath']}/concurrency/raw.jsonl)。压缩交付副本的逻辑原字节与实际存储摘要由[归档转换映射]({evidence}/archive-transforms.json)说明；不修改原始阶段文件。

## 故障注入与原子回滚

每案在本轮隔离测试 schema 创建受控触发器，以 `SIGNAL` 在真实 Service 事务阶段拒绝操作；请求结束后对照七表有序全字段摘要，随后移除触发器并核无残留。产品源码、默认配置和初始化 SQL 不包含这些故障机制。

{faults}

这些结果证明本轮指定故障点上的整笔事务回滚；不据此声称覆盖所有数据库故障、进程崩溃或生产灾难恢复。

## 测试结果与证据索引

| 项目 | 本轮结果 | 观察边界 |
| --- | --- | --- |
| 39 项 P0 | 全部通过 | 同一最终提交，逐条断言和证据映射见矩阵 |
| 初始化、同库、共享图、空库、重启技术子项 | 通过 | 三种库初值分开；原INIT-03双根页主题标准保持历史身份，当前admin为受保护A02 |
| 85元交易、双端发货、快照、重启 | 通过 | 真实 HTTP 和七表对照；教学模拟支付与发货 |
| 8 项并发 | 通过 | 线程同步；C3共享会话边界见上文；非顺序点击 |
| 5 项事务故障注入 | 通过 | 仅隔离库触发器，无产品故障开关 |
| P1 TST-36 | 未选做 | 无确认收货功能验收结论 |
| 组员互评、另一位真人复现 | 未实施 | 不使用此前本人签署扩张本轮结论 |

完整入口为 [{summary['evidence_path']}]({evidence}/README.md)，包含最终 SHA、工作区、JDK/Maven/MySQL、端口与进程、运行输入摘要、HTTP、七表前后、同步时间、故障注入、失败和复测、页面截图、敏感扫描和清理记录。各层断言数字是检查项数，不能相加称为互不重复的业务用例数。

新截图仅证明捕获时页面状态；敏感收货和联系字段以不透明遮罩覆盖，不能从遮罩图核对原值。浏览器逐 GET 可仅有 after-only 观察，批次真 before/after 由外层编排记录，不补造单条 GET 前快照。证据不保存口令、密码散列、Cookie、CSRF、确认令牌原值或完整收货信息；历史失败记录保留，不改写为新版本成功。

## 统一清理与原始记录保护

{summary['cleanup_text']}见[统一清理]({evidence}/cleanup-all-runtime.json)及[独立只读复核]({evidence}/cleanup-verification.json)。清理预检首次因工具字段读取错误而中止，实际删除数为0，该原失败记录另存；修正预检后才执行已授权目录清理。该工具问题不记为产品缺陷，也没有改写原业务结果。

## 实际分工与 AI 使用

高宇弘负责项目与需求选择、先前本人抽验和本轮授权。Codex 辅助实现、代码审阅、工具与文档初稿，并自动执行本轮构建、真实 HTTP、数据库对照、并发、故障注入及页面和文档视觉检查。自动复核的参与者均为 AI，不能计为真实组员互评。

本轮报告需要由本人阅读并核对；未记录的新人工动作不写为已执行。此前2026-11-15本人签署保留原时间与原七项范围。课程模板 A/B/C 角色仍作为协作建议，本项目实际执行方式按本节说明。P1 未选做，未验证的性能、生产部署、安全审计和真实支付物流不填通过。
'''
    demo=f'''# CSUCampusCraft 课堂演示与答辩脚本

这是按已实现 P0 编排的后续演示脚本，脚本本身不构成一次新的真人演示或签署。项目负责人高宇弘，AI 辅助；P1 确认收货未选做，组员互评未实施。演示前在独立可重建库按 README 准备，避免重导已有开发数据。

## 开场与结构

“我们的项目是中南大学校园文创商城，重点是毕业专区和独立 SKU 礼盒。两个 Spring Boot 工程共用 MySQL，通过不同会话 Cookie 隔离顾客和管理员。页面由 Thymeleaf 服务端渲染，Controller 处理请求，Service 管理业务和事务，Mapper 访问数据库。”

展示用户首页、五个一级主题和毕业专区，再展示礼盒详情。说明礼盒以成品 SKU 销售，不展开组合库存；零库存仍可浏览但不能购买，缺图回退占位。

## 85元交易主线

先清空 alice 全部种子车，加入2本18元方格本和1盒49元礼盒。核对徽标3、确认总额85元；收货字段在本机输入，投影或截图遮罩，不展示令牌和会话值。提交一次后展示一主单两明细、待支付、库存10/12变8/11及徽标0。

“金额来自服务端当前车和商品，隐藏金额无效。真实写事务先锁当前用户复验，再按商品 ID 升序锁商品，核对确认、价格、状态、库存和版本。主单、明细、扣库和清车同事务，任何失败全回滚。”

先点模拟失败说明仍待支付，再点模拟成功。切到管理端按完整单号查单并发货，回用户端看到 SHIPPED。说明支付和发货不再扣库；另一张待支付单用于取消，取消只返一次库存且商品不回车，不能拿已支付主线单取消。

## 管理端联动

展示分类商品、草稿与上架、独立增量补货、相册与用户端详情。演示商品已有版本与旧表单409，修改相册推进父商品版本；封面独立，移除只删相册行，不删图片文件。已有礼盒 SKU 用于上下架，新增商品换未占用测试码。

从订单详情进入对应顾客，再进入该顾客订单列表。禁用前展开确认说明；随后旧会话受保护请求需重新登录，启用不恢复旧会话，车和历史订单保留。展示控制台五张实际计数卡，解释统计失败显示错误和重试，不能编造0。

## 解释一项真实并发与回滚证据

展示本轮 [{summary['evidence_path']}]({evidence}/README.md) 的最终受测 `{summary['source_sha']}`，选最后一件竞争场景说明同步起点、两次真实响应、唯一成功订单、库存0、失败车保留。不要用依次点击演示替代该证据。

再选一项触发器故障，展示真实请求失败、七表摘要相同、触发器移除记录。说明这些机制仅放隔离测试 schema，生产源码没有故障入口。若现场不重跑，只明确“这是已归档的本轮自动实测”，不声称刚才真人现场执行。

## 常见答辩问题

- 为什么每个写事务还要锁用户？入口认证到真正写入之间账号可能被禁用，事务内锁定并复验能把身份和写入串行到同一个受控区间。
- 为什么购物车不锁商品或预留库存？车只表达选购意向；确认不扣库，提交订单时在商品锁内重新校验并扣减，避免购物车长期占用库存。
- 怎样避免重复支付或取消？先锁订单再判当前状态，重复合法动作保留首次时间和凭证，取消已处理则不再返库。
- 为什么需要订单快照？当前商品资料会改动，历史成交必须保留成交时的名称、SKU、封面、价格、数量和小计。
- 这次结果有什么边界？39项P0、八并发和五故障在指定最终SHA自动实测；组员互评未实施、P1未选做，真实支付物流、生产部署和性能不据此认定通过。
'''
    target=STAGE/'documents';target.mkdir(parents=True,exist_ok=True)
    (target/'实验报告.md').write_text(report,encoding='utf-8')
    (target/'答辩演示脚本.md').write_text(demo,encoding='utf-8')
    print(json.dumps({'overall':'PASS','report':str(target/'实验报告.md'),'demo':str(target/'答辩演示脚本.md')},ensure_ascii=False))

if __name__=='__main__':main()
