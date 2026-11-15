"""Read-only verification; writes only this new closeout directory."""
from pathlib import Path
from collections import Counter
import datetime
import hashlib
import json
import re
import subprocess

ROOT = Path('D:/Github Projects/CSUCampusCraft')
OUT = ROOT / 'docs/evidence/2026-11-15-review/closeout/owner-review-docs'
BASE = 'd228a506a48b8eecf15c0a10c23a49249cf9188c'
MAIN = '0329c9810c4ad2719c4ae95190ff516d1d21a9ed'
commands, checks = [], []

def run(argv):
    p = subprocess.run(argv, cwd=ROOT, capture_output=True, encoding='utf-8')
    commands.append(dict(argv=argv, exit_code=p.returncode, stdout=p.stdout, stderr=p.stderr))
    return p

def check(name, ok, detail=None):
    checks.append(dict(name=name, passed=bool(ok), details=detail))

def blob(path):
    p = run(['git', 'show', BASE + ':' + path])
    assert p.returncode == 0
    return p.stdout

def paths(args):
    p = run(['git', '-c', 'core.quotepath=false', 'diff', '--name-only', '-z'] + args)
    assert p.returncode == 0
    return [s for s in p.stdout.split('\0') if s]

def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')

docs = ['README.md', 'docs/\u5f00\u53d1\u8ba1\u5212\u4e0e\u4efb\u52a1.md',
        'docs/\u6d4b\u8bd5\u4e0e\u9a8c\u6536\u7528\u4f8b.md',
        'docs/\u9875\u9762\u6e05\u5355\u4e0e\u539f\u578b.md',
        'docs/\u7cfb\u7edf\u8bbe\u8ba1\u4e0e\u8def\u7531.md']
old = {s: blob(s) for s in docs}
new = {s: (ROOT / s).read_text(encoding='utf-8') for s in docs}
hash_pattern = r'(?<![0-9a-f])(?:[0-9a-f]{64}|[0-9a-f]{40})(?![0-9a-f])'
for s in docs:
    a, b = Counter(re.findall(hash_pattern, old[s])), Counter(re.findall(hash_pattern, new[s]))
    check('all original SHA and digest occurrences retained: ' + s, a == b,
          dict(before=sum(a.values()), after=sum(b.values())))

ledger = docs[1]
def rows(text):
    return {line.split('|')[1].strip(): line.split('|') for line in text.splitlines()
            if re.match(r'\| STEP(?:0[2-9]|1[0-2]) \| \u8d1f\u8d23\u4eba', line)}
a, b = rows(old[ledger]), rows(new[ledger])
check('eleven ledger input and tested-SHA cells byte-for-text identical',
      len(a) == len(b) == 11 and all(a[k][5] == b[k][5] for k in a))
check('eleven ledger statuses and real owner/reviewer',
      len(b) == 11 and all('\u901a\u8fc7\uff082026-11-15 \u672c\u4eba\u590d\u6838' in v[4]
      and '\u8d1f\u8d23\u4eba\uff1a\u9ad8\u5b87\u5f18' in v[2]
      and '\u590d\u6838\u4eba\uff1a\u9ad8\u5b87\u5f18' in v[2] for v in b.values()))
step_order = lambda t: re.findall(r'^### STEP\d{2} .*$', t, re.M)
check('all fourteen step headings and order retained', step_order(old[ledger]) == step_order(new[ledger]))
guides = lambda t: [l for l in t.splitlines() if re.match(r'^(?:\d+\. |(?:\u4ea4\u4ed8|\u9000\u51fa\u6807\u51c6)\uff1a)', l)]
check('numbered operations and deliverable/exit lines unchanged',
      guides(old[ledger]) == guides(new[ledger]), dict(lines=len(guides(old[ledger]))))
test = docs[2]
stats = lambda t: re.findall(r'\d+\s*(?:\u9879|\u6761|\u6b21|\u7ec4|\u4efd|\u5f20|\u4e2a)', t[t.index('### STEP02'):t.index('### \u5546\u54c1\u4e0e\u767b\u5f55')])
check('STEP02-12 historical measurement count sequence unchanged', stats(old[test]) == stats(new[test]),
      dict(before=len(stats(old[test])), after=len(stats(new[test]))))
business = '### \u5546\u54c1\u4e0e\u767b\u5f55'
check('business TST tables including TST40 and STEP13 gates unchanged',
      old[test][old[test].index(business):] == new[test][new[test].index(business):])
links = lambda t: Counter(re.findall(r'\[[^\]]*\]\(([^)]+)\)', t))
check('all prior test-document links retained', not (links(old[test]) - links(new[test])))

