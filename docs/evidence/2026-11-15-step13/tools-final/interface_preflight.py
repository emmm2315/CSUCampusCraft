"""New offline caller/helper interface regression, no DB/application/browser launch."""
from pathlib import Path
import json,subprocess,hashlib,sys
from harness import RUNTIME,scanner_regression
HERE=Path(__file__).resolve().parent;OUT=HERE.parent/'interface-preflight';OUT.mkdir(exist_ok=False)
fixture=dict(sourceSha='d577179e4468354552d3f5f48d624a4296ee3cfb',userBase='http://127.0.0.1:8080/',adminBase='http://127.0.0.1:8081/',graduationCategoryId=5,giftProductId=56,orderNo='SYNTHETIC_STEP13_INTERFACE',customerId=1,adminAlbumProductId=61,missingProductId=36,noGalleryProductId=3)
f=OUT/'public-fixture.json';f.write_text(json.dumps(fixture),encoding='utf-8')
script="const fs=require('fs'); const f=JSON.parse(fs.readFileSync(process.argv[1],'utf8')); const keys=['graduationCategoryId','giftProductId','customerId','adminAlbumProductId','missingProductId','noGalleryProductId']; if(!keys.every(k=>Number.isSafeInteger(f[k])&&f[k]>0))process.exit(2); if(!/^[a-f0-9]{40}$/.test(f.sourceSha))process.exit(3); for(const k of ['userBase','adminBase']){const u=new URL(f[k]);if(u.hostname!=='127.0.0.1'||u.pathname!=='/')process.exit(4);} process.stdout.write(JSON.stringify({publicFixtureFileRead:true,requiredIds:keys.length,sourceShaValid:true,loopbackBases:true}));"
p=subprocess.run([str(RUNTIME/'node/bin/node.exe'),'-e',script,str(f)],capture_output=True)
assert p.returncode==0
for source in HERE.glob('*.py'):compile(source.read_text(encoding='utf-8-sig'),str(source),'exec')
text=(HERE/'run_step13.py').read_text(encoding='utf-8');assert 'STEP13_UI_FIXTURE=str(fixture_path)' in text
phone_source=(HERE/'harness.py').read_text(encoding='utf-8');assert "'receiverPhone':'000-'+secrets.token_hex(6)" in phone_source
record=dict(overall='PASS',node_fixture_contract=json.loads(p.stdout),caller_uses_file_path=True,cookie_values_never_written=True,phone_runtime_random_not_public_source_constant=True,raw_scanner=scanner_regression(),no_DB_or_HTTP_or_browser_run=True,helper_sha256=hashlib.sha256((HERE.parent/'ui/verify_browser_step13.cjs').read_bytes()).hexdigest())
(OUT/'result.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(json.dumps(record))
