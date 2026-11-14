from pathlib import Path
import subprocess,hashlib,json
ROOT=Path('D:/Github Projects/CSUCampusCraft');HERE=Path(__file__).resolve().parent
GIT='C:/Program Files/Git/cmd/git.exe';BASE='dc2033da0ee52eb478999031c4f6838d6434d70b'
paths=['csucampuscraft-user/src/main/java/org/csucampuscraft/storefront/order','csucampuscraft-user/src/main/java/org/csucampuscraft/storefront/checkout','csucampuscraft-user/src/main/java/org/csucampuscraft/storefront/auth','csucampuscraft-admin','database','.mvn','mvnw','mvnw.cmd','assets']
def git(*args):return subprocess.check_output([GIT,'-C',str(ROOT),'-c','core.quotepath=false',*args])
assert not git('diff','--name-only',BASE,'HEAD','--',*paths).strip()
rows=[]
for name in git('ls-tree','-r','--name-only',BASE,'--',*paths).decode('utf-8').splitlines():
    old=git('show',BASE+':'+name).replace(b'\r\n',b'\n')
    new=(ROOT/name).read_bytes().replace(b'\r\n',b'\n')
    assert old==new,name
    rows.append(dict(path=name,normalized_sha256=hashlib.sha256(new).hexdigest()))
report=dict(overall='PASS',baseline_sha=BASE,tested_code_sha=git('rev-parse','HEAD').decode().strip(),
            unchanged_paths=paths,files=rows,normalization='CRLF/LF only; Git diff also empty for all protected paths')
(HERE/'step09-source-preservation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(overall='PASS',protected_files=len(rows))))
