from pathlib import Path
import subprocess,hashlib,json
ROOT=Path('D:/Github Projects/CSUCampusCraft');HERE=Path(__file__).resolve().parent
GIT='C:/Program Files/Git/cmd/git.exe';BASE='8dd7794e5b84fbc9a95069b76a74b761218e6d0a'
paths=['csucampuscraft-user','csucampuscraft-admin/pom.xml','csucampuscraft-admin/src/main/java','csucampuscraft-admin/src/main/resources/application.yml','database','.mvn','mvnw','mvnw.cmd','assets']
def git(*args):return subprocess.check_output([GIT,'-C',str(ROOT),'-c','core.quotepath=false',*args])
# Existing files only: new administrator order classes are permitted.
assert not git('diff','--diff-filter=DMRT','--name-only',BASE,'HEAD','--',*paths).strip()
rows=[]
for name in git('ls-tree','-r','--name-only',BASE,'--',*paths).decode('utf-8').splitlines():
    old=git('show',BASE+':'+name).replace(b'\r\n',b'\n')
    new=(ROOT/name).read_bytes().replace(b'\r\n',b'\n')
    assert old==new,name
    rows.append(dict(path=name,normalized_sha256=hashlib.sha256(new).hexdigest()))
report=dict(overall='PASS',baseline_sha=BASE,tested_code_sha=git('rev-parse','HEAD').decode().strip(),
            unchanged_paths=paths,files=rows,normalization='CRLF/LF only; No Git modifications/deletions to existing protected files; new admin classes excluded')
(HERE/'protected-source-preservation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(overall='PASS',protected_files=len(rows))))
