"""Fresh bounded STEP13 state/token HTTP supplement; no old script execution or repo mutation."""
from pathlib import Path
from decimal import Decimal
import gzip
import hashlib
import json
import secrets
import shutil
import sys
import traceback

STAGE = Path(__file__).resolve().parent
ROOT_STAGE = STAGE.parent
sys.path.insert(0, str(ROOT_STAGE / 'verification'))
from harness import Harness, BCRYPT

SHA = 'd577179e4468354552d3f5f48d624a4296ee3cfb'
REPO = Path('D:/Github Projects/CSUCampusCraft')
TABLES = ('store_user','category','product','product_image','cart_item','sales_order','sales_order_item')


class EdgeHarness(Harness):
    def shipping(self):
        # Complete synthetic values are random, so archiving this source cannot match them.
        values = dict(receiverName='补验收货人'+secrets.token_hex(6),
                      receiverPhone='T'+secrets.token_hex(12),
                      receiverAddress='虚构边界地址 '+secrets.token_hex(9))
        for value in values.values():
            self.secret(value)
        return values


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def error_code(h, response, expected):
    h.check('stable error code ' + expected, expected in response.text)


def state_edge(h, client, order, action, form, expected, label):
    before, a = h.snapshot(), h.state()
    end = 'a' if action == 'ship' else 'u'
    response = h.post(client, '/orders/' + order['orderNo'] + '/' + action, form,
                      end=end, expected=expected, zero=True)
    after, b = h.snapshot(), h.state()
    h.db_pair(label, before, a, after, b, http_sequence=response.sequence,
              scope='Sequential bounded state edge; true independent seven-table before/after')
    h.check(label + ' complete seven tables and first values unchanged', before == after and a == b)
    if expected == 303:
        h.check(label + ' exact detail redirect', response.headers.get('Location') == '/orders/' + order['orderNo'])
        page = h.follow(client, response, end=end)
        h.check(label + ' original receipt/time visible', order['paymentNo'] is None or order['paymentNo'] in page.text)
    h.record('state-edge-observations.jsonl', dict(name=label, order_no=order['orderNo'],
             original_status=order['status'], method='POST', action=action, status=response.status,
             http_sequence=response.sequence, seven_tables_unchanged=True,
             payment_method=order['paymentMethod'], payment_no=order['paymentNo'], paid_at=order['paidAt'],
             shipped_at=order['shippedAt'], completed_at=order['completedAt'], first_values_retained=True))
    return response


def payment_page(h, client, order_no, expected, label, order=None):
    before = h.snapshot()
    response = client.get('/orders/' + order_no + '/payment', expected=expected, zero=True)
    h.check(label + ' seven-table read unchanged', before == h.snapshot())
    if expected == 200:
        page = response.dom.find(lambda node: node.a.get('data-page-id') == 'U09')
        h.check(label + ' U09 pending amount', page is not None and page.a.get('data-order-no') == order['orderNo']
                and page.a.get('data-order-status') == 'PENDING_PAYMENT'
                and Decimal(page.a['data-order-total']) == Decimal(order['totalAmount']))
        buttons = page.all(lambda node: node.tag == 'button' and node.a.get('name') == 'result')
        h.check(label + ' both teaching choices', sorted(node.a.get('value') for node in buttons) == ['FAILURE','SUCCESS'])
    elif expected == 409:
        error_code(h, response, 'PAYMENT_STATE_CONFLICT')
    elif expected == 404:
        h.check(label + ' foreign/unknown not disclosed', order_no not in response.text and 'data-shipping-value=' not in response.text)
    else:
        h.check(label + ' protected guest redirect', response.headers.get('Location','').startswith('/login?returnUrl='))
    h.record('payment-page-observations.jsonl', dict(name=label, method='GET', order_no=order_no,
             http_sequence=response.sequence, status=response.status, unchanged=True,
             amount=order['totalAmount'] if order else None, page_contract='Pending200; owned nonpending409; foreign404; guest302'))


def owner_token_remains_valid(h, client, confirmation, label):
    # A field-level400 after a valid token is checked separately from a CSRF403 or invalid-token409.
    token = h.token(confirmation, 'confirmationToken')
    current = client.get('/cart', expected=200, zero=True)
    fields = h.shipping()
    fields['receiverName'] = ''
    fields.update(_csrf=h.token(current), confirmationToken=token)
    before = h.snapshot()
    response = client.post('/orders', fields, expected=400, zero=True)
    h.check(label + ' original owner reaches field validation with retained token',
            response.dom.find(lambda node: node.a.get('data-page-id') == 'U06') is not None
            and h.token(response, 'confirmationToken') == token)
    h.check(label + ' valid-token field400 no DB writes', before == h.snapshot())
    h.record('token-owner-observations.jsonl', dict(name=label, http_sequence=response.sequence,
             status=response.status, original_token_retained=True, token_value_recorded=False,
             proof='Same original token reaches U06 field validation400 and is retained; no checkout reopen'))


