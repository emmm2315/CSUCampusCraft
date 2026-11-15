"""New INIT-02 transaction failure proof using untouched current SQL source in a new schema."""
import re,json,hashlib
def run(h):
    name='csu13_seed_failure';h.create_schema(name,'empty')
    source=(h.repo/'database/02-schema-with-demo.sql').read_bytes();text=source.decode('utf-8-sig')
    begin=text.index('START TRANSACTION;');end=text.rindex('COMMIT;')
    payload=text[begin:end]+"SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='STEP13_SEED_TRANSACTION_FAILURE';\nCOMMIT;\n"
    p=h.sql(payload,db=name,fail_ok=True)
    h.check('fresh seed fixture client stops at deliberate precommit SIGNAL',p.returncode!=0 and b'STEP13_SEED_TRANSACTION_FAILURE' in p.stderr)
    h.save('initialization/seed-failure-stderr.log',p.stderr.decode('utf-8',errors='replace'))
    counts={t:int(h.rows('SELECT COUNT(*) FROM '+t,db=name)) for t in ['store_user','category','product','product_image','cart_item','sales_order','sales_order_item']}
    h.check('seed DML entire transaction rolled back while7DDL retained',list(counts.values())==[0]*7)
    checks=[json.loads(x) for x in h.rows("SELECT JSON_OBJECT('table',TABLE_NAME,'name',CONSTRAINT_NAME,'enforced',ENFORCED) FROM information_schema.TABLE_CONSTRAINTS WHERE CONSTRAINT_SCHEMA="+h.literal(name)+" AND CONSTRAINT_TYPE='CHECK' ORDER BY TABLE_NAME,CONSTRAINT_NAME",db=name).splitlines()]
    h.check('fresh empty schema35CHECK allENFORCED',len(checks)==35 and all(x['enforced']=='YES' for x in checks))
    h.save('initialization/seed-failure.json',json.dumps(dict(source_sql_sha256=hashlib.sha256(source).hexdigest(),schema=name,untouched_repository_sql=True,test_only_in_memory_dml_payload_sha256=hashlib.sha256(payload.encode('utf-8')).hexdigest(),injection="SIGNAL SQLSTATE '45000' immediately before source COMMIT",exit_code=p.returncode,counts=counts,checks=checks,result='PASS',seed_rows_or_credentials_recorded=False),ensure_ascii=False,indent=2))
