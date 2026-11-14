from pathlib import Path
import gzip, hashlib, json, re

base = Path(__file__).resolve().parent
def read(p): return json.loads((base/p).read_text(encoding='utf-8'))
result = read('result.json')
assert result['overall'] == 'PASS' and result['attempt'] == 'attempt2'
assert all(v['passed'] for v in result['checks'].values())
assert read('attempt1/result.json')['overall'] == 'FAIL'
assert read('cleanup.json')['passed']
http = [json.loads(x) for x in (base/'attempt2/http.jsonl').read_text(encoding='utf-8').splitlines()]
writes = [json.loads(x) for x in (base/'attempt2/database-writes.jsonl').read_text(encoding='utf-8').splitlines()]
auto = [x for x in writes if x.get('automatic_all_posts')]
posts = {x['sequence'] for x in http if x['method'] == 'POST'}
assert len(auto) == len(posts) == result['http_posts'] == 71
assert {x['http_sequence'] for x in auto} == posts
album_changes = rejected = noops = 0
for w in auto:
    assert len(w['before']) == len(w['after']) == 7
    for table in ['store_user','category','cart_item','sales_order','sales_order_item']:
        assert w['before'][table] == w['after'][table], w['name']
    if w['status'] != 303:
        rejected += 1
        assert w['before'] == w['after'], w['name']
        assert not any(w['deltas'].values()), w['name']
    match = re.fullmatch(r'/products/(\d+)/images(?:/\d+(?:/remove)?)?', w['path'])
    if not match: continue
    pid = int(match[1])
    pd = w['deltas']['product']
    im = w['deltas']['product_image']
    for d in pd:
        assert int(d['id']) == pid, w['name']
        assert d['before'] and d['after'], w['name']
        for k in d['before']:
            if k not in ['version','updatedAt']:
                assert d['before'][k] == d['after'][k], (w['name'],k)
        assert d['after']['version'] == d['before']['version'] + 1, w['name']
    for d in im:
        for state in [d['before'],d['after']]:
            if state is not None: assert state['productId'] == pid, w['name']
    if im:
        album_changes += 1
        assert len(im) == len(pd) == 1 and w['status'] == 303, w['name']
    else:
        assert not pd, w['name']
        if w['status'] == 303:
            noops += 1
            assert w['before'] == w['after'], w['name']
for ref in read('artifact-references.json')['references']:
    data=(base/ref['canonical_path']).read_bytes()
    assert hashlib.sha256(data).hexdigest() == ref['sha256'] and len(data)==ref['bytes']
    name=Path(ref['original_path']).name
    old=next(x for x in read('attempt1/browser/result.json')['screenshots'] if x['path']==name)
    assert old['sha256'] == ref['sha256']
for ref in read('compressed-text-index.json'):
    data=gzip.decompress((base/ref['compressed_path']).read_bytes())
    assert hashlib.sha256(data).hexdigest()==ref['original_sha256'] and len(data)==ref['original_bytes']
report={
    'result':'PASS', 'reviewer':'independent Codex root; human review pending',
    'tested_sha':result['tested_code_sha'], 'http_records':len(http),
    'automatic_post_db_pairs':len(auto), 'rejected_posts_zero_write':rejected,
    'album_change_posts_single_target_single_bump':album_changes,
    'album_success_noop_posts':noops,
    'findings':[],
    'coverage':'Every POST linked to one seven-table audit; all rejected states unchanged; album deltas only request parent and its own image, one parent version increment per image mutation; other five tables unchanged; failed screenshot references and compressed commands retain exact bytes.',
    'limits':'No real concurrent requests or injected failure after DML; no claim that unexecuted input variants or future business modules passed.'
}
(base/'independent-observation-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
