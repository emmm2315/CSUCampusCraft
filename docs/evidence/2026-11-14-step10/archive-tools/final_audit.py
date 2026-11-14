"""Check frozen observations, lossless archive transforms and three documentation candidates."""
from pathlib import Path
import gzip, hashlib, json, re, zipfile

HERE=Path(__file__).resolve().parent
EV=HERE/'final-evidence'
RAW=HERE/'verification/evidence'
REPO=Path('D:/Github Projects/CSUCampusCraft')
SHA='b0253a5ecc920dfa862eec0eb8358f301ac41c10'
PREFIX='docs/evidence/2026-11-14-step10'
checks=[]
def check(name,value):
    checks.append(dict(name=name,passed=bool(value)))
    if not value: raise AssertionError(name)
def sha(data):return hashlib.sha256(data).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8'))

compression={x['path'][:-3]:x for x in read(EV/'compressed-text-index.json')}
for name,entry in compression.items():
    raw=gzip.decompress((EV/entry['path']).read_bytes())
    check('gzip SHA '+entry['path'],sha(raw)==entry['decompressed_sha256'])
    check('gzip equals original '+entry['path'],raw==(RAW/name).read_bytes())
relocations={x['original_path']:x for x in read(EV/'artifact-references.json')['files']}
check('24 failed images mapped',len(relocations)==24)
with zipfile.ZipFile(EV/'attempt1/browser/screenshots.zip') as z:
    check('24 safe ZIP image entries',len(z.namelist())==24 and all(Path(x).name==x and x.endswith('.png') for x in z.namelist()))
    for name,row in relocations.items():
        data=z.read(row['zip_entry'])
        check('ZIP equals failed original '+name,data==(RAW/name).read_bytes() and sha(data)==row['sha256'])
        check('failed direct archive relocated '+name,not (EV/name).exists())

attempts=read(EV/'attempts-summary.json')
check('same production code both attempts',attempts['same_production_code'])
check('failed native proof gap honestly retained',attempts['old_native_before_after_pair_missing'] and attempts['no_retrospective_native_zero_write_claim'])
for entry in attempts['attempts']:
    attempt=entry['attempt']
    check('attempt result hash '+attempt,sha((EV/attempt/'result.json').read_bytes())==entry['result_sha256'])
    for item in entry['inventory']:
        name=attempt+'/'+item['path']
        if name in compression:data=gzip.decompress((EV/compression[name]['path']).read_bytes())
        elif name in relocations:
            with zipfile.ZipFile(EV/relocations[name]['stored_as']) as z:data=z.read(relocations[name]['zip_entry'])
        else:data=(EV/name).read_bytes()
        check('original inventory byte hash '+name,len(data)==item['bytes'] and sha(data)==item['sha256'])
    for row in map(json.loads,(EV/attempt/'http.jsonl').read_text(encoding='utf-8').splitlines()):
        if not row.get('body_available',True):
            check('unavailable body explicitly marked '+attempt+' '+str(row['sequence']),row['body_available'] is False)
        raw=gzip.decompress((EV/attempt/row['body_file']).read_bytes())
        check('HTTP body SHA '+attempt+' '+str(row['sequence']),sha(raw)==row['redacted_body_sha256'])
    for shot in read(EV/attempt/'browser/result.json')['screenshots']:
        name=attempt+'/browser/'+shot['path']
        if name in relocations:
            with zipfile.ZipFile(EV/relocations[name]['stored_as']) as z:data=z.read(relocations[name]['zip_entry'])
        else:data=(EV/name).read_bytes()
        check('browser PNG index hash '+name,sha(data)==shot['sha256'])

check('24 successful direct images only',len(list(EV.rglob('*.png')))==24 and len(list((EV/'attempt2/browser').glob('*.png')))==24)
visual=read(EV/'ui-visual-review.json')
check('actual 24 visual review PASS',visual['overall']=='PASS' and visual['raw_originals_actually_viewed']==24 and visual['tested_code_sha']==SHA)
check('visual report bytes',sha((EV/'ui-visual-review.json').read_bytes())=='3bfc6fe7eef185dca59a0b3285731b8143f63ad4b90dad4f23bd8ad516ead4fc')
check('independent observations PASS',read(EV/'independent-observation-review.json')['overall']=='PASS')
check('100 protected source files preserved',read(EV/'step09-source-preservation.json')['overall']=='PASS' and len(read(EV/'step09-source-preservation.json')['files'])==100)

