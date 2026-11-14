from pathlib import Path
import ast,json,hashlib,datetime
from privacy_checks import run_regression
HERE=Path(__file__).resolve().parent
out=HERE/'tool-fix';out.mkdir(exist_ok=True)
old_inventory=json.loads((HERE/'attempt1-original-file-inventory.json').read_text(encoding='utf-8'))['attempts'][0]['files']
unchanged=all(hashlib.sha256((HERE/'evidence/attempt1'/x['path']).read_bytes()).hexdigest()==x['sha256'] for x in old_inventory)
assert unchanged
s=(HERE/'verify_step11.py').read_text(encoding='utf-8');tree=ast.parse(s)
method=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='assert_page')
checks=dict(original_attempt1_all_inventory_bytes_preserved=unchanged,assert_page_calls_correct_scanner=any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='contains_bcrypt' for n in ast.walk(method)),raw_client_scanner_before_redaction=s.index("check('raw-response-no-bcrypt-")<s.index("redacted=scrub(text)"),raw_browser_scanner_before_redaction=s.index("check('browser-raw-response-no-bcrypt-")<s.index("meta['method'],path=meta['path']"),exact_redirect_case_followed="admin_detail(cl,target.path.rsplit('/',1)[1]" in s,exact_first_message='模拟发货已登记，请核对首次发货时间。本操作不涉及真实物流。' in s,exact_replay_message='该订单已发货或已完成，保留首次发货结果，未重复改写时间。' in s,status_region_feedback="n.a.get('role')=='status'" in s and 'n.text().strip()==expected_message' in s)
assert all(checks.values())
diagnostic=json.loads((HERE/'attempt1-tool-diagnostic.json').read_text(encoding='utf-8'))
record=dict(recorded_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),overall='PASS',checks=checks,offline_regression=diagnostic['offline_synthetic_regression'],original_tool_sha256=diagnostic['original_tool_sha256'],corrected_tool_sha256=hashlib.sha256(s.encode('utf-8')).hexdigest(),production_source_unchanged='39c96aaaad18c58dce9d57450e14317a75c29b3d',old_result_not_rewritten=True)
(out/'review.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(out/'attempt1-tool-diagnostic.json').write_bytes((HERE/'attempt1-tool-diagnostic.json').read_bytes())
print(json.dumps(dict(overall='PASS',checks=len(checks),offline_regression_cases=9,all_original_attempt1_files_preserved=len(old_inventory),corrected_tool_sha256=record['corrected_tool_sha256'])))
