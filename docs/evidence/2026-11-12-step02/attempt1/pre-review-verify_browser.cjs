const {chromium} = require('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1111-574-0_26.1111.574.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/playwright');
const fs = require('fs'); const path = require('path');
const out = process.env.STEP02_BROWSER_OUT || path.join(__dirname,'browser');fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 const results=[];
 try {
  for(const port of [8080,8081]) {
   const context=await browser.newContext({viewport:{width:1366,height:768}});
   const page=await context.newPage();
   for(const width of [1366,1920]) {
    await page.setViewportSize({width,height:width===1366?768:1080});
    const response=await page.goto('http://127.0.0.1:'+port+'/',{waitUntil:'networkidle'});
    const record=await page.evaluate(()=>({app:document.body.dataset.csucampuscraftApp,count:document.querySelector('[data-theme-count]')?.dataset.themeCount,font:getComputedStyle(document.body).fontSize,h1:getComputedStyle(document.querySelector('h1')).fontSize,overflow:document.documentElement.scrollWidth>innerWidth}));
    if(response.status()!==200||record.count!=='5'||record.font!=='16px'||record.h1!=='28px'||record.overflow)throw Error('Home style regression '+port);
    await page.screenshot({path:path.join(out,port+'-home-'+width+'.png'),fullPage:true});
    results.push({port,width,kind:'home',...record,passed:true});
   }
   await page.setViewportSize({width:1366,height:768});
   await page.goto('http://127.0.0.1:'+port+'/__verification/foundation',{waitUntil:'networkidle'});
   const form=await page.evaluate(()=>({
    allLabelsMatch:[...document.querySelectorAll('label[for]')].every(n=>!!document.getElementById(n.htmlFor)),
    csrfCount:document.querySelectorAll('form input[name="_csrf"][type="hidden"]').length,
    imageFallback:[...document.images].every(n=>n.complete&&n.naturalWidth>0&&n.src.endsWith('/images/catalog-placeholder.svg'))
   }));
   if(!form.allLabelsMatch||form.csrfCount!==1||!form.imageFallback)throw Error('Form or image fallback failed '+port);
   const input=page.locator('input[type=text]').first();await input.focus();
   const focus=await input.evaluate(n=>({width:getComputedStyle(n).outlineWidth,style:getComputedStyle(n).outlineStyle}));
   if(focus.width!=='2px'||focus.style==='none')throw Error('Focus styling failed');
   await page.screenshot({path:path.join(out,port+'-fields.png'),fullPage:true});
   results.push({port,kind:'fields',...form,focus,passed:true});
   for(const status of [404,500]) {
    const r=await page.goto('http://127.0.0.1:'+port+'/__verification/errors/'+status,{waitUntil:'networkidle'});
    if(r.status()!==status)throw Error('Error status mismatch');
    await page.screenshot({path:path.join(out,port+'-error-'+status+'.png'),fullPage:true});
    results.push({port,kind:'error',status,passed:true});
   }
   await context.close();
  }
 }finally{await browser.close();fs.writeFileSync(path.join(out,'result.json'),JSON.stringify(results,null,2));}
 process.stdout.write(JSON.stringify({browser:'Microsoft Edge headless via bundled Playwright',checks:results.length,passed:true}));
})().catch(e=>{process.stderr.write(e.message);process.exit(1)});

