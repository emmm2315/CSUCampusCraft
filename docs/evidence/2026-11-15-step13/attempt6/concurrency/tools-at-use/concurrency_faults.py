"""Fresh STEP13 real HTTP concurrency and trigger rollback cases. Import has no side effects.

Only the single orchestrator invokes run_concurrency/run_faults after build and owned-DB checks.
Every C/D gets a separate schema and fresh app sessions; production files are never written.
"""
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal
import gzip
import hashlib
import json
import re
import secrets
import urllib.parse
import zipfile

from harness import JAVA, Parser, Response


HERE = Path(__file__).resolve().parent
TABLES = ('store_user', 'category', 'product', 'product_image', 'cart_item', 'sales_order', 'sales_order_item')
C_MAP = {'C1': 'TST-35', 'C2': 'TST-28', 'C3': 'TST-17', 'C4': 'TST-24',
         'C5': 'TST-29', 'C6': 'TST-40', 'C7': 'TST-39', 'C8': 'TST-17'}
D_MAP = {'D1': 'TST-16', 'D2': 'TST-16', 'D3': 'TST-16', 'D4': 'TST-23', 'D5': 'TST-20'}


def utc():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


class Suite:
    def __init__(self, h):
        self.h = h
        self.original_schema = h.schema
        self.classes = h.runtime / 'concurrent-runner/classes'
        self.libs = h.runtime / 'concurrent-runner/lib'
        self.cp = None
        self.created = []
        self.verify_owned()

    def verify_owned(self):
        h = self.h
        observed = h.rows('SELECT @@server_uuid,@@port;').split('\t')
        h.check('C/D own isolated MySQL UUID and port', observed == [h.result['mysql_uuid'], str(h.mysql_port)])

    def compile(self):
        """Called at formal-run time only, against the already-built final admin JAR."""
        h = self.h
        self.classes.mkdir(parents=True, exist_ok=False)
        self.libs.mkdir(parents=True, exist_ok=False)
        jar = h.repo / 'csucampuscraft-admin/target/csucampuscraft-admin-0.0.1-SNAPSHOT.jar'
        with zipfile.ZipFile(jar) as archive:
            for entry in archive.namelist():
                if entry.startswith('BOOT-INF/lib/') and entry.endswith('.jar'):
                    (self.libs / Path(entry).name).write_bytes(archive.read(entry))
        self.cp = str(self.classes) + ';' + str(self.libs / '*')
        source = HERE / 'ConcurrentHttpRunner.java'
        module = Path(__file__).resolve()
        h.save('concurrency/tools-at-use/ConcurrentHttpRunner.java', source.read_bytes())
        h.save('concurrency/tools-at-use/concurrency_faults.py', module.read_bytes())
        h.save('concurrency/tools-at-use/version-reason.json', json.dumps(dict(
            source_sha256=digest(source.read_bytes()), module_sha256=digest(module.read_bytes()),
            initial_version_retained=['verification/tool-versions/c5-gate-initial', 'verification/tool-versions/utf8-stdout-initial'],
            reason='Same-index C5 gate retained; explicit UTF8 JSON bytes after attempt5 external stdout decode failure, with old attempt/tool identities preserved; product SHA/JAR unchanged',
            actual_tool_version_saved_at_compile=True), indent=2))
        p = h.command([JAVA.parent / 'javac.exe', '--release', '21', '-encoding', 'UTF-8',
                       '-cp', self.cp, '-d', self.classes, source], timeout=60)
        h.save('concurrency/runner-compile.log', p.stdout.decode('utf-8', errors='replace') + p.stderr.decode('utf-8', errors='replace'))
        h.record('concurrency/tool-identity.jsonl', dict(source_sha256=digest(source.read_bytes()),
                 admin_jar_sha256=digest(jar.read_bytes()), exit_code=p.returncode,
                 dependencies='Actual final admin BOOT-INF/lib, external tool only'))
        h.check('fresh external HTTP latch runner compiles', p.returncode == 0)

    def begin(self, label):
        h = self.h
        self.verify_owned()
        schema = 'step13_' + label.lower()
        h.stop_apps()
        h.create_schema(schema, 'demo')
        h.start_apps(schema)
        self.created.append(schema)
        h.record('concurrency/scenarios.jsonl', dict(case=label, schema=schema, started_at_utc=utc(),
                 independent_demo_schema=True, same_final_JAR=True, reset_during_window=False))

    def restore(self):
        h = self.h
        h.stop_apps()
        h.start_apps(self.original_schema)

    def clients(self, names):
        out = []
        for name in names:
            client, _ = self.h.login(self.h.Client('fresh-' + name + '-' + secrets.token_hex(3)),
                                     end='a' if name == 'admin' else 'u', username=name)
            out.append(client)
        return out

    def setup_cart(self, client, quantities, uid=1):
        self.h.clear_cart(client, uid)
        for pid, quantity in quantities:
            self.h.add(client, pid, quantity)
        confirmation = self.h.checkout(client)
        form = self.h.shipping()
        form.update(_csrf=self.h.token(confirmation), confirmationToken=self.h.token(confirmation, 'confirmationToken'))
        for value in form.values():
            self.h.secret(value)
        return confirmation, form

    def request(self, name, client, path, form, end='u', csrf_page=None):
        h = self.h
        data = dict(form)
        if '_csrf' not in data:
            page = client.get(csrf_page or ('/cart' if end == 'u' else '/'), end, expected=200)
            data['_csrf'] = h.token(page)
        for key, value in data.items():
            if key in ['_csrf', 'confirmationToken', 'receiverName', 'receiverPhone', 'receiverAddress']:
                h.secret(value)
        value = client.cookie(end)
        h.secret(value)
        cookie_name = 'CSUCAMPUSCRAFT_USER_SESSION' if end == 'u' else 'CSUCAMPUSCRAFT_ADMIN_SESSION'
        return dict(name=name, method='POST', url=h.base(end) + path,
                    headers={'Cookie': cookie_name + '=' + value},
                    form_body=urllib.parse.urlencode(data, doseq=True),
                    private_form_values=[str(v) for k, v in data.items() if k in ['_csrf', 'confirmationToken', 'receiverName', 'receiverPhone', 'receiverAddress']],
                    credential_values=[h.password, h.rootpass, h.apppass])

    def observe(self, item, label):
        """The Java runner scans raw bytes; Python only receives and stores redacted text."""
        h = self.h
        text = h.redact(item['redacted_body'])
        raw = text.encode('utf-8')
        file = 'bodies/' + digest(raw)[:32] + '.html.gz'
        if not (h.evidence / file).exists():
            h.save(file, gzip.compress(raw, mtime=0))
        with h.lock:
            h.n += 1
            sequence = h.n
        port = item['port']
        end = 'u' if port == h.ports['u'] else 'a'
        headers = {'Location': item['location'], 'Content-Type': item['content_type']}
        h.record('http.jsonl', dict(sequence=sequence, method=item['method'], path=item['path'], end=end,
                 port=port, schema=h.schema, status=item['status'], location=item['location'],
                 content_type=item['content_type'], body_file=file, stored_file_sha256=digest((h.evidence/file).read_bytes()),
                 stored_file_bytes=(h.evidence/file).stat().st_size, redacted_content_sha256=digest(raw),
                 raw_body_sha256=item['raw_body_sha256'], raw_body_bytes=item['raw_body_bytes'],
                 raw_body_available=True, raw_privacy_scan_executor='External Java before redaction; Python did not rescan raw bytes',
                 raw_bcrypt_scan_passed=not item['raw_bcrypt_present'], raw_known_credential_scan_passed=not item['raw_known_credential_present'],
                 credentials_or_session_values_recorded=False, started_at_utc=item['started_at_utc'],
                 finished_at_utc=item['finished_at_utc'], elapsed_ns=item['elapsed_ns'],
                 window_id=label, transport='Actual independent Java HTTP worker', per_request_isolation_not_claimed=True))
        h.record('db-writes.jsonl', dict(name='http-'+str(sequence), http_sequence=sequence, schema=h.schema,
                 before=None, after=None, observation='CONCURRENT_WINDOW', window_id=label,
                 per_request_isolation_not_claimed=True))
        h.check(label + ' Java raw credential/hash scan', not item['raw_bcrypt_present'] and not item['raw_known_credential_present'])
        h.check(label + ' Java raw response has no session URL rewriting', not item['raw_session_url_tracking'])
        return Response(item['status'], headers, raw, Parser(text).root, sequence)

    def pair(self, label, requests, table, target, minimum_waiters=2, note=''):
        h = self.h
        credentials = h.connection_env(root=True)
        config = dict(scenario=label, schema=h.schema,
                      jdbc=dict(url=credentials['STEP13_JDBC_URL'], user=credentials['STEP13_DB_USER'], password=credentials['STEP13_DB_PASSWORD']),
                      gate=dict(table=table, id=target, minimum_waiters=minimum_waiters),
                      private_values=[h.password, h.rootpass, h.apppass], requests=requests)
        before, a = h.snapshot(), h.state()
        with h.concurrent_window(label):
            p = h.command([JAVA, '-cp', self.cp, 'ConcurrentHttpRunner'],
                          input=json.dumps(config, ensure_ascii=False).encode('utf-8'), timeout=115)
            try:
                output = p.stdout.decode('utf-8')
                utf8_valid = True
            except UnicodeDecodeError:
                output = None
                utf8_valid = False
            # Preserve byte identity before parsing. Raw stdout is not archived, because future
            # exceptional third-party diagnostics might bypass the runner's response redaction.
            h.record('concurrency/runner-wire.jsonl', dict(case=label, tool_exit_code=p.returncode,
                     stdout_bytes=len(p.stdout), stdout_sha256=digest(p.stdout), strict_utf8_valid=utf8_valid,
                     stderr_bytes=len(p.stderr), stderr_sha256=digest(p.stderr),
                     raw_stdout_or_stderr_archived=False, private_stdin_recorded=False))
            h.check(label + ' runner stdout is explicit strict UTF8', utf8_valid)
            result = json.loads(output)
            public = {k: v for k, v in result.items() if k != 'responses'}
            public['responses'] = [{k: v for k, v in row.items() if k != 'redacted_body'} for row in result.get('responses', [])]
            public.update(schema=h.schema, tool_exit_code=p.returncode, caller_note=note)
            h.record('concurrency/raw.jsonl', public)
            h.check(label + ' two real HTTP workers completed', p.returncode == 0 and result.get('completed') and len(result.get('responses', [])) == 2)
            h.check(label + ' actual JDBC lock wait observed', result['gate']['threshold_observed'])
            responses = [self.observe(row, label) for row in result['responses']]
        after, b = h.snapshot(), h.state()
        return responses, before, a, after, b

    def unchanged(self, name, a, b, allowed):
        self.h.check(name + ' untouched tables preserve complete row state', all(a[t] == b[t] for t in TABLES if t not in allowed))

    def fresh_orders(self, a, b):
        return [row for key, row in b['sales_order'].items() if key not in a['sales_order']]

    def one_order(self, label, a, b, owner, pids):
        h = self.h
        rows = self.fresh_orders(a, b)
        h.check(label + ' exactly one new order', len(rows) == 1 and rows[0]['userId'] == owner)
        order = rows[0]
        lines = [row for key, row in b['sales_order_item'].items() if key not in a['sales_order_item']]
        h.check(label + ' exact new immutable lines', len(lines) == len(pids) and {x['productId'] for x in lines} == set(pids)
                and all(x['orderId'] == order['id'] for x in lines))
        h.check(label + ' old orders and snapshots untouched', all(b['sales_order'].get(k) == v for k, v in a['sales_order'].items())
                and all(b['sales_order_item'].get(k) == v for k, v in a['sales_order_item'].items()))
        h.check(label + ' pending new order with no payment or fulfillment fields', order['status'] == 'PENDING_PAYMENT'
                and all(order[k] is None for k in ['paymentMethod', 'paymentNo', 'paidAt', 'cancelledAt', 'shippedAt', 'completedAt']))
        for line in lines:
            old = a['product'][str(line['productId'])]
            h.check(label + ' product snapshot '+str(line['productId']), line['skuSnapshot'] == old['sku']
                    and line['productNameSnapshot'] == old['name'] and line['coverImageSnapshot'] == old['coverImage']
                    and Decimal(line['unitPrice']) == Decimal(old['price'])
                    and Decimal(line['lineAmount']) == Decimal(line['unitPrice']) * line['quantity'])
        return order, lines

    def only_rows(self, label, a, b, table, ids, fields):
        ids = {str(i) for i in ids}
        self.h.check(label + ' only allowed '+table+' rows/fields', all(
            a[table].get(key) == b[table].get(key) if key not in ids else
            (a[table].get(key) is not None and b[table].get(key) is not None and
             all(a[table][key][field] == b[table][key][field] for field in a[table][key] if field not in fields))
            for key in set(a[table]) | set(b[table])))

    def C1(self):
        h = self.h
        alice, bob = self.clients(['alice', 'bob'])
        pid = h.pid('CSU-LMK-NOTE-01')
        h.fixture(f"UPDATE product SET stock=1,status='ON_SALE' WHERE id={pid};", 'C1-last-item-root-fixture')
        _, first = self.setup_cart(alice, [(pid, 1)], 1)
        _, second = self.setup_cart(bob, [(pid, 1)], 2)
        replies, before, a, after, b = self.pair('C1', [self.request('alice', alice, '/orders', first), self.request('bob', bob, '/orders', second)], 'product', pid)
        h.check('C1 one303 one409', sorted(r.status for r in replies) == [303, 409])
        winner = 1 if replies[0].status == 303 else 2
        loser = 3 - winner
        order, lines = self.one_order('C1', a, b, winner, [pid])
        h.check('C1 final stock0 version+1', b['product'][str(pid)]['stock'] == 0 and b['product'][str(pid)]['version'] == a['product'][str(pid)]['version'] + 1)
        h.check('C1 loser cart exact preserved winner cart cleared',
                [x for x in a['cart_item'].values() if x['userId'] == loser] == [x for x in b['cart_item'].values() if x['userId'] == loser]
                and not [x for x in b['cart_item'].values() if x['userId'] == winner])
        h.check('C1 no loser order or line residual', all(x['userId'] != loser for x in self.fresh_orders(a, b)) and lines[0]['quantity'] == 1)
        self.only_rows('C1', a, b, 'product', [pid], {'stock','version','updatedAt'})
        self.unchanged('C1', a, b, {'product', 'cart_item', 'sales_order', 'sales_order_item'})
        losing_client, old = (bob, second) if loser == 2 else (alice, first)
        retry = losing_client.post('/orders', old, expected=409, zero=True)
        h.check('C1 losing confirmation actually invalidated, not merely stock rejection', 'CHECKOUT_CONFIRMATION_INVALID' in retry.text)

    def C2(self):
        h = self.h
        alice, admin = self.clients(['alice', 'admin'])
        pid = h.pid('CSU-LMK-NOTE-01')
        h.fixture(f"UPDATE product SET stock=10,status='ON_SALE' WHERE id={pid};", 'C2-initial-stock10')
        _, form = self.setup_cart(alice, [(pid, 2)])
        requests = [self.request('buy2', alice, '/orders', form), self.request('restock3', admin, f'/products/{pid}/restock', {'quantity': 3}, 'a')]
        replies, before, a, after, b = self.pair('C2', requests, 'product', pid)
        h.check('C2 both303', [r.status for r in replies] == [303, 303])
        order, lines = self.one_order('C2', a, b, 1, [pid])
        h.check('C2 quantity2 total36', lines[0]['quantity'] == 2 and Decimal(order['totalAmount']) == Decimal('36.00'))
        h.check('C2 stock11 version+2 and cart clear', b['product'][str(pid)]['stock'] == 11 and b['product'][str(pid)]['version'] == a['product'][str(pid)]['version'] + 2 and not [x for x in b['cart_item'].values() if x['userId'] == 1])
        self.unchanged('C2', a, b, {'product', 'cart_item', 'sales_order', 'sales_order_item'})
        self.only_rows('C2', a, b, 'product', [pid], {'stock','version','updatedAt'})

    def C3(self):
        h = self.h
        alice, = self.clients(['alice'])
        pid = h.pid('CSU-LMK-NOTE-01')
        _, form = self.setup_cart(alice, [(pid, 2)])
        replies, before, a, after, b = self.pair('C3', [self.request('same-confirmation-1', alice, '/orders', form), self.request('same-confirmation-2', alice, '/orders', form)], 'product', pid, 1,
                'Actual concurrent HTTP with one shared server session. synchronized(session) serializes business entry: second request may wait on Java monitor, not a second simultaneous JDBC transaction.')
        h.check('C3 exactly one303 one409', sorted(r.status for r in replies) == [303, 409])
        h.check('C3 second same-session request sees consumed confirmation', 'CHECKOUT_CONFIRMATION_INVALID' in next(r.text for r in replies if r.status == 409))
        order, lines = self.one_order('C3', a, b, 1, [pid])
        h.check('C3 quantity2 total36 once', lines[0]['quantity'] == 2 and Decimal(order['totalAmount']) == Decimal('36.00'))
        h.check('C3 one stock/version change', b['product'][str(pid)]['stock'] == a['product'][str(pid)]['stock'] - 2 and b['product'][str(pid)]['version'] == a['product'][str(pid)]['version'] + 1)
        self.unchanged('C3', a, b, {'product', 'cart_item', 'sales_order', 'sales_order_item'})
        self.only_rows('C3', a, b, 'product', [pid], {'stock','version','updatedAt'})
        h.add(alice, h.pid('CSU-GRAD-BOX-01'), 1)
        preserve = h.snapshot()
        retry = alice.post('/orders', form, expected=409, zero=True)
        h.check('C3 original confirmation remains invalid', 'CHECKOUT_CONFIRMATION_INVALID' in retry.text)
        h.check('C3 old retry does not delete newly added cart row', h.snapshot() == preserve and len(h.cartrows(1)) == 1)

    def C4(self):
        h = self.h
        alice, other = self.clients(['alice', 'alice'])
        order = h.new_order85(alice)
        no = order['orderNo']
        requests = [self.request('payment', alice, f'/orders/{no}/payment', {'result': 'SUCCESS'}), self.request('cancel', other, f'/orders/{no}/cancel', {})]
        replies, before, a, after, b = self.pair('C4', requests, 'store_user', 1)
        h.check('C4 one303 one409', sorted(r.status for r in replies) == [303, 409])
        final = b['sales_order'][str(order['id'])]
        lines = [r for r in a['sales_order_item'].values() if r['orderId'] == order['id']]
        if final['status'] == 'PAID':
            h.check('C4 payment wins first credentials only', replies[0].status == 303 and final['paymentMethod'] == 'MOCK' and final['paymentNo'] and final['paidAt'] and final['cancelledAt'] is None and a['product'] == b['product'])
        else:
            h.check('C4 cancellation wins no payment credentials', final['status'] == 'CANCELLED' and replies[1].status == 303 and final['cancelledAt'] and all(final[k] is None for k in ['paymentMethod', 'paymentNo', 'paidAt']))
            for line in lines:
                old, now = a['product'][str(line['productId'])], b['product'][str(line['productId'])]
                h.check('C4 only once refund product'+str(line['productId']), now['stock'] == old['stock'] + line['quantity'] and now['version'] == old['version'] + 1)
        h.check('C4 no new orders and original snapshot retained', len(a['sales_order']) == len(b['sales_order']) and all(final[k] == a['sales_order'][str(order['id'])][k] for k in final if k not in {'status','updatedAt','paymentMethod','paymentNo','paidAt','cancelledAt'}))
        self.only_rows('C4', a, b, 'sales_order', [order['id']], {'status','updatedAt','paymentMethod','paymentNo','paidAt','cancelledAt'})
        self.only_rows('C4', a, b, 'product', [x['productId'] for x in lines], {'stock','version','updatedAt'})
        self.unchanged('C4', a, b, {'product', 'sales_order'})

    def C5(self):
        h = self.h
        alice, admin = self.clients(['alice', 'admin'])
        order = h.new_order85(alice)
        no = order['orderNo']
        requests = [self.request('payment', alice, f'/orders/{no}/payment', {'result': 'SUCCESS'}), self.request('shipment', admin, f'/orders/{no}/ship', {}, 'a')]
        replies, before, a, after, b = self.pair('C5', requests, 'sales_order', order['id'])
        final = b['sales_order'][str(order['id'])]
        h.check('C5 payment succeeds shipment is303or409', replies[0].status == 303 and replies[1].status in [303, 409])
        h.check('C5 legal serialized state', final['status'] == ('SHIPPED' if replies[1].status == 303 else 'PAID'))
        h.check('C5 first receipt/time retained', final['paymentMethod'] == 'MOCK' and final['paymentNo'] and final['paidAt'] and (final['shippedAt'] >= final['paidAt'] if final['status'] == 'SHIPPED' else final['shippedAt'] is None))
        self.only_rows('C5', a, b, 'sales_order', [order['id']], {'status','updatedAt','paymentMethod','paymentNo','paidAt','shippedAt'})
        self.unchanged('C5', a, b, {'sales_order'})

    def C6(self):
        h = self.h
        admin, other = self.clients(['admin', 'admin'])
        pid = h.pid('CSU-LMK-NOTE-01')
        product = h.product(pid)
        form = {key: '' if product.get(key) is None else product[key] for key in ['categoryId', 'name', 'price', 'summary', 'description', 'coverImage', 'sortOrder', 'version']}
        form['name'] = 'STEP13 concurrent edited product'
        image = dict(productVersion=product['version'], imagePath='images/catalog-placeholder.svg', altText='STEP13 concurrent album', sortOrder=0)
        replies, before, a, after, b = self.pair('C6', [self.request('details', admin, f'/products/{pid}', form, 'a'), self.request('album', other, f'/products/{pid}/images', image, 'a')], 'store_user', 4)
        h.check('C6 one303 one409', sorted(r.status for r in replies) == [303, 409])
        now = b['product'][str(pid)]
        new_images = [r for i, r in b['product_image'].items() if i not in a['product_image']]
        h.check('C6 parent version exactly+1', now['version'] == product['version'] + 1)
        h.check('C6 failed operation no write', (now['name'] == form['name'] and not new_images and a['product_image'] == b['product_image']) if replies[0].status == 303 else (now['name'] == product['name'] and len(new_images) == 1 and new_images[0]['productId'] == pid))
        self.only_rows('C6', a, b, 'product', [pid], {'name','version','updatedAt'})
        h.check('C6 existing image rows preserved', all(b['product_image'].get(k) == row for k, row in a['product_image'].items()))
        self.unchanged('C6', a, b, {'product', 'product_image'})

    def C7(self):
        h = self.h
        alice, admin = self.clients(['alice', 'admin'])
        pid = h.pid('CSU-LMK-NOTE-01')
        _, form = self.setup_cart(alice, [(pid, 1)])
        requests = [self.request('ongoing-order', alice, '/orders', form), self.request('disable', admin, '/customers/1/status', {'targetStatus': 'DISABLED'}, 'a')]
        replies, before, a, after, b = self.pair('C7', requests, 'store_user', 1)
        h.check('C7 admin disable303 and user commits-or302', replies[1].status == 303 and replies[0].status in [303, 302])
        h.check('C7 disabled account stamp advanced', b['store_user']['1']['status'] == 'DISABLED' and b['store_user']['1']['updatedAt'] > a['store_user']['1']['updatedAt'])
        if replies[0].status == 303:
            order, lines = self.one_order('C7 write before disable', a, b, 1, [pid])
            h.check('C7 committed prior write remains complete', b['product'][str(pid)]['stock'] == a['product'][str(pid)]['stock'] - 1
                    and b['product'][str(pid)]['version'] == a['product'][str(pid)]['version'] + 1
                    and lines[0]['quantity'] == 1 and Decimal(order['totalAmount']) == Decimal('18.00')
                    and not [x for x in b['cart_item'].values() if x['userId'] == 1])
        else:
            h.check('C7 rejected write has no partial order/cart/stock', all(a[t] == b[t] for t in TABLES if t != 'store_user'))
        alice.get('/cart', expected=302, zero=True)
        h.post(admin, '/customers/1/status', {'targetStatus': 'ENABLED'}, end='a')
        alice.get('/cart', expected=302, zero=True)
        self.unchanged('C7', a, b, {'store_user', 'product', 'cart_item', 'sales_order', 'sales_order_item'})
        self.only_rows('C7', a, b, 'store_user', [1], {'status','updatedAt'})
        self.only_rows('C7', a, b, 'product', [pid], {'stock','version','updatedAt'})

    def C8(self):
        h = self.h
        alice, other = self.clients(['alice', 'alice'])
        h.clear_cart(alice, 1)
        pid = h.pid('CSU-LMK-NOTE-01')
        requests = [self.request('add1', alice, '/cart/items', {'productId': pid, 'quantity': 1}), self.request('add2', other, '/cart/items', {'productId': pid, 'quantity': 2})]
        replies, before, a, after, b = self.pair('C8-add', requests, 'store_user', 1)
        own = [r for r in b['cart_item'].values() if r['userId'] == 1]
        h.check('C8 concurrent adds unique row exact quantity/version', [r.status for r in replies] == [303, 303] and len(own) == 1 and own[0]['quantity'] == 3 and own[0]['version'] == 1)
        h.check('C8 adds preserve every other account cart', all(b['cart_item'].get(k) == row for k, row in a['cart_item'].items() if row['userId'] != 1))
        self.unchanged('C8-add', a, b, {'cart_item'})
        row = own[0]
        requests = [self.request('add2', alice, '/cart/items', {'productId': pid, 'quantity': 2}), self.request('set4', other, f"/cart/items/{row['id']}/quantity", {'quantity': 4, 'version': row['version']})]
        replies, before, a, after, b = self.pair('C8-quantity', requests, 'store_user', 1)
        final = b['cart_item'][str(row['id'])]
        h.check('C8 add succeeds edit success-or-stale', replies[0].status == 303 and replies[1].status in [303, 409])
        h.check('C8 no lost quantity/version update', (final['quantity'], final['version']) == ((6, 3) if replies[1].status == 303 else (5, 2)))
        self.only_rows('C8-quantity', a, b, 'cart_item', [row['id']], {'quantity','version','updatedAt'})
        self.unchanged('C8-quantity', a, b, {'cart_item'})

    def enable_history(self):
        h = self.h
        query = "SELECT JSON_OBJECT('name',NAME,'enabled',ENABLED) FROM performance_schema.setup_consumers WHERE NAME IN ('events_statements_current','events_statements_history','events_statements_history_long') ORDER BY NAME;"
        old = [json.loads(line) for line in h.rows(query).splitlines()]
        h.sql("UPDATE performance_schema.setup_consumers SET ENABLED='YES' WHERE NAME IN ('events_statements_current','events_statements_history','events_statements_history_long');")
        h.record('faults/instrumentation.jsonl', dict(owned_mysql_uuid=h.result['mysql_uuid'], before=old, after=[json.loads(line) for line in h.rows(query).splitlines()], scope='External isolated server statement error observation only'))
        return old

    def trigger(self, label, table, event, condition):
        h = self.h
        self.verify_owned()
        name = 's13_' + label.lower() + '_' + secrets.token_hex(4)
        marker = 'STEP13_' + label + '_' + secrets.token_hex(6)
        statement = (f"CREATE TRIGGER `{h.schema}`.`{name}` BEFORE {event} ON `{table}` FOR EACH ROW BEGIN "
                     f"IF {condition} THEN SIGNAL SQLSTATE '45000' SET MYSQL_ERRNO=1644,MESSAGE_TEXT='{marker}'; END IF; END")
        try:
            h.sql('\nDELIMITER $$\n' + statement + '$$\nDELIMITER ;\n')
            created = h.rows('SELECT TRIGGER_NAME FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA=' + h.literal(h.schema) + ' AND TRIGGER_NAME=' + h.literal(name))
            h.check(label + ' isolated conditional trigger created', created == name)
            h.record('faults/triggers.jsonl', dict(case=label, schema=h.schema, trigger=name, marker=marker,
                     statement=statement, at_phase='CREATE', exact_owned_schema=True, production_source_changed=False))
            return name, marker
        except BaseException:
            h.sql(f'DROP TRIGGER IF EXISTS `{h.schema}`.`{name}`;')
            h.record('faults/triggers.jsonl', dict(case=label, schema=h.schema, trigger=name, at_phase='DROP_AFTER_CREATE_OR_CHECK_FAILURE'))
            raise

    def fault(self, label):
        h = self.h
        alice, = self.clients(['alice'])
        if label in ['D1', 'D2', 'D3']:
            first, second = h.pid('CSU-LMK-NOTE-01'), h.pid('CSU-GRAD-BOX-01')
            _, form = self.setup_cart(alice, [(first, 2), (second, 1)])
            if label == 'D1': table, event, condition = 'sales_order_item', 'INSERT', f'NEW.product_id IN ({first},{second})'
            elif label == 'D2': table, event, condition = 'product', 'UPDATE', f'OLD.id={max(first,second)} AND NEW.stock<OLD.stock'
            else:
                row_id = max(r['id'] for r in h.cartrows(1))
                table, event, condition = 'cart_item', 'DELETE', f'OLD.id={row_id} AND OLD.user_id=1'
            action = lambda: alice.post('/orders', form, expected=[409, 500], zero=True)
            order = None
        else:
            order = h.new_order85(alice)
            if label == 'D4':
                lines = [r for r in h.state()['sales_order_item'].values() if r['orderId'] == order['id']]
                table, event, condition = 'product', 'UPDATE', f"OLD.id={max(r['productId'] for r in lines)} AND NEW.stock>OLD.stock"
                action = lambda: h.post(alice, '/orders/'+order['orderNo']+'/cancel', {}, expected=[409, 500], zero=True)
            else:
                table, event, condition = 'sales_order', 'UPDATE', f"OLD.id={order['id']} AND OLD.status='PENDING_PAYMENT' AND NEW.status='PAID'"
                action = lambda: h.post(alice, '/orders/'+order['orderNo']+'/payment', {'result': 'SUCCESS'}, expected=[409, 500], zero=True)
        name, marker = self.trigger(label, table, event, condition)
        try:
            before, a = h.snapshot(), h.state()
            heads = {int(t):int(e) for t,e in (line.split('\t') for line in h.rows('SELECT THREAD_ID,MAX(EVENT_ID) FROM performance_schema.events_statements_history_long GROUP BY THREAD_ID;').splitlines())}
            response = action()
            hidden = all(text not in response.text for text in [marker,'SQLSTATE','SQLException','jdbc:mysql:','java.lang.','org.springframework.','org.apache.ibatis.','\tat '])
            h.record('faults/http-safety.jsonl', dict(case=label, schema=h.schema, http_sequence=response.sequence,
                     observed_status=response.status, signal_SQL_or_stack_not_exposed=hidden,
                     generic500_or_stable409=True, private_raw_values_recorded=False))
            h.check(label+' technical fault details hidden from page', hidden)
            after, b = h.snapshot(), h.state()
            h.db_pair(label+'-fault-rollback', before, a, after, b, trigger=name, signal_marker=marker, http_sequence=response.sequence, fault_injection='Isolated schema conditional BEFORE trigger SIGNAL45000')
            h.check(label + ' complete seven-table rollback', before == after and a == b)
            events = [json.loads(line) for line in h.rows("SELECT JSON_OBJECT('threadId',THREAD_ID,'eventId',EVENT_ID,'nestingEventId',NESTING_EVENT_ID,'eventName',EVENT_NAME,'errno',MYSQL_ERRNO,'sqlstate',RETURNED_SQLSTATE,'message',MESSAGE_TEXT,'objectSchema',OBJECT_SCHEMA,'objectName',OBJECT_NAME,'rowsAffected',ROWS_AFFECTED) FROM performance_schema.events_statements_history_long WHERE MYSQL_ERRNO=1644 AND MESSAGE_TEXT=" + h.literal(marker) + ' ORDER BY THREAD_ID,EVENT_ID;').splitlines()]
            h.record('faults/signal-events.jsonl', dict(case=label, schema=h.schema, marker=marker, trigger=name, observed_events=events, raw_SQL_TEXT_not_recorded=True))
            h.check(label + ' actual database SIGNAL1644 observed', bool(events) and all(e['errno'] == 1644 and e['message'] == marker for e in events))
            trace = []
            for thread in sorted({int(e['threadId']) for e in events}):
                upper = max(int(e['eventId']) for e in events if int(e['threadId']) == thread)
                query = "SELECT JSON_OBJECT('threadId',THREAD_ID,'eventId',EVENT_ID,'nestingEventId',NESTING_EVENT_ID,'eventName',EVENT_NAME,'errno',MYSQL_ERRNO,'rowsAffected',ROWS_AFFECTED,'digestText',DIGEST_TEXT,'objectSchema',OBJECT_SCHEMA,'objectName',OBJECT_NAME) FROM performance_schema.events_statements_history_long WHERE THREAD_ID="+str(thread)+' AND EVENT_ID>'+str(heads.get(thread,0))+' AND EVENT_ID<='+str(upper)+' ORDER BY EVENT_ID;'
                trace.extend(json.loads(line) for line in h.rows(query).splitlines())
            h.record('faults/intermediate-statements.jsonl', dict(case=label, schema=h.schema, trigger=name,
                     query_scope='Only fault app THREAD after pre-request event head through SIGNAL; no root seed thread, no SQL_TEXT or parameters', events=trace))
            successful = [e for e in trace if e['errno'] == 0 and e['rowsAffected'] == 1]
            def writes(verb, table):
                return [e for e in successful if re.search(r'\b'+verb+r'\s+(?:INTO\s+|FROM\s+)?'+table+r'\b', (e.get('digestText') or '').replace('`',''), re.I)]
            if label in ['D1','D2','D3']:
                h.check(label+' master insert actually executed before fault', bool(writes('INSERT','sales_order')))
            if label in ['D2','D3']:
                h.check(label+' two immutable line inserts executed before fault', len(writes('INSERT','sales_order_item')) == 2)
            if label == 'D2':h.check('D2 first product deduction executed before second failure', len(writes('UPDATE','product')) == 1)
            if label == 'D3':
                h.check('D3 both product deductions executed before cart failure', len(writes('UPDATE','product')) == 2)
                h.check('D3 first cart delete executed before second failure', len(writes('DELETE','cart_item')) == 1)
            if label == 'D4':h.check('D4 first product refund executed before second failure', len(writes('UPDATE','product')) == 1)
            if order:
                unchanged = h.order(order['orderNo'])
                h.check(label + ' pending state and payment/cancel times remain empty', unchanged['status'] == 'PENDING_PAYMENT' and all(unchanged[k] is None for k in ['paymentMethod', 'paymentNo', 'paidAt', 'cancelledAt']))
            return dict(case=label, schema=h.schema, http_sequence=response.sequence, observed_status=response.status,
                        seven_tables_identical=True, actual_signal_events=len(events), rollback_scope='Committed row data; no claim to undo auto-increment allocator gaps')
        finally:
            h.sql(f'DROP TRIGGER IF EXISTS `{h.schema}`.`{name}`;')
            remaining = int(h.rows('SELECT COUNT(*) FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA=' + h.literal(h.schema) + ' AND TRIGGER_NAME=' + h.literal(name)))
            h.record('faults/triggers.jsonl', dict(case=label, schema=h.schema, trigger=name, at_phase='DROP', remaining=remaining))
            h.check(label + ' trigger removed with no residue', remaining == 0)


