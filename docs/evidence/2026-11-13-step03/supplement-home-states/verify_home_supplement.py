"""Independent extra home-state scope; never reruns or overwrites full attempts."""
from pathlib import Path
import textwrap
_helper=Path(__file__).parent/'verify_step03.py'
_source=_helper.read_text(encoding='utf-8-sig')
_prefix=_source.split('restore_actions=[]\ntry:',1)[0]
_prefix=_prefix.replace("re.fullmatch(r'attempt[1-9][0-9]*',RUN)","re.fullmatch(r'supplement-home-states',RUN)")
exec(compile(_prefix,str(_helper),'exec'),globals())
restore_actions=[]
try:
    # Reuse reviewed private DB/source/toolchain setup, stopping before full-suite cases.
    _setup=_source.split('restore_actions=[]\ntry:\n',1)[1].split('    plans=[]',1)[0]
    exec(compile(textwrap.dedent(_setup),str(_helper)+'[setup]','exec'),globals())
    save(EV/'verify_step03.py',_source)
    save(EV/'verify_home_supplement.py',Path(__file__).read_text(encoding='utf-8-sig'))
    previous=json.loads((HERE/'evidence'/'attempt3'/'result.json').read_text(encoding='utf-8-sig'))
    check('same-tested-sha-as-full-suite',TESTED==previous['tested_code_sha'])
    check('same-user-jar-as-full-suite',result['csucampuscraft-user_jar_sha256']==previous['csucampuscraft-user_jar_sha256'])
    check('same-admin-jar-as-full-suite',result['csucampuscraft-admin_jar_sha256']==previous['csucampuscraft-admin_jar_sha256'])
    original=snapshot();save(EV/'database-original.json',json.dumps(original,indent=2))
    originals=[x.split('\t') for x in rows('SELECT id,stock,status FROM product ORDER BY id;').splitlines()]
    stock1=next(x[1] for x in originals if x[0]=='1')
    restore_stock='UPDATE product SET stock='+stock1+',updated_at=updated_at WHERE id=1;'
    restore_status='UPDATE product SET status=CASE id '+''.join('WHEN '+x[0]+" THEN '"+x[2]+"' " for x in originals)+'END,updated_at=updated_at;'
    with socket.socket() as s:s.bind(('127.0.0.1',8080))
    user=launch('csucampuscraft-user',8080,'csucampuscraft');client=Client()
    restore_actions.append(restore_stock)
    sql('UPDATE product SET stock=0,updated_at=updated_at WHERE id=1;','csucampuscraft')
    record('fixtures.jsonl',{'fixture':'featured-product-sold-out','temporary_product_ids':[1],'change':'stock=0','created_by':'isolated root SQL only','application_account':'SELECT only','source_sql_changed':False})
    before=snapshot();save(EV/'database-sold-out-before-reads.json',json.dumps(before,indent=2))
    page=home(client)
    featured=marker(page,'data-section','featured')
    card=marker(featured,'data-product-id','1')
    check('sold-out-featured-still-visible',card is not None and card.a.get('data-stock')=='0' and '售罄' in card.text())
    browser('sold-out-home',[{'name':'featured-sold-out','path':'/','kind':'home','status':200}])
    after=snapshot();save(EV/'database-sold-out-after-reads.json',json.dumps(after,indent=2))
    check('sold-out-home-zero-app-write',after==before)
    sql(restore_stock,'csucampuscraft');restore_actions.clear()
    check('sold-out-fixture-restored',snapshot()==original)
    restore_actions.append(restore_status)
    sql("UPDATE product SET status='DRAFT',updated_at=updated_at;",'csucampuscraft')
    record('fixtures.jsonl',{'fixture':'all-products-draft-themes-retained','temporary_product_count':60,'change':'all product.status=DRAFT','created_by':'isolated root SQL only','application_account':'SELECT only','source_sql_changed':False})
    before=snapshot();save(EV/'database-all-draft-before-reads.json',json.dumps(before,indent=2))
    page=home(client)
    check('all-draft-five-theme-navigation',marker(page,'data-theme-count').a['data-theme-count']=='5')
    check('all-draft-distinct-product-empty-states','暂无可售商品，稍后再来看看。' in page.text() and '暂无可售商品，可稍后再来看看。' in page.text() and '暂无主题' not in page.text())
    form=page.find(lambda n:n.tag=='form' and n.a.get('role')=='search')
    check('all-draft-search-form-remains',form is not None and clean_href(form.a.get('action',''))=='/products' and form.find(lambda n:n.tag=='input' and n.a.get('name')=='q') is not None)
    verify_list(client,{},'all-draft-global')
    verify_list(client,{'q':'毕业'},'all-draft-search')
    for theme_id in range(1,6):verify_list(client,{'categoryId':theme_id,'type':'ALL'},'all-draft-theme-'+str(theme_id))
    browser('all-draft-home',[{'name':'all-products-draft','path':'/','kind':'home','status':200}])
    after=snapshot();save(EV/'database-all-draft-after-reads.json',json.dumps(after,indent=2))
    check('all-draft-home-zero-app-write',after==before)
    sql(restore_status,'csucampuscraft');restore_actions.clear()
    final=snapshot();save(EV/'database-final.json',json.dumps(final,indent=2))
    check('all-supplement-fixtures-restored',final==original)
    check('supplement-source-inputs-stable',all(hashlib.sha256((REPO/line.split('  ',1)[1]).read_bytes()).hexdigest()==line.split('  ',1)[0] for line in manifest.splitlines()))
    result.update(overall='PASS',scope='Additional two home states only; does not replace full attempt3',full_suite_attempt='attempt3')
except Exception as e:
    result['overall']='FAIL';result['error']=scrub(type(e).__name__+': '+str(e))
    save(EV/'failure.txt',traceback.format_exc());print(result['error'],flush=True)
finally:
    if restore_actions and server and server.poll() is None:
        restored=True
        for q in restore_actions:
            try:sql(q,'csucampuscraft')
            except Exception:restored=False
        result['fixture_cleanup_succeeded']=restored
    for p in processes:stop(p)
    if server and server.poll() is None:
        try:command([MYSQL/'mysqladmin.exe','--no-defaults','--no-login-paths','--protocol=TCP','--host=127.0.0.1',f'--port={mysqlport}','--user=root','shutdown'],env=env,timeout=15);server.wait(timeout=15)
        except Exception:stop(server)
    for h in handles:h.close()
    for p in private_files:p.unlink(missing_ok=True)
    for p in BASE.glob('*.log'):save(EV/p.name,p.read_text(encoding='utf-8',errors='replace'))
    result['tracked_processes_stopped']=all(p.poll() is not None for p in processes) and (server is None or server.poll() is not None)
    save(EV/'result.json',json.dumps(result,ensure_ascii=False,indent=2))
    print('RESULT '+str(EV/'result.json'),flush=True)
if result['overall']!='PASS':raise SystemExit(1)
