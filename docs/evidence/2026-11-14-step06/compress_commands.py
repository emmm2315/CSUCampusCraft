from pathlib import Path
import json,gzip,hashlib,shutil
here=Path(__file__).resolve().parent
out=here.parent/'final-evidence'
entries=[]
for p in sorted(out.glob('attempt*/commands.jsonl')):
 raw=p.read_bytes();compressed=p.with_name(p.name+'.gz')
 compressed.write_bytes(gzip.compress(raw,mtime=0))
 entries.append({'original_path':p.relative_to(out).as_posix(),'compressed_path':compressed.relative_to(out).as_posix(),'original_bytes':len(raw),'original_sha256':hashlib.sha256(raw).hexdigest(),'original_stage_file_preserved':True})
 p.unlink()
(out/'compressed-text-index.json').write_text(json.dumps(entries,indent=2),encoding='utf-8')
for name in ['audit_evidence.py','cleanup.py','compress_commands.py']:shutil.copy2(here/name,out/name)
p=out/'README.md';p.write_text(p.read_text(encoding='utf-8')+'\n命令原始JSONL以`attemptN/commands.jsonl.gz`无损压缩归档，`compressed-text-index.json`保存原字节数与解压后完整SHA，原stage命令文件未修改；敏感/hash审计同样解压检查。\n',encoding='utf-8')
print(json.dumps({'commands_compressed':len(entries),'final_bytes':sum(p.stat().st_size for p in out.rglob('*') if p.is_file())}))
