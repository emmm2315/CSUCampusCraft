from pathlib import Path
import json,gzip,hashlib,shutil
here=Path(__file__).resolve().parent
out=here.parent/'final-evidence'
index=out/'compressed-text-index.json'
entries=json.loads(index.read_text(encoding='utf-8')) if index.exists() else []
for p in sorted([*out.glob('attempt*/commands.jsonl'),*out.glob('attempt*/database-writes.jsonl')]):
 raw=p.read_bytes();compressed=p.with_name(p.name+'.gz')
 compressed.write_bytes(gzip.compress(raw,mtime=0))
 entries.append({'original_path':p.relative_to(out).as_posix(),'compressed_path':compressed.relative_to(out).as_posix(),'original_bytes':len(raw),'original_sha256':hashlib.sha256(raw).hexdigest(),'original_stage_file_preserved':True})
 p.unlink()
index.write_text(json.dumps(entries,indent=2),encoding='utf-8',newline='\n')
for name in ['audit_evidence.py','cleanup.py','compress_commands.py']:shutil.copy2(here/name,out/name)
p=out/'README.md';text=p.read_text(encoding='utf-8')
text=text.replace('/database-writes.jsonl`','/database-writes.jsonl.gz`')
note='命令和逐请求数据库前后原始JSONL分别以 `attemptN/commands.jsonl.gz`、`attemptN/database-writes.jsonl.gz` 无损压缩归档；`compressed-text-index.json` 保存每份原字节数与解压后完整SHA，原stage文件未改、内容未删减，敏感/hash审计实际解压核对。'
if note not in text:text+='\n'+note+'\n'
p.write_text(text,encoding='utf-8',newline='\n')
print(json.dumps({'commands_compressed':len(entries),'final_bytes':sum(p.stat().st_size for p in out.rglob('*') if p.is_file())}))
