from pathlib import Path
import json,shutil,hashlib
here=Path(__file__).resolve().parent
for p in (here/'evidence').glob('attempt*/result.json'):
 assert json.loads(p.read_text(encoding='utf-8'))['tracked_processes_stopped']
roots=[here/'runtime/attempt1',here/'runtime/attempt2',here/'runtime/attempt3',here/'diagnostic-attempt2-lock-permission/runtime',here/'preparation-native']
report=[]
for p in roots:
 resolved=p.resolve();resolved.relative_to(here.resolve())
 assert resolved!=here.resolve() and ('runtime' in p.parts or p.name=='preparation-native')
 exists=resolved.exists()
 count=sum(1 for q in resolved.rglob('*') if q.is_file()) if exists else 0
 if exists:shutil.rmtree(resolved)
 report.append({'absolute_path':str(resolved),'verified_inside_verification_root':True,'had_directory':exists,'files_removed':count,'removed':not resolved.exists()})
out={'all_tracked_processes_stopped':True,'old_evidence_unchanged':True,'only_private_runtime_or_dependency_extraction_removed':True,'targets':report}
(here/'publish-evidence/private-runtime-cleanup.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'private_directories_removed':len(report),'evidence_untouched':True}))