product = paths([MAIN, '--', 'csucampuscraft-user', 'csucampuscraft-admin', 'database', 'assets',
                 'pom.xml', '.mvn', 'mvnw', 'mvnw.cmd'])
check('product SQL POM Wrapper and assets unchanged from main baseline', not product, product)
prior = paths([BASE, '--', 'docs/evidence',
               ':(exclude)docs/evidence/2026-11-15-review/closeout/owner-review-docs/**'])
check('all committed prior evidence and personal records unchanged', not prior, prior)
oldsteps = paths([MAIN, '--', 'docs/evidence', ':(exclude)docs/evidence/2026-11-15-review/**'])
check('old step evidence unchanged from main', not oldsteps, oldsteps)
untouched = paths([BASE, '--', '.gitattributes', 'docs/\u9879\u76ee\u7acb\u9879\u4e0e\u8303\u56f4.md',
                   'docs/\u9700\u6c42\u4e0e\u4e1a\u52a1\u89c4\u5219.md'])
check('attributes scope and requirements unchanged in this round', not untouched, untouched)
all_changed = paths([MAIN, '--'])
unexpected = [s for s in all_changed if not (s == 'README.md' or s == '.gitattributes' or s.startswith('docs/'))]
check('cumulative changed paths restricted to documentation and existing attributes rule', not unexpected, unexpected)
origin = run(['git', 'rev-parse', 'origin/main']).stdout.strip()
check('origin main unchanged', origin == MAIN, origin)
attrs = run(['git', 'diff', MAIN, '--', '.gitattributes']).stdout
check('existing attributes diff only three-line review protection rule',
      [l for l in attrs.splitlines() if l.startswith('+') and not l.startswith('+++')] ==
      ['+', '+# Preserve independent review evidence bytes.', '+docs/evidence/2026-11-15-review/** -text'])
whitespace = run(['git', 'diff', '--check', '--'] + docs)
check('current Markdown diff whitespace check', whitespace.returncode == 0)

# Full required searches. Store ASCII JSON so this index does not become a recursive search hit.
patterns = [
    '\u7ec4\u5458\u59d3\u540d\u5f85\u586b|\u7ec4\u5458\u590d\u6838\u5f85\u8865|\u5f85\u590d\u6838',
    '\u8d1f\u8d23\u4eba\uff1a<\u672c\u4eba\u59d3\u540d\u5f85\u586b>|\u590d\u6838\u4eba\uff1a<\u7ec4\u5458\u59d3\u540d\u5f85\u586b>'
]
searches = []
for pattern in patterns:
    plain = run(['rg', '-n', pattern, 'README.md', 'docs'])
    p = run(['rg', '--json', '-n', pattern, 'README.md', 'docs'])
    hits = []
    for raw in p.stdout.splitlines():
        row = json.loads(raw)
        if row.get('type') != 'match':
            continue
        data = row['data']
        path = data['path']['text'].replace('\\', '/')
        line = data['lines']['text'].rstrip('\r\n')
        in_old_archive = path.startswith('docs/evidence/') and '/owner-review-docs/' not in path
        annotated = '\u8be5\u53e5\u4e3a\u5f53\u65f6\u72b6\u6001\uff0c2026-11-15 \u5df2\u590d\u6838\u901a\u8fc7' in line
        if in_old_archive:
            category = 'historical-raw-evidence'
            explanation = 'Original snapshot preserved; subsequent owner signature and this closeout supersede the dated pending state.'
        elif '\u72b6\u6001\u679a\u4e3e' in line:
            category = 'template-status-enumeration'
            explanation = 'Available status vocabulary, explicitly not the current step state.'
        elif annotated:
            category = 'historical-current-doc-with-same-paragraph-date-note'
            explanation = 'Original handoff statement retained with explicit 2026-11-15 owner review note in the same paragraph.'
        elif '/owner-review-docs/' in path:
            category = 'verification-tool-or-metadata'
            explanation = 'New audit material, not a product completion claim.'
        else:
            category = 'UNEXPLAINED-CURRENT-STATE'
            explanation = 'Must resolve before commit.'
        hits.append(dict(path=path, line=data['line_number'], text=line,
                         phrases=[m['match']['text'] for m in data['submatches']],
                         category=category, same_paragraph_date_note=annotated,
                         original_annotation_present=annotated, explanation=explanation,
                         current_status_source='docs/evidence/2026-11-15-review/README.md#\u672c\u4eba\u6267\u884c\u8bb0\u5f552026-11-15 and owner-review-docs/README.md'))
    assert plain.returncode == p.returncode
    searches.append(dict(pattern=pattern, rg_exit_code=p.returncode, match_lines=len(hits),
                         by_category=dict(Counter(h['category'] for h in hits)), hits=hits))
