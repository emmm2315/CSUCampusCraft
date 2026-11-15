"""Read original STEP13 leaf artifacts and write a separate delivery index.

Never modifies a leaf result, matrix, HTTP record, body, screenshot or manifest.
The parent owns the final 39-case composition and final archive.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

HERE = Path(__file__).resolve().parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def lines(path):
    return [json.loads(row) for row in path.read_text(encoding='utf-8').splitlines()] if path.exists() else []


def main():
    descriptions = {
        'attempt1': 'External SQL-literal collation mismatch before business HTTP. Original FAIL retained.',
        'attempt2': 'External CONVERT-expression coercibility mismatch in fixture lookup. Original FAIL retained.',
        'attempt3': 'External parse_qs blank-value assertion dropped the valid q= parameter. Original FAIL retained.',
        'attempt4': 'External browser caller passed JSON text instead of a fixture-file path; no browser navigation. Secondary private-value source self-match from a fixed synthetic shipping phone. Both original FAIL records retained.',
        'attempt5': 'Serial/empty/demo/restart/browser components completed. First C1 Java stdout was not strict UTF8; decoding failed before response archival. Original overall FAIL retained; no C1 success inferred or reused.',
        'attempt6': 'New private-datadir C/D-only group on the same fixed product SHA and JARs. Ten identifiers and thirteen scenario segments; not a standalone all39 result.',
    }
    attempts = []
    for name in descriptions:
        directory = HERE / 'evidence' / name
        result_path = directory / 'result.json'
        result = json.loads(result_path.read_text(encoding='utf-8'))
        manifest = directory / 'artifacts.sha256'
        entries = []
        for row in manifest.read_text(encoding='utf-8').splitlines():
            expected, relative = row.split('  ', 1)
            target = (directory / relative).resolve()
            if not target.is_relative_to(directory.resolve()):
                raise AssertionError('Unsafe manifest path')
            entries.append(dict(path=relative, matches=target.is_file() and sha(target.read_bytes()) == expected))
        http = lines(directory / 'http.jsonl')
        browser = directory / 'browser' / 'result.json'
        sensitive = json.loads((directory / 'sensitive-scan.json').read_text(encoding='utf-8'))
        matrix = result['p0_matrix']
        attempts.append(dict(
            attempt=name, original_overall=result['overall'], diagnosis=descriptions[name],
            original_result_file=f'evidence/{name}/result.json', original_result_sha256=sha(result_path.read_bytes()),
            original_manifest_sha256=sha(manifest.read_bytes()), manifest_entries=len(entries),
            original_manifest_entries_match=all(row['matches'] for row in entries),
            tested_sha=result['tested_sha'], scope=result['scope'],
            started_at_utc=result['started_at_utc'], finished_at_utc=result['finished_at_utc'],
            checks=result['checks'], failed_assertions=result['checks_failed'],
            archived_http_records=len(http), archived_post_records=sum(row['method'] == 'POST' for row in http),
            original_matrix_total=len(matrix), original_complete_pass_identifiers=sum(row['result'] == 'PASS' for row in matrix),
            raw_privacy_result=sensitive['overall'], runtime_inputs_stable=result['runtime_inputs_stable'],
            tracked_processes_stopped=result['tracked_processes_stopped'],
            mysql_port=result.get('mysql_port'), mysql_uuid=result.get('mysql_uuid'),
            user_jar_sha256=result.get('user_jar_sha256'), admin_jar_sha256=result.get('admin_jar_sha256'),
            runtime_input_count=result.get('runtime_file_count'), runtime_manifest_sha256=result.get('runtime_manifest_sha256'),
            browser_result_file=f'evidence/{name}/browser/result.json' if browser.exists() else None,
            concurrency_result_records=len(lines(directory / 'concurrency/results.jsonl')),
            fault_result_records=len(lines(directory / 'faults/results.jsonl')),
        ))
    if not all(row['original_manifest_entries_match'] for row in attempts):
        raise AssertionError('An original leaf artifact changed')
    output = dict(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        scope='Read-only index of original leaf identities; this file is not the final parent 39-case verdict.',
        original_artifacts_rewritten=False,
        original_failed_leaf_overall_values_unchanged=True,
        selected_same_round_sources=dict(
            serial_empty_demo_restart_browser='evidence/attempt5: only its successfully completed segments; original C1 failure excluded',
            all_eight_concurrency_and_five_trigger_faults='evidence/attempt6: all thirteen scenario segments on a new private datadir',
            additional_subbranch_observations='Parent separately indexes same-round home-filter and state-token supplements; no prior STEP verdict inheritance',
        ),
        boundaries=[
            'Attempt5 original C1 runner stdout was not archived before strict decoding failed; no HTTP winner/loser claim is inferred from that attempt.',
            'Attempt5 browser has 24 after-only navigation metadata records, 20 real PNGs and 207 assertions. A real whole-batch seven-table before/after proves no business DB writes; per-navigation raw bodies were not archived or scanned by this helper.',
            'Concurrent worker POSTs have no independent before/after attribution. Nine common lock-gated windows cover eight scenarios because C8 has two phases.',
            'Trigger rollback equality concerns committed seven-table row data, not auto-increment allocator gaps.',
            'Human cross reproduction and group peer sign-off remain NOT_IMPLEMENTED; technical Codex observations do not substitute for them.',
        ],
        attempts=attempts,
    )
    target = HERE / 'child-delivery-summary.json'
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(dict(path=str(target), leaf_count=len(attempts), manifests_all_match=True, leaf6_original_overall=attempts[-1]['original_overall'])))


if __name__ == '__main__':
    main()
