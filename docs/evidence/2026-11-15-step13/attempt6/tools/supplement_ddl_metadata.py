"""Fresh database-only INIT02 supplement: full CHECK predicates and indexes from both sources."""
from pathlib import Path
import json,re,sys,traceback
from harness import Harness
ROOT=Path(__file__).resolve().parents[1];REPO=Path('D:/Github Projects/CSUCampusCraft');SHA='d577179e4468354552d3f5f48d624a4296ee3cfb'
def main():
    stage=ROOT/'ddl-metadata-supplement';stage.mkdir(exist_ok=True)
    plan=dict(scope='Database-only full CHECK/index metadata; no HTTP or new39-P0 verdict',cases=[dict(id='INIT-02',required_segments=['metadata'],assertion_plan='SQL01/02 live35 CHECK names/predicates/enforced and index columns match')])
    (stage/'p0-plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8');h=Harness(stage,REPO,SHA,'attempt1');h.result['scope']=plan['scope'];error=None
    try:
        h.save('tools/'+Path(__file__).name,Path(__file__).read_bytes());h.save('tools/harness.py',Path(__file__).with_name('harness.py').read_bytes());h.initialize()
        matrices={};indexes={};counts={}
        with h.case('INIT-02','metadata'):
            expected={(a,b) for a,b in re.findall(r'\|\s*`(\w+)`\s*\|\s*`(ck_[^`]+)`\s*\|',(REPO/'docs/数据库设计.md').read_text(encoding='utf-8'))}
            h.check('LLD enumerates35 named CHECK constraints',len(expected)==35)
            for schema,kind in [('csu13_ddl_empty','empty'),('csu13_ddl_demo','demo')]:
                h.create_schema(schema,kind);h.schema=schema;counts[kind]=h.snapshot()
                query="SELECT JSON_OBJECT('table',tc.TABLE_NAME,'name',tc.CONSTRAINT_NAME,'predicate',cc.CHECK_CLAUSE,'enforced',tc.ENFORCED) FROM information_schema.TABLE_CONSTRAINTS tc JOIN information_schema.CHECK_CONSTRAINTS cc ON cc.CONSTRAINT_SCHEMA=tc.CONSTRAINT_SCHEMA AND cc.CONSTRAINT_NAME=tc.CONSTRAINT_NAME WHERE tc.CONSTRAINT_SCHEMA="+h.literal(schema)+" AND tc.CONSTRAINT_TYPE='CHECK' ORDER BY tc.TABLE_NAME,tc.CONSTRAINT_NAME"
                matrices[kind]=[json.loads(x) for x in h.rows(query,db=schema).splitlines()]
                h.check(kind+'35 live CHECK names match LLD and allENFORCED',len(matrices[kind])==35 and {(x['table'],x['name']) for x in matrices[kind]}==expected and all(x['enforced']=='YES' for x in matrices[kind]))
                query="SELECT JSON_OBJECT('table',TABLE_NAME,'index',INDEX_NAME,'nonUnique',NON_UNIQUE,'column',COLUMN_NAME,'sequence',SEQ_IN_INDEX) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA="+h.literal(schema)+" ORDER BY TABLE_NAME,INDEX_NAME,SEQ_IN_INDEX"
                indexes[kind]=[json.loads(x) for x in h.rows(query,db=schema).splitlines()]
            h.check('both source scripts produce identical full normalized predicates',matrices['empty']==matrices['demo'])
            h.check('both source scripts produce identical index columns/order/uniqueness',indexes['empty']==indexes['demo'])
            h.check('structure7zero and demoexpected7counts',[counts['empty'][x]['rows'] for x in ['store_user','category','product','product_image','cart_item','sales_order','sales_order_item']]==[0]*7 and [counts['demo'][x]['rows'] for x in ['store_user','category','product','product_image','cart_item','sales_order','sales_order_item']]==[4,15,60,100,10,10,20])
            h.save('full-check-predicates.json',json.dumps(matrices,ensure_ascii=False,indent=2));h.save('indexes.json',json.dumps(indexes,ensure_ascii=False,indent=2));h.save('schema-counts.json',json.dumps(counts,ensure_ascii=False,indent=2))
    except BaseException as exc:error=exc;h.save('failure.txt',traceback.format_exc())
    finally:r=h.finish(error);print('DDL_METADATA_RESULT '+r['overall'],flush=True)
    return 0 if r['overall']=='PASS' else 1
if __name__=='__main__':sys.exit(main())
