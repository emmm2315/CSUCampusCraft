from pathlib import Path
import hashlib,json,sys,zipfile
ROOT=Path('D:/Github Projects/CSUCampusCraft');STAGE=Path(__file__).resolve().parent.parent
def extract():
    result={}
    for app in ('user','admin'):
        jar=ROOT/f'csucampuscraft-{app}/target/csucampuscraft-{app}-0.0.1-SNAPSHOT.jar'
        with zipfile.ZipFile(jar) as z:
            result[app]={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.endswith('.class') or n.startswith('BOOT-INF/lib/') and not n.endswith('/')}
    return result
now=extract()
if sys.argv[1]=='before':
    path=STAGE/'baseline/jar-business-before.json';assert not path.exists()
    path.write_text(json.dumps(now,indent=2),encoding='utf-8')
    print(json.dumps({app:len(values) for app,values in now.items()}))
else:
    old=json.loads((STAGE/'baseline/jar-business-before.json').read_text())
    report={'overall':'PASS' if old==now else 'FAIL','apps':{app:{'original_entries':len(old[app]),'current_entries':len(now[app]),'missing_or_changed':[n for n,h in old[app].items() if now[app].get(n)!=h],'added':sorted(set(now[app])-set(old[app]))} for app in old}}
    (STAGE/'jar-business-preservation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report));assert old==now