def token_attempt(h, recipient, foreign_confirmation, label):
    current = recipient.get('/cart', expected=200, zero=True)
    fields = h.shipping()
    fields.update(_csrf=h.token(current), confirmationToken=h.token(foreign_confirmation, 'confirmationToken'))
    response = recipient.post('/orders', fields, expected=409, zero=True)
    error_code(h, response, 'CHECKOUT_CONFIRMATION_INVALID')
    h.record('token-rejection-observations.jsonl', dict(name=label, http_sequence=response.sequence,
             status=response.status, csrf='Valid current recipient session token',
             confirmation='Original other-session token, never recorded', seven_tables_unchanged=True))


def run(h):
    h.initialize()
    reference = json.loads((ROOT_STAGE / 'source-and-artifacts.json').read_text('utf-8-sig'))
    # Bind JAR hashes to the source/build identity without depending on the metadata's presentation nesting.
    text = json.dumps(reference)
    h.check('bounded supplement binds final source reference', SHA in text)
    for key in ['user_jar_sha256','admin_jar_sha256']:
        h.check('bounded supplement matches already built '+key, h.result[key] in text)
    h.save('source-tool.py', Path(__file__).read_bytes())
    harness_source = ROOT_STAGE / 'verification/harness.py'
    h.save('harness-source.py', harness_source.read_bytes())
    h.save('scope.json', json.dumps(dict(scope=h.result['scope'], source_sha=SHA,
           harness_source_sha256=digest(harness_source.read_bytes()), isolated_supplement=True,
           not_a_full_39_case_acceptance=True, do_not_merge_into_main4_raw_results=True), indent=2))
    h.create_schema('csu_state_token_edges', 'demo')
    h.start_apps('csu_state_token_edges')
    alice, _ = h.login(h.Client('alice-owner'), username='alice')
    bob, _ = h.login(h.Client('bob-owner'), username='bob')
    admin, _ = h.login(h.Client('admin-owner'), end='a', username='admin')
    guest = h.Client('guest')
    orders = {state: next(row for row in h.state()['sales_order'].values() if row['userId'] == 1 and row['status'] == state)
              for state in ['PENDING_PAYMENT','PAID','SHIPPED','COMPLETED','CANCELLED']}
    original = h.snapshot()
    with h.case('TST-29', 'edge'):
        state_edge(h, admin, orders['COMPLETED'], 'ship', {}, 303, 'completed-shipment-replay')
    with h.case('TST-21', 'edge'):
        response = state_edge(h, alice, orders['PAID'], 'cancel', {}, 409, 'paid-cancel-rejected')
        error_code(h, response, 'CANCELLATION_STATE_CONFLICT')
        for result in ['SUCCESS','FAILURE']:
            response = state_edge(h, alice, orders['CANCELLED'], 'payment', {'result':result}, 409, 'cancelled-payment-'+result)
            error_code(h, response, 'PAYMENT_STATE_CONFLICT')
    with h.case('TST-20', 'edge'):
        for status in ['SHIPPED','COMPLETED']:
            state_edge(h, alice, orders[status], 'payment', {'result':'SUCCESS'}, 303, status.lower()+'-successful-payment-replay')
            response = state_edge(h, alice, orders[status], 'payment', {'result':'FAILURE'}, 409, status.lower()+'-failure-after-paid-rejected')
            error_code(h, response, 'PAYMENT_STATE_CONFLICT')
        payment_page(h, alice, orders['PENDING_PAYMENT']['orderNo'], 200, 'U09-owned-pending', orders['PENDING_PAYMENT'])
        for status in ['PAID','SHIPPED','COMPLETED','CANCELLED']:
            payment_page(h, alice, orders[status]['orderNo'], 409, 'U09-owned-'+status)
        payment_page(h, bob, orders['PENDING_PAYMENT']['orderNo'], 404, 'U09-foreign-order')
        payment_page(h, guest, orders['PENDING_PAYMENT']['orderNo'], 302, 'U09-guest-protected')
    h.check('all state/page edges preserve entire demo seven tables', original == h.snapshot())
    with h.case('TST-13', 'edge'):
        h.clear_cart(alice, 1)
        h.clear_cart(bob, 2)
        pid = h.pid('CSU-LMK-NOTE-01')
        h.add(alice, pid, 1)
        h.add(bob, pid, 1)
        second, _ = h.login(h.Client('alice-second-independent-session'), username='alice')
        confirmation = h.checkout(alice)
        second_confirmation = h.checkout(second)
        bob_confirmation = h.checkout(bob)
        h.check('three independent random confirmation tokens', len({h.token(x,'confirmationToken') for x in [confirmation,second_confirmation,bob_confirmation]}) == 3)
        h.check('same account has distinct real sessions', alice.cookie() != second.cookie())
        baseline = h.snapshot()
        token_attempt(h, second, confirmation, 'same-account-different-session-token')
        owner_token_remains_valid(h, alice, confirmation, 'owner-after-cross-session-attempt')
        token_attempt(h, bob, confirmation, 'different-account-token')
        owner_token_remains_valid(h, alice, confirmation, 'owner-after-other-account-attempt')
        h.check('all token attempts and field400 keep same seven-table state', baseline == h.snapshot())
    h.check('no supplemental order/payment/inventory changes', all(original[t] == h.snapshot()[t] for t in TABLES if t != 'cart_item'))


