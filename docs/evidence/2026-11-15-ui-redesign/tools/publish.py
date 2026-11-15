from pathlib import Path
import hashlib,json,subprocess
ROOT=Path('D:/Github Projects/CSUCampusCraft');STAGE=Path(__file__).resolve().parent.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT).decode().strip()
assert git('rev-parse','HEAD')=='e2bdeb9df9cc7888383ef7afa28d5fbe94f29696'
assert git('branch','--show-current')=='feat/ui-redesign'
assert git('rev-parse','main')=='e2bdeb9df9cc7888383ef7afa28d5fbe94f29696'
assert not git('status','--porcelain')
assert (STAGE/'verification/BEFORE_COMPLETE.json').exists(), 'Need verified before capture gate'
before=json.loads((STAGE/'baseline/tracked-sha256.json').read_text(encoding='utf-8'))
assert all(sha(ROOT/p)==value for p,value in before.items()), 'baseline source/evidence drift'
candidates=sorted((STAGE/'candidate').rglob('*'))
files=[p for p in candidates if p.is_file()]
assert len([p for p in files if p.suffix=='.html'])==46
assert len(files)==60,len(files)
published=[]
for p in files:
    rel=p.relative_to(STAGE/'candidate').as_posix()
    assert rel.startswith(('csucampuscraft-user/src/main/resources/templates/','csucampuscraft-user/src/main/resources/static/','csucampuscraft-admin/src/main/resources/templates/','csucampuscraft-admin/src/main/resources/static/')),rel
    target=ROOT/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes());published.append(rel)
(ROOT/'docs/UI设计规范.md').write_bytes((STAGE/'UI设计规范.md').read_bytes());published.append('docs/UI设计规范.md')
for name,needle,line in [
    ('README.md','## 当前阶段','交付后 UI 重设计（终末地风格）：双端统一 standard 视觉与可选深色外观，业务验收保持冻结。见[UI 设计规范](docs/UI设计规范.md)与[改前/改后及回归证据](docs/evidence/2026-11-15-ui-redesign/README.md)。'),
    ('docs/页面清单与原型.md','## 用户端页面','视觉规范：[交付后 UI 设计规范](UI设计规范.md)。页面编号、字段、状态、路由与以下业务规格保持不变。')]:
    path=ROOT/name;raw=path.read_bytes();nl=b'\r\n' if b'\r\n' in raw else b'\n'
    assert raw.count(needle.encode())==1
    if name=='README.md':
        token=needle.encode()+nl+nl;assert raw.count(token)==1
        raw=raw.replace(token,token+line.encode()+nl+nl,1)
    else:raw=raw.replace(needle.encode(),line.encode()+nl+nl+needle.encode(),1)
    path.write_bytes(raw);published.append(name)
path=ROOT/'.gitattributes';raw=path.read_bytes();nl=b'\r\n' if b'\r\n' in raw else b'\n'
assert b'2026-11-15-ui-redesign' not in raw
path.write_bytes(raw+nl+b'# Preserve UI redesign before/after observations as archived bytes.'+nl+b'docs/evidence/2026-11-15-ui-redesign/** -text'+nl);published.append('.gitattributes')
allowed=set(published)
drift=[p for p,value in before.items() if sha(ROOT/p)!=value and p not in allowed]
assert not drift,drift
for app in ('user','admin'):
    p=ROOT/f'csucampuscraft-{app}/src/main/resources/static/js/app.js'
    old=STAGE/'baseline/templates'/f'csucampuscraft-{app}'
    original=subprocess.check_output(['git','show','e2bdeb9:'+p.relative_to(ROOT).as_posix()],cwd=ROOT)
    assert p.read_bytes().replace(b'\r\n',b'\n').startswith(original.replace(b'\r\n',b'\n'))
report={'files':published,'count':len(published),'protected_tracked_files_unchanged':len(before)-sum(p in before for p in allowed),'old_evidence_files_unchanged':sum(p.startswith('docs/evidence/') for p in before),'main_unchanged':git('rev-parse','main')}
(STAGE/'published.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='files'},ensure_ascii=False))
