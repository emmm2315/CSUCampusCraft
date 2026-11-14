"""Audit STEP12 archived bytes, source freeze, privacy structure and doc candidates."""
from pathlib import Path
import gzip,hashlib,json,re,zipfile
HERE=Path(__file__).resolve().parent;EV=HERE/'final-evidence';RAW=HERE/'verification/evidence'
REPO=Path('D:/Github Projects/CSUCampusCraft');SHA='03384367c87147f1c29859c799f3c464b016b760'
PREFIX=json.loads((HERE/'verification/evidence-date.json').read_text(encoding='utf-8-sig'))['evidence_directory'];checks=[]
def check(name,value):
    checks.append(dict(name=name,passed=bool(value)))
    if not value:raise AssertionError(name)
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(data):return hashlib.sha256(data).hexdigest()
result=read(EV/'result.json');success=result['successful_attempt']
check('actual completed PASS',result['overall']=='PASS' and result['tested_code_sha']==SHA)
compression={x['path'][:-3]:x for x in read(EV/'compressed-text-index.json')}
relocated={x['original_path']:x for x in read(EV/'artifact-references.json')['files']}
for name,entry in compression.items():
    raw=gzip.decompress((EV/entry['path']).read_bytes())
    check('gzip lossless '+name,sha(raw)==entry['decompressed_sha256'] and raw==(RAW/name).read_bytes())
for name,row in relocated.items():
    with zipfile.ZipFile(EV/row['stored_as']) as z:
        check('ZIP safe image entries '+name,all(not Path(x).is_absolute() and '..' not in Path(x).parts and x.endswith('.png') for x in z.namelist()))
        raw=z.read(row['zip_entry'])
    check('ZIP preserves original image '+name,sha(raw)==row['sha256'] and raw==(RAW/name).read_bytes())
for entry in read(EV/'original-attempt-inventory.json')['attempts']:
    attempt=entry['attempt'];run=read(EV/attempt/'result.json')
    check('all tracked processes stopped '+attempt,run['tracked_processes_stopped'])
    for item in entry['files']:
        name=attempt+'/'+item['path']
        if name in compression:raw=gzip.decompress((EV/compression[name]['path']).read_bytes())
        elif name in relocated:
            row=relocated[name]
            with zipfile.ZipFile(EV/row['stored_as']) as z:raw=z.read(row['zip_entry'])
        else:raw=(EV/name).read_bytes()
        check('original attempt byte SHA '+name,len(raw)==item['bytes'] and sha(raw)==item['sha256'])
    for row in map(json.loads,(EV/attempt/'http.jsonl').read_text(encoding='utf-8').splitlines()):
        raw=gzip.decompress((EV/attempt/row['body_file']).read_bytes())
        check('HTTP redacted body SHA '+attempt+' '+str(row['sequence']),sha(raw)==row['redacted_body_sha256'])
    for shot in read(EV/attempt/'browser/result.json')['screenshots']:
        name=attempt+'/browser/'+shot['path']
        if name in relocated:
            row=relocated[name]
            with zipfile.ZipFile(EV/row['stored_as']) as z:raw=z.read(row['zip_entry'])
        else:raw=(EV/name).read_bytes()
        check('browser PNG SHA '+name,sha(raw)==shot['sha256'])
br=read(EV/success/'browser/result.json');visual=read(EV/'ui-visual-review.json')
check('20 to 26 fresh direct PNGs',20<=len(br['screenshots'])<=26 and len(list(EV.rglob('*.png')))==len(br['screenshots']))
check('all direct PNGs visually inspected',visual['overall']=='PASS' and visual.get('raw_originals_actually_viewed',visual.get('actual_original_images_viewed'))==len(br['screenshots']) and visual.get('tested_code_sha',visual.get('tested_source_sha'))==SHA)
check('independent observations PASS',read(EV/'independent-observation-review.json')['overall']=='PASS')
protected=read(EV/'protected-source-preservation.json')
check('160 existing protected source files preserved',protected['overall']=='PASS' and len(protected['files'])==160)

