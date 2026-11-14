const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {chromium}=require('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/playwright');
const out=process.env.STEP06_BROWSER_OUT,cases=JSON.parse(process.env.STEP06_BROWSER_CASES||'[]');
fs.mkdirSync(out,{recursive:true});
const checks=[],shots=[];let completed=false,failure=null;
function check(name,ok){checks.push({name,passed:!!ok});if(!ok)throw Error(name);}
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true,args:['--no-proxy-server']});
 try{
  for(const viewport of [{width:1366,height:768},{width:1920,height:1080}]){
   const context=await browser.newContext({viewport,locale:'zh-CN'});
   await context.addCookies([{name:'CSUCAMPUSCRAFT_ADMIN_SESSION',value:process.env.STEP06_ADMIN_COOKIE,domain:'127.0.0.1',path:'/',httpOnly:true,secure:false,sameSite:'Lax'}]);
   const page=await context.newPage();
   const imageRequests=[];
   page.on('response',async r=>{if(r.request().resourceType()==='image')imageRequests.push({path:new URL(r.url()).pathname,status:r.status()});});
   for(const c of cases){
    imageRequests.length=0;
    const response=await page.goto('http://127.0.0.1:'+c.port+c.path,{waitUntil:'domcontentloaded'});
    check(c.name+'-http-'+viewport.width,response.status()===200);
    await page.evaluate(async()=>{if(document.fonts)await document.fonts.ready;for(let y=0;y<document.documentElement.scrollHeight;y+=innerHeight){scrollTo(0,y);await new Promise(r=>setTimeout(r,50));}scrollTo(0,0);await Promise.all(Array.from(document.images).map(i=>i.decode().catch(()=>{})));});
    await page.waitForFunction(()=>Array.from(document.images).every(i=>i.complete&&i.naturalWidth>0),null,{timeout:8000});
    const dom=await page.evaluate(()=>{
      const root=document.querySelector('[data-page-id]');
      return {pageId:root?.dataset.pageId,productId:root?.dataset.productId,productVersion:root?.dataset.productVersion,imageCount:root?.dataset.imageCount,overflow:document.documentElement.scrollWidth>innerWidth+1,sessionInLinks:Array.from(document.querySelectorAll('[href],[action]')).some(n=>/;CSUCAMPUSCRAFT_(?:USER|ADMIN)_SESSION=/.test(n.getAttribute('href')||n.getAttribute('action')||'')),labelProblems:Array.from(document.querySelectorAll('input:not([type=hidden]),select,textarea')).filter(n=>!n.id||!document.querySelector('label[for="'+n.id+'"]')).length,postForms:Array.from(document.forms).filter(f=>(f.method||'').toLowerCase()==='post').map(f=>({action:f.getAttribute('action'),csrfCount:f.querySelectorAll('input[name="_csrf"]').length,version:f.querySelector('input[name=productVersion]')?.value})),gallery:Array.from(document.querySelectorAll('[data-product-gallery] figure[data-image-id]')).map(n=>({id:n.dataset.imageId,sort:n.dataset.imageSort,alt:n.querySelector('img')?.alt})),fallbacks:Array.from(document.querySelectorAll('img[data-image-fallback-used=true]')).map(i=>({path:new URL(i.src).pathname,loaded:i.complete&&i.naturalWidth>0})),allImagesLoaded:Array.from(document.images).every(i=>i.complete&&i.naturalWidth>0),injectedScript:!!Array.from(document.scripts).find(s=>s.textContent.includes('step06()'))};
    });
    check(c.name+'-page-id-'+viewport.width,dom.pageId===c.kind);
    check(c.name+'-no-overflow-'+viewport.width,!dom.overflow);
    check(c.name+'-cookie-only-'+viewport.width,!dom.sessionInLinks);
    check(c.name+'-labels-'+viewport.width,dom.labelProblems===0);
    check(c.name+'-csrf-per-form-'+viewport.width,dom.postForms.every(f=>f.csrfCount===1));
    check(c.name+'-images-loaded-'+viewport.width,dom.allImagesLoaded);
    check(c.name+'-escaped-alt-'+viewport.width,!dom.injectedScript);
    if(c.kind==='A10')check(c.name+'-album-form-version-'+viewport.width,dom.postForms.filter(f=>f.action!='/logout').every(f=>f.version===dom.productVersion));
    if(c.fallback){check(c.name+'-fallback-used-'+viewport.width,dom.fallbacks.length>0&&dom.fallbacks.every(x=>x.path==='/images/catalog-placeholder.svg'&&x.loaded));check(c.name+'-fallback-http200-'+viewport.width,imageRequests.some(x=>x.path==='/images/catalog-placeholder.svg'&&x.status===200));}
    const filename=c.name+'-'+viewport.width+'.png';await page.screenshot({path:path.join(out,filename),fullPage:true});
    const b=fs.readFileSync(path.join(out,filename));
    shots.push({path:filename,viewport,status:response.status(),pngWidth:b.readUInt32BE(16),pngHeight:b.readUInt32BE(20),sha256:crypto.createHash('sha256').update(b).digest('hex'),observation:dom,imageRequests:[...imageRequests]});
   }
   await context.close();
  }
  completed=true;
 }catch(e){failure=String(e.message).replace(/;CSUCAMPUSCRAFT_(?:USER|ADMIN)_SESSION=[A-Za-z0-9.-]+/g,';SESSION=[REDACTED]');throw e;}
 finally{await browser.close();fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({overall:completed&&checks.every(x=>x.passed)?'PASS':'FAIL',completed,error:failure,checks,screenshots:shots},null,2));}
 process.stdout.write(JSON.stringify({overall:'PASS',completed,checks:checks.length,screenshots:shots.length,secretsRecorded:false}));
})().catch(e=>{process.stderr.write(failure||'Browser tool failed');process.exit(1);});
