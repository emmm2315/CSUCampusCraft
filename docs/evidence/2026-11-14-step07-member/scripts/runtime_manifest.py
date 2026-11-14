from pathlib import Path
import hashlib,json,subprocess,sys
repo=Path('D:/severlt/实验1/CSUCampusCraft')
paths=[]
for module in ('csucampuscraft-user','csucampuscraft-admin'):
    paths.extend(p for p in (repo/module/'src/main').rglob('*') if p.is_file())
    paths.append(repo/module/'pom.xml')
for directory in ('assets','database','.mvn'):
    paths.extend(p for p in (repo/directory).rglob('*') if p.is_file())
paths.extend([repo/'mvnw',repo/'mvnw.cmd'])
files={p.relative_to(repo).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths))}
manifest={'baseline_git_sha':subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip(),
          'source_state':'uncommitted STEP07 changes on feat/step07-cart; not a tested committed SHA',
          'files':files,'count':len(files),
          'inputs_digest':hashlib.sha256(json.dumps(files,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
          'jars':{m:hashlib.sha256((repo/m/'target'/(m+'-0.0.1-SNAPSHOT.jar')).read_bytes()).hexdigest() for m in ('csucampuscraft-user','csucampuscraft-admin')}}
target=Path(sys.argv[1]); target.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in manifest.items() if k!='files'},ensure_ascii=False))
