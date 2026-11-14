"""Guarded STEP12 candidate publication and immutable-baseline checks."""
from pathlib import Path
import hashlib, json, subprocess, sys

ROOT = Path('D:/Github Projects/CSUCampusCraft')
HERE = Path(__file__).resolve().parent
GIT = 'C:/Program Files/Git/cmd/git.exe'
BASE = 'a899cce263526926292afec8ed55d6757aed0597'

def git(*args):
    p = subprocess.run([GIT, '-C', str(ROOT), '-c', 'core.quotepath=false', *args], capture_output=True, check=True)
    return p.stdout.decode('utf-8').strip()

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None

mode = sys.argv[1]
if mode == 'baseline':
    assert git('rev-parse', 'HEAD') == BASE
    assert git('branch', '--show-current') == 'feat/step12-admin-customers'
    assert not git('status', '--porcelain')
    refs = git('for-each-ref', '--format=%(refname) %(objectname)').splitlines()
    existing = {str(p.relative_to(ROOT)).replace('\\', '/'): digest(p)
                for p in (ROOT/'docs/evidence').rglob('*') if p.is_file()}
    record = dict(base=BASE, refs=refs, existing_evidence=existing)
    (HERE/'baseline.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(base=BASE, refs=len(refs), existing_evidence_files=len(existing))))
elif mode == 'publish-source':
    assert git('rev-parse', 'HEAD') == BASE
    assert git('branch', '--show-current') == 'feat/step12-admin-customers'
    publication = []
    paths = set()
    planned = []
    for group in ['backend', 'ui']:
        entries = json.loads((HERE/group/'manifest.json').read_text(encoding='utf-8-sig'))
        if isinstance(entries, dict): entries = entries['files']
        for entry in entries:
            name = entry.get('path', entry.get('relative_path'))
            assert name and name not in paths, name
            assert name.startswith('csucampuscraft-admin/src/'), name
            assert '..' not in Path(name).parts
            target, source = ROOT/name, HERE/group/name
            expected = entry.get('original_sha256', entry.get('old_sha256', entry.get('old_raw_sha256')))
            candidate_sha = entry.get('sha256', entry.get('new_sha256', entry.get('new_raw_sha256')))
            action = entry.get('action', 'write')
            assert action in {'write', 'delete'}, name
            if action == 'delete':
                assert name == 'csucampuscraft-admin/src/main/java/org/csucampuscraft/admin/web/HomeController.java' and candidate_sha is None and expected
            else:
                assert candidate_sha and digest(source) == candidate_sha, name
            # Permit only byte-identical partial publication after a tooling preflight failure.
            assert digest(target) in {expected, candidate_sha}, ('original drift', name)
            paths.add(name)
            planned.append((name, target, source, expected, action))
    changed = set(git('diff', '--name-only', BASE).splitlines())
    untracked = set(git('ls-files', '--others', '--exclude-standard').splitlines())
    assert (changed | untracked) <= paths, ('unexpected working tree paths', sorted((changed | untracked) - paths))
    for name, target, source, expected, action in planned:
            target.parent.mkdir(parents=True, exist_ok=True)
            if action == 'delete':
                if target.exists(): target.unlink()
            else:
                target.write_bytes(source.read_bytes())
            publication.append(dict(path=name, action=action, original_sha256=expected, sha256=digest(target)))
    (HERE/'source-publication.json').write_text(json.dumps(dict(files=publication), ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(published=len(paths), paths=sorted(paths)), ensure_ascii=False))
elif mode == 'verify-baseline':
    base = json.loads((HERE/'baseline.json').read_text(encoding='utf-8'))
    refs = git('for-each-ref', '--format=%(refname) %(objectname)').splitlines()
    before = {line.split()[0]: line.split()[1] for line in base['refs']}
    after = {line.split()[0]: line.split()[1] for line in refs}
    unchanged = {k: after.get(k) == v for k, v in before.items() if k != 'refs/heads/feat/step12-admin-customers'}
    assert all(unchanged.values()), unchanged
    drift = [name for name, sha in base['existing_evidence'].items() if digest(ROOT/name) != sha]
    assert not drift, drift
    forbidden = [x for x in git('diff', '--name-only', BASE).splitlines()
                 if not (x.startswith('csucampuscraft-admin/src/main/') or x in ['README.md', '.gitattributes', 'docs/开发计划与任务.md', 'docs/测试与验收用例.md', 'docs/页面清单与原型.md', 'docs/系统设计与路由.md'] or (x.startswith('docs/evidence/2026-11-14-step12/') or x.startswith('docs/evidence/2026-11-15-step12/')))]
    assert not forbidden, forbidden
    record = dict(old_refs_unchanged=unchanged, old_evidence_files_unchanged=len(base['existing_evidence']), forbidden_paths=forbidden, current_branch=git('branch', '--show-current'), main=git('rev-parse','main'))
    (HERE/'baseline-preservation.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(record, ensure_ascii=False))
else:
    raise SystemExit('Unknown mode')
