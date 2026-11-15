"""Build a new bounded-size STEP13 delivery copy. Never changes any source evidence file."""
from pathlib import Path
import hashlib,json,gzip,lzma,shutil,sys,datetime
S=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def run(number,cd_number):
    source=S/'verification/evidence'/('attempt'+str(number));result=json.loads((source/'result.json').read_text(encoding='utf-8-sig'))
    cd=json.loads((S/'verification/evidence'/('attempt'+str(cd_number))/'result.json').read_text(encoding='utf-8-sig'))
    assert len(result['p0_matrix'])==39 and result['checks_failed']==0 and result['runtime_inputs_stable']
    assert cd['overall']=='PASS' and len(cd['p0_matrix'])==10 and all(x['result']=='PASS' for x in cd['p0_matrix'])
    assert cd['tested_sha']==result['tested_sha'] and cd['user_jar_sha256']==result['user_jar_sha256'] and cd['admin_jar_sha256']==result['admin_jar_sha256']
    dest=S/'package';dest.mkdir(exist_ok=False);transforms=[];copied=[];manifests=[]
    def put(p,relative):
        raw=p.read_bytes();target=dest/relative
        # Retain exact logical JSONL bytes in lossless gzip. Original stage evidence stays intact.
        if p.suffix=='.jsonl' and p.name!='http.jsonl' and len(raw)>100_000:
            target=target.with_name(target.name+'.xz');stored=lzma.compress(raw,preset=6)
            transforms.append(dict(logical_path=str(relative).replace('\\','/'),logical_bytes=len(raw),logical_sha256=sha(raw),stored_path=target.relative_to(dest).as_posix(),stored_bytes=len(stored),stored_sha256=sha(stored),encoding='lossless xz/LZMA2; decompressed bytes exactly equal source evidence'))
        elif p.name=='historical-evidence-baseline.json':
            target=target.with_name(target.name+'.gz');stored=gzip.compress(raw,compresslevel=9,mtime=0)
            transforms.append(dict(logical_path=str(relative).replace('\\','/'),logical_bytes=len(raw),logical_sha256=sha(raw),stored_path=target.relative_to(dest).as_posix(),stored_bytes=len(stored),stored_sha256=sha(stored),encoding='lossless gzip'))
        else:stored=raw
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():
            assert target.read_bytes()==stored,'Different source files may not silently overwrite one archive path'
            return
        target.write_bytes(stored)
        copied.append(dict(path=target.relative_to(dest).as_posix(),bytes=len(stored),sha256=sha(stored)))
    def tree(base,prefix):
        if not base.exists():return
        for p in sorted(base.rglob('*')):
            if not p.is_file() or '__pycache__' in p.parts or p.suffix in ['.jar','.class','.pdf']:continue
            if any(x in p.relative_to(base).parts for x in ['runtime','mysql-data','lib','classes','renders','qa-pages']):continue
            relative=Path(prefix)/p.relative_to(base)
            if p.name=='artifacts.sha256':
                observations=[]
                for line in p.read_text(encoding='utf-8-sig').splitlines():
                    if not line.strip():continue
                    digest,name=line.split('  ',1);f=p.parent/name
                    assert f.resolve().is_relative_to(p.parent.resolve()) and f.is_file()
                    actual=sha(f.read_bytes());assert actual==digest,(str(f),digest,actual)
                    observations.append(dict(path=name,sha256=actual))
                manifests.append(dict(manifest=relative.as_posix(),logical_source_entries=len(observations),all_original_source_bytes_match=True))
            put(p,relative)
    for d in sorted((S/'verification/evidence').glob('attempt*')):tree(d,d.name)
    tree(S/'home-filter-supplement/evidence/attempt1','home-filter-supplement/attempt1')
    tree(S/'state-token-supplement/evidence/attempt1','state-token-supplement/attempt1')
    tree(S/'ddl-metadata-supplement/evidence/attempt1','ddl-metadata-supplement/attempt1')
    for base,prefix in [(S/'native','native-prechecks'),(S/'verification/literal-preflight','literal-preflight'),(S/'literal-preflight','literal-preflight'),(S/'verification/tool-versions','tool-versions')]:tree(base,prefix)
    for folder in ['state-token-supplement','home-filter-supplement','ddl-metadata-supplement']:
        for p in sorted((S/folder).glob('*')):
            if p.is_file():put(p,Path(folder)/p.name)
    for p in sorted((S/'verification').glob('*')):
        if p.is_file() and p.suffix in ['.py','.java','.json']:put(p,Path('tools-final')/p.name)
    for name in ['source-and-artifacts.json','runtime-inputs.json','runtime-inputs.sha256','historical-evidence-baseline.json','capture-baseline.py','build-step13.ps1','build-user.log','build-admin.log','build-user.json','build-admin.json','jdk-version.log','wrapper-version.log','task-contract.txt','supplement-run.log','ddl-metadata-run.log']:
        p=S/name
        if p.exists():put(p,Path(name))
    for p in sorted(S.glob('attempt*-run.log')):put(p,Path('runner-logs')/p.name)
    payload=dict(created_at_utc=datetime.datetime.now(datetime.UTC).isoformat(),tested_sha=result['tested_sha'],original_stage_evidence_not_modified=True,lossless_transforms=transforms,source_manifests_checked=manifests,child_manifest_semantics='Original child artifacts.sha256 stays unchanged and addresses logical source bytes; consult lossless_transforms when a JSONL is stored as gzip. Parent artifacts.sha256 addresses actual final stored files.',files_copied=len(copied),stored_bytes=sum(x['bytes'] for x in copied))
    (dest/'archive-transforms.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in payload.items() if k not in ['lossless_transforms','source_manifests_checked']},ensure_ascii=False));return dest
if __name__=='__main__':run(int(sys.argv[1]),int(sys.argv[2]))
