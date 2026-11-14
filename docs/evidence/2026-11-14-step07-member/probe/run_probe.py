"""Compile/run temporary Java probes against the real module classes and packaged dependencies."""
import datetime, hashlib, json, os, re, subprocess, sys, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
REPO=Path('D:/severlt/实验1/CSUCampusCraft')
TOOLCHAIN=json.loads((ROOT.parent/'toolchain.json').read_text(encoding='utf-8'))
JAVA=Path(TOOLCHAIN['java_home'])/'bin/java.exe'
JAVAC=Path(TOOLCHAIN['java_home'])/'bin/javac.exe'
CLASSES=ROOT/'classes'; CLASSES.mkdir(exist_ok=True)
LIB=ROOT/'lib'; LIB.mkdir(exist_ok=True)
JAR=REPO/'csucampuscraft-user/target/csucampuscraft-user-0.0.1-SNAPSHOT.jar'
with zipfile.ZipFile(JAR) as archive:
    for member in archive.namelist():
        if member.startswith('BOOT-INF/lib/') and member.endswith('.jar'):
            dest=LIB/Path(member).name
            if not dest.exists(): dest.write_bytes(archive.read(member))

mode=sys.argv[1] if len(sys.argv)>1 else 'ModelProbe'
source=ROOT/(mode+'.java')
run_env=os.environ.copy()
if mode=='ServiceProbe':
    manifest=Path(os.environ['STEP07_INSTANCE_MANIFEST']).resolve()
    runtime=(ROOT.parent/'runtime').resolve()
    if not manifest.is_relative_to(runtime): raise RuntimeError('Manifest must identify a STEP07 workspace-local instance')
    info=json.loads(manifest.read_text(encoding='utf-8'))
    credential_path=Path(info['credentials_private']).resolve()
    if not credential_path.is_relative_to(manifest.parent): raise RuntimeError('Credential file outside this temporary instance')
    private=json.loads(credential_path.read_text(encoding='utf-8'))
    run_env.update(private)
    run_env['STEP07_PROBE_PORT']=str(info['port'])
    run_env['STEP07_PROBE_SCHEMA']=info['schema']
cp=os.pathsep.join([str(CLASSES),str(REPO/'csucampuscraft-user/target/classes'),str(LIB/'*')])
sources=[str(source)]
if mode=='ModelProbe':
    # Use the amended source directly even when the application's next package build is pending.
    sources.append(str(REPO/'csucampuscraft-user/src/main/java/org/csucampuscraft/storefront/foundation/web/PageModelAdvice.java'))
compile_run=subprocess.run([str(JAVAC),'-encoding','UTF-8','-cp',cp,'-d',str(CLASSES),*sources],
                           capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=60,
                           creationflags=subprocess.CREATE_NO_WINDOW)
(ROOT/(mode+'-compile.log')).write_text(compile_run.stdout+compile_run.stderr,encoding='utf-8')
if compile_run.returncode:
    print(compile_run.stdout+compile_run.stderr);sys.exit(compile_run.returncode)
suffix='-readonly' if 'readonly' in sys.argv[2:] else ''
if mode=='ServiceProbe': suffix+='-'+manifest.parent.name
run=subprocess.run([str(JAVA),'-cp',cp,mode,*sys.argv[2:]],capture_output=True,text=True,encoding='utf-8',errors='replace',
                   env=run_env,timeout=150,creationflags=subprocess.CREATE_NO_WINDOW)
(ROOT/(mode+suffix+'-run.log')).write_text(run.stdout+run.stderr,encoding='utf-8')
record={'probe':mode,'arguments':sys.argv[2:],'exit_code':run.returncode,
        'passed_checks':sum(1 for line in run.stdout.splitlines() if line.startswith('PASS ')),
        'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'completed':run.returncode==0,
        'time':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()}
if mode=='ServiceProbe':
    record.update(database_version=info['version'],compatibility_only=info.get('compatibility_only'),
                  instance_uuid=info['uuid'],port=info['port'],schema=info['schema'])
(ROOT/(mode+suffix+'-result.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(run.stdout+run.stderr)
sys.exit(run.returncode)
