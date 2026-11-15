from pathlib import Path
import gzip,hashlib,json,shutil
STAGE=Path(__file__).resolve().parent.parent
OUT=STAGE/'delivery/evidence'
def sha(b):return hashlib.sha256(b).hexdigest()
OUT.mkdir(parents=True,exist_ok=True)
summary=[]
for source in sorted((STAGE/'verification/evidence').glob('attempt*')):
    if not source.is_dir():continue
    target=OUT/source.name
    assert not target.exists(), 'Never overwrite packed attempt'
    target.mkdir()
    mappings=[]
    for p in sorted(source.rglob('*')):
        if not p.is_file():continue
        assert not p.is_symlink(),p
        rel=p.relative_to(source).as_posix();raw=p.read_bytes()
        stored='source-artifacts.sha256' if rel=='artifacts.sha256' else rel
        compress=p.suffix=='.jsonl' and len(raw)>262144
        if compress:stored+='.gz'
        dest=target/stored;dest.parent.mkdir(parents=True,exist_ok=True)
        archive=gzip.compress(raw,compresslevel=9,mtime=0) if compress else raw
        dest.write_bytes(archive)
        decoded=gzip.decompress(dest.read_bytes()) if compress else dest.read_bytes()
        assert decoded==raw
        mappings.append({'source_path':rel,'stored_path':stored,'source_sha256':sha(raw),'stored_sha256':sha(archive),'source_bytes':len(raw),'stored_bytes':len(archive),'codec':'gzip' if compress else 'identity','source_byte_verification':'PASS'})
    original=source/'artifacts.sha256';verified=0
    if original.is_file():
        for line in original.read_text(encoding='utf-8-sig').splitlines():
            if not line.strip():continue
            expected,name=line.split(None,1);name=name.strip().lstrip('*').replace('\\','/')
            p=source/name
            assert p.resolve().is_relative_to(source.resolve()),name
            assert sha(p.read_bytes())==expected,(source.name,name,'Source manifest mismatch')
            verified+=1
    report={'archive_policy':'Archive copies only. Large JSONL uses lossless gzip with mtime=0. Source manifest is preserved verbatim as source-artifacts.sha256; logical source bytes are verified after decompression. artifacts.sha256 lists actual stored bytes. Original staging observations and all older repository evidence remain unchanged.','source_manifest_verified_files':verified,'source_files':len(mappings),'source_bytes':sum(x['source_bytes'] for x in mappings),'stored_payload_bytes':sum(x['stored_bytes'] for x in mappings),'mappings':mappings}
    (target/'packing.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (target/'source-byte-verification.json').write_text(json.dumps({'overall':'PASS','source_manifest_verified_files':verified,'lossless_files':len(mappings),'compressed_files':sum(x['codec']=='gzip' for x in mappings)},indent=2)+'\n',encoding='utf-8')
    lines=[sha(p.read_bytes())+'  '+p.relative_to(target).as_posix() for p in sorted(target.rglob('*')) if p.is_file() and p.name!='artifacts.sha256']
    (target/'artifacts.sha256').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    summary.append({k:v for k,v in report.items() if k not in ('mappings','archive_policy')}|{'attempt':source.name,'actual_stored_bytes':sum(p.stat().st_size for p in target.rglob('*') if p.is_file())})
(OUT/'packing-summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,indent=2))
