"""New STEP13 C/D-only group on the same fixed product SHA and fresh private DB.

The parent acceptance result combines same-round groups explicitly. This runner
does not rerun or change attempt5's completed serial/browser observations and
does not claim a standalone all-39 P0 result.
"""
from pathlib import Path
import json
import sys
import traceback

from harness import Harness, scanner_regression, digest

HERE = Path(__file__).resolve().parent
REPO = Path('D:/Github Projects/CSUCampusCraft')
SHA = 'd577179e4468354552d3f5f48d624a4296ee3cfb'
SEGMENTS = {
    'TST-16': ['D1', 'D2', 'D3'],
    'TST-17': ['C3', 'C8'],
    'TST-20': ['D5'],
    'TST-23': ['D4'],
    'TST-24': ['C4'],
    'TST-28': ['C2'],
    'TST-29': ['C5'],
    'TST-35': ['C1'],
    'TST-39': ['C7'],
    'TST-40': ['C6'],
}


def main():
    attempt = sys.argv[1] if len(sys.argv) > 1 else ''
    h = Harness(HERE, REPO, SHA, attempt)
    h.plan = dict(h.plan)
    h.plan['scope'] = 'C/D-only same-SHA group: ten identifiers, thirteen required scenario segments. The parent resolves other segments from separately indexed same-round observations; this leaf does not claim all39.'
    h.plan['cases'] = [dict(row, required_segments=SEGMENTS[row['id']],
                            parent_requirement_description=row['assertion_plan'],
                            assertion_plan='This leaf only asserts scenario segments ' + ', '.join(SEGMENTS[row['id']]) + '; other requirement parts are outside this leaf.')
                       for row in h.plan['cases'] if row['id'] in SEGMENTS]
    h.result.update(scope='C/D-only current-round group: eight concurrency and five trigger rollback scenarios; ten P0 identifiers, thirteen required segments; not standalone all39 acceptance',
                    parent_acceptance_composition='Root combines this new private-DB group with same-round attempt5 successful serial/empty/restart/browser segments and separately referenced supplements. Attempt5 original overall FAIL remains unchanged.',
                    standalone_all39_claimed=False,
                    required_scenarios=13,
                    required_p0_identifiers=10)
    error = None
    try:
        regression = scanner_regression()
        h.check('new nine-case raw scanner self-test', regression['overall'] == 'PASS' and regression['passed'] == 9)
        h.save('raw-scanner-self-test.json', json.dumps(regression, indent=2))
        h.save('p0-plan-at-use.json', json.dumps(h.plan, ensure_ascii=False, indent=2))
        tools = []
        for source in sorted(HERE.glob('*')):
            if source.is_file() and source.suffix in ['.py', '.java', '.json']:
                raw = source.read_bytes()
                h.save('tools/' + source.name, raw)
                tools.append(dict(path=source.name, sha256=digest(raw)))
        h.save('tool-inputs.json', json.dumps(tools, indent=2))
        h.initialize()
        h.create_schema('csucampuscraft', 'demo')
        h.start_apps('csucampuscraft')
        before = h.snapshot()
        h.check('fresh SQL02 demo before independent C/D schemas',
                [before[t]['rows'] for t in ['store_user', 'category', 'product', 'product_image', 'cart_item', 'sales_order', 'sales_order_item']] == [4, 15, 60, 100, 10, 10, 20])
        h.save('demo-original.json', json.dumps(before, indent=2))
        import concurrency_faults
        concurrency_faults.run_concurrency(h)
        concurrency_faults.run_faults(h)
        h.check('all independent C/D groups leave original demo unchanged', h.snapshot() == before)
        matrix = h.matrix()
        h.check('all ten selected P0 group identifiers and thirteen C/D segments complete',
                len(matrix) == 10 and sum(len(row['required_segments']) for row in matrix) == 13 and all(row['result'] == 'PASS' for row in matrix))
    except BaseException as exc:
        error = exc
        h.save('failure.txt', traceback.format_exc())
        print(type(exc).__name__ + ': ' + str(exc), flush=True)
    finally:
        result = h.finish(error)
        print('STEP13_CD_RESULT ' + str(h.evidence / 'result.json') + ' ' + result['overall'], flush=True)
    return 0 if result['overall'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
