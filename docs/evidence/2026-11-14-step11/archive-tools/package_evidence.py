"""Prepare a new archive from actual completed STEP11 runs; never rewrite originals."""
from pathlib import Path
import datetime,gzip,hashlib,json,shutil,zipfile
HERE=Path(__file__).resolve().parent;RAW=HERE/'verification/evidence';EV=HERE/'final-evidence'
SHA='39c96aaaad18c58dce9d57450e14317a75c29b3d'
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(data):return hashlib.sha256(data).hexdigest()
assert not EV.exists(),'Never overwrite archive draft'
attempts=sorted([p for p in RAW.glob('attempt*') if p.is_dir() and (p/'result.json').exists()],key=lambda p:int(p.name[7:]))
assert attempts and read(attempts[-1]/'result.json')['overall']=='PASS'
run=read(attempts[-1]/'result.json');success=attempts[-1].name
assert run['tested_code_sha']==SHA and all(read(p/'result.json')['tracked_processes_stopped'] for p in attempts)
visual=read(HERE/'ui-visual-review.json');assert visual['overall']=='PASS' and visual['tested_code_sha']==SHA
review=read(RAW/'independent-observation-review.json');assert review['overall']=='PASS'
EV.mkdir()
def write(name,obj):
    p=EV/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def copy(source,target):
    p=EV/target;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE/source,p)
compression=[];moves=[];inventory=[]
for directory in attempts:
    attempt=directory.name;result=read(directory/'result.json');shutil.copytree(directory,EV/attempt)
    inventory.append(dict(attempt=attempt,overall=result['overall'],tested_code_sha=result['tested_code_sha'],files=[dict(path=p.relative_to(directory).as_posix(),bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in sorted(directory.rglob('*')) if p.is_file()]))
    for name in ['commands.jsonl','database-writes.jsonl']:
        p=EV/attempt/name
        if not p.exists():continue
        raw=p.read_bytes();packed=gzip.compress(raw,compresslevel=9,mtime=0);(EV/attempt/(name+'.gz')).write_bytes(packed)
        assert gzip.decompress(packed)==raw;p.unlink()
        compression.append(dict(path=attempt+'/'+name+'.gz',original_bytes=len(raw),decompressed_sha256=sha(raw),compressed_bytes=len(packed)))
    browser=directory/'browser/result.json'
    if attempt!=success and browser.exists():
        shots=read(browser)['screenshots'];archive=EV/attempt/'browser/screenshots.zip'
        with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for shot in shots:
                name=shot['path'];assert Path(name).name==name
                raw=(directory/'browser'/name).read_bytes();assert sha(raw)==shot['sha256'];z.writestr(name,raw)
                moves.append(dict(original_path=attempt+'/browser/'+name,stored_as=attempt+'/browser/screenshots.zip',zip_entry=name,sha256=sha(raw)))
        with zipfile.ZipFile(archive) as z:
            for row in [x for x in moves if x['stored_as']==attempt+'/browser/screenshots.zip']:
                assert sha(z.read(row['zip_entry']))==row['sha256'];(EV/row['original_path']).unlink()
write('compressed-text-index.json',compression)
write('artifact-references.json',dict(policy='Only archive copies transformed losslessly. Original stage records and result identities unchanged.',files=moves))
write('original-attempt-inventory.json',dict(captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),capture='Current bytes after completed runs, not a claimed failure-instant historical seal.',attempts=inventory))
for source,target in [
 ('source-publication.json','source-publication.json'),('source-review.json','source-review.json'),
 ('backend-review.json','backend-review.json'),('ui/static-review.json','ui-static-review.json'),
 ('ui-visual-review.json','ui-visual-review.json'),('baseline-preservation.json','baseline-preservation.json'),
 ('protected-source-preservation.json','protected-source-preservation.json'),
 ('tool-audit.json','tool-audit.json'),
 ('review_observations.py','review_observations.py'),('verification/evidence/independent-observation-review.json','independent-observation-review.json'),
 ('verification/delivery-metadata.json','delivery-metadata.json'),('verification/attempts-summary.json','attempts-summary.json'),
 ('verification/browser-capture-diagnostic.json','browser-capture-diagnostic.json')]:copy(source,target)
for name in ['attempt1-ui-visual-review.json']:
    if (HERE/name).exists():copy(name,name)
if (HERE/'verification/tool-fix').exists():
    for p in (HERE/'verification/tool-fix').rglob('*'):
        if p.is_file() and p.suffix in {'.json','.log','.py','.md'}:copy(p.relative_to(HERE),p.relative_to(HERE))
for name in ['privacy_checks.py','tool_fix_review.py','attempt1-tool-diagnostic.json']:
    if (HERE/'verification'/name).exists():copy('verification/'+name,'verification/'+name)
for name in ['integrate.py','protected_sources.py','package_evidence.py','final_audit.py','publish_final.py']:
    copy(name,'archive-tools/'+name)
copy('verification/cleanup.py','archive-tools/cleanup.py')
for name in ['build-fresh.ps1','build-user.log','build-admin.log','build-user.json','build-admin.json']:
    copy(name,'builds/'+name)
write('builds/build-exits.json',{x:read(HERE/('build-'+x+'.json'))['exit_code'] for x in ['user','admin']})
for folder in ['native-tools']:
    for p in (HERE/folder).rglob('*'):
        if p.is_file() and p.suffix in {'.java','.json','.log','.md','.py','.ps1'}:copy(p.relative_to(HERE),p.relative_to(HERE))
base=read(HERE/'baseline.json');write('original-refs.json',dict(base=base['base'],refs=base['refs']))
metadata=read(HERE/'verification/delivery-metadata.json')
latest=next(x for x in metadata['attempts']if x['attempt']==success)
write('result.json',dict(latest,overall=run['overall'],baseline_git_sha=base['base'],tested_code_sha=SHA,branch='feat/step11-admin-orders',successful_attempt=success,attempts=[dict(path=p.name+'/result.json',overall=read(p/'result.json')['overall'])for p in attempts],prior_attempt_review='Original attempt1 tool-recorded PASS preserved, privacy/flash assertion limits recorded in tool-audit.json; final acceptance uses fresh attempt2.',team_review='待复核；姓名待填，M3前完成；旧STEP07–10台账保持原样'))
readme=HERE/'evidence-README.md';assert readme.exists();copy('evidence-README.md','README.md')
print(json.dumps(dict(archive=str(EV),successful_attempt=success,attempts=len(attempts),files=len([p for p in EV.rglob('*')if p.is_file()]),direct_pngs=len(list(EV.rglob('*.png'))),historical_pngs_in_zip=len(moves))))
