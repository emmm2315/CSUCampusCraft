from pathlib import Path
import hashlib, json, subprocess, difflib

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'docs/evidence/2026-11-15-review/integrity'
cases = [
    ('1aa6ad0c4a7546c5bfba7ed65ef05f5913132027','93f3c461163ff09f54b667299360068d450ca254','2026-11-14-step06'),
    ('39c96aaaad18c58dce9d57450e14317a75c29b3d','8dd7794e5b84fbc9a95069b76a74b761218e6d0a','2026-11-14-step11'),
    ('03384367c87147f1c29859c799f3c464b016b760','a899cce263526926292afec8ed55d6757aed0597','2026-11-15-step12'),
]
result=[]
def digest(b): return hashlib.sha256(b).hexdigest()
for source, baseline, name in cases:
    report=json.loads((OUT/(name+'.json')).read_text(encoding='utf-8'))
    for e in report['runtime_manifests'][-1]['entries']:
        if e['tested_git_blob_exact_match'] or e['tested_git_blob_crlf_reconstruction_match']: continue
        path=e['path']; expected=e['expected_sha256']
        new=subprocess.check_output(['git','-C',str(ROOT),'show',source+':'+path])
        old=subprocess.check_output(['git','-C',str(ROOT),'show',baseline+':'+path])
        lines=new.splitlines(keepends=True)
        same={j for block in difflib.SequenceMatcher(None,old.splitlines(keepends=True),lines,autojunk=False).get_matching_blocks() for j in range(block.b,block.b+block.size)}
        candidates=[]
        for unchanged_crlf in [False,True]:
            b=b''.join(x.removesuffix(b'\n').removesuffix(b'\r')+(b'\r\n' if (i in same)==unchanged_crlf else b'\n') for i,x in enumerate(lines))
            if digest(b)==expected: candidates.append({'method':'unchanged_vs_added_lines','unchanged_crlf':unchanged_crlf,'added_lines':[i+1 for i in range(len(lines)) if i not in same]})
        for split in range(len(lines)+1):
            for prefix_crlf in [False,True]:
                b=b''.join(x.removesuffix(b'\n').removesuffix(b'\r')+(b'\r\n' if (i<split)==prefix_crlf else b'\n') for i,x in enumerate(lines))
                if digest(b)==expected: candidates.append({'method':'prefix_suffix_line_endings','prefix_last_line':split,'prefix_crlf':prefix_crlf})
        result.append({'directory':name,'source':source,'comparison_base':baseline,'path':path,'expected_sha256':expected,'matches_by_newline_reconstruction':candidates})
(OUT/'newline-diagnostic.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
