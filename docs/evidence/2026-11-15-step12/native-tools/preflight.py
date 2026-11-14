from pathlib import Path
import hashlib,json,subprocess,zipfile
H=Path(__file__).resolve().parent;D=H/'preflight2';D.mkdir(exist_ok=False)
CLASSES=D/'classes';LIB=D/'lib';OUT=D/'probe-classes'
for p in (CLASSES,LIB,OUT):p.mkdir()
JAR=Path('D:/Github Projects/CSUCampusCraft/csucampuscraft-admin/target/csucampuscraft-admin-0.0.1-SNAPSHOT.jar')
SOURCE=H/'NativeCustomerDashboardProbe.java';JAVA=Path('C:/Users/Starmetor/.jdks/ms-21.0.12.1/bin')
jar_sha=hashlib.sha256(JAR.read_bytes()).hexdigest();assert jar_sha=='d724fcca643a556f595c97adbd117667921b19d120221d27d2d5ee7d71c25b55'
with zipfile.ZipFile(JAR) as z:
 for name in z.namelist():
  if name.startswith('BOOT-INF/classes/') and not name.endswith('/'):
   relative=name[len('BOOT-INF/classes/'):];assert '..' not in Path(relative).parts
   target=CLASSES/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(name))
  elif name.startswith('BOOT-INF/lib/') and name.endswith('.jar'):(LIB/Path(name).name).write_bytes(z.read(name))
assert (CLASSES/'org/csucampuscraft/admin/customer/CustomerService.class').exists()
cp=str(CLASSES)+';'+str(LIB/'*')+';'+str(OUT)
compile=subprocess.run([str(JAVA/'javac.exe'),'--release','17','-cp',cp,'-d',str(OUT),str(SOURCE)],capture_output=True);(D/'compile.log').write_bytes(compile.stdout+compile.stderr)
metadata={'tested_code_sha':'03384367c87147f1c29859c799f3c464b016b760','compile_exit':compile.returncode,'jar_sha256':jar_sha,'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'application_started':False,'database_used':False,'scope':'Actual STEP12 admin JAR compile and actual MyBatis ParamMap structural check only'}
if compile.returncode==0:
 run=subprocess.run([str(JAVA/'java.exe'),'-cp',cp,'org.csucampuscraft.admin.customer.NativeCustomerDashboardProbe','--structural'],capture_output=True);(D/'structural.log').write_bytes(run.stdout+run.stderr);metadata['structural_exit']=run.returncode
 if run.returncode==0:
  result=json.loads(run.stdout.decode('utf-8').strip().splitlines()[-1]);metadata['structural_overall']=result['overall'];metadata['structural_checks']=result['checks'];metadata['structural_checks_passed']=result['checksPassed']
(D/'metadata.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8');print(json.dumps(metadata))
if compile.returncode:print((compile.stdout+compile.stderr).decode('utf-8',errors='replace'))
raise SystemExit(compile.returncode or metadata.get('structural_exit',1))
