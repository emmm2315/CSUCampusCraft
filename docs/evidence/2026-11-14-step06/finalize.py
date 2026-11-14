from pathlib import Path
import json,shutil,hashlib,datetime,collections,gzip,re,sys
here=Path(__file__).resolve().parent
attempt=sys.argv[1]
assert re.fullmatch(r'attempt[1-9][0-9]*',attempt)
source=here/'evidence'/attempt
result=json.loads((source/'result.json').read_text(encoding='utf-8'))
assert result['overall']=='PASS' and result['tracked_processes_stopped']
out=here.parent/'final-evidence'
assert not out.exists()
out.mkdir()
for p in (here/'evidence').iterdir():
 if p.is_dir() and re.fullmatch(r'attempt[1-9][0-9]*',p.name):shutil.copytree(p,out/p.name)
# Keep the failed attempt's original result/JSON/log bytes. Identical PNGs may be referenced
# at the successful attempt instead of duplicated; a separate full-SHA map resolves them.
canonical={hashlib.sha256(p.read_bytes()).hexdigest():p for p in (out/attempt/'browser').glob('*.png')}
references=[]
for d in out.iterdir():
 if d.is_dir() and d.name!=attempt:
  for p in (d/'browser').glob('*.png'):
   digest=hashlib.sha256(p.read_bytes()).hexdigest()
   if digest in canonical:
    references.append({'original_path':p.relative_to(out).as_posix(),'canonical_path':canonical[digest].relative_to(out).as_posix(),'sha256':digest,'bytes':p.stat().st_size,'original_stage_file_preserved':True})
    p.unlink()
(out/'artifact-references.json').write_text(json.dumps({'scope':'Byte-identical screenshot sharing only; failed original result/log/JSON and stage originals are unchanged','references':references},ensure_ascii=False,indent=2),encoding='utf-8')
shutil.copy2(here/'preparation-selfcheck.json',out/'preparation-selfcheck.json')
shutil.copy2(source/'runtime-inputs.sha256',out/'runtime-inputs.sha256')
for name in ['prepare.py','cases.pyfrag','selfcheck.py','audit_evidence.py','finalize.py']:
 if (here/name).exists():shutil.copy2(here/name,out/name)
if (here/(attempt+'-run.log')).exists():shutil.copy2(here/(attempt+'-run.log'),out/attempt/'console.log')
http=[json.loads(x) for x in (source/'http.jsonl').read_text(encoding='utf-8').splitlines()]
writes=[json.loads(x) for x in (source/'database-writes.jsonl').read_text(encoding='utf-8').splitlines()]
post=[x for x in http if x['method']=='POST']
auto=[x for x in writes if x.get('automatic_all_posts')]
assert {x['sequence'] for x in post}=={x['http_sequence'] for x in auto}
assert all(x['before']==x['after'] for x in auto if x['status']!=303)
bodychecks=[]
from html.parser import HTMLParser
class Markers(HTMLParser):
 def __init__(self):super().__init__();self.ids=[];self.anchors=[];self.inputs=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if a.get('id'):self.ids.append(a['id'])
  if a.get('href','').startswith('#') and len(a['href'])>1:self.anchors.append(a['href'][1:])
  if tag=='input':self.inputs.append(a)
for r in http:
 if r['status'] not in [400,409]:continue
 text=gzip.decompress((source/r['body_file']).read_bytes()).decode('utf-8')
 dom=Markers();dom.feed(text)
 bodychecks.append({'http_sequence':r['sequence'],'status':r['status'],'unique_ids':len(dom.ids)==len(set(dom.ids)),'error_anchors_resolve':all(x in dom.ids for x in dom.anchors),'invalid_abc_sort_retained':any(x.get('name')=='sortOrder' and x.get('value')=='abc' for x in dom.inputs)})
