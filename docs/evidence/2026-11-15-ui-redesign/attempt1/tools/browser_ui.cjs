/* Fresh UI-redesign browser capture. No historical runner or result is imported. */
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {chromium}=require(process.env.UI_PLAYWRIGHT);
const fixture=JSON.parse(fs.readFileSync(process.env.UI_FIXTURE,'utf8'));
const out=process.env.UI_OUT;
if(fs.existsSync(out))throw Error('Output must be a fresh directory');
fs.mkdirSync(out,{recursive:true});
const observations=[],screenshots=[],network=[],outside=[];
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
async function control(action,data){const r=await fetch(process.env.UI_CONTROL+'/'+action,{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+process.env.UI_CONTROL_SECRET},body:JSON.stringify(data)});if(!r.ok)throw Error('Control failed '+r.status);return r.json();}
async function run(){
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 const contexts={};
 try{
  for(const auth of ['u','a','guest']){
   const context=await browser.newContext({viewport:{width:1366,height:768},locale:'zh-CN',timezoneId:'UTC',colorScheme:'light',reducedMotion:'reduce'});
   if(auth!=='guest'){const value=process.env[auth==='u'?'UI_USER_COOKIE':'UI_ADMIN_COOKIE'];await context.addCookies([{name:auth==='u'?'CSUCAMPUSCRAFT_USER_SESSION':'CSUCAMPUSCRAFT_ADMIN_SESSION',value,url:fixture.bases[auth]}]);}
   await context.route('**/*',async route=>{const u=new URL(route.request().url());if(!Object.values(fixture.bases).some(b=>new URL(b).origin===u.origin)){outside.push({host:u.host,protocol:u.protocol});return route.abort();}return route.continue();});
   contexts[auth]=context;
  }
  for(const scene of fixture.scenes){
   const context=contexts[scene.auth||scene.end],page=await context.newPage();
   page.on('response',r=>{const u=new URL(r.url());network.push({scene:scene.id,path:u.pathname+u.search,host:u.host,status:r.status(),resource:r.request().resourceType()});});
   const viewports=[{width:1366,height:768},{width:1920,height:1080},{width:390,height:844},{width:430,height:932}];
   for(const viewport of viewports){
    await page.setViewportSize(viewport);
    const ticket=await control('before',{method:'GET',path:scene.path,end:scene.end,scene:scene.id,viewport});
    const response=await page.goto(fixture.bases[scene.end]+scene.path,{waitUntil:'networkidle',timeout:45000});
    if(!response)throw Error('Missing navigation response');
    const raw=await response.body();
    await control('after',{ticket:ticket.ticket,status:response.status(),headers:{'Content-Type':response.headers()['content-type']||''},body:raw.toString('base64')});
    if(response.status()!==scene.status)throw Error('Wrong scene status '+scene.id+':'+response.status());
    await page.locator('img').evaluateAll(imgs=>Promise.all(imgs.map(img=>img.complete?Promise.resolve():new Promise(resolve=>{img.addEventListener('load',resolve,{once:true});img.addEventListener('error',resolve,{once:true});setTimeout(resolve,1500)}))));
    const dom=await page.evaluate(()=>{
     const visible=e=>e.getClientRects().length>0;
     const fields=[...document.querySelectorAll('input:not([type=hidden]),select,textarea')].filter(visible);
     const unlabeled=fields.filter(e=>!(e.labels&&e.labels.length)&&!e.getAttribute('aria-label')&&!e.getAttribute('aria-labelledby')).map(e=>({tag:e.tagName,type:e.type||'',name:e.name||'',id:e.id||''}));
     const unresolved=[...document.querySelectorAll('[aria-labelledby],[aria-describedby]')].flatMap(e=>['aria-labelledby','aria-describedby'].flatMap(a=>(e.getAttribute(a)||'').split(/\s+/).filter(Boolean).filter(id=>!document.getElementById(id)).map(id=>({attribute:a,id}))));
     return {pageId:document.querySelector('[data-page-id]')?.getAttribute('data-page-id')||null,width:innerWidth,documentWidth:document.documentElement.scrollWidth,overflow:document.documentElement.scrollWidth>innerWidth+1,h1:[...document.querySelectorAll('h1')].map(e=>e.textContent.trim()),unlabeled,unresolved,tables:[...document.querySelectorAll('table')].map(t=>({caption:!!t.querySelector('caption'),columns:t.querySelectorAll('th').length})),bodyBackground:getComputedStyle(document.body).backgroundColor,images:[...document.images].map(i=>({loaded:i.complete&&i.naturalWidth>0,path:new URL(i.currentSrc||i.src).pathname}))};
    });
    observations.push({scene:scene.id,path:scene.path,end:scene.end,viewport,status:response.status(),...dom});
    const take=viewport.width>1000||scene.mobile;
    if(take){const filename=scene.id+'-'+viewport.width+'.png';const file=path.join(out,filename);await page.screenshot({path:file,fullPage:false,animations:'disabled',mask:[page.locator('[data-shipping-value],[data-customer-contact],input[type=password],input[name=username],input[name=receiverName],input[name=receiverPhone],input[name=receiverAddress],textarea[name=receiverAddress]')],maskColor:'#676d69'});const bytes=fs.readFileSync(file);screenshots.push({scene:scene.id,path:filename,viewport,sha256:hash(bytes),bytes:bytes.length,status:response.status()});}
   }
   await page.close();
  }
  if(fixture.extraAudits){
   const page=await contexts.u.newPage();await page.goto(fixture.bases.u+'/',{waitUntil:'networkidle'});
   const light=await page.evaluate(()=>getComputedStyle(document.body).backgroundColor);
   await page.emulateMedia({colorScheme:'dark',reducedMotion:'reduce'});await page.reload({waitUntil:'networkidle'});
   const dark=await page.evaluate(()=>({background:getComputedStyle(document.body).backgroundColor,motion:[...document.querySelectorAll('*')].filter(e=>{const s=getComputedStyle(e);return s.animationDuration.split(',').some(x=>parseFloat(x)>.05)||s.transitionDuration.split(',').some(x=>parseFloat(x)>.05)}).length}));
   await page.keyboard.press('Tab');const focus=await page.evaluate(()=>{const e=document.activeElement,s=getComputedStyle(e);return {tag:e.tagName,visible:e.getClientRects().length>0,outlineWidth:s.outlineWidth,outlineStyle:s.outlineStyle,label:(e.getAttribute('aria-label')||e.textContent||'').trim().slice(0,80)}});
   observations.push({extra:'dark-reduced-motion-focus',light,dark,focus});await page.close();
  }
  fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({overall:'PASS',phase:fixture.phase,sourceSha:fixture.sourceSha,documentNetworkCapture:'Every scene navigation has a real seven-table before/after and raw response privacy scan in Python; asset statuses are metadata only; extra media audit GETs have batch-only read proof.',observations,screenshots,network,externalRequests:outside},null,2));
 }finally{await browser.close();}
}
run().then(()=>console.log('UI_BROWSER_PASS')).catch(error=>{fs.writeFileSync(path.join(out,'failure.json'),JSON.stringify({overall:'FAIL',failureClass:error.name,message:String(error.message),screenshots,observations,network,externalRequests:outside},null,2));console.error(error.name+': '+error.message);process.exitCode=1});
