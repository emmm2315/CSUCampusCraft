"""Read-only evidence audit; all output stays in the new review directory.

Historical result labels are inventory metadata, never a current test verdict.
"""
from pathlib import Path
import datetime, hashlib, json, re, subprocess

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'docs/evidence/2026-11-15-review'
BASE = '0329c9810c4ad2719c4ae95190ff516d1d21a9ed'
COMMANDS = []

def rel(p):
    return p.relative_to(ROOT).as_posix()

def sha(b):
    return hashlib.sha256(b).hexdigest()

def read_json(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))

def git(*args):
    p = subprocess.run(['git', '-C', str(ROOT), *args], capture_output=True)
    COMMANDS.append({'argv': ['git', '-C', str(ROOT), *args], 'exit_code': p.returncode,
                     'stdout': p.stdout.decode('utf-8', errors='replace'),
                     'stderr': p.stderr.decode('utf-8', errors='replace')})
    return p

def write(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

BLOBS = {}
NEWLINES = {}
def blobs(requests):
    missing = sorted(set(requests) - BLOBS.keys())
    if not missing:
        return
    p = subprocess.run(['git', '-C', str(ROOT), 'cat-file', '--batch'],
                       input=('\n'.join(missing) + '\n').encode(), capture_output=True)
    COMMANDS.append({'argv': ['git', '-C', str(ROOT), 'cat-file', '--batch'],
                     'input_objects': missing, 'exit_code': p.returncode,
                     'stderr': p.stderr.decode('utf-8', errors='replace')})
    pos = 0
    for req in missing:
        end = p.stdout.index(b'\n', pos)
        header = p.stdout[pos:end].decode()
        pos = end + 1
        if header.endswith(' missing'):
            BLOBS[req] = None
        else:
            size = int(header.rsplit(' ', 1)[1])
            BLOBS[req] = p.stdout[pos:pos + size]
            pos += size + 1

def read_manifest(p):
    result = []
    for line_no, line in enumerate(p.read_text(encoding='utf-8-sig').splitlines(), 1):
        m = re.fullmatch(r'([0-9a-fA-F]{64})\s+\*?(.+)', line)
        if not m:
            raise ValueError(f'{p}:{line_no}: bad manifest format')
        result.append({'path': m[2].replace('\\', '/'), 'expected_sha256': m[1].lower()})
    return result

def source_of(o):
    for key in ('tested_code_sha', 'source_sha', 'tested_source_sha'):
        v = o.get(key)
        if isinstance(v, str) and re.fullmatch('[a-f0-9]{40}', v):
            return v
    return None

def check_entries(entries, source):
    blobs([f'{s}:{e["path"]}' for e in entries for s in (source, BASE) if s])
    checked = []
    for e in entries:
        path, expected = e['path'], e['expected_sha256']
        item = dict(e)
        b = BLOBS.get(f'{source}:{path}') if source else None
        item['tested_git_blob_sha256'] = sha(b) if b is not None else None
        item['tested_git_blob_exact_match'] = b is not None and sha(b) == expected
        crlf = b.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n') if b is not None else None
        item['tested_git_blob_crlf_reconstruction_match'] = crlf is not None and sha(crlf) == expected
        diagnostic = NEWLINES.get((source, path, expected))
        mixed_match = False
        if diagnostic and b is not None:
            lines = b.splitlines(keepends=True)
            for candidate in diagnostic['matches_by_newline_reconstruction']:
                if candidate['method'] != 'prefix_suffix_line_endings': continue
                split = candidate['prefix_last_line']
                prefix_crlf = candidate['prefix_crlf']
                rebuilt = b''.join(x.removesuffix(b'\n').removesuffix(b'\r') +
                                   (b'\r\n' if (i < split) == prefix_crlf else b'\n')
                                   for i, x in enumerate(lines))
                if sha(rebuilt) == expected:
                    mixed_match = True
                    item['mixed_newline_reconstruction'] = candidate
                    break
        item['tested_git_blob_mixed_newline_reconstruction_match'] = mixed_match
        item['tested_source_verified_by_hash_allowing_only_line_endings'] = item['tested_git_blob_exact_match'] or item['tested_git_blob_crlf_reconstruction_match'] or mixed_match
        current = BLOBS.get(f'{BASE}:{path}')
        item['baseline_git_blob_sha256'] = sha(current) if current is not None else None
        disk = ROOT / path
        item['worktree_sha256'] = sha(disk.read_bytes()) if disk.is_file() else None
        item['worktree_exact_match'] = item['worktree_sha256'] == expected
        checked.append(item)
    return {'file_count': len(checked),
            'tested_git_blob_exact_matches': sum(x['tested_git_blob_exact_match'] for x in checked),
            'tested_git_blob_exact_or_crlf_matches': sum(x['tested_git_blob_exact_match'] or x['tested_git_blob_crlf_reconstruction_match'] for x in checked),
            'tested_source_hash_matches_allowing_only_line_endings': sum(x['tested_source_verified_by_hash_allowing_only_line_endings'] for x in checked),
            'worktree_exact_matches': sum(x['worktree_exact_match'] for x in checked),
            'entries': checked}

def archive_index(d, p):
    o = read_json(p)
    if isinstance(o, dict) and 'files' in o:
        rows = o['files']
    elif isinstance(o, dict):
        rows = [dict(v, path=k) for k, v in o.items()]
    else:
        rows = o
    records = []
    for row in rows:
        if 'destination_path' in row:
            target = ROOT / row['destination_path']
        else:
            target = d / row['path']
        b = target.read_bytes() if target.is_file() else None
        records.append({'path': rel(target), 'exists': b is not None,
                        'expected_sha256': row['sha256'], 'actual_sha256': sha(b) if b is not None else None,
                        'expected_bytes': row.get('bytes'), 'actual_bytes': len(b) if b is not None else None,
                        'matches': b is not None and sha(b) == row['sha256'] and (row.get('bytes') is None or len(b) == row['bytes'])})
    return {'index': rel(p), 'count': len(records), 'matches': sum(x['matches'] for x in records),
            'mismatches': [x for x in records if not x['matches']], 'files': records}

def main():
    diagnostic = OUT / 'integrity/newline-diagnostic.json'
    if diagnostic.is_file():
        NEWLINES.update({(x['source'], x['path'], x['expected_sha256']): x for x in read_json(diagnostic)})
    baseline = {'sha': git('rev-parse', 'HEAD').stdout.decode().strip(),
                'branch': git('branch', '--show-current').stdout.decode().strip(),
                'status': git('status', '--short').stdout.decode(),
                'core_autocrlf': git('config', '--get', 'core.autocrlf').stdout.decode().strip()}
    dirs = sorted(d for d in (ROOT / 'docs/evidence').iterdir() if d.is_dir() and re.search(r'-step\d\d(?:-|$)', d.name))
    reports = []
    for d in dirs:
        print('Auditing', d.name, flush=True)
        result_file = d / 'result.json'
        o = read_json(result_file) if result_file.exists() else {}
        source = source_of(o)
        member = d.name.endswith('step07-member')
        if member:
            source = read_json(d / 'publication.json')['code_commit']
        r = {'directory': rel(d), 'README_exists': (d / 'README.md').is_file(),
             'top_result_exists': result_file.is_file(),
             'top_result_keys': list(o), 'tested_code_sha': source,
             'original_test_identity': 'uncommitted worktree; code_commit is later publication linkage' if member else 'result metadata SHA',
             'result_sha256': sha(result_file.read_bytes()) if result_file.is_file() else None,
             'runtime_manifests': [], 'attempt_inventory': [], 'archive_indexes': []}
        # Runtime manifests from every archived attempt, with nearest local SHA.
        for manifest in sorted(d.rglob('runtime-inputs.sha256')):
            local_result = manifest.parent / 'result.json'
            local = read_json(local_result) if local_result.is_file() else o
            local_source = source_of(local) or source
            entries = read_manifest(manifest)
            check = check_entries(entries, local_source)
            expected_manifest = local.get('runtime_manifest_sha256')
            check.update({'manifest': rel(manifest), 'manifest_sha256': sha(manifest.read_bytes()),
                          'declared_manifest_sha256': expected_manifest,
                          'manifest_digest_matches_if_declared': sha(manifest.read_bytes()) == expected_manifest if expected_manifest else None,
                          'tested_code_sha': local_source,
                          'declared_file_count': local.get('runtime_file_count')})
            r['runtime_manifests'].append(check)
        if member:
            before, after = (read_json(d / f'runtime-inputs-{n}.json') for n in ('before', 'after'))
            entries = [{'path': p, 'expected_sha256': h} for p, h in before['files'].items()]
            check = check_entries(entries, source)
            digest = sha(json.dumps(before['files'], ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode())
            check.update({'manifest': rel(d / 'runtime-inputs-before.json'),
                          'original_worktree_not_commit': True, 'later_publication_sha': source,
                          'before_after_files_equal': before['files'] == after['files'],
                          'before_after_jars_equal': before.get('jars') == after.get('jars'),
                          'inputs_digest_recomputed': digest, 'inputs_digest_matches': digest == before['inputs_digest'] == after['inputs_digest']})
            r['runtime_manifests'].append(check)
        for a in sorted(d.iterdir()):
            if a.is_dir() and re.fullmatch(r'attempt\d+', a.name):
                af = a / 'result.json'
                ao = read_json(af) if af.is_file() else {}
                r['attempt_inventory'].append({'directory': rel(a), 'result_exists': af.is_file(),
                                               'result_sha256': sha(af.read_bytes()) if af.is_file() else None,
                                               'keys': list(ao), 'tested_code_sha': source_of(ao),
                                               'historical_raw_label_not_current_verdict': ao.get('overall'),
                                               'file_count': sum(p.is_file() for p in a.rglob('*'))})
        for index in ('evidence-files.json', 'IMPORTED-FILES.json'):
            p = d / index
            if p.is_file():
                r['archive_indexes'].append(archive_index(d, p))
        attr = git('check-attr', 'text', '--', rel(d / 'README.md'))
        r['text_attribute'] = attr.stdout.decode().strip()
        r['text_unset'] = attr.returncode == 0 and attr.stdout.decode().strip().endswith(': unset')
        if source:
            ps = ('csucampuscraft-user/src', 'csucampuscraft-admin/src',
                  'csucampuscraft-user/pom.xml', 'csucampuscraft-admin/pom.xml',
                  'database', 'assets', '.mvn', 'mvnw', 'mvnw.cmd')
            p = git('diff', '--name-status', source + '..' + BASE, '--', *ps)
            r['product_diff_exit_code'] = p.returncode
            r['product_diff_name_status'] = p.stdout.decode().splitlines()
            r['product_diff_empty'] = p.returncode == 0 and not p.stdout
        # File inventories and comparisons are newly computed; no old business label is promoted.
        reports.append(r)
        write(OUT / 'integrity' / (d.name + '.json'), r)
    # All old evidence files must still equal BASE; excludes the new review tree.
    old_diff = git('diff', BASE, '--name-status', '--', *[rel(d) for d in dirs])
    attr_paths = sorted({x['path'] for r in reports for a in r['archive_indexes'] for x in a['files']})
    ap = subprocess.run(['git', '-C', str(ROOT), 'check-attr', 'text', '--stdin'],
                        input=('\n'.join(attr_paths)+'\n').encode(), capture_output=True)
    attr_lines = ap.stdout.decode('utf-8').splitlines()
    attributes = {'command': ['git','-C',str(ROOT),'check-attr','text','--stdin'],
                  'input_paths': attr_paths, 'exit_code': ap.returncode,
                  'checked_count': len(attr_lines),
                  'all_unset': len(attr_lines) == len(attr_paths) and all(s.endswith(': unset') for s in attr_lines),
                  'non_unset': [s for s in attr_lines if not s.endswith(': unset')],
                  'stderr': ap.stderr.decode('utf-8', errors='replace')}
    write(OUT / 'integrity/text-attributes.json', attributes)
    runtime_paths = sorted(set(x['path'] for r in reports for m in r['runtime_manifests'] for x in m['entries']))
    current_entries = [{'path': p, 'expected_sha256': sha((ROOT / p).read_bytes())} for p in runtime_paths if (ROOT / p).is_file()]
    current_manifest = ''.join(f'{e["expected_sha256"]}  {e["path"]}\n' for e in current_entries)
    (OUT / 'integrity' / 'review-runtime-inputs.sha256').write_text(current_manifest, encoding='utf-8', newline='')
    summary = {'generated_at': datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
               'executor': 'Codex AI read-only audit; human sign-off pending',
               'baseline': baseline, 'historical_results_are_inventory_only': True,
               'old_evidence_diff_from_review_baseline': old_diff.stdout.decode().splitlines(),
               'all_indexed_archive_files_text_unset': attributes['all_unset'],
               'text_attributes_checked_count': attributes['checked_count'],
               'review_runtime_file_count': len(current_entries),
               'review_runtime_manifest_sha256': sha(current_manifest.encode()),
               'archives': [{k: v for k, v in r.items() if k not in ('runtime_manifests', 'archive_indexes')} | {
                   'runtime_manifests': [{k: v for k, v in m.items() if k != 'entries'} for m in r['runtime_manifests']],
                   'archive_indexes': [{k: v for k, v in a.items() if k != 'files'} for a in r['archive_indexes']],
                   'detail': 'integrity/' + r['directory'].split('/')[-1] + '.json'} for r in reports]}
    write(OUT / 'evidence-integrity.json', summary)
    write(OUT / 'integrity' / 'commands.json', COMMANDS)
    print(json.dumps({'archives': len(reports),
                      'archive_files_checked': sum(a['count'] for r in reports for a in r['archive_indexes']),
                      'archive_mismatches': sum(a['count'] - a['matches'] for r in reports for a in r['archive_indexes']),
                      'runtime_manifests': sum(len(r['runtime_manifests']) for r in reports),
                      'runtime_manifest_source_mismatches_allowing_only_line_endings': sum(m['file_count']-m['tested_source_hash_matches_allowing_only_line_endings'] for r in reports for m in r['runtime_manifests']),
                      'final_step12_diff_empty': reports[-1].get('product_diff_empty')}, ensure_ascii=False), flush=True)

if __name__ == '__main__':
    main()
