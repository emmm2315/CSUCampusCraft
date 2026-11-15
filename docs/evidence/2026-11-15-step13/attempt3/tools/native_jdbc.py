"""Fresh STEP13 native Hikari observation, invoked by the new orchestrator with its private env."""
from pathlib import Path
import subprocess,zipfile,os,json

def run(h):
 s=Path(__file__).resolve().parents[1];native=s/'native';java=Path('C:/Users/Starmetor/.jdks/ms-21.0.12.1/bin')
 source=s/'verification/Step13JdbcContextProbe.java';copy=native/source.name;copy.write_text(source.read_text(encoding='utf-8-sig'),encoding='utf-8')
 libs=list((native/'lib').glob('*.jar'));cp=';'.join([str(native),*[str(x) for x in libs]])
 p=h.command([java/'javac.exe','-encoding','UTF-8','-cp',cp,'-d',native,copy]);h.check('native actual Hikari context probe compile',p.returncode==0)
 for module in ['user','admin']:
  classes=native/module/'classes';classes.mkdir(parents=True,exist_ok=True)
  with zipfile.ZipFile(h.repo/f'csucampuscraft-{module}/target/csucampuscraft-{module}-0.0.1-SNAPSHOT.jar') as z:
   for member in z.namelist():
    if member.startswith('BOOT-INF/classes/') and not member.endswith('/'):
     dest=classes/member[len('BOOT-INF/classes/'):];dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(member))
  p=h.command([java/'java.exe','-cp',str(classes)+';'+cp,'Step13JdbcContextProbe',module],env=h.app_env(),timeout=60)
  stdout=p.stdout.decode('utf-8',errors='replace');stderr=p.stderr.decode('utf-8',errors='replace')
  h.save('native-jdbc/'+module+'-stdout.log',stdout);h.save('native-jdbc/'+module+'-stderr.log',stderr)
  h.check('native actual Hikari context exit '+module,p.returncode==0)
  row=json.loads(next(x.split('STEP13_JDBC_CONTEXT ',1)[1] for x in stdout.splitlines() if x.startswith('STEP13_JDBC_CONTEXT ')))
  h.check('actual Hikari UTC UUID schema '+module,row['session_timezone']=='+00:00' and row['mysql_uuid']==h.result['mysql_uuid'] and row['mysql_port']==h.mysql_port and row['schema']==h.schema,row)
  h.save('native-jdbc/'+module+'.json',json.dumps(row,ensure_ascii=False,indent=2))
