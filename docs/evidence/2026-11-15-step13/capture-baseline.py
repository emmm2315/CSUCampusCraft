import hashlib,json,pathlib,subprocess,datetime
R=pathlib.Path('D:/Github Projects/CSUCampusCraft')
S=pathlib.Path('C:/Users/Starmetor/.codex/visualizations/2026/11/10/01a1c2de-c7a6-7290-8ee3-510d0f746abe/step13-acceptance')
def git(*args): return subprocess.check_output(['git','-c','core.quotepath=false',*args],cwd=R).decode('utf-8').strip()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
tracked=git('ls-files').splitlines()
inputs=[p for p in tracked if p.startswith(('csucampuscraft-user/src/','csucampuscraft-admin/src/','database/','assets/','.mvn/')) or p in ['mvnw','mvnw.cmd','csucampuscraft-user/pom.xml','csucampuscraft-admin/pom.xml']]
rows=[{'path':p,'sha256':sha(R/p),'bytes':(R/p).stat().st_size} for p in inputs]
b=json.dumps(rows,ensure_ascii=False,sort_keys=True,indent=2).encode('utf-8')
(S/'runtime-inputs.json').write_bytes(b)
(S/'runtime-inputs.sha256').write_text(''.join(f"{x['sha256']}  {x['path']}\n" for x in rows),encoding='utf-8',newline='\n')
old=[{'path':p,'sha256':sha(R/p),'bytes':(R/p).stat().st_size} for p in tracked if p.startswith('docs/evidence/')]
(S/'historical-evidence-baseline.json').write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
refs=git('show-ref').splitlines()
jars=[]
for module in ['user','admin']:
 p=R/f'csucampuscraft-{module}/target/csucampuscraft-{module}-0.0.1-SNAPSHOT.jar'
 jars.append({'module':module,'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size})
result={'recorded_at_utc':datetime.datetime.now(datetime.UTC).isoformat(),'tested_sha':git('rev-parse','HEAD'),'branch':git('branch','--show-current'),'initial_status':git('status','--porcelain=v1'),'main':git('rev-parse','main'),'refs':refs,'runtime_input_count':len(rows),'runtime_inputs_json_sha256':hashlib.sha256(b).hexdigest(),'historical_evidence_files':len(old),'historical_evidence_baseline_sha256':sha(S/'historical-evidence-baseline.json'),'jars':jars,'builds':{m:json.loads((S/f'build-{m}.json').read_text(encoding='utf-8-sig')) for m in ['user','admin']}}
(S/'source-and-artifacts.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ['refs','builds']},ensure_ascii=False))
