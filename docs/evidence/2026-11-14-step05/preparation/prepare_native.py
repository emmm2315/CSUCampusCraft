from pathlib import Path
import zipfile,subprocess,json
base=Path(__file__).resolve().parent;out=base/'preparation-native';libs=out/'lib';libs.mkdir(parents=True,exist_ok=True)
jar=Path('D:/Github Projects/CSUCampusCraft/csucampuscraft-admin/target/csucampuscraft-admin-0.0.1-SNAPSHOT.jar')
with zipfile.ZipFile(jar) as z:
 for name in z.namelist():
  if name.startswith('BOOT-INF/lib/') and name.endswith('.jar'):(libs/Path(name).name).write_bytes(z.read(name))
argv=['C:/Users/Starmetor/.jdks/ms-21.0.12.1/bin/javac.exe','-encoding','UTF-8','-cp',str(libs/'*'),'-d',str(out),str(base/'ActorWriteProbe.java')]
p=subprocess.run(argv,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
(base/'preparation-native-compile.log').write_bytes(p.stdout+p.stderr)
(base/'preparation-native-compile.json').write_text(json.dumps({'exit_code':p.returncode,'argv':argv,'scope':'tools syntax/API compile against existing actual JAR dependencies only; not a live Service test'},indent=2),encoding='utf-8')
print('Native tool preparation compile exit='+str(p.returncode))
raise SystemExit(p.returncode)

