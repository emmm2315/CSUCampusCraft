"""Supplemental byte index, preserving every original HTML and HTTP index byte."""
from pathlib import Path
import datetime, hashlib, json, sys

ROOT=Path(__file__).resolve().parents[4]
REVIEW=ROOT/'docs/evidence/2026-11-15-review'
output=REVIEW/(sys.argv[1] if len(sys.argv)>1 else 'capture-byte-audit.json')
records=[]
indexes=[]
for prefix in [REVIEW,REVIEW/'attempt1']:
    index=prefix/'http.jsonl'
    if not index.is_file(): continue
    data=index.read_bytes()
    rows=[json.loads(x) for x in data.decode('utf-8-sig').splitlines() if x.strip()]
    indexes.append({'path':index.relative_to(REVIEW).as_posix(),
                    'index_raw_sha256':hashlib.sha256(data).hexdigest(),
                    'records_in_snapshot':len(rows)})
    for row in rows:
        path=prefix/row['body']; raw=path.read_bytes()
        actual=hashlib.sha256(raw).hexdigest()
        reconstructed=hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest()
        declared=row['body_sha256']
        records.append({'scope':prefix.relative_to(REVIEW).as_posix(),'id':row['id'],
                        'stage':row['stage'],'method':row['method'],'label':row['label'],
                        'body':path.relative_to(REVIEW).as_posix(),
                        'raw_file_bytes':len(raw),'raw_file_sha256':actual,
                        'index_declared_body_sha256':declared,
                        'raw_file_matches_declared_index':actual==declared,
                        'reverse_one_crlf_conversion_sha256':reconstructed,
                        'reverse_one_crlf_matches_declared_index':reconstructed==declared,
                        'cr_cr_lf_sequences':raw.count(b'\r\r\n'),
                        'cr_lf_sequences':raw.count(b'\r\n'),
                        'covered_by_exact_or_reconstructed_match':actual==declared or reconstructed==declared})
result={'generated_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
        'executor':'Codex AI independent byte audit; not human sign-off',
        'problem':'Original common.py hashes safe.encode() before Windows write_text newline translation. Original body_sha256 identifies sanitized pre-write text bytes, not necessarily archived file bytes.',
        'correction':'This new index provides actual archived raw_file_sha256. Original HTML files and HTTP indexes are unmodified. Reverse-one-CRLF is an in-memory diagnostic, not a rewrite.',
        'scope':'Snapshot through the last record shown for each index. Later HTTP additions require a new incremental or final snapshot.',
        'indexes':indexes,'record_count':len(records),
        'raw_exact_matches':sum(x['raw_file_matches_declared_index'] for x in records),
        'raw_mismatches':sum(not x['raw_file_matches_declared_index'] for x in records),
        'all_records_exact_or_reverse_one_crlf_match':all(x['covered_by_exact_or_reconstructed_match'] for x in records),
        'records':records}
output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
print(json.dumps({k:result[k] for k in ['record_count','raw_exact_matches','raw_mismatches','all_records_exact_or_reverse_one_crlf_match']},ensure_ascii=False))
