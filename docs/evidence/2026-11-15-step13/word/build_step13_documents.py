"""STEP13 bounded document patch. Run only with final observed summary from the orchestrator.

Reads the retained guide; writes candidates under stage, never to the repository.
The marker must have completed exactly once immediately before the first execution.
"""
import argparse
import copy
import hashlib
import html
import json
import pathlib
import re
import xml.etree.ElementTree as ET
import xml.parsers.expat
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = pathlib.Path('D:/Github Projects/CSUCampusCraft/docs/实验一 CSUCampusCraft 校园文创商店实验指导书.docx')
SOURCE_HASH = '85d3e052f82c3a79f1bd7259b84ceb229ed4c8fd5526d980c0412e4c0cae7c4d'
NS = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

def sha(raw): return hashlib.sha256(raw).hexdigest()
def load(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def ptext(raw):
    return ''.join(ET.fromstring(b'<root xmlns:w="'+NS['w'].encode()+b'">'+raw+b'</root>').itertext())

def direct_elements(raw):
    parser=xml.parsers.expat.ParserCreate()
    stack=[]; starts=[]; elements=[]
    def start(name, attrs):
        starts.append(parser.CurrentByteIndex); stack.append(name)
    def end(name):
        start_index=starts.pop()
        if len(stack)==3 and stack[-2]=='w:body':
            close=raw.find(b'>',parser.CurrentByteIndex)+1
            elements.append((name,start_index,close))
        stack.pop()
    parser.StartElementHandler=start; parser.EndElementHandler=end; parser.Parse(raw,True)
    return elements

def replace_text(raw, text):
    matches=list(re.finditer(rb'(<w:t(?:\s[^>]*)?>)(.*?)(</w:t>)',raw,re.S))
    if not matches: raise ValueError('Expected plain text paragraph slot')
    encoded=html.escape(text,quote=False).encode('utf-8')
    for index,m in reversed(list(enumerate(matches))):
        raw=raw[:m.start(2)]+(encoded if index==0 else b'')+raw[m.end(2):]
    return raw

def gate(summary):
    assert re.fullmatch('[0-9a-f]{40}',summary['source_sha'])
    assert summary['overall']=='PASS'
    actual_path=pathlib.Path(summary['observed_result_path'])
    actual=load(actual_path)
    assert actual['overall']=='PASS' and actual['tested_sha']==actual['source_sha']==summary['source_sha']
    assert actual['runtime_inputs_stable'] is True and actual['checks_failed']==0
    assert actual['tracked_processes_stopped'] is True
    package=actual_path.parent.resolve()
    def within(relative):
        target=(package/relative).resolve()
        assert target.is_relative_to(package), 'Evidence reference must stay within this new package'
        assert target.is_file()
        return target
    groups=actual['groups'];assert len(groups)>=2
    group_map={x['id']:x for x in groups};assert len(group_map)==len(groups)
    leaves={};identities=set()
    for group in groups:
        file=within(group['result_file']);raw=file.read_bytes();leaf=load(file)
        assert sha(raw)==group['result_sha256']
        assert leaf['overall']==group['raw_overall']
        leaf_sha=leaf.get('tested_sha',leaf.get('tested_source_sha',leaf.get('source_sha')))
        assert leaf_sha==summary['source_sha']
        assert group['scoped_components_passed'] is True
        if group.get('cleanup_retry_file'):
            retry=load(within(group['cleanup_retry_file']))
            assert retry['passed'] is True and retry['tracked_processes_stopped'] is True
            assert retry['scoped_ports_no_listener'] is True and retry['private_runtime_removed'] is True
            assert retry['production_or_main5_instances_touched'] is False
        identity=tuple(group[x] for x in ['user_jar_sha256','admin_jar_sha256','runtime_manifest_sha256','runtime_file_count'])
        identities.add(identity)
        assert identity[-1]==199
        for key in ['user_jar_sha256','admin_jar_sha256','runtime_manifest_sha256','runtime_file_count']:
            if key in leaf:assert leaf[key]==group[key]
        leaves[group['id']]=leaf
    assert len(identities)==1, 'All adopted groups must use the same two JARs and199 runtime inputs'
    baseline=load(ROOT/'source-and-artifacts.json')
    jars={x['module']:x['sha256'] for x in baseline['jars']}
    identity=next(iter(identities))
    assert identity[:2]==(jars['user'],jars['admin'])
    expected_p0={f'TST-{i:02}' for i in range(1,41) if i!=36}
    matrix=actual['p0_matrix']
    assert len(matrix)==39 and {x['id'] for x in matrix}==expected_p0
    assert all(x['result']=='PASS' and x['tested_sha']==summary['source_sha'] for x in matrix)
    for row in matrix:
        assert row['observed_segments']
        for segment,record in row['observed_segments'].items():
            assert record['passed'] is True
            group=group_map[record['source_group']]
            source_segment=record['source_segment']
            assert source_segment in group['accepted_segments']
            source_matrix=load(within(record['source_matrix_file']))
            source_matrix=source_matrix['p0_matrix'] if isinstance(source_matrix,dict) else source_matrix
            matches=[x for x in source_matrix if x['id']==row['id']]
            assert len(matches)==1 and matches[0]['tested_sha']==summary['source_sha']
            assert matches[0]['observed_segments'][source_segment]['passed'] is True
            leaf_matrix=leaves[group['id']]['p0_matrix']
            leaf_matches=[x for x in leaf_matrix if x['id']==row['id']]
            assert len(leaf_matches)==1 and leaf_matches[0]['observed_segments'][source_segment]['passed'] is True
            assert leaf_matches[0]['observed_segments'][source_segment]==matches[0]['observed_segments'][source_segment]
            if re.fullmatch('[CD][1-8]',source_segment):assert group['raw_overall']=='PASS'
    for folder,prefix,total in [('concurrency','C',8),('faults','D',5)]:
        index=package/folder/'results.jsonl'
        observed=[json.loads(line) for line in index.read_text(encoding='utf-8-sig').splitlines() if line.strip()]
        assert len(observed)==total and {x['case'] for x in observed}=={prefix+str(i) for i in range(1,total+1)}
        assert all(x['result']=='PASS' for x in observed)
        adopted=[x for x in groups if prefix+'1' in x['accepted_segments']]
        assert len(adopted)==1
        original=within(adopted[0]['result_file']).parent/folder/'results.jsonl'
        assert index.read_bytes()==original.read_bytes(), 'Copied C/D index must preserve the actual accepted raw bytes'
    assert load(actual_path.parent/'sensitive-scan.json')['overall']=='PASS'
    cleanup=load(pathlib.Path(summary['cleanup_result_path']))
    cleanup_check=load(pathlib.Path(summary['cleanup_verification_path']))
    assert cleanup['overall']==cleanup_check['overall']=='PASS'
    assert cleanup_check['cleanup_report_sha256']==sha(pathlib.Path(summary['cleanup_result_path']).read_bytes())
    assert cleanup_check['source_result_hashes_unchanged'] and cleanup_check['protected_file_set_unchanged']
    assert cleanup_check['no_owned_runtime_processes'] and cleanup_check['no_relevant_port_listeners']
    assert not cleanup_check['killed_any_process'] and not cleanup_check['product_or_repo_accessed_for_write']
    assert summary['p0_total']==summary['p0_pass']==39
    assert len(summary['concurrency'])==8 and all(x['status']=='PASS' for x in summary['concurrency'])
    assert len(summary['faults'])==5 and all(x['status']=='PASS' for x in summary['faults'])
    assert {x.get('id',x.get('case')) for x in summary['concurrency']}=={'C'+str(i) for i in range(1,9)}
    assert {x.get('id',x.get('case')) for x in summary['faults']}=={'D'+str(i) for i in range(1,6)}
    for key in ['structure_empty_pass','admin_only_empty_pass','demo_initial_counts_pass','demo_85_pass','restart_pass','snapshot_pass','evidence_integrity_pass','sensitive_scan_pass']:
        assert summary[key] is True,key
    assert re.fullmatch('[A-Za-z0-9_-]{1,40}',summary['demo_order_no'])
    assert summary['peer_review_performed'] is False
    assert summary['p1_selected'] is False

def create_docx(summary):
    original=SOURCE.read_bytes(); assert sha(original)==SOURCE_HASH
    with zipfile.ZipFile(SOURCE) as z:
        members={i.filename:z.read(i.filename) for i in z.infolist()}
        infos=z.infolist()
    xml=members['word/document.xml']
    blocks=direct_elements(xml)
    ps=[x for x in blocks if x[0]=='w:p']
    tables=[x for x in blocks if x[0]=='w:tbl']
    assert len(ps)==319 and len(tables)==2
    original_ps=[xml[a:b] for _,a,b in ps]
    replacements={
      3: ('当前状态：STEP01–12 已交付，原本人复核范围不变。STEP13 在同一 SHA、JAR 和199项输入下完成39项P0分组自动验收，M3自动验收通过；原叶FAIL保留，组员互评未实施，P1未选做。本轮由高宇弘授权Codex自动执行；完整分组、证据及人工范围见末尾补充。以下 STEP01–14 操作指引保留。'),
      19: ('A 为用户端，B 为管理端，C 为共享数据与联调。每步登记真实负责人和复核人；两人组可以分担 C。实际执行说明：项目由高宇弘负责并使用 AI 辅助；2026-11-15 本人抽验签署仅覆盖原七项确认。本轮 STEP13 自动实测由本人授权 Codex 执行，未新增真人抽验或另一位组员复现，组员互评未实施。建议先看立项范围，再看需求业务，随后按本步查看页面 数据库 系统路由和测试文档。'),
      25: '.\\mvnw.cmd -f csucampuscraft-user/pom.xml verify',
      26: '.\\mvnw.cmd -f csucampuscraft-admin/pom.xml verify',
      29: 'mysql --host=127.0.0.1 --port=3306 --user=root --password --default-character-set=utf8mb4 --batch --database=csucampuscraft --execute="SOURCE database/02-schema-with-demo.sql"',
      35: ('浏览器访问 http://127.0.0.1:8080/ 和 http://127.0.0.1:8081/。用户端根页公开显示目录，演示版有主题与商品，结构空库显示空态。管理端根页先要求 ADMIN 登录，登录后显示 A02 真实控制台；结构空库没有账号，不能登录，另用 ADMIN-only 空业务库核对五项计数为0。M0 根页主题复现指引仍保留在 STEP01。启动失败先看连接和端口日志，不重复导入；在各终端用 Ctrl+C 停止应用。'),
      51: ('M0 已独立复现双端单独及同时运行、同库改名、重启保留和共享图片。本步保留给新成员复现；“仅到主题读取与初始化”为 M0 历史状态。当前 STEP01–12 已交付并通过原范围本人复核，STEP13 最终版本的 P0 自动验收结果另见末尾补充，不改写原 M0 证据。'),
      292: ('本页在 P0 功能开发后使用。STEP01–12 已交付并通过 2026-11-15 原范围本人复核；以下操作指引保留。本轮 STEP13 在最终版本完成85元交易、双端履约、重启、并发与故障回滚自动验收，实际执行和证据见末尾补充。该结果不替代尚未实施的组员互评或另一位真人复现。所有分支使用隔离测试库恢复初值，前一分支的变更不得隐含成为后一分支的夹具。')
    }
    teaching=ptext(original_ps[37])
    teaching_secret=re.search(r'教学密码\s*([^。]+)',teaching).group(1).strip().encode('utf-8')
    safe_teaching,n=re.subn(r'教学密码\s*[^。]+','教学口令为本机演示口令（由演示库初始化时在本机查看，证据中不记录）',teaching,count=1)
    assert n==1
    replacements[37]=safe_teaching
    append=[]
    def paragraph(text,template=2,newpage=False):
        raw=replace_text(original_ps[template],text)
        if newpage:
            if b'<w:pPr>' in raw:raw=raw.replace(b'<w:pPr>',b'<w:pPr><w:pageBreakBefore/>',1)
            else:raw=raw.replace(b'>',b'><w:pPr><w:pageBreakBefore/></w:pPr>',1)
        append.append(raw)
    paragraph('STEP13 最终验收实测补充',291,True)
    paragraph('本节记录本轮自动实测，不改变前文操作标准或历史证据。受测完整 Git SHA 为 '+summary['source_sha']+'；证据目录为 '+summary['evidence_path']+'。M3 分组自动验收通过，P0 共39项通过；父汇总逐格指向同一源码、两端 JAR 和199项运行输入下的实际有效组，不把任何原叶结果改写为通过。P1 确认收货未选做，真实支付、物流与 REST 未实现。')
    paragraph('执行身份与环境',4)
    paragraph('项目负责人高宇弘使用 AI 辅助完成项目；本轮 STEP13 由其授权 Codex 自动执行。此前 2026-11-15 本人七项确认仍只对应原抽验范围，本轮未伪造新人工操作或另一位组员签署；组员互评未实施。')
    paragraph(summary['environment_text']+'。构建使用仓库 Maven Wrapper 固定3.9.16，JAVA_HOME 指向 JDK21，继续按 Java17 编译；Wrapper 不包含 JDK。')
    paragraph('正常主线与干净复现',4)
    paragraph('分别验证 SQL01 结构空库、保留 ADMIN 的空业务库及 SQL02 演示库。演示初值按 store_user/category/product/product_image/cart_item/sales_order/sales_order_item 顺序为 4/15/60/100/10/10/20。结构空库不造账号，管理端不可登录；ADMIN-only 库五项控制台计数为0。')
    paragraph('真实85元订单 '+summary['demo_order_no']+'：清空 alice 种子车后加入2本18元方格本和1盒49元礼盒；确认85元，下单1主单2明细，库存10/12变8/11，两商品版本各加1，确认车清空、徽标0。模拟支付成功后管理端按完整单号发货，用户端读取 SHIPPED。订单快照不随后续商品名、价、封面或上下架变化；重启后订单、购物车、相册和统计保留。')
    paragraph('并发竞争与真实事务回滚',4)
    paragraph('八项同步并发场景均通过：'+ '；'.join(x['name'] for x in summary['concurrency'])+'。同一确认双提交共享会话，两个 HTTP 请求并发，事务入口由会话 monitor 串行；其余场景使用独立会话。同步起点、两次响应及独立连接前后值见 concurrency 原始记录；顺序点击和底层锁探针不替代真实 HTTP 业务结果。')
    paragraph('五项隔离测试库触发器注入均通过：'+ '；'.join(x['name'] for x in summary['faults'])+'。真实请求结束后用独立连接核对七表摘要，无部分订单、明细、库存版本或购物车残留；每案移除触发器并核无残留，不把注入机制写入产品源码或默认运行配置。')
    paragraph('证据边界与交付',4)
    paragraph('初始化、同库、共享图、空库、重启技术子项与39项P0的最终结果、完整SHA、工作区状态、环境、运行输入摘要、HTTP记录、数据库前后、并发与故障结果、失败和复测、截图及清理结果见本轮证据索引。'+summary.get('grouping_text','父汇总分别采纳主5的串行、空库、重启、浏览器与后续新库并发故障等有效段；主5整体FAIL保留，C1工具解码所缺原始输出不追认，清理失败与独立重试分列，不把任何原叶改写为整轮通过。')+'M0 原INIT-03双根页五主题标准保留历史身份，当前管理根页为受保护A02。报告中的通过来自本轮观察，不把旧证据换名复用；工具问题与产品问题分开。截图隐去联系方式和收货字段，证据不保存口令、密码散列、Cookie、CSRF或确认令牌原值。')
    paragraph(summary['cleanup_text'])
    paragraph('组员互评和另一位真人独立复现仍未实施；P1未选做。AI 视觉校验只证明文档和页面捕获时的可见效果，性能、真实支付、物流或生产安全审计未验证。')
    patches=[]
    for i,text in replacements.items():
        _,a,b=ps[i];patches.append((a,b,replace_text(original_ps[i],text)))
    section=next(x for x in blocks if x[0]=='w:sectPr')
    patches.append((section[1],section[1],b''.join(append)))
    updated=xml
    for a,b,value in sorted(patches,reverse=True):updated=updated[:a]+value+updated[b:]
    ET.fromstring(updated)
    assert teaching_secret not in updated
    assert all(teaching_secret not in raw for name,raw in members.items() if name!='word/document.xml')
    outdir=ROOT/'documents';outdir.mkdir(parents=True,exist_ok=True)
    out=outdir/SOURCE.name
    with zipfile.ZipFile(out,'w') as z:
        for info in infos:z.writestr(copy.copy(info),updated if info.filename=='word/document.xml' else members[info.filename])
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None
        assert set(z.namelist())==set(members)
        assert all(z.read(name)==raw for name,raw in members.items() if name!='word/document.xml')
        newblocks=direct_elements(z.read('word/document.xml'))
        newp=[z.read('word/document.xml')[a:b] for kind,a,b in newblocks if kind=='w:p']
        newtables=[z.read('word/document.xml')[a:b] for kind,a,b in newblocks if kind=='w:tbl']
        assert newtables==[xml[a:b] for _,a,b in tables]
        assert len(newp)==319+len(append)
        assert all(newp[i]==original_ps[i] for i in range(319) if i not in replacements)
    validation={'overall':'PASS','source_sha256':SOURCE_HASH,'output_sha256':sha(out.read_bytes()),'source_bytes':len(original),'output_bytes':out.stat().st_size,'original_paragraphs':319,'new_paragraphs':319+len(append),'tables_unchanged':2,'only_changed_package_part':'word/document.xml','retained_original_paragraphs_unchanged_except':sorted(replacements),'appended_paragraph_count':len(append),'old_teaching_credential_not_recorded':True,'original_source_unmodified':sha(SOURCE.read_bytes())==SOURCE_HASH,'tested_source_sha':summary['source_sha'],'human_scope_not_expanded':True}
    (ROOT/'word/word-update-validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return out,validation

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--summary',type=pathlib.Path,required=True);args=parser.parse_args()
    summary=load(args.summary);gate(summary)
    out,result=create_docx(summary)
    print(json.dumps({'overall':'PASS','output':str(out),'sha256':result['output_sha256'],'append':result['appended_paragraph_count']},ensure_ascii=False))

if __name__=='__main__':main()
