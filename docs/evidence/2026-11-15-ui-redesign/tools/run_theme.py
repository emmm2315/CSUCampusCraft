"""New narrowly scoped live theme visual supplement; no prior generator import."""
from pathlib import Path
import json,os,traceback
from ui_harness import UIHarness,RUNTIME

HERE=Path(__file__).resolve().parent
h=UIHarness(HERE,Path('D:/Github Projects/CSUCampusCraft'),'d22433c2abf87b1a996c6a18467fd7a9a5a43372','attempt5')
h.plan={'scope':'Theme-visual-only supplement, not functional regression or paired92','cases':[{'id':'UI-THEME','required_segments':['visual'],'assertion_plan':'Two actual dark U01/A02 images after button click, live same final JARs, genuine whole batch seven-table equality'}]}
h.result['scope']='Narrow independent theme-visual-supplement: fresh private demo, two logins and two dark screenshots; not one of the92 paired or14 full-page captures.'
error=None
try:
    for name in ['run_theme.py','theme_visual.cjs','ui_harness.py']:h.save('tools/'+name,(HERE/name).read_bytes())
    h.initialize();h.create_schema('csucampuscraft','demo');h.start_apps()
    with h.case('UI-THEME','visual'):
        before=h.snapshot();a=h.state();user,_=h.login(username='alice');admin,_=h.login(end='a',username='admin')
        h.save('theme-visual-fixture.json',json.dumps({'sourceSha':h.tested_sha,'bases':{'u':h.base('u'),'a':h.base('a')}},indent=2))
        env=os.environ.copy();env.update(UI_PLAYWRIGHT=str(RUNTIME/'node/node_modules/playwright'),UI_THEME_FIXTURE=str(h.evidence/'theme-visual-fixture.json'),UI_THEME_OUT=str(h.evidence/'theme-visual-supplement'),UI_USER_COOKIE=user.cookie('u'),UI_ADMIN_COOKIE=admin.cookie('a'),UI_PRIVATE_VALUES=json.dumps([h.password,h.apppass,h.rootpass]))
        p=h.command([RUNTIME/'node/bin/node.exe',HERE/'theme_visual.cjs'],env=env,timeout=120)
        after=h.snapshot();b=h.state();h.db_pair('two-logins-and-two-dark-GET-images-batch',before,a,after,b,observation='Real full seven-table before/after; two browser GETs separately metadata/raw-hash scanned, no raw bodies archived')
        h.save('theme-stdout.log',p.stdout.decode('utf-8',errors='replace'));h.save('theme-stderr.log',p.stderr.decode('utf-8',errors='replace'))
        h.check('fresh actual theme screenshot helper succeeds',p.returncode==0)
        result=json.loads((h.evidence/'theme-visual-supplement/result.json').read_text(encoding='utf-8'));h.check('two real dark screenshots',result['overall']=='PASS' and len(result['screenshots'])==2)
        h.check('login and dark screenshots preserve all seven tables',before==after)
except BaseException as exc:error=exc;h.save('failure.txt',traceback.format_exc())
finally:
    result=h.finish(error);print('UI_THEME_RESULT '+str(h.evidence/'result.json')+' '+result['overall'],flush=True)
raise SystemExit(0 if result['overall']=='PASS' else 1)
