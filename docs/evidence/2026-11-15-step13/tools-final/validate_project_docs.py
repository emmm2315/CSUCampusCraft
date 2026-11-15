"""Check local closeout edits preserve historical records and business contract text."""
from pathlib import Path
import json,hashlib
S=Path(__file__).resolve().parent;R=Path('D:/Github Projects/CSUCampusCraft')
def norm(p):return Path(p).read_text(encoding='utf-8-sig')
def main():
    checks=[]
    def ck(name,value):checks.append(dict(name=name,passed=bool(value)));assert value,name
    old=norm(R/'docs/测试与验收用例.md');new=norm(S/'candidates/docs/测试与验收用例.md')
    start=new.index('### STEP13 实测记录\n');end=new.index('## 业务用例\n',start)
    restored=new[:start]+new[end:];restored=restored.replace(new.splitlines()[4],old.splitlines()[4],1)
    restored=restored.replace('STEP13 已按本节标准在最终受测 SHA 分组完成 39 条 P0 技术验收，8 类并发与 5 类故障回滚见新增实测记录；原步骤结果与工具失败保留各自身份。TST-36 为 P1 未选做。','STEP13 整体验收待执行，未覆盖的并发、竞争、故障注入及最终 SHA 全链路复测留 STEP13，TST-36 为 P1 未选做。',1)
    ck('Tests original history and all business standards preserved outside current intro/new STEP13 section',restored==old)
    old=norm(R/'docs/开发计划与任务.md');new=norm(S/'candidates/docs/开发计划与任务.md')
    ck('Plan STEP01–12 full instructions and history preserved',old[old.index('### STEP01'):old.index('### STEP13')] in new)
    ck('Plan STEP13 original five operations and gates preserved',old[old.index('- 阶段与负责人：M3'):old.index('### STEP14')] in new)
    ck('Plan STEP14 optional instructions preserved',old[old.index('### STEP14'):old.index('## 认领与核对记录')] in new)
    oldrows=[line for line in old.splitlines() if line.startswith('| STEP') and not line.startswith('| STEP 子任务')]
    ck('All prior claim/verification rows preserved byte text',all(line in new for line in oldrows))
    ck('STEP13 status and new ledger row present','| STEP13 | 高宇弘' in new and '### STEP13 并发回滚与整体验收\n\n状态：通过。' in new)
    ck('P1 marked unselected','| P1 | STEP14 | 未选做 |' in new)
    old=norm(R/'README.md');new=norm(S/'candidates/README.md')
    ck('README previous operational/handoff sections preserved',old[old.index('\nMySQL 8.4',old.index('## 当前阶段')):] in new)
    result=dict(overall='PASS',checks=checks,scope='Current status/STEP13 additions only; no requirement, rule, route, field or historical-result semantics changed')
    (S/'package/project-doc-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