def run_concurrency(h):
    """Single orchestrator only. No background reset or automatic business-request retry."""
    suite = Suite(h)
    suite.compile()
    original = h.snapshot()
    results = []
    for label, tst in C_MAP.items():
        with h.case(tst, label):
            suite.begin(label)
            getattr(suite, label)()
            item = dict(case=label, tst=tst, result='PASS', schema=h.schema, finished_at_utc=utc())
            h.record('concurrency/results.jsonl', item)
            results.append(item)
    suite.restore()
    h.check('all C cases preserve original main schema', original == h.snapshot())
    return dict(completed=True, scenarios=results, independent_schemas=suite.created,
                C3_scope='Concurrent HTTP, same-session application monitor serializes business transaction entry',
                C8_scope='Two separately synchronized phases within one independent fixture: same-SKU adds then add/versioned quantity edit')


def run_faults(h):
    """Five fresh schemas, existing app routes, conditional triggers, always DROP after request."""
    suite = Suite(h)
    original = h.snapshot()
    settings = suite.enable_history()
    results = []
    primary_failure = None
    try:
        for label, tst in D_MAP.items():
            with h.case(tst, label):
                suite.begin(label)
                result = suite.fault(label)
                result.update(tst=tst, result='PASS', finished_at_utc=utc())
                h.record('faults/results.jsonl', result)
                results.append(result)
        suite.restore()
    except BaseException as failed:
        primary_failure = failed
        raise
    finally:
        try:
            for row in settings:
                h.sql('UPDATE performance_schema.setup_consumers SET ENABLED=' + h.literal(row['enabled']) + ' WHERE NAME=' + h.literal(row['name']) + ';')
            h.record('faults/instrumentation.jsonl', dict(restored_consumer_settings=settings, owned_mysql_uuid=h.result['mysql_uuid']))
        except BaseException as restoration_failed:
            h.record('faults/instrumentation.jsonl', dict(restoration_failed_class=type(restoration_failed).__name__, primary_failure_preserved=primary_failure is not None))
            if primary_failure is None:
                raise
    h.check('all D cases preserve original main schema', original == h.snapshot())
    return dict(completed=True, cases=results, independent_schemas=suite.created,
                mechanism='Owned isolated MySQL BEFORE triggers SIGNAL SQLSTATE45000; no production hooks',
                HTTP_failure_status='Actual500 or409 retained according to exception translation; no fixed-code fabrication')
