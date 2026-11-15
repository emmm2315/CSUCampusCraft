import pathlib,zipfile,subprocess,re,json,hashlib,datetime
S=pathlib.Path(__file__).resolve().parents[1]; R=pathlib.Path('D:/Github Projects/CSUCampusCraft');N=S/'native';N.mkdir(exist_ok=True)
JAVA=pathlib.Path('C:/Users/Starmetor/.jdks/ms-21.0.12.1/bin')
cp=[str(N)];members=[]
for mod,ns in [('user','storefront'),('admin','admin')]:
 jar=R/f'csucampuscraft-{mod}/target/csucampuscraft-{mod}-0.0.1-SNAPSHOT.jar'
 with zipfile.ZipFile(jar) as z:
  for name in z.namelist():
   if name.startswith('BOOT-INF/lib/') and name.endswith('.jar'):
    dest=N/'lib'/pathlib.Path(name).name; dest.parent.mkdir(exist_ok=True); data=z.read(name)
    if dest.exists(): assert dest.read_bytes()==data
    else:dest.write_bytes(data)
    if str(dest) not in cp:cp.append(str(dest))
   if name.endswith(f'org/csucampuscraft/{ns}/foundation/security/PasswordService.class'):
    dest=N/name[len('BOOT-INF/classes/'):];dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(name));members.append({'module':mod,'member':name,'sha256':hashlib.sha256(z.read(name)).hexdigest()})
source=S/'verification/Step13FoundationProbe.java'
# Strip UTF8 BOM for javac; keep source file unchanged and compile a task-local copy.
compile_source=N/source.name;compile_source.write_text(source.read_text(encoding='utf-8-sig'),encoding='utf-8')
classpath=';'.join(cp)
build=subprocess.run([str(JAVA/'javac.exe'),'-encoding','UTF-8','-cp',classpath,'-d',str(N),str(compile_source)],capture_output=True,text=True)
assert build.returncode==0,build.stderr
rules=(R/'docs/需求与业务规则.md').read_text(encoding='utf-8')
raw=re.search(r'种子教学口令仍为 `([^`]+)`',rules).group(1)
seed=(R/'database/02-schema-with-demo.sql').read_text(encoding='utf-8')
hashes=re.findall(r'\$2[aby]\$10\$[./A-Za-z0-9]{53}',seed)
assert len(hashes)==4
payload='\n'.join([raw,str(len(hashes)),*hashes])+'\n'
r=subprocess.run([str(JAVA/'java.exe'),'-cp',classpath,'Step13FoundationProbe'],input=payload,capture_output=True,text=True,encoding='utf-8')
assert all(secret not in r.stdout+r.stderr for secret in [raw,*hashes])
(N/'foundation-probe.stdout.jsonl').write_text(r.stdout,encoding='utf-8',newline='\n')
(N/'foundation-probe.stderr.log').write_text(r.stderr,encoding='utf-8',newline='\n')
result={'status':'PASS' if r.returncode==0 else 'FAIL','exit_code':r.returncode,'observed_at_utc':datetime.datetime.now(datetime.UTC).isoformat(),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'extracted_classes':members,'records':[json.loads(x) for x in r.stdout.splitlines()],'secret_values_archived':False}
(N/'foundation-probe.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False));assert r.returncode==0
