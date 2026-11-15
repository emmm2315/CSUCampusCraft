"""Restore exact logical evidence into a NEW separate directory; uses only Python stdlib."""
from pathlib import Path
import argparse,gzip,lzma,json,hashlib,shutil
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    source=Path(__file__).resolve().parent;output=Path(args.output).resolve()
    if output.exists() or output.is_relative_to(source):raise SystemExit('Output must be a new directory outside this archive')
    shutil.copytree(source,output)
    mapping=json.loads((source/'archive-transforms.json').read_text(encoding='utf-8'))
    for row in mapping['lossless_transforms']:
        stored=(source/row['stored_path']).resolve();target=(output/row['logical_path']).resolve()
        if not stored.is_relative_to(source) or not target.is_relative_to(output):raise SystemExit('Unsafe mapping path')
        raw=stored.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=row['stored_sha256']:raise SystemExit('Stored-byte digest mismatch')
        raw=lzma.decompress(raw) if stored.suffix=='.xz' else gzip.decompress(raw)
        if hashlib.sha256(raw).hexdigest()!=row['logical_sha256']:raise SystemExit('Logical-byte digest mismatch')
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    print('Restored exact logical files; original archive remains unchanged:',output)
if __name__=='__main__':main()
