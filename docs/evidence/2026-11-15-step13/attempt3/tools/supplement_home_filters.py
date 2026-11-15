"""New current-SHA supplemental edge checks, separate fresh datadir; never reuses old results."""
from pathlib import Path
import json,sys,hashlib,traceback
from harness import Harness
from serial_user import product_list
ROOT=Path(__file__).resolve().parents[1]
REPO=Path('D:/Github Projects/CSUCampusCraft')
SHA='d577179e4468354552d3f5f48d624a4296ee3cfb'

def home(h,c):
    r=c.get('/',expected=200);data=h.state();sale=[p for p in data['product'].values() if p['status']=='ON_SALE']
    for kind,expected in [('newest',sorted(sale,key=lambda p:(p['createdAt'],p['id']),reverse=True)[:3]),('featured',sorted(sale,key=lambda p:(p['sortOrder'],p['id']))[:4])]:
        section=r.dom.find(lambda n:n.a.get('data-section')==kind)
        cards=section.all(lambda n:n.tag=='article' and 'data-product-id' in n.a) if section else []
        h.check(kind+' exact SQL list and bound',[int(n.a['data-product-id']) for n in cards]==[p['id'] for p in expected])
        for n,p in zip(cards,expected):
            if p['stock']==0:h.check(kind+' selected zero stock visibly soldout','售罄' in n.text(),{'product_id':p['id'],'http':r.sequence})
    return r

def main():
    stage=ROOT/'home-filter-supplement';stage.mkdir(exist_ok=True)
    plan=dict(scope='Two supplementary final-SHA home/filter edge cases, not a separate39-P0 full run',cases=[dict(id='TST-02',required_segments=['home-edges'],assertion_plan='Selected home zero-stock, created/sort ties, five-theme no-sale, graduation missing'),dict(id='TST-03',required_segments=['combined-filters'],assertion_plan='Simultaneous root/type/name with pagination/count and retained conditions')])
    (stage/'p0-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    h=Harness(stage,REPO,SHA,'attempt1');h.result['scope']=plan['scope'];error=None
    try:
        for p in [Path(__file__),Path(__file__).with_name('harness.py'),Path(__file__).with_name('serial_user.py')]:h.save('tools/'+p.name,p.read_bytes())
        h.initialize();h.create_schema('csucampuscraft','demo');h.start_apps();client=h.Client('supplement-public')
        original=h.snapshot();data=h.state()
        with h.case('TST-02','home-edges'):
            home(h,client)
            selected=sorted((p for p in data['product'].values() if p['status']=='ON_SALE'),key=lambda p:p['id'])[:2]
            ids=','.join(str(p['id']) for p in selected)
            h.fixture("UPDATE product SET stock=0,sort_order=0,created_at='2030-01-01 00:00:00.000000',updated_at=updated_at WHERE id IN ("+ids+")",'supplement home zero-stock and tie fixture')
            home(h,client)
            for p in selected:
                h.fixture('UPDATE product SET stock='+str(p['stock'])+',sort_order='+str(p['sortOrder'])+',created_at='+h.literal(p['createdAt'])+',updated_at='+h.literal(p['updatedAt'])+' WHERE id='+str(p['id']),'restore original home fixture row')
            graduation=next(x for x in data['category'].values() if x['code']=='GRADUATION' and x['parentId'] is None)
            h.fixture("UPDATE category SET code='NO_GRAD_THEME',updated_at=updated_at WHERE id="+str(graduation['id']),'missing graduation-code fixture')
            r=home(h,client);h.check('missing graduation code only omits banner',r.dom.find(lambda n:'data-graduation-link' in n.a) is None and len(r.dom.all(lambda n:'data-theme-code' in n.a))==5 and r.dom.find(lambda n:n.tag=='form' and n.a.get('action')=='/products') is not None)
            h.fixture('UPDATE category SET code='+h.literal(graduation['code'])+',updated_at='+h.literal(graduation['updatedAt'])+' WHERE id='+str(graduation['id']),'restore graduation-code fixture')
            saleids=','.join(str(p['id']) for p in data['product'].values() if p['status']=='ON_SALE')
            h.fixture("UPDATE product SET status='DRAFT',updated_at=updated_at WHERE id IN ("+saleids+")",'five themes with no publicly sellable product fixture')
            r=home(h,client);h.check('no-sale preserves all five themes and graduation search',len(r.dom.all(lambda n:'data-theme-code' in n.a))==5 and r.dom.find(lambda n:'data-graduation-link' in n.a) is not None and r.text.count('暂无可售商品')==2)
            product_list(h,client)
            h.fixture("UPDATE product SET status='ON_SALE',updated_at=updated_at WHERE id IN ("+saleids+")",'restore sale-state fixture')
            h.check('all home fixtures restored full seven-table bytes',h.snapshot()==original)
        with h.case('TST-03','combined-filters'):
            p=selected[0];child=data['category'][str(p['categoryId'])];theme=child['parentId'];kind='STATIONERY' if child['code'].endswith('_STATIONERY') else 'SOUVENIR'
            for number in [1,2]:product_list(h,client,dict(categoryId=theme,type=kind,q=p['name'][:2],sort='PRICE_ASC',size=1,page=number))
            product_list(h,client,dict(categoryId=theme,type=kind,q='__no_literal_match__',sort='NEWEST',size=1,page=1))
            h.check('combined filters and GETs no database writes',h.snapshot()==original)
        h.save('supplement-summary.json',json.dumps(dict(result='PASS',tested_sha=SHA,scope=plan['scope'],main39P0_verdict_not_replaced=True,all_fixtures_restored=True),ensure_ascii=False,indent=2))
    except BaseException as exc:error=exc;h.save('failure.txt',traceback.format_exc())
    finally:r=h.finish(error);print('SUPPLEMENT_RESULT '+r['overall'],flush=True)
    return 0 if r['overall']=='PASS' else 1
if __name__=='__main__':sys.exit(main())
