from pathlib import Path
from html.parser import HTMLParser
import json,re,hashlib,os
here=Path(__file__).resolve().parent
base=Path(os.environ.get('STEP04_EVIDENCE_DIR',here/'publish-evidence'))
findings=[];counts={'text_files':0,'http_bodies':0,'csrf_values':0,'session_values':0,'cookie_headers':0,'bcrypt_values':0,'teaching_password_values':0}
password=re.search(r'教学密码为\s*\x60([^\x60]+)\x60',Path('D:/Github Projects/CSUCampusCraft/README.md').read_text(encoding='utf-8')).group(1)
class Parse(HTMLParser):
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='input' and a.get('name')=='_csrf' and a.get('value') not in (None,'','[REDACTED]'):
   findings.append({'path':current,'kind':'csrf-value'});counts['csrf_values']+=1
for p in base.rglob('*'):
 if not p.is_file() or p.suffix=='.png':continue
 current=p.relative_to(base).as_posix();text=p.read_text(encoding='utf-8-sig',errors='replace');counts['text_files']+=1
 if p.suffix=='.body':counts['http_bodies']+=1;Parse(convert_charrefs=True).feed(text)
 patterns={'session_values':r';CSUCAMPUSCRAFT_(?:USER|ADMIN)_SESSION=(?!\[REDACTED\])[A-Za-z0-9.-]{8,}','cookie_headers':r'(?im)^(?:Set-Cookie|Cookie):\s*(?!\[REDACTED\])[^\r\n]{8,}','bcrypt_values':r'\$2[aby]\$\d\d\$[./A-Za-z0-9]{53}'}
 for kind,pattern in patterns.items():
  if re.search(pattern,text):counts[kind]+=1;findings.append({'path':current,'kind':kind})
 if password in text:counts['teaching_password_values']+=1;findings.append({'path':current,'kind':'teaching-password'})
report={'passed':not findings,'scope':'text/HTML token inputs/cookie/session/bcrypt plus known teaching secret; screenshots separately visually reviewed','counts':counts,'findings':findings}
(base/'sensitive-data-scan.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
entries=[{'path':p.relative_to(base).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(base.rglob('*')) if p.is_file() and p.name!='evidence-files.json']
(base/'evidence-files.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True))
if findings:raise SystemExit(1)

