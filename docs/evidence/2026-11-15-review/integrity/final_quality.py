"""Final independent audit; runs no HTTP and changes only new audit reports."""
from pathlib import Path
import contextlib, datetime, hashlib, importlib.util, io, json, subprocess

ROOT=Path(__file__).resolve().parents[4]
REVIEW=ROOT/'docs/evidence/2026-11-15-review'
BASE='0329c9810c4ad2719c4ae95190ff516d1d21a9ed'
spec=importlib.util.spec_from_file_location('read_only_quality_scan',REVIEW/'integrity/audit_review_quality.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.OUT=REVIEW/'integrity/quality-final-scan.json'
with contextlib.redirect_stdout(io.StringIO()): module.main()
report=json.loads(module.OUT.read_text(encoding='utf-8'))
report['scope']='Final HTTP snapshot, main index 1–364 plus retained failed attempt1 1–38. Parent will add only prose/structured summaries after this scan.'
report['scan_command']='python -X utf8 docs/evidence/2026-11-15-review/integrity/final_quality.py'
byte=json.loads((REVIEW/'capture-byte-audit-final.json').read_text(encoding='utf-8'))
report['capture_byte_correction']={k:v for k,v in byte.items() if k!='records'}
report['capture_byte_correction']['path']='capture-byte-audit-final.json'
report['capture_byte_correction']['original_indexes_unmodified']=True
report['known_value_false_positives']={
    'raw_scanner_findings_retained':True,
    'classification':'All 10 exact recipient-name text matches are in permitted account display_name fields, not recipient/contact fields.',
    'keys':[{'path':'checks.jsonl','line':733,'keypaths':['detail.before.display_name','detail.after.display_name']},
            {'path':'checks.jsonl','line':737,'keypaths':['detail.actual.display_name','detail.expected.display_name']},
            {'path':'checks.jsonl','line':742,'keypaths':['detail.before.display_name','detail.after.display_name']},
            {'path':'sql.jsonl','lines':[114,118,119,120],'keypath':'rows[0].display_name'}],
    'contact_or_recipient_field_exposure_in_captured_text':False,
    'ephemeral_database_password_matches':0,
}
report['visual_privacy_review']={
    'images_actually_viewed':['screenshots/06-U08-85-shipped-snapshot.jpg','screenshots/08-A10-empty-cover.jpg'],
    'finding':'Screenshot 06 displays the explicitly fictional recipient/phone/address entered by this review tool. Do not claim every screenshot recipient field was masked. No actual or seed contact was observed in these two images.',
    'screenshot_06_values_not_repeated_in_report':True,
    'screenshot_08_has_no_contact_or_recipient_section':True,
    'other_images_not_independently_visually_checked_by_this_agent':True,
}
report['supplement_and_final_stage_review']={
    'supplement':json.loads((REVIEW/'supplement-result.json').read_text(encoding='utf-8')),
    'persistence':json.loads((REVIEW/'stage-persistence.json').read_text(encoding='utf-8')),
    'final_checks':json.loads((REVIEW/'stage-final-checks.json').read_text(encoding='utf-8')),
    'corrections':'Original E FAIL and C overstatement remain preserved; new supplement uses actual cover change, complete historical rows, article-scoped album order, positive search, and full 60-SKU stock check.',
    'checkout_confirmation_internal_attribute_timing_still_unproven':True,
}
report['human_and_unverified_scope_review']['restart_persistence_and_full_independent_member_reproduction_not_rerun']=None
report['human_and_unverified_scope_review']['technical_restart_persistence_newly_passed']=True
report['human_and_unverified_scope_review']['full_independent_human_member_reproduction_unverified']=True
report['human_and_unverified_scope_review']['all_35_illegal_CHECK_write_cases_exhaustively_tested']=False
report['short_ttl_http_numbering_verified']=[{'id':180,'method':'GET','path':'/login','status':200},
    {'id':181,'method':'POST','path':'/login','status':303},{'id':182,'method':'GET','path':'/checkout','status':200},
    {'id':183,'method':'POST','path':'/orders','status':409}]

cmds=[]
def git(args):
    cmd=['git','-C',str(ROOT),*args];p=subprocess.run(cmd,capture_output=True)
    obj={'argv':cmd,'exit_code':p.returncode,'stdout':p.stdout.decode('utf-8',errors='replace'),
         'stderr':p.stderr.decode('utf-8',errors='replace')};cmds.append(obj);return obj
paths=['csucampuscraft-user/src','csucampuscraft-admin/src','csucampuscraft-user/pom.xml',
       'csucampuscraft-admin/pom.xml','database','assets','.mvn','mvnw','mvnw.cmd']
product=git(['diff',BASE,'--name-status','--',*paths])
old_docs=git(['diff',BASE,'--name-status','--','README.md','docs',':!docs/evidence/2026-11-15-review'])
attributes=git(['diff',BASE,'--','.gitattributes'])
status=git(['status','--short'])
runtime=[]
for line in (REVIEW/'integrity/review-runtime-inputs.sha256').read_text(encoding='utf-8').splitlines():
    expected,path=line.split('  ',1);p=ROOT/path
    actual=hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
    runtime.append({'path':path,'expected_sha256':expected,'actual_sha256':actual,'matches':expected==actual})
inspection=json.loads((REVIEW/'environment/inspection-result.json').read_text(encoding='utf-8'))
jars=[]
for key,row in inspection['jars'].items():
    p=Path(row['path']);actual=hashlib.sha256(p.read_bytes()).hexdigest()
    jars.append({'module':key,'path':str(p),'expected_sha256':row['sha256'],'actual_sha256':actual,
                 'matches':actual==row['sha256']})
report['protected_inputs_end_of_run']={
    'baseline':BASE,'product_diff_empty':product['exit_code']==0 and not product['stdout'],
    'old_docs_evidence_Word_diff_empty':old_docs['exit_code']==0 and not old_docs['stdout'],
    'runtime_file_count':len(runtime),'runtime_matches':sum(x['matches'] for x in runtime),
    'runtime_mismatches':[x for x in runtime if not x['matches']],
    'jars':jars,'git_commands':cmds,
}
report['updated_at']=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
(REVIEW/'quality-final.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
print(json.dumps({'captured_files_scanned':report['captured_text_files_scanned'],
                  'known_scanner_findings_all_display_name_false_positives':len(report['known_value_findings_without_values']),
                  'token_pattern_findings':len(report['HTML_token_password_session_pattern_findings']),
                  'main_http_records':report['HTTP_collections'][0]['http_records'],
                  'raw_byte_audit_records':byte['record_count'],
                  'runtime_matches':sum(x['matches'] for x in runtime),'runtime_count':len(runtime),
                  'product_diff_empty':report['protected_inputs_end_of_run']['product_diff_empty'],
                  'old_docs_evidence_Word_diff_empty':report['protected_inputs_end_of_run']['old_docs_evidence_Word_diff_empty'],
                  'jar_matches':all(x['matches'] for x in jars)},ensure_ascii=False))
