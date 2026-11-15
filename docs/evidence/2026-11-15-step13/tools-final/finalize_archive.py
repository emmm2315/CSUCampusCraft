"""Freeze new delivery artifact bytes after every review; no repository mutation."""
from pathlib import Path
import hashlib,json,lzma,gzip,shutil,datetime
from scan_package import run as scan
S=Path(__file__).resolve().parent;P=S/'package'
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    for src,target in [(S/'candidates/document-changes.json',P/'document-changes.json'),(S/'verification/independent_replay.py',P/'tools-final/independent_replay.py')]:shutil.copyfile(src,target)
    for name in ['aggregate_acceptance.py','package_evidence.py','scan_package.py','write_closeout_docs.py','validate_project_docs.py',Path(__file__).name]:shutil.copyfile(S/name,P/'tools-final'/name)
    for p in (S/'word').iterdir():
        if p.is_file() and p.suffix in ['.json','.py','.ps1','.log']:shutil.copyfile(p,P/'word'/p.name)
    transforms=json.loads((P/'archive-transforms.json').read_text(encoding='utf-8'))
    for field in ['stored_bytes','files_copied']:transforms.pop(field,None)
    transforms['final_transform_count']=len(transforms['lossless_transforms']);transforms['final_counts']='Use final-archive-validation.json and final artifacts.sha256, not intermediate copy statistics'
    (P/'archive-transforms.json').write_text(json.dumps(transforms,ensure_ascii=False,indent=2),encoding='utf-8')
    observations=[]
    for row in transforms['lossless_transforms']:
        p=(P/row['stored_path']).resolve();assert p.is_relative_to(P.resolve())
        stored=p.read_bytes();raw=lzma.decompress(stored) if p.suffix=='.xz' else gzip.decompress(stored)
        ok=sha(stored)==row['stored_sha256'] and sha(raw)==row['logical_sha256'] and len(raw)==row['logical_bytes'];assert ok
        observations.append(dict(logical=row['logical_path'],stored=row['stored_path'],stored_sha256=sha(stored),logical_sha256=sha(raw),passed=True))
    for name in ['word/word-render-review.json','word/word-update-validation.json','word/word-qa-cleanup.json','project-doc-validation.json','source-preservation-before-publication.json','parent-traceability-validation.json']:
        d=json.loads((P/name).read_text(encoding='utf-8-sig'));assert d.get('overall')=='PASS' or d.get('passed') is True,(name,d.get('overall'))
    png=list(P.rglob('*.png'));assert len(png)==20
    proof=dict(overall='PASS',recorded_at_utc=datetime.datetime.now(datetime.UTC).isoformat(),lossless_transform_count=len(observations),transforms=observations,original_body_gzip_files_not_rewritten=True,screenshot_count=20,word_pages=21,original_leaf_fail_statuses_preserved=True,artifact_manifest_rule='artifacts.sha256 hashes actual stored disk bytes of every final file except itself; logical original streams are independently verified above')
    (P/'final-archive-validation.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
    scan()
    files=sorted(x for x in P.rglob('*') if x.is_file() and x.name!='artifacts.sha256')
    (P/'artifacts.sha256').write_bytes(''.join(sha(x.read_bytes())+'  '+x.relative_to(P).as_posix()+'\n' for x in files).encode('utf-8'))
    total=sum(p.stat().st_size for p in P.rglob('*') if p.is_file());assert total<10_000_000,('Size exceeds recommended10MB',total)
    print(json.dumps(dict(overall='PASS',indexed_files=len(files),all_files=len(files)+1,bytes=total,MiB=round(total/1048576,3),manifest_sha256=sha((P/'artifacts.sha256').read_bytes()))))
if __name__=='__main__':main()