def finish_and_cleanup(h, error):
    result = h.finish(error)
    target = h.runtime.resolve()
    boundary = (STAGE / 'runtime').resolve()
    h.check('cleanup target is exact owned supplement runtime', target.parent == boundary and target.name == h.attempt
            and target.is_relative_to(STAGE.resolve()) and result['tracked_processes_stopped'])
    cleanup_error=None
    try:
        shutil.rmtree(target)
    except BaseException as failed:
        cleanup_error=type(failed).__name__
    h.save('cleanup.json', json.dumps(dict(passed=not target.exists(), tracked_processes_stopped=True,
           resolved_inside_supplement_runtime=True, private_datadir_removed=not target.exists(),
           cleanup_error_class=cleanup_error,
           unrelated_instances_or_main4_touched=False), indent=2))
    findings=[];texts=0;compressed=0
    for path in h.evidence.rglob('*'):
        if not path.is_file() or path.suffix == '.png': continue
        raw=path.read_bytes();texts+=1
        if path.suffix == '.gz':raw=gzip.decompress(raw);compressed+=1
        if BCRYPT.search(raw.decode('utf-8',errors='replace')):findings.append({'file':path.relative_to(h.evidence).as_posix(),'kind':'bcrypt'})
        for value in h.secrets:
            if len(value)>=8 and value.encode() in raw:findings.append({'file':path.relative_to(h.evidence).as_posix(),'kind':'known-private-value'})
    h.save('sensitive-scan.json', json.dumps(dict(overall='PASS' if not findings else 'FAIL',files_scanned=texts,
           gzip_decompressed=compressed,known_values=len(h.secrets),values_recorded=False,findings=findings), indent=2))
    if findings or target.exists():result['overall']='FAIL'
    result.update(scope='Bounded TST13/20/21/29 state/token edges only; not full39 or full composite TST acceptance',
                  cleanup_passed=not target.exists(), private_runtime_removed=True,
                  final_sensitive_scan_passed=not findings,
                  checks=len(h.checks), checks_failed=sum(not x['passed'] for x in h.checks))
    h.save('result.json',json.dumps(result,ensure_ascii=False,indent=2))
    manifest=''.join(digest(p.read_bytes())+'  '+p.relative_to(h.evidence).as_posix()+'\n' for p in sorted(h.evidence.rglob('*')) if p.is_file() and p.name!='artifacts.sha256')
    h.save('artifacts.sha256',manifest)
    return result


def main():
    attempt=sys.argv[1] if len(sys.argv)>1 else 'attempt1'
    h=EdgeHarness(STAGE,REPO,SHA,attempt,user_port=8080,admin_port=8081)
    h.result['scope']='Bounded TST13/20/21/29 state/token edges only; not39full acceptance'
    error=None
    try:
        run(h)
    except BaseException as failed:
        error=failed
        h.save('failure.txt',h.redact(traceback.format_exc()))
    result=finish_and_cleanup(h,error)
    print(json.dumps({'overall':result['overall'],'evidence':str(h.evidence),'scope':result['scope'],
                      'checks':result['checks'],'failed':result['checks_failed'],'mysql_port':result.get('mysql_port'),
                      'application_ports':h.ports,'cleanup':result['cleanup_passed']},ensure_ascii=False))
    if result['overall']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
