from pathlib import Path
from html.parser import HTMLParser
import gzip,hashlib,json,re
STAGE=Path(__file__).resolve().parent.parent;OUT=STAGE/'delivery/evidence'
findings=[];texts=0;gz_count=0;hidden_values=0
safe={'','[REDACTED]','REDACTED','[MASKED]','[redacted]','<redacted>','***'}
class Inputs(HTMLParser):
    def handle_starttag(self,t,a):
        global hidden_values
        attrs=dict(a)
        if t=='input' and attrs.get('name') in ('_csrf','confirmationToken') and 'value' in attrs:
            hidden_values+=1;value=attrs.get('value','')
            if value not in safe and not value.startswith(('${','[redacted','[REDACTED')):findings.append({'file':current,'kind':'unredacted-hidden-token'})
for p in sorted(OUT.rglob('*')):
    if not p.is_file() or p.suffix.lower() in ('.png','.jpg','.jpeg','.ttf','.woff','.woff2'):continue
    raw=p.read_bytes();current=p.relative_to(OUT).as_posix()
    if p.suffix=='.gz':raw=gzip.decompress(raw);gz_count+=1
    try:text=raw.decode('utf-8-sig')
    except UnicodeDecodeError:continue
    texts+=1
    if re.search(r'\$2[aby]\$\d\d\$[./A-Za-z0-9]{53}',text):findings.append({'file':current,'kind':'bcrypt-hash'})
    for m in re.finditer(r'CSUCAMPUSCRAFT_(?:USER|ADMIN)_SESSION=([^\s;"<>\\]+)',text):
        if m.group(1) not in safe and not m.group(1).startswith(('[REDACTED','[redacted','[MASKED','<')):findings.append({'file':current,'kind':'session-value'})
    if p.name.endswith('.html.gz'):
        parser=Inputs(convert_charrefs=True);parser.feed(text)
attempt_scans=[]
for attempt in sorted(OUT.glob('attempt*')):
    p=attempt/'sensitive-scan.json'
    if p.exists():
        scan=json.loads(p.read_text(encoding='utf-8'));attempt_scans.append({'attempt':attempt.name,'overall':scan['overall'],'known_values_checked_in_original_scan':scan.get('known_values'),'raw_values_archived':scan.get('values_recorded')})
        assert scan['overall']=='PASS' and not scan.get('findings')
report={'overall':'PASS' if not findings else 'FAIL','text_files_scanned':texts,'gzip_files_decompressed':gz_count,'hidden_token_inputs_checked':hidden_values,'findings':findings,'original_known_value_scans':attempt_scans,'scope':'Final archived text/decompressed gzip structural scan; each original attempt already scanned known in-memory private values. Lossless packing preserves those sanitized original bytes. Screenshot receiver/login regions masked; no OCR/full privacy certification claimed.'}
(OUT/'sensitive-scan-final.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
assert not findings
lines=[]
for p in sorted(OUT.rglob('*')):
    if p.is_file() and p!=OUT/'artifacts.sha256':lines.append(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(OUT).as_posix())
(OUT/'artifacts.sha256').write_text('\n'.join(lines)+'\n',encoding='utf-8')
for line in lines:
    expected,name=line.split('  ',1);assert hashlib.sha256((OUT/name).read_bytes()).hexdigest()==expected
print(json.dumps({'artifact_files':len(lines),'all_raw_byte_hashes_verified':True,'archive_bytes':sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())}))
