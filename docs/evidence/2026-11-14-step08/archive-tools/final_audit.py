"""Audit the finalized archive, its compression/indexes, and its documentation draft."""
from pathlib import Path
import gzip, hashlib, json, re

HERE=Path(__file__).resolve().parent
EV=HERE/'final-evidence'
REPO=Path('D:/Github Projects/CSUCampusCraft')
checks=[]
def check(name, value):
    checks.append(dict(name=name,passed=bool(value)))
    if not value: raise AssertionError(name)
def sha(data): return hashlib.sha256(data).hexdigest()

for entry in json.loads((EV/'compressed-text-index.json').read_text(encoding='utf-8')):
    raw=gzip.decompress((EV/entry['path']).read_bytes())
    check('compressed byte SHA '+entry['path'],sha(raw)==entry['decompressed_sha256'])
    check('compressed original retained '+entry['path'],raw==(HERE/'verification/evidence'/entry['path'][:-3]).read_bytes())
for row in map(json.loads,(EV/'attempt1/http.jsonl').read_text(encoding='utf-8').splitlines()):
    raw=gzip.decompress((EV/'attempt1'/row['body_file']).read_bytes())
    check('body index SHA '+str(row['sequence']),sha(raw)==row['redacted_body_sha256'])

files=sorted(p for p in EV.rglob('*') if p.is_file())
scan=[]; decompressed=0
for path in files:
    name=path.relative_to(EV).as_posix()
    if path.suffix.lower()=='.png': continue
    raw=path.read_bytes()
    if path.suffix=='.gz': raw=gzip.decompress(raw);decompressed+=1
    text=raw.decode('utf-8-sig')
    check('valid UTF8 no replacement '+name,'\ufffd' not in text)
    hits=[]
    if re.search(r'\$2[aby]\$\d\d\$[./A-Za-z0-9]{53}',text): hits.append('bcrypt value')
    if re.search(r'(?im)^(?:Set-Cookie|Cookie):\s*(?!\[REDACTED\])\S+',text): hits.append('cookie header value')
    if re.search(r';CSUCAMPUSCRAFT_(?:USER|ADMIN)_SESSION=[A-Za-z0-9.-]{12,}',text): hits.append('rewritten session value')
    check('structural secret scan '+name,not hits)
    scan.append(dict(path=name,bytes=len(raw),sha256=sha(raw),findings=hits))

manifest=(EV/'attempt1/runtime-inputs.sha256').read_text(encoding='utf-8')
for line in manifest.splitlines():
    expected,name=line.split('  ',1)
    check('frozen runtime input '+name,sha((REPO/name).read_bytes())==expected)
check('147 frozen inputs',len(manifest.splitlines())==147)
check('runtime manifest SHA',sha(manifest.encode())=='e23e25c23afb45c22474833685506d5086ab9193f253920b70b818673a39bec2')
cleanup=json.loads((EV/'cleanup.json').read_text(encoding='utf-8'))
check('cleanup complete',cleanup['passed'] and all(x['directory_removed'] for x in cleanup['private_runtime_cleanup']))

candidate=json.loads((HERE/'docs/manifest.json').read_text(encoding='utf-8'))['files']
for entry in candidate:
    check('documentation old hash '+entry['path'],sha((REPO/entry['path']).read_bytes())==entry['original_sha256'])
    check('documentation candidate hash '+entry['path'],sha((HERE/'docs'/entry['path']).read_bytes())==entry['sha256'])
plan_old=(REPO/'docs/开发计划与任务.md').read_text(encoding='utf-8').splitlines()
plan_new=(HERE/'docs/docs/开发计划与任务.md').read_text(encoding='utf-8').splitlines()
old7=next(x for x in plan_old if x.startswith('| STEP07 | 负责人：'))
new7=next(x for x in plan_new if x.startswith('| STEP07 | 负责人：'))
check('STEP07 exact unchanged and pending review',old7==new7 and '| 待复核 |' in new7)
new8=next(x for x in plan_new if x.startswith('| STEP08 | 负责人：'))
check('STEP08 pending review and real source', '| 待复核 |' in new8 and '54d6b007eb1317c14be090016ea75aec02ead6c5' in new8)

for path in [EV/'README.md',HERE/'docs/README.md',HERE/'docs/docs/开发计划与任务.md',HERE/'docs/docs/测试与验收用例.md']:
    text=path.read_text(encoding='utf-8')
    for link in re.findall(r'(?<!!)\[[^\]]+\]\(([^)]+)\)',text):
        if re.match(r'^[a-z]+://',link) or link.startswith('#'): continue
        dest=link.split('#',1)[0].strip('<>')
        if not dest: continue
        if path==EV/'README.md': target=EV/dest
        else:
            rel=path.relative_to(HERE/'docs')
            expected=(REPO/rel).parent/dest
            normalized=expected.resolve()
            archive=(REPO/'docs/evidence/2026-11-14-step08').resolve()
            if normalized==archive or archive in normalized.parents: target=EV/normalized.relative_to(archive)
            else: target=normalized
        check('local link '+str(path.name)+' '+dest,target.exists())

report=dict(overall='PASS',tested_code_sha='54d6b007eb1317c14be090016ea75aec02ead6c5',
            checks=checks,text_files_scanned=len(scan),gzip_files_decompressed=decompressed,
            scan=scan,known_private_scan='See original attempt1/sensitive-scan.json; 108 actual private values checked in process, zero findings.',
            boundaries='Saved evidence and source/doc integrity checks only; no new order or concurrency claim.')
(EV/'final-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
index=[dict(path=p.relative_to(EV).as_posix(),bytes=p.stat().st_size,sha256=sha(p.read_bytes()))
       for p in sorted(EV.rglob('*')) if p.is_file() and p.name!='evidence-files.json']
(EV/'evidence-files.json').write_text(json.dumps(dict(files=index),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(overall='PASS',checks=len(checks),archive_files=len(index)+1,
                     total_bytes=sum(x['bytes'] for x in index),texts=len(scan),gzip=decompressed)))
