from pathlib import Path
from html.parser import HTMLParser
import ast, types, hashlib, re, json, zipfile, subprocess
here=Path(__file__).resolve().parent
tree=ast.parse((here/'verify_step07.py').read_text(encoding='utf-8'))
nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in ['Node','Parser','assert_page','snapshot','deltas','snapshot_pair']]
observed=[]
def check(name,ok,detail=''):
    assert ok,name
    observed.append(name)
ns={'HTMLParser':HTMLParser,'re':re,'PASSWORD':'unrelated-test-secret','check':check,'hashlib':hashlib,'TABLES':['a','b']}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<isolated helpers>','exec'),ns)
Parser=ns['Parser']
ns['assert_page']((303,{'Location':'/cart'},b'',Parser('').root),303,'empty-303')
for status in [400,409]:
    body='<main data-page-id="U05"><p class="field-error">请修正字段</p></main>'
    ns['assert_page']((status,{'Content-Type':'text/html;charset=UTF-8'},body.encode(),Parser(body).root),status,'inline-'+str(status))
for sep in [b'\n',b'\r\n']:
    raw=b'1\tvalue'+sep+b'extra multiline text'+sep
    data=b'__STEP07_a__'+sep+b'1'+sep+raw+b'__STEP07_b__'+sep+b'0'+sep
    ns['sql']=lambda *a,**kw:types.SimpleNamespace(stdout=data)
    assert ns['snapshot']()=={'a':{'rows':1,'sha256':hashlib.sha256(raw).hexdigest()},'b':{'rows':0,'sha256':hashlib.sha256(b'').hexdigest()}}
observed+=['multiline-seven-table-snapshot-lf-crlf']
records=[];ns['record']=lambda name,obj:records.append(obj)
s={'product':{'1':{'id':1,'version':0}},'cart_item':{'1':{'id':1,'userId':1,'quantity':2,'version':0}}}
ns['snapshot_pair']('reject',{},s,{},s,path='/cart/items')
assert records[0]['cart_before']==s['cart_item'] and records[0]['product_before']==s['product'] and all(not v for v in records[0]['deltas'].values())
observed+=['full-cart-and-current-product-state-preserved']
assert any(isinstance(n,ast.If) and ast.unparse(n.test)=="method == 'POST'" and 'snapshot_pair' in ast.unparse(n) for n in ast.walk(tree))
for n in ast.walk(tree):
    if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='read_text':assert any(x.arg=='encoding' for x in n.keywords)
browser=(here/'verify_browser.cjs').read_text(encoding='utf-8')
assert 'previous.checks' in browser and 'previous.screenshots' in browser
assert "tr[data-cart-item-id]" in browser and "#cart-quantity" in browser
runtime=Path('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies')
p=subprocess.run([runtime/'node/bin/node.exe','--check',here/'verify_browser.cjs'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
assert p.returncode==0,p.stderr.decode('utf-8',errors='replace')
out=here/'preflight-native';libs=out/'lib';libs.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile('D:/Github Projects/CSUCampusCraft/csucampuscraft-user/target/csucampuscraft-user-0.0.1-SNAPSHOT.jar') as z:
    assert 'BOOT-INF/classes/org/csucampuscraft/storefront/cart/CartService.class' in z.namelist()
    for n in z.namelist():
        if n.startswith('BOOT-INF/lib/') and n.endswith('.jar'):(libs/Path(n).name).write_bytes(z.read(n))
cmd=['C:/Users/Starmetor/.jdks/ms-21.0.12.1/bin/javac.exe','--release','17','-cp',str(libs/'*'),'-d',str(out),str(here/'CartWriteProbe.java')]
p=subprocess.run(cmd,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
assert p.returncode==0,p.stderr.decode('utf-8',errors='replace')
observed+=['native-javac-preflight-from-actual-user-JAR','every-post-automatic-db-pair','UTF8-all-read_text','browser-two-phase-append','row-selectors-not-form-markers','browser-js-syntax']
(here/'preparation-selfcheck.json').write_text(json.dumps({'overall':'PASS','checks':observed,'planned_screenshots':24,'live_application_test':False},ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
print('PREPARATION_PASS helpers, native compile, browser syntax, explicit UTF8; no live attempt created')
