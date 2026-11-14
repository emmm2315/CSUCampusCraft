from pathlib import Path
from html.parser import HTMLParser
import ast,types,hashlib,re,json,zipfile,subprocess
here=Path(__file__).resolve().parent
tree=ast.parse((here/'verify_step06.py').read_text(encoding='utf-8'))
nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in ['Node','Parser','assert_page','snapshot','deltas','snapshot_pair']]
observed=[]
def check(name,ok,detail=''):
 assert ok,name
 observed.append(name)
ns={'HTMLParser':HTMLParser,'re':re,'PASSWORD':'unrelated-test-secret','check':check,'hashlib':hashlib,'TABLES':['a','b']}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<isolated helpers>','exec'),ns)
Parser=ns['Parser']
ns['assert_page']((303,{'Location':'/products/1/images'},b'',Parser('').root),303,'empty-303')
for status in [400,409]:
 body='<main data-page-id="A10"><p class="field-error">请修正字段</p></main>'
 ns['assert_page']((status,{'Content-Type':'text/html;charset=UTF-8'},body.encode(),Parser(body).root),status,'inline-'+str(status))
for sep in [b'\n',b'\r\n']:
 raw=b'1\tvalue'+sep+b'extra multiline text'+sep
 data=b'__STEP06_a__'+sep+b'1'+sep+raw+b'__STEP06_b__'+sep+b'0'+sep
 ns['sql']=lambda *a,**kw:types.SimpleNamespace(stdout=data)
 assert ns['snapshot']()=={'a':{'rows':1,'sha256':hashlib.sha256(raw).hexdigest()},'b':{'rows':0,'sha256':hashlib.sha256(b'').hexdigest()}}
observed+=['multiline-snapshot-lf-crlf']
records=[];ns['record']=lambda name,obj:records.append(obj)
s={'product':{'1':{'id':1,'version':0},'2':{'id':2,'version':0}},'product_image':{'1':{'id':1,'productId':1},'2':{'id':2,'productId':2}}}
ns['snapshot_pair']('reject',{},s,{},s,path='/products/1/images')
assert set(records[0]['target_before']['product'])=={'1'} and set(records[0]['target_before']['product_image'])=={'1'}
observed+=['target-raw-parent-and-image-scoping']
assert any(isinstance(n,ast.If) and ast.unparse(n.test)=="method == 'POST'" and 'snapshot_pair' in ast.unparse(n) for n in ast.walk(tree))
counts=[len(n.value.elts) for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='cases' for t in n.targets) and isinstance(n.value,ast.List)]
assert counts==[12],counts
out=here/'preflight-native';libs=out/'lib';libs.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile('D:/Github Projects/CSUCampusCraft/csucampuscraft-admin/target/csucampuscraft-admin-0.0.1-SNAPSHOT.jar') as z:
 for n in z.namelist():
  if n.startswith('BOOT-INF/lib/') and n.endswith('.jar'):(libs/Path(n).name).write_bytes(z.read(n))
cmd=['C:/Users/Starmetor/.jdks/ms-21.0.12.1/bin/javac.exe','-cp',str(libs/'*'),'-d',str(out),str(here/'AlbumWriteProbe.java')]
p=subprocess.run(cmd,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
assert p.returncode==0,p.stderr.decode(errors='replace')
observed+=['native-javac-preflight-no-framework','all-post-automatic-db-pair','12-browser-cases-24-screenshots']
(here/'preparation-selfcheck.json').write_text(json.dumps({'overall':'PASS','checks':observed,'planned_screenshots':24,'live_application_test':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('PREPARATION_PASS helpers, javac, 12 browser cases/24 screenshots; no live attempt created')
