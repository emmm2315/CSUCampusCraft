"""Publish only reviewed docs/new evidence, then verify archived Git blob bytes."""
from pathlib import Path
import hashlib, json, shutil, subprocess, sys

HERE=Path(__file__).resolve().parent
ROOT=Path('D:/Github Projects/CSUCampusCraft')
EV=HERE/'final-evidence'
PREFIX='docs/evidence/2026-11-14-step11'
TARGET=ROOT/PREFIX
GIT='C:/Program Files/Git/cmd/git.exe'
SHA='39c96aaaad18c58dce9d57450e14317a75c29b3d'
def git(*args):
    p=subprocess.run([GIT,'-C',str(ROOT),'-c','core.quotepath=false',*args],capture_output=True,check=True)
    return p.stdout.decode('utf-8').strip()
def sha(data): return hashlib.sha256(data).hexdigest()
mode=sys.argv[1]
entries=json.loads((EV/'evidence-files.json').read_text(encoding='utf-8'))['files']
if mode=='publish':
    assert git('branch','--show-current')=='feat/step11-admin-orders'
    assert git('rev-parse','HEAD')==SHA
    assert not git('status','--porcelain'), 'Source tree drifted'
    assert git('rev-parse','main')=='8dd7794e5b84fbc9a95069b76a74b761218e6d0a'
    assert not TARGET.exists(), 'Never overwrite any existing evidence directory'
    assert TARGET.resolve().parent==(ROOT/'docs/evidence').resolve()
    assert json.loads((EV/'final-audit.json').read_text(encoding='utf-8'))['overall']=='PASS'
    documents=json.loads((HERE/'docs/manifest.json').read_text(encoding='utf-8'))['files']
    for item in documents:
        assert sha((ROOT/item['path']).read_bytes())==item['original_sha256'],item['path']
        assert sha((HERE/'docs'/item['path']).read_bytes())==item['sha256'],item['path']
    for item in entries:
        assert sha((EV/item['path']).read_bytes())==item['sha256'],item['path']
    attributes=ROOT/'.gitattributes'
    old=attributes.read_bytes()
    assert PREFIX.encode() not in old
    for item in documents:
        (ROOT/item['path']).write_bytes((HERE/'docs'/item['path']).read_bytes())
    attributes.write_bytes(old.rstrip()+b'\n\n# Preserve STEP11 archived observations and their recorded hashes.\n'+PREFIX.encode()+b'/** -text\n')
    shutil.copytree(EV,TARGET)
    assert all(sha((TARGET/x['path']).read_bytes())==x['sha256'] for x in entries)
    print(json.dumps(dict(published_documents=len(documents),new_evidence_files=len(entries)+1,old_evidence_overwritten=False)))
elif mode=='index':
    index={line.partition('\t')[2]:line.partition('\t')[0].split()[1]
           for line in git('ls-files','--stage','--',PREFIX).splitlines()}
    checked=[]
    for path in sorted(TARGET.rglob('*')):
        if not path.is_file():continue
        name=path.relative_to(ROOT).as_posix();data=path.read_bytes()
        blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        assert index.get(name)==blob,('Git raw blob differs',name)
        checked.append(dict(path=name,bytes=len(data),sha256=sha(data),git_blob=blob))
    assert len(checked)==len(index)==len(entries)+1
    (HERE/'published-git-blob-verification.json').write_text(json.dumps(dict(overall='PASS',files=checked),indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(overall='PASS',raw_git_blobs_verified=len(checked))))
else: raise SystemExit('Unknown mode')