assert all(x['unique_ids'] and x['error_anchors_resolve'] for x in bodychecks)
assert any(x['invalid_abc_sort_retained'] for x in bodychecks)
(out/'http-post-coverage.json').write_text(json.dumps({'passed':True,'http_posts':len(post),'automatic_seven_table_db_pairs':len(auto),'all_rejected_posts_zero_write':True,'inline_error_html_checks':bodychecks,'notes':'Login, guest POST, CSRF and role rejection are included; target parent full columns and images retained, every table has ordered raw-row digest.'},ensure_ascii=False,indent=2),encoding='utf-8')
summary=dict(result)
summary['attempt']=attempt;summary['http_count']=len(http);summary['http_status_counts']=dict(collections.Counter(str(x['status']) for x in http));summary['http_posts']=len(post);summary['database_pairs']=len(writes);summary['group_cross_review']='姓名待填；组员交叉复核待补，M3前完成'
(out/'result.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
readme=f'''# STEP06 后台商品相册实测证据

- 受测完整 Git SHA：`{result['tested_code_sha']}`；基线：`{result['baseline_git_sha']}`。
- 受测分支：`{result['branch']}`；源码工作区为空（`{attempt}/git-input-status.txt`）；源码、SQL、静态素材、两端JAR图片的执行前后摘要未变化。
- 结论：**PASS（自动验收，组员复核待补）**；成功轮次 `{attempt}`，此前失败轮次如有保留原始证据，不能视为通过。
- attempt1产品HTTP、原生Service与浏览器各项观测通过，但最终读取浏览器JSON时验收脚本漏设UTF-8，触发Windows GBK UnicodeDecodeError，**该轮整体FAIL原样保留**。只修验收工具编码后，attempt2在新隔离库完整复跑通过，同一源码SHA。若失败图与成功图字节相同，原stage不改，归档由artifact-references.json给出原path→可直接查看的成功图path及完整SHA，避免双份PNG。
- 环境：JDK21、Wrapper Maven3.9.16、MySQL {result['mysql_version']}；隔离库 `csucampuscraft` 端口 `{result['mysql_port']}`，Java监听127.0.0.1:8080/8081。版本实际输出见 `{attempt}/versions.txt`；JAR摘要、运行输入摘要见 result.json / runtime-inputs.sha256。
- 两端真实 `mvnw.cmd -f <module>/pom.xml verify` 均退出0并有BUILD SUCCESS；原始日志保存在该轮次 build-user.log/build-admin.log。只依赖已有运行时，无新增测试框架或业务探针路由。

## 覆盖与原始记录

- HTTP {len(http)} 条，POST {len(post)} 条；**每一POST（含登录、游客、CSRF/角色拒绝）**均有7表before/after行数和有序原始行SHA、目标父商品所有资料/状态/封面/库存/version/时间字段与相册行前后记录，见 `{attempt}/database-writes.jsonl` 与 `http-post-coverage.json`。账户、地址及订单行只留摘要，未公开敏感明文。
- A10读页、入口、创建、排序/替代文本编辑、同排序按ID、重复path允许、空alt回商品名；新增/修改/删除仅真实变化增父version，同值编辑303且全部状态不变；移除最后图片后用户详情回封面，封面缺失浏览器回占位。
- 跨商品/不存在image404，父不存在优先404；旧/缺失/空version409，格式/负数/Long溢出400；路径/排序/替代文本边界400；缺/错CSRF403、错角色403、未登录302。拒绝POST无数据变化。
- MAX父版本真变更在容量校验阶段409零写入，同值可303；这是上溢拒绝观测，**不是**后段故障注入或并发回滚实验。
- 旧A05表单在相册增版后409；旧相册表单在补货后409。封面独立；其余5表（含历史快照）最终与种子完全一致。
- 实际JAR Service原生串行调用 + MyBatis拦截观测：操作者SELECT FOR UPDATE为首个SQL，随后父商品锁，RC事务和单连接；版本验证早于图片归属查找，同值无DML；身份失效/错角色在业务表前拒绝。源码及输出见 `{attempt}/AlbumWriteProbe.java` 与 native-probe.log。没有实现并发、生产故障钩子或测试HTTP端点。
- 两端同path200的Content-Type/字节/SHA与assets一致，见 static-resources.jsonl；缺资源**原始404**与浏览器占位资源**200**分别留证，不能把缺文件写成200。
- 24张PNG（1366×768、1920×1080各12张），含A10多图/空态/缺封面、A04/A05入口、用户详情联动，见 `{attempt}/browser/`；浏览器仅GET，不触发写库。result.json记录截图尺寸、SHA、真实HTTP以及占位资源事件。
- HTTP正文脱敏后gzip去重，http.jsonl索引记解压后SHA。sensitive-data-scan.json实际解压并检查正文、CSRF值、会话、Cookie、BCrypt和已知教学密码。evidence-files.json对除自身外全部文件给出字节SHA。

## 口径与尚未覆盖

1. 当前任务明确缺失/空productVersion为409，历史TST-40表原标准为400；本轮按任务覆盖，原标准保留，由项目文档实测差异说明。
2. 用户“4条写路由”实际列3条POST和1条GET；只验证列出的3条POST，无新增第4条。
3. 写入路径比BR-17和用户图片片段更严：拒任意`..`子串、冒号、百分号、反斜杠、查询/片段、控制字符和独立`.`段；合法Unicode/空格/缺文件/重复路径通过，用户片段未改。
4. TST-40并发/故障注入和订单快照写入留STEP13；本轮仅证明已有历史快照不受相册写影响。Word指导书未修改，M1统一更新待评估。
5. 负责人：本人姓名待填（Codex生成初稿，本人核对与验证）；复核人：组员姓名待填（组员复核待补，M3前完成）。AI执行单元的自动验收不代替组员签字。

## 运行与停机

验收脚本 verify_step06.py、verify_browser.cjs 与 AlbumWriteProbe.java 原文归档在成功轮次；执行环境变量只传受测SHA、构建日志目录及秘密，秘密未进入命令参数/证据。隔离DB先导入后授权，app仅SELECT/LOCK TABLES、product_image DML与product UPDATE，其他表无DML权限。每个独立SQL连接先设UTC。

`tracked_processes_stopped=true` 证明此次受控Java/MySQL进程全部退出；私有运行目录与临时认证文件不进归档。cleanup.json另记私有目录清理。
'''
(out/'README.md').write_text(readme,encoding='utf-8',newline='\n')
print(json.dumps({'published':str(out),'overall':summary['overall'],'http':len(http),'posts':len(post),'screenshots':result['screenshots']},ensure_ascii=False))
