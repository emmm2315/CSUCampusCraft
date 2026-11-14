from pathlib import Path
import json,shutil,datetime
here=Path(__file__).resolve().parent
intended=(here/'runtime').resolve()
assert intended.parent==here.resolve() and intended.name=='runtime'
items=[]
for p in sorted(intended.iterdir()):
 if not p.is_dir():continue
 result=json.loads((here/'evidence'/p.name/'result.json').read_text(encoding='utf-8'))
 assert result['tracked_processes_stopped'],p.name
 resolved=p.resolve()
 assert resolved.parent==intended and resolved.name.startswith('attempt')
 shutil.rmtree(resolved)
 items.append({'attempt':p.name,'tracked_processes_stopped':True,'resolved_inside_owned_runtime':True,'directory_removed':not resolved.exists()})
report={'date':datetime.datetime.now(datetime.timezone.utc).isoformat(),'passed':all(x['directory_removed'] for x in items),'private_runtime_cleanup':items,'secrets_in_archive':False,'production_databases_touched':False}
(here.parent/'final-evidence/cleanup.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
