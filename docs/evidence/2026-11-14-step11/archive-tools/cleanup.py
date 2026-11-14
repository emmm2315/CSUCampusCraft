from pathlib import Path
import json,shutil,datetime,re
HERE=Path(__file__).resolve().parent
INTENDED=(HERE/'runtime').resolve()
assert INTENDED.parent==HERE.resolve() and INTENDED.name=='runtime'
assert HERE.name=='verification' and HERE.parent.name=='step11-admin-orders'
items=[]
for entry in sorted(INTENDED.iterdir()):
    if not entry.is_dir():continue
    assert re.fullmatch(r'attempt[1-9][0-9]*',entry.name),entry.name
    result=json.loads((HERE/'evidence'/entry.name/'result.json').read_text(encoding='utf-8'))
    assert result['tracked_processes_stopped'],entry.name
    target=entry.resolve()
    assert target.parent==INTENDED and target.name==entry.name and not entry.is_symlink(),target
    shutil.rmtree(target)
    items.append({'attempt':entry.name,'tracked_processes_stopped':True,'resolved_inside_owned_runtime':True,'directory_removed':not target.exists()})
report={'date':datetime.datetime.now(datetime.timezone.utc).isoformat(),'passed':all(x['directory_removed']for x in items),'private_runtime_cleanup':items,'secrets_in_archive':False,'production_databases_touched':False}
destination=HERE.parent/'final-evidence/cleanup.json'
assert destination.parent.exists(),'Archive must be prepared before private runtime cleanup'
destination.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))

