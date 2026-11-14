const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {chromium}=require('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/playwright');
const out=process.env.STEP05_BROWSER_OUT,cases=JSON.parse(process.env.STEP05_BROWSER_CASES||'[]');
fs.mkdirSync(out,{recursive:true});
const checks=[],shots=[];let completed=false,failure=null;
function check(name,ok){checks.push({name,passed:!!ok});if(!ok)throw Error(name);}
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true,args:['--no-proxy-server']});
 try{
  for(const viewport of [{width:1366,height:768},{width:1920,height:1080}]){
   const context=await browser.newContext({viewport,locale:'zh-CN'});
   await context.addCookies([{name:'CSUCAMPUSCRAFT_ADMIN_SESSION',value:process.env.STEP05_ADMIN_COOKIE,domain:'127.0.0.1',path:'/',httpOnly:true,secure:false,sameSite:'Lax'}]);
   const page=await context.newPage();
   for(const c of cases){
    const response=await page.goto('http://127.0.0.1:'+c.port+c.path,{waitUntil:'domcontentloaded'});
    check(c.name+'-initial-http-'+viewport.width,response.status()===200);
    let status=response.status();
    if(c.submit){
      const form=page.locator(c.submit.kind==='category'?'form[data-category-form]':'form[data-product-form]');
      for(const [name,value] of Object.entries(c.submit.fields)){
        const control=form.locator('[name="'+name+'"]');
        check(c.name+'-control-'+name+'-'+viewport.width,await control.count()===1);
        const tag=await control.evaluate(n=>n.tagName);
        if(tag==='SELECT')await control.selectOption(String(value));else await control.fill(String(value));
      }
      if(c.submit.stale)await form.locator('[name="version"]').evaluate(n=>n.value='0');
      await form.evaluate(f=>f.noValidate=true);
      const action=await form.getAttribute('action');
      const waiting=page.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname===action);
      const navigation=page.waitForNavigation({waitUntil:'domcontentloaded'});
      await form.locator('button[type="submit"]').first().click();
      status=(await waiting).status();await navigation;
      check(c.name+'-post-http-'+viewport.width,status===c.submit.status);
    }
    await page.evaluate(async()=>{if(document.fonts)await document.fonts.ready;if(document.images.length){for(let y=0;y<document.documentElement.scrollHeight;y+=innerHeight){scrollTo(0,y);await new Promise(r=>setTimeout(r,45));}scrollTo(0,0);}await Promise.all(Array.from(document.images).map(i=>i.decode().catch(()=>{})));});
    await page.waitForFunction(()=>Array.from(document.images).every(i=>i.complete&&i.naturalWidth>0),null,{timeout:6000});
    const dom=await page.evaluate(()=>{
      const root=document.querySelector('[data-page-id]');
      return {pageId:root?.dataset.pageId,overflow:document.documentElement.scrollWidth>innerWidth+1,passwordEmpty:Array.from(document.querySelectorAll('input[type=password]')).every(n=>!n.value&&!n.hasAttribute('value')),sessionInLinks:Array.from(document.querySelectorAll('[href],[action]')).some(n=>/;CSUCAMPUSCRAFT_(?:USER|ADMIN)_SESSION=/.test(n.getAttribute('href')||n.getAttribute('action')||'')),labelProblems:Array.from(document.querySelectorAll('input:not([type=hidden]),select,textarea')).filter(n=>n.id&&!document.querySelector('label[for="'+n.id+'"]')).length,postForms:Array.from(document.forms).filter(f=>(f.method||'').toLowerCase()==='post').map(f=>({csrfCount:f.querySelectorAll('input[name="_csrf"]').length})),fieldErrors:document.querySelectorAll('.field-error').length,alerts:document.querySelectorAll('[role=alert]').length,allImagesLoaded:Array.from(document.images).every(i=>i.complete&&i.naturalWidth>0)};
    });
    check(c.name+'-page-id-'+viewport.width,dom.pageId===c.kind);
    check(c.name+'-no-page-overflow-'+viewport.width,!dom.overflow);
    check(c.name+'-password-cleared-'+viewport.width,dom.passwordEmpty);
    check(c.name+'-cookie-only-links-'+viewport.width,!dom.sessionInLinks);
    check(c.name+'-labels-'+viewport.width,dom.labelProblems===0);
    check(c.name+'-csrf-per-form-'+viewport.width,dom.postForms.every(f=>f.csrfCount===1));
    check(c.name+'-images-loaded-'+viewport.width,dom.allImagesLoaded);
    if(c.submit)check(c.name+'-visible-feedback-'+viewport.width,dom.fieldErrors>0||dom.alerts>0);
    const filename=c.name+'-'+viewport.width+'.png';await page.screenshot({path:path.join(out,filename),fullPage:true});
    const b=fs.readFileSync(path.join(out,filename));
    shots.push({path:filename,viewport,status,pngWidth:b.readUInt32BE(16),pngHeight:b.readUInt32BE(20),sha256:crypto.createHash('sha256').update(b).digest('hex'),observation:dom});
   }
   await context.close();
  }
  completed=true;
 }catch(e){failure=String(e.message).replace(/;CSUCAMPUSCRAFT_(?:USER|ADMIN)_SESSION=[A-Za-z0-9.-]+/g,';SESSION=[REDACTED]');throw e;}
 finally{await browser.close();fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({overall:completed&&checks.every(x=>x.passed)?'PASS':'FAIL',completed,error:failure,checks,screenshots:shots},null,2));}
 process.stdout.write(JSON.stringify({overall:'PASS',completed,checks:checks.length,screenshots:shots.length,secretsRecorded:false}));
})().catch(e=>{process.stderr.write(failure||'Browser tool failed');process.exit(1);});

