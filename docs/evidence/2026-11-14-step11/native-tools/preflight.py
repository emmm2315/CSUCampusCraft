from pathlib import Path
import hashlib,json,subprocess,zipfile

HERE=Path(__file__).resolve().parent
DEST=HERE/'preflight1'
DEST.mkdir(exist_ok=False)
CLASSES=DEST/'classes';LIBS=DEST/'lib';OUTPUT=DEST/'probe-classes'
for target in (CLASSES,LIBS,OUTPUT):target.mkdir()
JAR=Path('D:/Github Projects/CSUCampusCraft/csucampuscraft-admin/target/csucampuscraft-admin-0.0.1-SNAPSHOT.jar')
SOURCE=HERE/'NativeAdminOrderProbe.java'
JAVA=Path('C:/Users/Starmetor/.jdks/ms-21.0.12.1/bin')
with zipfile.ZipFile(JAR) as archive:
    assert 'BOOT-INF/classes/org/csucampuscraft/admin/order/AdminOrderService.class' in archive.namelist()
    for entry in archive.namelist():
        if entry.startswith('BOOT-INF/classes/') and not entry.endswith('/'):
            relative=entry[len('BOOT-INF/classes/'):]
            assert '..' not in Path(relative).parts
            target=CLASSES/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(archive.read(entry))
        elif entry.startswith('BOOT-INF/lib/') and entry.endswith('.jar'):
            (LIBS/Path(entry).name).write_bytes(archive.read(entry))
cp=str(CLASSES)+';'+str(LIBS/'*')+';'+str(OUTPUT)
run=subprocess.run([str(JAVA/'javac.exe'),'--release','17','-cp',cp,'-d',str(OUTPUT),str(SOURCE)],capture_output=True)
(DEST/'compile.log').write_bytes(run.stdout+run.stderr)
metadata={'compile_exit':run.returncode,'jar_sha256':hashlib.sha256(JAR.read_bytes()).hexdigest(),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'application_started':False,'database_used':False,'scope':'Compile against actual STEP11 admin JAR, then actual MyBatis ParamMap structural regression only'}
if run.returncode==0:
    structural=subprocess.run([str(JAVA/'java.exe'),'-cp',cp,'org.csucampuscraft.admin.order.NativeAdminOrderProbe','--structural'],capture_output=True)
    (DEST/'structural.log').write_bytes(structural.stdout+structural.stderr)
    metadata['structural_exit']=structural.returncode
    if structural.returncode==0:
        check=json.loads(structural.stdout.decode('utf-8').strip().splitlines()[-1]);metadata['structural_checks']=check['checks'];metadata['structural_checks_passed']=check['checksPassed'];metadata['structural_overall']=check['overall']
(DEST/'metadata.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
print(json.dumps(metadata))
if run.returncode:print((run.stdout+run.stderr).decode('utf-8',errors='replace'))
raise SystemExit(run.returncode or metadata.get('structural_exit',1))
