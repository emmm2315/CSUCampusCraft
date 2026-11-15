"""The only new full STEP13 orchestrator. It never imports a historical evidence runner."""
from pathlib import Path
import json,os,subprocess,sys,traceback,urllib.parse
from harness import Harness,TABLES,RUNTIME,scanner_regression,digest
import serial_user,serial_admin,native_jdbc

HERE=Path(__file__).resolve().parent
REPO=Path('D:/Github Projects/CSUCampusCraft')
SHA=os.environ.get('STEP13_TESTED_SHA','d577179e4468354552d3f5f48d624a4296ee3cfb')

def bootstrap(h):
    with h.case('TST-32','empty-demo'):
        h.create_schema('csu13_empty','empty');h.start_apps('csu13_empty');empty=h.snapshot();h.check('SQL01 seven tables literally empty',[empty[t]['rows'] for t in TABLES]==[0]*7)
        c=h.Client('literal-empty');home=c.get('/',expected=200);h.check('literal empty home theme0',home.dom.find(lambda n:n.a.get('data-theme-count')=='0') is not None);serial_user.product_list(h,c);c.get('/products/1',expected=404)
        a,r=h.login(end='a',username='admin',expected=200);a.get('/',end='a',expected=302);h.check('no account can log into literal empty schema',h.snapshot()==empty)
        h.stop_apps();h.create_schema('csucampuscraft','demo');h.schema='csucampuscraft';seed=h.snapshot();h.check('SQL02 original demo rows',[seed[t]['rows'] for t in TABLES]==[4,15,60,100,10,10,20]);h.save('demo-original.json',json.dumps(seed,indent=2))
        checks=json.loads(h.rows("SELECT JSON_ARRAYAGG(JSON_OBJECT('table',TABLE_NAME,'name',CONSTRAINT_NAME,'enforced',ENFORCED)) FROM information_schema.TABLE_CONSTRAINTS WHERE CONSTRAINT_SCHEMA="+h.literal(h.schema)+" AND CONSTRAINT_TYPE='CHECK'"));h.check('35 enforced CHECK constraints',len(checks)==35 and all(x['enforced']=='YES' for x in checks));h.save('live-check-constraints.json',json.dumps(checks,ensure_ascii=False,indent=2))
        h.sql('INSERT INTO csu13_empty.store_user(id,username,password_hash,display_name,role,status,email,phone,created_at,updated_at) SELECT id,username,password_hash,display_name,role,status,email,phone,created_at,updated_at FROM csucampuscraft.store_user WHERE id=4',False)
        h.start_apps('csu13_empty')
        with h.case('TST-37','empty-demo'):
            a,_=h.login(end='a',username='admin');r=a.get('/',end='a',expected=200);n=r.dom.find(lambda n:n.a.get('data-page-id')=='A02');h.check('ADMIN-only business-zero five cards',n is not None and all(n.a[k]=='0' for k in ['data-on-sale-count','data-draft-count','data-paid-order-count','data-enabled-customer-count','data-disabled-customer-count']));a.get('/customers',end='a',expected=200);a.get('/orders',end='a',expected=200);a.get('/customers/1',end='a',expected=404)
            h.check('empty schema retains only ADMIN fixture',[h.snapshot()[t]['rows'] for t in TABLES]==[1,0,0,0,0,0,0]);h.save('empty-business-scope.json',json.dumps(dict(schema='csu13_empty',kept_ADMIN_id=4,store_user_rows=1,not_a_seven_table_zero_login=True),indent=2))
            products=a.get('/products',end='a',expected=200);h.check('empty admin product list count0',products.dom.find(lambda n:n.a.get('data-product-count')=='0') is not None);a.get('/categories',end='a',expected=200)
            for path in ['/products/1/edit','/products/1/images','/orders/UNKNOWN']:a.get(path,end='a',expected=404)
        h.stop_apps();h.start_apps('csucampuscraft');h.check('demo not touched by empty scenario',h.snapshot()==seed)
    import seed_failure
    seed_failure.run(h)
    native_jdbc.run(h)
    user,_=h.login(username='alice');admin,_=h.login(end='a',username='admin');return user,admin

