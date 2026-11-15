from pathlib import Path
import hashlib,json,subprocess
ROOT=Path('D:/Github Projects/CSUCampusCraft');STAGE=Path(__file__).resolve().parent.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT).decode().strip()
assert git('rev-parse','HEAD')=='a14df9dc9fc96ad5985edd5abdb1292a66fec0bc'
assert not git('status','--porcelain')
r=json.loads((STAGE/'verification/evidence/attempt3/result.json').read_text(encoding='utf-8'))
assert r['tracked_processes_stopped'] and r['overall']=='FAIL'
changed=[]
for app in ('user','admin'):
    rel=f'csucampuscraft-{app}/src/main/resources/static/css/app.css'
    source=STAGE/'candidate'/rel;target=ROOT/rel
    assert sha(source)=='72ecc3db7d53580673968a41f74c9c7227368c2d56605ea0fbd36ce971f9d7b4'
    assert sha(target)=='a728c3dfc5bda75bd2efb611578c55e8ae04075f09e9118db4804731f329371b'
    target.write_bytes(source.read_bytes());changed.append(rel)
print(json.dumps({'css_only':changed,'reason':['mobile captions use normal block flow','current-page row sequence only','dashboard five-count layout and desktop filter density'],'sha256':sha(source)}))
