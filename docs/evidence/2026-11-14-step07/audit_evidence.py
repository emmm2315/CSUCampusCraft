from pathlib import Path
from html.parser import HTMLParser
import os,re,json,gzip,hashlib
here=Path(__file__).resolve().parent
base=Path(os.environ.get('STEP07_EVIDENCE_DIR',str(here/'publish-evidence')))
password=re.search(r'教学密码为\s*\x60([^\x60]+)\x60',Path('D:/Github Projects/CSUCampusCraft/README.md').read_text(encoding='utf-8')).group(1)
counts={'text_files':0,'gzip_bodies_decoded':0,'gzip_other_text_decoded':0,'http_records_verified':0,'csrf_values':0,'session_values':0,'cookie_headers':0,'bcrypt_values':0,'teaching_password_values':0}
findings=[]
class Inputs(HTMLParser):
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='input' and a.get('name')=='_csrf' and a.get('value') not in [None,'','[REDACTED]']:
   findings.append({'path':current,'kind':'csrf_value'});counts['csrf_values']+=1
for p in sorted(base.rglob('*')):
 if not p.is_file() or p.suffix.lower()=='.png':continue
 current=p.relative_to(base).as_posix()
 if p.name.endswith('.body.gz'):
  data=gzip.decompress(p.read_bytes());counts['gzip_bodies_decoded']+=1
 elif p.name.endswith('.gz'):
  data=gzip.decompress(p.read_bytes());counts['gzip_other_text_decoded']+=1
 else:data=p.read_bytes()
 text=data.decode('utf-8-sig',errors='replace');counts['text_files']+=1
 if p.name.endswith(('.body.gz','.body')):Inputs(convert_charrefs=True).feed(text)
 patterns={'session_values':r';CSUCAMPUSCRAFT_(?:USER|ADMIN)_SESSION=(?!\[REDACTED\])[A-Za-z0-9.-]{8,}','cookie_headers':r'(?im)^(?:Set-Cookie|Cookie):\s*(?!\[REDACTED\])[^\r\n]{8,}','bcrypt_values':r'\$2[aby]\$\d\d\$[./A-Za-z0-9]{53}'}
 for kind,pat in patterns.items():
  if re.search(pat,text):findings.append({'path':current,'kind':kind});counts[kind]+=1
 if password in text:findings.append({'path':current,'kind':'teaching_password_values'});counts['teaching_password_values']+=1
for index in base.rglob('http.jsonl'):
 for line in index.read_text(encoding='utf-8').splitlines():
  r=json.loads(line);p=index.parent/r['body_file'];data=gzip.decompress(p.read_bytes()) if r.get('body_encoding')=='gzip' else p.read_bytes()
  if r.get('redacted_body_sha256') and hashlib.sha256(data).hexdigest()!=r['redacted_body_sha256']:findings.append({'path':p.relative_to(base).as_posix(),'kind':'decompressed_http_sha_mismatch'})
  counts['http_records_verified']+=1
report={'passed':not findings,'scope':'all text plus every gzip-decompressed HTTP body, HTML CSRF values, actual cookie/session/BCrypt and known teaching secret; indexed decompressed SHA verified','counts':counts,'findings':findings}
packing=base/'compressed-text-index.json'
if packing.exists():
 for item in json.loads(packing.read_text(encoding='utf-8')):
  raw=gzip.decompress((base/item['compressed_path']).read_bytes())
  if len(raw)!=item['original_bytes'] or hashlib.sha256(raw).hexdigest()!=item['original_sha256']:findings.append({'path':item['compressed_path'],'kind':'decompressed_command_sha_mismatch'})
 report['passed']=not findings
(base/'sensitive-data-scan.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
entries=[{'path':p.relative_to(base).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(base.rglob('*')) if p.is_file() and p.name!='evidence-files.json']
(base/'evidence-files.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
if findings:raise SystemExit(1)


