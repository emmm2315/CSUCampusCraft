"""Read-only independent review quality scan. Never serializes known secrets.

Contact/recipient values and ephemeral DB passwords stay only in process memory.
"""
from pathlib import Path
from html.parser import HTMLParser
import datetime, hashlib, json, re, subprocess

ROOT = Path(__file__).resolve().parents[4]
REVIEW = ROOT / 'docs/evidence/2026-11-15-review'
OUT = REVIEW / 'integrity/review-quality.json'
CFG = Path('C:/Users/Starmetor/AppData/Local/Temp/review-connection.json')

def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def lines(p): return [json.loads(x) for x in p.read_text(encoding='utf-8-sig').splitlines() if x.strip()]
def sha(b): return hashlib.sha256(b).hexdigest()
def relative(p): return p.relative_to(REVIEW).as_posix()

class Inputs(HTMLParser):
    def __init__(self,s):
        super().__init__(convert_charrefs=True); self.inputs=[]; self.feed(s)
    def handle_starttag(self,t,a):
        if t=='input': self.inputs.append(dict(a))

def main():
    cfg = load(CFG)
    known = {}
    sql_commands = []
    for category, query in [
        ('contact', 'SELECT email,phone FROM store_user'),
        ('recipient', 'SELECT receiver_name,receiver_phone,receiver_address FROM sales_order'),
        ('BCrypt', 'SELECT password_hash FROM store_user'),
    ]:
        args=[cfg['mysql_exe'],'--defaults-extra-file='+cfg['root_defaults_file'],
              '--default-character-set=utf8mb4','--batch','--raw','--skip-column-names',
              '--database='+cfg['database'],'--execute',query]
        p=subprocess.run(args,capture_output=True)
        sql_commands.append({'argv':args,'exit_code':p.returncode,'raw_result_not_archived':True})
        if p.returncode: raise RuntimeError('Read-only private lookup failed, output withheld')
        for row in p.stdout.decode('utf-8').splitlines():
            for value in row.split('\t'):
                if value and value!='NULL': known.setdefault(category,set()).add(value)
    # Only password values are taken from transient private config; no config content is written.
    for p in [Path(cfg['root_defaults_file']), CFG,
              Path('C:/Users/Starmetor/AppData/Local/Temp/csucampuscraft-review-20261115-b53811e5a70e42d792037669ec7cad67/private-state.json')]:
        if not p.is_file(): continue
        if p.suffix=='.json':
            obj=load(p)
            def walk(x):
                if isinstance(x,dict):
                    for key,v in x.items():
                        if re.search('password|passwd|pwd',key,re.I) and isinstance(v,str) and v:
                            known.setdefault('ephemeral_password',set()).add(v)
                        elif isinstance(v,(dict,list)): walk(v)
                elif isinstance(x,list):
                    for v in x: walk(v)
            walk(obj)
        else:
            for line in p.read_text(encoding='utf-8-sig').splitlines():
                m=re.match(r'\s*password\s*=\s*(.*)',line,re.I)
                if m and m[1]: known.setdefault('ephemeral_password',set()).add(m[1].strip('"\''))
    # Test input constants intentionally remain in executable tools; captured responses and logs must redact them.
    captured_suffixes={'.html','.jsonl','.log','.tsv','.txt','.json'}
    known_findings=[]; patterns=[]; files_checked=[]
    for p in sorted(REVIEW.rglob('*')):
        if not p.is_file() or p==OUT or p.suffix not in captured_suffixes: continue
        if 'integrity' in p.relative_to(REVIEW).parts: continue
        text=p.read_text(encoding='utf-8-sig',errors='replace')
        files_checked.append(relative(p))
        for category,values in known.items():
            for value in values:
                if value in text:
                    # Values are never emitted, hashed, or embedded in snippets.
                    known_findings.append({'path':relative(p),'category':category,'value_length':len(value),
                                           'occurrences':text.count(value),
                                           'first_line':text[:text.index(value)].count('\n')+1})
        if p.suffix=='.html':
            for a in Inputs(text).inputs:
                name=a.get('name',''); value=a.get('value','')
                if name in ('_csrf','confirmationToken') and value not in ('','[REDACTED]'):
                    patterns.append({'path':relative(p),'kind':'unredacted '+name,'value_not_emitted':True})
                if name=='password' and value:
                    patterns.append({'path':relative(p),'kind':'nonempty password input','value_not_emitted':True})
            if re.search(r';jsessionid=(?!\[REDACTED\])[^\s"\'<>;]+',text,re.I):
                patterns.append({'path':relative(p),'kind':'URL session candidate','value_not_emitted':True})
            if re.search(r'\$2[aby]\$\d\d\$[./A-Za-z0-9]{53}',text):
                patterns.append({'path':relative(p),'kind':'BCrypt candidate','value_not_emitted':True})
    collections=[]
    for prefix in [REVIEW, REVIEW/'attempt1']:
        p=prefix/'http.jsonl'
        if not p.is_file(): continue
        records=lines(p); failures=[]
        for rec in records:
            body=prefix/rec['body']
            if not body.is_file() or sha(body.read_bytes())!=rec['body_sha256']:
                failures.append({'id':rec['id'],'kind':'missing or mismatched response body'})
            if rec['method']!='GET' and (rec.get('before') is None or rec.get('after') is None):
                failures.append({'id':rec['id'],'kind':'POST missing before/after'})
            for k,v in rec.get('request',{}).items():
                if k in ('password','_csrf','confirmationToken','receiverName','receiverPhone','receiverAddress') and v!='[REDACTED]':
                    failures.append({'id':rec['id'],'kind':'unredacted request field','field':k})
        ids=[x['id'] for x in records]
        collections.append({'scope':relative(prefix),'http_records':len(records),
                            'post_records':sum(x['method']!='GET' for x in records),
                            'unique_contiguous_ids':ids==list(range(1,len(ids)+1)),
                            'response_hash_and_before_after_failures':failures})
    checks=lines(REVIEW/'checks.jsonl')
    failed=[{k:v for k,v in x.items() if k in ('stage','name','detail')} for x in checks if not x['passed']]
    result={
        'audited_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
        'executor':'Codex AI independent read-only audit; human review pending',
        'scope':'Snapshot of current review files; parent may add supplemental evidence later',
        'read_only_private_lookups':sql_commands,
        'known_value_counts':{k:len(v) for k,v in known.items()},
        'known_short_recipient_values':sum(len(v)<3 for v in known.get('recipient',set())),
        'captured_text_files_scanned':len(files_checked),
        'known_value_findings_without_values':known_findings,
        'HTML_token_password_session_pattern_findings':patterns,
        'HTTP_collections':collections,
        'main_checks':len(checks),'main_failed_checks':failed,
        'script_sha256':{relative(p):sha(p.read_bytes()) for p in [REVIEW/'common.py',REVIEW/'run_review.py',REVIEW/'admin/admin_review.py']},
        'source_read_review':[
            {'id':'QA-01','severity':'P2','finding':'C initially submits the same placeholder cover as the original product. Original C note saying cover changed is too broad; parent notified and separate cover-change supplement requested.'},
            {'id':'QA-02','severity':'P2','finding':'E A10 ordering assertion collected repeated nested data-image-id markers. Original failure is retained; independent row-scoped supplement required, rather than replacing original result.'},
            {'id':'QA-03','severity':'P2','finding':'B original search HTTP checks only a no-result keyword; positive keyword and literal wildcard matching are not established by the original checks. Parent notified.'},
            {'id':'QA-04','severity':'scope','finding':'A does not inspect server session internals for checkout removal. HTTP relogin rejection cannot alone prove confirmation attribute removed before relogin. Existing A note correctly discloses this.'},
            {'id':'QA-05','severity':'scope','finding':'F covers full-database amounts/orphans/unique fields and representative time/null conditions. 35 CHECK metadata plus one negative-stock rejection is not exhaustive illegal-write testing; existing note correctly limits scope.'},
            {'id':'QA-06','severity':'scope','finding':'Only root new-evidence directory and .gitattributes may change. Runtime/old-evidence end-of-run protection audit remains parent finalization work.'},
        ],
        'human_and_unverified_scope_review':{
            'AI_executor_declared_in_stage_summaries':all('AI' in (REVIEW/f'stage-{s}.md').read_text(encoding='utf-8') for s in 'ABCDEF'),
            'checklist_explicitly_human_signature_pending':'尚待用户完成' in (REVIEW/'checklist.md').read_text(encoding='utf-8'),
            'concurrency_fault_injection_real_payment_logistics_performance_not_covered':True,
            'empty_dashboard_error_configuration_not_rerun':True,
            'restart_persistence_and_full_independent_member_reproduction_not_rerun':True,
        },
    }
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'files':len(files_checked),'known_findings':len(known_findings),
                      'pattern_findings':len(patterns),'HTTP_collections':collections,
                      'main_failed_check_count':len(failed)},ensure_ascii=False))

if __name__=='__main__': main()