def browser(h,fixtures):
    # A separate pair of sessions means GET /checkout cannot replace a future backend test confirmation.
    user,_=h.login(username='alice');admin,_=h.login(end='a',username='admin');h.clear_cart(user);h.add(user,h.pid('CSU-LMK-NOTE-01'),2);h.add(user,h.pid('CSU-GRAD-BOX-01'))
    admin_fixture=json.loads((h.evidence/'serial-admin-fixtures.json').read_text(encoding='utf-8'))
    public=dict(sourceSha=h.tested_sha,userBase=h.base('u')+'/',adminBase=h.base('a')+'/',graduationCategoryId=fixtures['graduationCategoryId'],giftProductId=fixtures['giftProductId'],orderNo=fixtures['main_order_no'],customerId=1,missingProductId=fixtures['missingProductId'],noGalleryProductId=fixtures['noGalleryProductId'],adminAlbumProductId=admin_fixture['product_id'])
    h.save('browser-public-fixture.json',json.dumps(public,ensure_ascii=False,indent=2))
    fixture_path=h.evidence/'browser-public-fixture.json'
    h.check('browser public fixture file roundtrip',json.loads(fixture_path.read_text(encoding='utf-8'))==public)
    env=h.app_env();env.update(STEP13_UI_FIXTURE=str(fixture_path),STEP13_UI_USER_COOKIE=user.cookie('u'),STEP13_UI_ADMIN_COOKIE=admin.cookie('a'),STEP13_UI_OUT=str(h.evidence/'browser'))
    before=h.snapshot();a=h.state();source=HERE.parent/'ui/verify_browser_step13.cjs';h.save('verify_browser_step13.cjs',source.read_text(encoding='utf-8'));p=h.command([RUNTIME/'node/bin/node.exe',source],env=env,timeout=300);after=h.snapshot();b=h.state()
    h.save('browser-stdout.log',p.stdout.decode('utf-8',errors='replace'));h.save('browser-stderr.log',p.stderr.decode('utf-8',errors='replace'));h.db_pair('browser-GET-batch',before,a,after,b,observation='Genuine batch before/after; per-navigation metadata after-only; no browser POST allowed')
    h.check('browser new helper exit',p.returncode==0);data=json.loads((h.evidence/'browser/result.json').read_text(encoding='utf-8'));h.check('browser final PASS',data['overall']=='PASS');h.check('browser batch seven-table zero DB writes',before==after)
    h.mark_p0('TST-04','browser',True,dict(evidence='browser/result.json',scope='Actual missing-image load/error fallback and no-gallery loaded cover; DOM assertions, no extra PNG'))
    h.result['browser_summary']=dict(result_file='browser/result.json',screenshots=len(data.get('screenshots',[])),checks=len(data.get('checks',[])),navigation_database_boundary='After-only per navigation, genuine whole-batch before/after; no business POST')

def restart(h,fixtures):
    before=h.snapshot();a=h.state();h.stop_apps();h.start_apps();after=h.snapshot();b=h.state();h.db_pair('dual-JAR-restart',before,a,after,b,observation='Fresh processes, same owned MySQL; database full fields persistent')
    with h.case('TST-09','restart'):
        h.check('seven-table persistence through both app restarts',before==after);u,_=h.login(username='alice');bob,_=h.login(username='bob');serial_user.badge(h,u.get('/cart',expected=200),1);serial_user.badge(h,bob.get('/cart',expected=200),2);h.check('other account nonempty cart persists',bool(h.cartrows(2)))
    with h.case('TST-32','restart'):
        admin,_=h.login(end='a',username='admin');serial_user.order_detail(h,u,fixtures['main_order_no']);serial_user.order_detail(h,admin,fixtures['main_order_no'],'a');h.check('main actual85 remains SHIPPED with receipt',h.order(fixtures['main_order_no'])['status']=='SHIPPED' and h.order(fixtures['main_order_no'])['paymentNo'] is not None);serial_admin.dashboard(h,admin,'post-restart');h.check('album rows persist full fields',a['product_image']==b['product_image'])
        h.save('human-reproduction-boundary.json',json.dumps(dict(current_round='User-authorized Codex automated clean reproduction and restart',new_human_cross_reproduction='NOT_IMPLEMENTED',prior_human_review='Only its original recorded subset; not reused as this final-SHA39P0 run',group_peer_review='NOT_IMPLEMENTED'),ensure_ascii=False,indent=2))

def main():
    attempt=sys.argv[1] if len(sys.argv)>1 else ''
    h=Harness(HERE,REPO,SHA,attempt);error=None
    try:
        regression=scanner_regression();h.check('new nine-case raw scanner self-test',regression['overall']=='PASS' and regression['passed']==9);h.save('raw-scanner-self-test.json',json.dumps(regression,indent=2))
        tools=[]
        for source in sorted(HERE.glob('*')):
            if source.is_file() and source.suffix in ['.py','.java','.json'] and source.name not in ['result.json']:
                raw=source.read_bytes();h.save('tools/'+source.name,raw);tools.append(dict(path=source.name,sha256=digest(raw)))
        h.save('tool-inputs.json',json.dumps(tools,indent=2));h.initialize();user,admin=bootstrap(h)
        fixtures=serial_user.run(h,user,admin);user,admin=serial_admin.run(h,fixtures['user'],fixtures['admin']);browser(h,fixtures);restart(h,fixtures)
        main_schema=h.schema;main_before=h.snapshot();main_state=h.state()
        import concurrency_faults
        concurrency_faults.run_concurrency(h);concurrency_faults.run_faults(h)
        h.stop_apps();h.start_apps(main_schema);h.check('isolated C/D schemas preserve main seven tables',h.snapshot()==main_before);h.save('main-final.json',json.dumps(h.snapshot(),indent=2))
        h.check('all39 P0 current source segments complete',len(h.matrix())==39 and all(x['result']=='PASS' for x in h.matrix()))
    except BaseException as exc:error=exc;h.save('failure.txt',traceback.format_exc());print(type(exc).__name__+': '+str(exc),flush=True)
    finally:result=h.finish(error);print('STEP13_RESULT '+str(h.evidence/'result.json')+' '+result['overall'],flush=True)
    return 0 if result['overall']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
