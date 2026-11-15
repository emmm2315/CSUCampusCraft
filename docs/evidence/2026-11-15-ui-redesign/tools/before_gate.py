from pathlib import Path
import hashlib,json
STAGE=Path(__file__).resolve().parent.parent
source=STAGE/'verification/evidence/attempt2/result.json'
r=json.loads(source.read_text(encoding='utf-8'))
assert r['phase']=='before' and r['checks_failed']==0
assert r['tested_sha']=='e2bdeb9df9cc7888383ef7afa28d5fbe94f29696'
assert r['screenshots']==92 and r['browser_navigation_count']==144
assert r.get('overall',r.get('result'))=='PASS',r.keys()
assert r['tracked_processes_stopped'] and r['runtime_inputs_stable']
gate={'result_path':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'tested_sha':r['tested_sha'],'screenshots':r['screenshots'],'browser_navigations':r['browser_navigation_count'],'root_verified_result':True,'agent_reported_owned_processes_stopped':True,'authorization':'Read-only before acceptance delivered by verification agent; permits publishing candidate UI only.'}
(STAGE/'verification/BEFORE_COMPLETE.json').write_text(json.dumps(gate,indent=2),encoding='utf-8')
print('BEFORE gate validated')