scan=[];decompressed=0
for path in sorted(EV.rglob('*')):
    if not path.is_file() or path.name in {'final-audit.json','evidence-files.json'} or path.suffix.lower() in {'.png','.zip'}:continue
    name=path.relative_to(EV).as_posix();data=path.read_bytes()
    if path.suffix=='.gz':data=gzip.decompress(data);decompressed+=1
    text=data.decode('utf-8-sig')
    check('UTF8 no replacement '+name,'\ufffd' not in text)
    hits=[]
    if re.search(r'\$2[aby]\$\d\d\$[./A-Za-z0-9]{53}',text):hits.append('bcrypt value')
    if re.search(r'(?im)^(?:Set-Cookie|Cookie):\s*(?!\[REDACTED\])\S+',text):hits.append('cookie header value')
    if re.search(r';CSUCAMPUSCRAFT_(?:USER|ADMIN)_SESSION=[A-Za-z0-9.-]{12,}',text):hits.append('rewritten session value')
    check('structural secrets '+name,not hits)
    scan.append(dict(path=name,bytes=len(data),sha256=sha(data),findings=hits))

manifest=(EV/'attempt2/runtime-inputs.sha256').read_text(encoding='utf-8')
for line in manifest.splitlines():
    expected,name=line.split('  ',1)
    check('frozen runtime input '+name,sha((REPO/name).read_bytes())==expected)
check('168 frozen inputs',len(manifest.splitlines())==168)
check('input manifest SHA',sha(manifest.encode())=='443291ac2bfd32c5ff0fe4b9f50ff584956753dca870c879304a03c44af07ca9')
cleanup=read(EV/'cleanup.json')
check('both private directories removed',cleanup['passed'] and len(cleanup['private_runtime_cleanup'])==2 and all(x['directory_removed'] for x in cleanup['private_runtime_cleanup']))

for entry in read(HERE/'docs/manifest.json')['files']:
    check('old documentation hash '+entry['path'],sha((REPO/entry['path']).read_bytes())==entry['original_sha256'])
    check('candidate documentation hash '+entry['path'],sha((HERE/'docs'/entry['path']).read_bytes())==entry['sha256'])
old=(REPO/'docs/开发计划与任务.md').read_text(encoding='utf-8').splitlines()
new=(HERE/'docs/docs/开发计划与任务.md').read_text(encoding='utf-8').splitlines()
for number in ['07','08','09']:
    prefix='| STEP'+number+' | 负责人：'
    before=next(x for x in old if x.startswith(prefix));after=next(x for x in new if x.startswith(prefix))
    check('STEP'+number+' exact ledger preserved pending',before==after and '| 待复核 |' in after)
new10=next(x for x in new if x.startswith('| STEP10 | 负责人：'))
check('STEP10 real SHA pending review',SHA in new10 and '| 待复核 |' in new10 and '姓名待填' in new10)
old_tests=(REPO/'docs/测试与验收用例.md').read_text(encoding='utf-8')
new_tests=(HERE/'docs/docs/测试与验收用例.md').read_text(encoding='utf-8')
check('all existing TST standards preserved',old_tests.split('## 业务用例\n',1)[1]==new_tests.split('## 业务用例\n',1)[1])
for path in [EV/'README.md',HERE/'docs/README.md',HERE/'docs/docs/开发计划与任务.md',HERE/'docs/docs/测试与验收用例.md']:
    for link in re.findall(r'(?<!!)\[[^\]]+\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
        if re.match(r'^[a-z]+://',link) or link.startswith('#'):continue
        dest=link.split('#',1)[0].strip('<>')
        if not dest:continue
        if path==EV/'README.md':target=EV/dest
        else:
            rel=path.relative_to(HERE/'docs');normalized=((REPO/rel).parent/dest).resolve();archive=(REPO/PREFIX).resolve()
            target=EV/normalized.relative_to(archive) if normalized==archive or archive in normalized.parents else normalized
        check('local link '+path.name+' '+dest,target.exists())

report=dict(overall='PASS',tested_code_sha=SHA,checks=checks,text_files_scanned=len(scan),gzip_files_decompressed=decompressed,scan=scan,
 known_private_scan='Original per-attempt sensitive-scan.json retained; attempt2 checked 49 known private values with zero findings. This final structural scan does not recreate discarded raw private inputs.',
 boundaries='Archived observations/source/doc integrity only. No new HTTP, concurrency or injected rollback assertion. Failed native missing before/after pair remains unproven.')
(EV/'final-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
index=[dict(path=p.relative_to(EV).as_posix(),bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in sorted(EV.rglob('*')) if p.is_file() and p.name!='evidence-files.json']
(EV/'evidence-files.json').write_text(json.dumps(dict(files=index),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(overall='PASS',checks=len(checks),archive_files=len(index)+1,total_bytes=sum(x['bytes'] for x in index),texts=len(scan),gzip=decompressed)))
