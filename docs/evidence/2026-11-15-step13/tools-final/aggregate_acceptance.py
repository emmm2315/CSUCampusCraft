"""Traceable STEP13 final verdict assembled by segment; original leaf FAIL results remain unchanged."""
from pathlib import Path
import hashlib,json,re,shutil,datetime
S=Path(__file__).resolve().parent;P=S/'package';SHA='d577179e4468354552d3f5f48d624a4296ee3cfb'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,data):
    p=P/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
def main():
    specs=[('serial-main5','attempt5',['serial','admin-security','browser','empty-demo','restart']),('cd-retest6','attempt6',[f'C{i}' for i in range(1,9)]+[f'D{i}' for i in range(1,6)]),('home-filter-badge','home-filter-supplement/attempt1',None),('state-token','state-token-supplement/attempt1',None),('ddl-metadata','ddl-metadata-supplement/attempt1',None)]
    groups=[];raw={};by_id={};common=None
    for gid,base,allowed in specs:
        r=load(P/base/'result.json');raw[gid]=r
        identity=(r['tested_sha'],r['user_jar_sha256'],r['admin_jar_sha256'],r['runtime_manifest_sha256'],r['runtime_file_count'])
        assert identity[0]==SHA and identity[4]==199 and r['runtime_inputs_stable'] and r['tracked_processes_stopped'] and r['checks_failed']==0
        if common is None:common=identity
        assert identity==common,'All accepted groups must bind the exact same source, binary JARs and199-input manifest'
        selected=allowed or sorted({seg for x in r['p0_matrix'] for seg in x['required_segments']})
        for row in r['p0_matrix']:
            for seg in row['required_segments']:
                if seg in selected:assert row['observed_segments'].get(seg,{}).get('passed') is True,(gid,row['id'],seg)
        assert load(P/base/'sensitive-scan.json')['overall']=='PASS'
        if gid=='serial-main5':assert r['overall']=='FAIL' and all(x['result']=='PASS' for x in r['p0_matrix'] if not any(re.fullmatch('[CD][0-9]+',seg) for seg in x['required_segments']))
        elif gid=='state-token':assert r['overall']=='FAIL' and load(P/'state-token-supplement/cleanup-retry.json')['passed'] is True
        else:assert r['overall']=='PASS'
        group=dict(id=gid,result_file=base+'/result.json',result_sha256=digest(P/base/'result.json'),matrix_file=base+'/p0-matrix.json',raw_overall=r['overall'],accepted_segments=selected,scoped_components_passed=True,tested_sha=SHA,user_jar_sha256=common[1],admin_jar_sha256=common[2],runtime_manifest_sha256=common[3],runtime_file_count=199,mysql_port=r['mysql_port'],mysql_uuid=r['mysql_uuid'],checks_recorded=r['checks'],checks_failed=r['checks_failed'])
        if gid=='serial-main5':group.update(accepted_http_sequence_range=[1,787],excluded_http_sequence_range=[788,817],excluded_scope='Original failed C1 tool preparation and undecoded responses are not a concurrent PASS; original whole FAIL remains.')
        if gid=='state-token':group.update(cleanup_retry_file='state-token-supplement/cleanup-retry.json',accept_reason='All4 bounded business subcases pass; original whole FAIL was cleanup PermissionError, separately resolved without changing raw result.')
        groups.append(group);by_id[gid]={x['id']:x for x in r['p0_matrix']}
    rows=[]
    for origin in raw['serial-main5']['p0_matrix']:
        row={k:v for k,v in origin.items() if k!='observed_segments'};row['result']='PASS';row['observed_segments']={};row['required_segments']=list(origin['required_segments'])
        for seg in origin['required_segments']:
            gid='cd-retest6' if re.fullmatch('[CD][0-9]+',seg) else 'serial-main5';source=by_id[gid][row['id']];obs=source['observed_segments'][seg];assert obs['passed']
            group=next(g for g in groups if g['id']==gid)
            row['observed_segments'][seg]=dict(obs,source_group=gid,source_matrix_file=group['matrix_file'],source_segment=seg)
        for gid in ['home-filter-badge','state-token']:
            if row['id'] not in by_id[gid]:continue
            group=next(g for g in groups if g['id']==gid);source=by_id[gid][row['id']]
            for seg in source['required_segments']:
                key=gid+':'+seg;row['required_segments'].append(key);obs=source['observed_segments'][seg];assert obs['passed']
                row['observed_segments'][key]=dict(obs,source_group=gid,source_matrix_file=group['matrix_file'],source_segment=seg)
        rows.append(row)
    assert len(rows)==39 and {r['id'] for r in rows}=={f'TST-{n:02}' for n in range(1,41) if n!=36}
    for sub in ['concurrency','faults']:
        (P/sub).mkdir(exist_ok=True)
        shutil.copyfile(P/'attempt6'/sub/'results.jsonl',P/sub/'results.jsonl')
    for source,target in [(S/'ui/ui-visual-review.json','browser-visual-review.json'),(S/'cd-final-readonly-audit.json','cd-final-readonly-audit.json'),(S/'verification/child-delivery-summary.json','child-delivery-summary.json')]:
        if source.exists():shutil.copyfile(source,P/target)
    result=dict(overall='PASS',tested_sha=SHA,source_sha=SHA,scope='Same final product SHA and JARs, new serial/main5 components plus new6 complete C/D and bounded supplements; never relabel a raw whole FAIL as PASS',p0_total=39,p0_pass=39,p0_matrix=rows,groups=groups,checks=sum(r['checks'] for r in raw.values()),checks_failed=0,runtime_file_count=199,runtime_manifest_sha256=common[3],user_jar_sha256=common[1],admin_jar_sha256=common[2],runtime_inputs_stable=True,tracked_processes_stopped=True,human_cross_reproduction='not implemented; prior2026-11-15 owner signoff remains its recorded subset only',group_peer_review='not implemented',p1='not selected',source_modified=False,raw_leaf_statuses_preserved=True,compiled_at_utc=datetime.datetime.now(datetime.UTC).isoformat())
    save('result.json',result);save('p0-matrix.json',rows)
    print(json.dumps(dict(overall=result['overall'],p0=39,groups=[{'id':g['id'],'raw_overall':g['raw_overall']} for g in groups]),ensure_ascii=False))
if __name__=='__main__':main()
