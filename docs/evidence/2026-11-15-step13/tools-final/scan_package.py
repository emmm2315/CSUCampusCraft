"""New stored-artifact scan; decompression preserves original bytes and no secret is printed."""
from pathlib import Path
import gzip,lzma,re,json,zipfile,datetime
S=Path(__file__).resolve().parent;P=S/'package';R=Path('D:/Github Projects/CSUCampusCraft')
def run():
    match=re.search(r'教学密码为\s*`([^`]+)`',(R/'README.md').read_text(encoding='utf-8'));credential=match[1]
    bcrypt=re.compile(rb'\$2[aby]\$\d\d\$[./A-Za-z0-9]{53}')
    findings=[];files=0;compressed=0;html_bodies=0;docx_parts=0
    for p in sorted(P.rglob('*')):
        if not p.is_file() or p.name=='sensitive-scan.json':continue
        if p.suffix=='.png':continue # Actual screenshot masking and visual observations are separate evidence.
        raw=p.read_bytes();files+=1
        if p.suffix=='.gz':raw=gzip.decompress(raw);compressed+=1
        elif p.suffix=='.xz':raw=lzma.decompress(raw);compressed+=1
        chunks=[raw]
        if p.suffix=='.docx':
            with zipfile.ZipFile(p) as z:chunks=[z.read(n) for n in z.namelist() if n.endswith('.xml')];docx_parts+=len(chunks)
        for chunk in chunks:
            if credential.encode('utf-8') in chunk:findings.append(dict(file=p.relative_to(P).as_posix(),kind='actual teaching credential'))
            if bcrypt.search(chunk):findings.append(dict(file=p.relative_to(P).as_posix(),kind='full encoded BCrypt value'))
        if '.html' in p.name:
            html_bodies+=1;text=raw.decode('utf-8',errors='replace')
            for tag in re.findall(r'<input\b[^>]*>',text,re.I):
                name=re.search(r'''\bname=["'](_csrf|confirmationToken|password|receiverName|receiverPhone|receiverAddress)["']''',tag,re.I)
                value=re.search(r'''\bvalue=["']([^"']*)["']''',tag,re.I)
                if name and value and value[1] not in ['', '[REDACTED]']:findings.append(dict(file=p.relative_to(P).as_posix(),kind='unmasked private input',field=name[1]))
            for value in re.findall(r'''<([a-z][a-z0-9]*)\b[^>]*\bdata-(?:shipping-value|customer-contact)(?:=["'][^"']*["'])?[^>]*>([\s\S]*?)</\1>''',text,re.I):
                if value[1] not in ['', '[REDACTED]', '[REDACTED-CONTACT]']:findings.append(dict(file=p.relative_to(P).as_posix(),kind='unmasked contact/shipping element'))
    result=dict(overall='PASS' if not findings else 'FAIL',observed_at_utc=datetime.datetime.now(datetime.UTC).isoformat(),files_scanned=files,compressed_files_decoded=compressed,html_bodies_checked=html_bodies,docx_xml_parts_checked=docx_parts,findings=findings,values_recorded=False,scope='Exact teaching credential, full BCrypt patterns, actual archived body token/password/contact/shipping elements; runtime child scans cover their generated known private values. PNG masking is checked in browser visual report.',historical_false_positive='Raw attempt4 scan FAIL is preserved: its own source template contained one fixed fictional test phone; archived HTTP/SQL recipient values were redacted. No complete recipient or real credential is accepted by this scan.')
    (P/'sensitive-scan.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False));assert not findings
if __name__=='__main__':run()