scan=[];decompressed=0
for p in sorted(EV.rglob('*')):
    if not p.is_file() or p.name in {'final-audit.json','evidence-files.json'} or p.suffix.lower() in {'.png','.zip'}:continue
    name=p.relative_to(EV).as_posix();raw=p.read_bytes()
    if p.suffix=='.gz':raw=gzip.decompress(raw);decompressed+=1
    text=raw.decode('utf-8-sig');check('UTF8 no replacement '+name,'\ufffd' not in text)
    hits=[]
    if re.search(r'\$2[aby]\$\d\d\$[./A-Za-z0-9]{53}',text):hits.append('bcrypt value')
    if re.search(r'(?im)^(?:Set-Cookie|Cookie):\s*(?!\[REDACTED\])\S+',text):hits.append('cookie header value')
    if re.search(r';CSUCAMPUSCRAFT_(?:USER|ADMIN)_SESSION=[A-Za-z0-9.-]{12,}',text):hits.append('rewritten session value')
    check('structural private scan '+name,not hits)
    scan.append(dict(path=name,bytes=len(raw),sha256=sha(raw),findings=hits))
run=read(EV/success/'result.json');manifest=(EV/success/'runtime-inputs.sha256').read_text(encoding='utf-8')
check('manifest count',len(manifest.splitlines())==run['runtime_file_count'])
check('manifest bytes SHA',sha(manifest.encode())==run['runtime_manifest_sha256'])
for line in manifest.splitlines():
    expected,name=line.split('  ',1);check('frozen source '+name,sha((REPO/name).read_bytes())==expected)
cleanup=read(EV/'cleanup.json')
check('private runtime directories removed',cleanup['passed'] and len(cleanup['private_runtime_cleanup'])==len(result['attempts']) and all(x['directory_removed']for x in cleanup['private_runtime_cleanup']))
for item in read(HERE/'docs/manifest.json')['files']:
    check('old doc original SHA '+item['path'],sha((REPO/item['path']).read_bytes())==item['original_sha256'])
    check('doc candidate SHA '+item['path'],sha((HERE/'docs'/item['path']).read_bytes())==item['sha256'])
old=(REPO/'docs/开发计划与任务.md').read_text(encoding='utf-8').splitlines();new=(HERE/'docs/docs/开发计划与任务.md').read_text(encoding='utf-8').splitlines()
for number in ['07','08','09','10','11']:
    prefix='| STEP'+number+' | 负责人：';a=next(x for x in old if x.startswith(prefix));b=next(x for x in new if x.startswith(prefix))
    check('STEP'+number+' ledger unchanged pending review',a==b and '| 待复核 |' in b)
new12=next(x for x in new if x.startswith('| STEP12 | 负责人：'))
check('STEP12 actual SHA pending review',SHA in new12 and '| 待复核 |' in new12 and '姓名待填' in new12)
a=(REPO/'docs/测试与验收用例.md').read_text(encoding='utf-8');b=(HERE/'docs/docs/测试与验收用例.md').read_text(encoding='utf-8')
check('all original business TST standards preserved',a.split('## 业务用例\n',1)[1]==b.split('## 业务用例\n',1)[1])
for p in [EV/'README.md',HERE/'docs/README.md',HERE/'docs/docs/开发计划与任务.md',HERE/'docs/docs/测试与验收用例.md',HERE/'docs/docs/页面清单与原型.md',HERE/'docs/docs/系统设计与路由.md']:
    for link in re.findall(r'(?<!!)\[[^\]]+\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
        if re.match(r'^[a-z]+://',link) or link.startswith('#'):continue
        dest=link.split('#',1)[0].strip('<>')
        if not dest:continue
        if p==EV/'README.md':target=EV/dest
        else:
            expected=((REPO/p.relative_to(HERE/'docs')).parent/dest).resolve();archive=(REPO/PREFIX).resolve()
            target=EV/expected.relative_to(archive) if expected==archive or archive in expected.parents else expected
        check('local Markdown link '+p.name+' '+dest,target.exists())
report=dict(overall='PASS',tested_code_sha=SHA,checks=checks,text_files_scanned=len(scan),gzip_files_decompressed=decompressed,scan=scan,boundaries='Stored evidence/source/doc integrity checks, not new HTTP, logistics, concurrency or fault injection. Original per-attempt known-private-value scan retained separately.')
(EV/'final-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
index=[dict(path=p.relative_to(EV).as_posix(),bytes=p.stat().st_size,sha256=sha(p.read_bytes()))for p in sorted(EV.rglob('*'))if p.is_file()and p.name!='evidence-files.json']
(EV/'evidence-files.json').write_text(json.dumps(dict(files=index),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(overall='PASS',checks=len(checks),archive_files=len(index)+1,total_bytes=sum(x['bytes']for x in index),texts=len(scan),gzip=decompressed)))
