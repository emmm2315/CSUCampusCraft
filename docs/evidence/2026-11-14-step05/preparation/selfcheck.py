from pathlib import Path
import ast,types,hashlib
from html.parser import HTMLParser
import re
base=Path(__file__).resolve().parent
tree=ast.parse((base/'verify_step05.py').read_text(encoding='utf-8'))
nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in ['Node','Parser','assert_page','snapshot']]
observed=[]
def check(name,ok,detail=''):
 assert ok,name
 observed.append(name)
ns={'HTMLParser':HTMLParser,'re':re,'PASSWORD':'unrelated-test-secret','check':check,'hashlib':hashlib,'TABLES':['a','b']}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<isolated prepared helpers>','exec'),ns)
Parser=ns['Parser'];assert_page=ns['assert_page']
assert_page((303,{'Location':'/products'},b'',Parser('').root),303,'empty-303')
for status in [400,409]:
 body='<main data-page-id="A05"><p class="field-error">请修正字段</p></main>'
 assert_page((status,{'Content-Type':'text/html;charset=UTF-8'},body.encode(),Parser(body).root),status,'inline-'+str(status))
for sep in [b'\n',b'\r\n']:
 raw_a=b'1\tvalue'+sep+b'extra multiline text'+sep
 raw_b=b''
 data=b'__STEP05_a__'+sep+b'1'+sep+raw_a+b'__STEP05_b__'+sep+b'0'+sep+raw_b
 ns['sql']=lambda *args,**kw:types.SimpleNamespace(stdout=data)
 snap=ns['snapshot']()
 assert snap=={'a':{'rows':1,'sha256':hashlib.sha256(raw_a).hexdigest()},'b':{'rows':0,'sha256':hashlib.sha256(raw_b).hexdigest()}}
observed+=['ordered-multiline-snapshot-lf','ordered-multiline-snapshot-crlf']
counts=[]
for node in ast.walk(tree):
 if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='cases' for t in node.targets) and isinstance(node.value,ast.List):counts.append(len(node.value.elts))
assert counts==[14],counts
(base/'preparation-selfcheck.json').write_text(__import__('json').dumps({'overall':'PASS','checks':observed,'browser_cases':counts[0],'planned_screenshots':28,'live_application_test':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('Preparation helpers PASS; 14 browser cases / 28 planned screenshots; no live attempt created')

