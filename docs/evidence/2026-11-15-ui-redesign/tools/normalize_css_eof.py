from pathlib import Path
import hashlib,json
ROOT=Path('D:/Github Projects/CSUCampusCraft');STAGE=Path(__file__).resolve().parent.parent
records=[]
for app in ('user','admin'):
    rel=f'csucampuscraft-{app}/src/main/resources/static/css/app.css'
    for directory in (ROOT,STAGE/'candidate'):
        p=directory/rel;raw=p.read_bytes()
        assert hashlib.sha256(raw).hexdigest()=='72ecc3db7d53580673968a41f74c9c7227368c2d56605ea0fbd36ce971f9d7b4'
        updated=raw.rstrip(b'\r\n')+b'\n';p.write_bytes(updated)
        records.append({'path':str(p),'before_sha256':hashlib.sha256(raw).hexdigest(),'after_sha256':hashlib.sha256(updated).hexdigest(),'reason':'Remove added blank line at EOF only; no CSS rule/content change.'})
(STAGE/'css-eof-normalization.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print(records[0]['after_sha256'])