check('all required full-search hits individually explained',
      all(h['category'] != 'UNEXPLAINED-CURRENT-STATE' for s in searches for h in s['hits']))
check('exact owner and reviewer placeholders have zero hits', searches[1]['match_lines'] == 0)
save('search-audit.json', dict(date='2026-11-15', note='Immutable historical evidence remains unchanged; each match is classified here.', searches=searches))
index_lines = [
    '# \u5168\u6587\u68c0\u7d22\u9010\u6761\u8bf4\u660e',
    '',
    '\u8be6\u7ec6\u547d\u4ee4\u3001\u539f\u6587\u548c\u547d\u4e2d\u77ed\u8bed\u4fdd\u5b58\u4e8e search-audit.json\u3002\u7cbe\u786e\u59d3\u540d\u5360\u4f4d\u68c0\u7d22\u4e3a 0\u3002',
    '',
    'D\uff1a\u5f53\u524d\u6587\u6863\u4fdd\u7559\u7684\u539f\u4ea4\u63a5\u53e5\uff0c\u540c\u6bb5\u5df2\u52a0\u201c\u8be5\u53e5\u4e3a\u5f53\u65f6\u72b6\u6001\uff0c2026-11-15 \u5df2\u590d\u6838\u901a\u8fc7\u201d\u6ce8\u91ca\u3002',
    '',
    'H\uff1a\u5386\u53f2\u539f\u8bc1\u636e/\u5de5\u5177\u5feb\u7167\uff0c\u539f\u6587\u6ca1\u6709\u540e\u7eed\u65e5\u671f\u6ce8\u91ca\uff1b\u4e3a\u4fdd\u62a4\u65e7\u8bc1\u636e\u4e0d\u6539\u5199\uff0c\u7531\u672c\u7d22\u5f15\u9010\u6761\u8865\u5145\u8bf4\u660e\u8bb0\u5f55\u65f6\u70b9\uff1b\u5f53\u524d\u72b6\u6001\u4ee5 2026-11-15 \u9ad8\u5b87\u5f18\u672c\u4eba\u7b7e\u7f72\u548c\u672c\u8f6e\u6536\u53e3\u4e3a\u51c6\u3002',
    '',
    'T\uff1a\u72b6\u6001\u8bcd\u6c47\u679a\u4e3e\uff0c\u5df2\u660e\u786e\u4e0d\u662f\u5f53\u524d\u6b65\u9aa4\u72b6\u6001\u3002',
    '',
    '| # | \u6587\u4ef6 | \u884c | \u9010\u6761\u8bf4\u660e |',
    '|---|---|---|---|'
]
codes = {'historical-raw-evidence': 'H',
         'historical-current-doc-with-same-paragraph-date-note': 'D',
         'template-status-enumeration': 'T'}
for i, h in enumerate(searches[0]['hits'], 1):
    index_lines.append(f"| {i} | {h['path']} | {h['line']} | {codes.get(h['category'], h['category'])} |")
(OUT / 'search-audit.md').write_text('\n'.join(index_lines) + '\n', encoding='utf-8')

word_path = ROOT / 'docs/\u5b9e\u9a8c\u4e00 CSUCampusCraft \u6821\u56ed\u6587\u521b\u5546\u5e97\u5b9e\u9a8c\u6307\u5bfc\u4e66.docx'
word = json.loads((OUT / 'word/word-update-validation.json').read_text(encoding='utf-8-sig'))
check('Word actual digest equals validated final document',
      hashlib.sha256(word_path.read_bytes()).hexdigest() == word['after_sha256'], word['after_sha256'])
check('Word structure and all non-document members preserved',
      word['formatting_xml_skeleton_unchanged'] and word['all_other_package_members_byte_identical']
      and word['table_xml_byte_identical'] and word['all_xml_and_relationships_parse']
      and word['zip_test'] == 'PASS' and word['python_docx_reopen'] == 'PASS'
      and word['STEP01_through_STEP14_present'])
check('Word render and full-page visual validation completed', word['status'] == 'PASS', word['status'])
result = dict(captured_at=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
              baseline=BASE, main_before=MAIN, scope='Documentation closeout only; no new product tests or STEP13 verdict.',
              result='PASS' if all(c['passed'] for c in checks) else 'FAIL',
              checks=checks, searches_summary=[{k:v for k,v in s.items() if k != 'hits'} for s in searches],
              commands=commands)
save('validation.json', result)
print(json.dumps(dict(result=result['result'], checks=len(checks),
                     failed=[c['name'] for c in checks if not c['passed']],
                     searches=result['searches_summary']), ensure_ascii=False, indent=2))
raise SystemExit(0 if result['result'] == 'PASS' else 1)
