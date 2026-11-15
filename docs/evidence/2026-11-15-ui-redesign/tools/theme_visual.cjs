/* Narrow fresh theme visual supplement, not one of the92 paired captures. */
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {chromium}=require(process.env.UI_PLAYWRIGHT);
const fixture=JSON.parse(fs.readFileSync(process.env.UI_THEME_FIXTURE,'utf8'));
const privateValues=JSON.parse(process.env.UI_PRIVATE_VALUES);
const out=process.env.UI_THEME_OUT;
const screenshots=[],observations=[],externalRequests=[];
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
async function run(){
 if(fs.existsSync(out))throw Error('Use new output directory');fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 try{
  for(const end of ['u','a']){
   const context=await browser.newContext({viewport:{width:1366,height:768},locale:'zh-CN',reducedMotion:'reduce'});
   await context.addCookies([{name:end==='u'?'CSUCAMPUSCRAFT_USER_SESSION':'CSUCAMPUSCRAFT_ADMIN_SESSION',value:process.env[end==='u'?'UI_USER_COOKIE':'UI_ADMIN_COOKIE'],url:fixture.bases[end]}]);
   await context.route('**/*',r=>{const u=new URL(r.request().url());if(['data:','blob:','about:'].includes(u.protocol)||u.origin===new URL(fixture.bases[end]).origin)return r.continue();externalRequests.push({origin:u.origin});return r.abort();});
   const page=await context.newPage(),response=await page.goto(fixture.bases[end]+'/',{waitUntil:'networkidle'}),raw=await response.body(),text=raw.toString('utf8');
   if(response.status()!==200||/\$2[aby]\$\d\d\$[./A-Za-z0-9]{53}/.test(text)||privateValues.some(v=>text.includes(v)))throw Error('Response status/privacy check failed');
   const light=await page.evaluate(()=>getComputedStyle(document.body).backgroundColor);
   await page.locator('.ef-theme-toggle').click();
   const state=await page.evaluate(()=>({theme:document.documentElement.dataset.theme,background:getComputedStyle(document.body).backgroundColor,pressed:document.querySelector('.ef-theme-toggle').getAttribute('aria-pressed'),stored:localStorage.getItem('csucampuscraft.theme')}));
   if(state.theme!=='dark'||state.pressed!=='true'||state.stored!=='dark'||state.background===light)throw Error('Actual dark control failed');
   const filename=(end==='u'?'U01':'A02')+'-dark-1366.png',file=path.join(out,filename);
   await page.screenshot({path:file,fullPage:false,animations:'disabled',mask:[page.locator('[data-shipping-value],[data-customer-contact],input[type=password],input[name=username]')],maskColor:'#676d69'});
   const png=fs.readFileSync(file);screenshots.push({end,path:filename,sha256:hash(png),bytes:png.length,viewport:{width:1366,height:768},scope:'After-only independent actual dark-theme screenshot; not a before/after paired image'});
   observations.push({end,path:'/',status:response.status(),raw_body_sha256:hash(raw),raw_body_bytes:raw.length,raw_privacy_scan_passed:true,raw_body_not_archived:true,light,...state});
   await context.close();
  }
  if(externalRequests.length)throw Error('External request');
  fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({overall:'PASS',sourceSha:fixture.sourceSha,scope:'Narrow real dark-theme button and two actual PNGs on fresh private demo; no business writes',screenshots,observations,externalRequests},null,2));
 }finally{await browser.close();}
}
run().then(()=>console.log('THEME_VISUAL_PASS')).catch(e=>{fs.writeFileSync(path.join(out,'failure.json'),JSON.stringify({overall:'FAIL',failureClass:e.name,screenshots,observations}));console.error(e.name);process.exitCode=1});
