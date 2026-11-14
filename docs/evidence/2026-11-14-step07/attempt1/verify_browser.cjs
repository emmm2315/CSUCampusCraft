const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {chromium}=require('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/playwright');
const out=process.env.STEP07_BROWSER_OUT,cases=JSON.parse(process.env.STEP07_BROWSER_CASES||'[]'),cookies=JSON.parse(process.env.STEP07_BROWSER_COOKIES||'{}');
fs.mkdirSync(out,{recursive:true});
const previous=fs.existsSync(path.join(out,'result.json'))?JSON.parse(fs.readFileSync(path.join(out,'result.json'),'utf8')):{checks:[],screenshots:[]};
const checks=[...previous.checks],shots=[...previous.screenshots];let completed=false,failure=null;
function check(name,ok){checks.push({name,passed:!!ok});if(!ok)throw Error(name);}
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true,args:['--no-proxy-server']});
 try{
  for(const viewport of [{width:1366,height:768},{width:1920,height:1080}]){
   const contexts={};
   for(const c of cases){
    if(!contexts[c.account]){
      const context=await browser.newContext({viewport,locale:'zh-CN'});
      if(cookies[c.account])await context.addCookies([{name:'CSUCAMPUSCRAFT_USER_SESSION',value:cookies[c.account],domain:'127.0.0.1',path:'/',httpOnly:true,secure:false,sameSite:'Lax'}]);
      contexts[c.account]=context;
    }
    const page=await contexts[c.account].newPage(),imageRequests=[];
    page.on('response',r=>{if(r.request().resourceType()==='image')imageRequests.push({path:new URL(r.url()).pathname,status:r.status()});});
    const response=await page.goto('http://127.0.0.1:8080'+c.path,{waitUntil:'domcontentloaded'});
    check(c.name+'-http-'+viewport.width,response.status()===c.status);
    await page.evaluate(async()=>{if(document.fonts)await document.fonts.ready;for(let y=0;y<document.documentElement.scrollHeight;y+=innerHeight){scrollTo(0,y);await new Promise(r=>setTimeout(r,30));}scrollTo(0,0);await Promise.all(Array.from(document.images).map(i=>i.decode().catch(()=>{})));});
    await page.waitForFunction(()=>Array.from(document.images).every(i=>i.complete&&i.naturalWidth>0),null,{timeout:8000});
    const dom=await page.evaluate(()=>{
      const root=document.querySelector('[data-page-id]'),badge=document.querySelector('#cart-quantity'),ids=[...document.querySelectorAll('[id]')].map(x=>x.id);
      return {pageId:root?.dataset.pageId,errorStatus:document.querySelector('[data-error-status]')?.dataset.errorStatus,badge:badge?.dataset.cartQuantity,badgeText:badge?.textContent.trim(),overflow:document.documentElement.scrollWidth>innerWidth+1,uniqueIds:ids.length===new Set(ids).size,sessionInLinks:Array.from(document.querySelectorAll('[href],[action]')).some(n=>/;CSUCAMPUSCRAFT_(?:USER|ADMIN)_SESSION=/.test(n.getAttribute('href')||n.getAttribute('action')||'')),labelProblems:Array.from(document.querySelectorAll('input:not([type=hidden]),select,textarea')).filter(n=>!n.id||!document.querySelector('label[for="'+n.id+'"]')).length,postForms:Array.from(document.forms).filter(f=>(f.method||'').toLowerCase()==='post').map(f=>({action:f.getAttribute('action'),csrfCount:f.querySelectorAll('input[name="_csrf"]').length,version:f.querySelector('input[name=version]')?.value})),cartRows:Array.from(document.querySelectorAll('tr[data-cart-item-id]')).map(n=>({id:n.dataset.cartItemId,productId:n.dataset.productId,quantity:n.dataset.quantity,version:n.dataset.version,valid:n.dataset.cartValid,reason:n.dataset.invalidReason})),cartTotal:document.querySelector('[data-cart-total]')?.dataset.cartTotal,checkoutUnavailable:Array.from(document.querySelectorAll('[data-checkout-unavailable]')).every(n=>n.disabled),checkoutControlCount:document.querySelectorAll('[data-checkout-unavailable]').length,forbiddenBusinessLinks:Array.from(document.querySelectorAll('[href],[action]')).filter(n=>/^\/(?:checkout|orders)(?:[/?]|$)/.test(n.getAttribute('href')||n.getAttribute('action')||'')).length,allImagesLoaded:Array.from(document.images).every(i=>i.complete&&i.naturalWidth>0),technicalLeak:document.documentElement.textContent.includes('VERIFICATION_SQL_PASSWORD_STACK_SENTINEL')};
    });
    check(c.name+'-page-'+viewport.width,c.kind==='error'?dom.errorStatus===String(c.status):dom.pageId===c.kind);
    check(c.name+'-no-overflow-'+viewport.width,!dom.overflow);
    check(c.name+'-cookie-only-'+viewport.width,!dom.sessionInLinks);
    check(c.name+'-labels-'+viewport.width,dom.labelProblems===0);
    check(c.name+'-unique-ids-'+viewport.width,dom.uniqueIds);
    check(c.name+'-csrf-every-form-'+viewport.width,dom.postForms.every(f=>f.csrfCount===1));
    check(c.name+'-images-loaded-'+viewport.width,dom.allImagesLoaded);
    check(c.name+'-badge-sum-'+viewport.width,dom.badge===String(c.badge)&&dom.badgeText===String(c.badge));
    check(c.name+'-no-future-business-links-'+viewport.width,dom.forbiddenBusinessLinks===0);
    check(c.name+'-no-technical-leak-'+viewport.width,!dom.technicalLeak);
    if(c.kind==='U05'){
      check(c.name+'-checkout-disabled-'+viewport.width,dom.checkoutControlCount===1&&dom.checkoutUnavailable);
      check(c.name+'-versions-present-'+viewport.width,dom.postForms.filter(f=>f.action!='/logout').every(f=>f.version!==undefined&&f.version!==''));
    }
    if(c.total)check(c.name+'-exact-money-'+viewport.width,dom.cartTotal===c.total);
    const filename=c.name+'-'+viewport.width+'.png';check(c.name+'-new-screenshot-'+viewport.width,!fs.existsSync(path.join(out,filename)));
    await page.screenshot({path:path.join(out,filename),fullPage:true});
    const b=fs.readFileSync(path.join(out,filename));
    shots.push({path:filename,viewport,status:response.status(),pngWidth:b.readUInt32BE(16),pngHeight:b.readUInt32BE(20),sha256:crypto.createHash('sha256').update(b).digest('hex'),account:c.account,observation:dom,imageRequests:[...imageRequests]});
    await page.close();
   }
   for(const context of Object.values(contexts))await context.close();
  }
  completed=true;
 }catch(e){failure=String(e.message).replace(/;CSUCAMPUSCRAFT_(?:USER|ADMIN)_SESSION=[A-Za-z0-9.-]+/g,';SESSION=[REDACTED]');throw e;}
 finally{await browser.close();fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({overall:completed&&checks.every(x=>x.passed)?'PASS':'FAIL',completed,error:failure,checks,screenshots:shots},null,2),'utf8');}
 process.stdout.write(JSON.stringify({overall:'PASS',completed,checks:checks.length,screenshots:shots.length,secretsRecorded:false}));
})().catch(e=>{process.stderr.write(failure||'Browser tool failed');process.exit(1);});
