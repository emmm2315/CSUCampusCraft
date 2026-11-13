const {chromium}=require('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path');
const out=process.env.STEP03_BROWSER_OUT;
const cases=JSON.parse(process.env.STEP03_BROWSER_CASES||'[]');
if(!out||!cases.length)throw Error('Explicit output directory and cases required');
fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 const results=[];
 try {
  const context=await browser.newContext();
  const page=await context.newPage();
  for(const c of cases) for(const width of [1366,1920]){
   await page.setViewportSize({width,height:width===1366?768:1080});
   const response=await page.goto('http://127.0.0.1:8080'+c.path,{waitUntil:'networkidle',timeout:20000});
   if(response.status()!==c.status)throw Error('Unexpected HTTP status for '+c.name);
   for(const image of await page.locator('img').all()){
    await image.scrollIntoViewIfNeeded();
    await image.evaluate(n=>n.loading='eager');
   }
   await page.waitForFunction(()=>[...document.images].every(n=>n.complete&&n.naturalWidth>0),null,{timeout:8000});
   await page.evaluate(()=>window.scrollTo(0,0));
   const data=await page.evaluate(()=>({
    pageId:document.querySelector('[data-page-id]')?.getAttribute('data-page-id')||null,
    productCount:document.querySelector('[data-product-count]')?.getAttribute('data-product-count')||null,
    page:document.querySelector('[data-page][data-product-count]')?.getAttribute('data-page')||null,
    themeCount:document.querySelector('[data-theme-count]')?.getAttribute('data-theme-count')||null,
    overflowing:document.documentElement.scrollWidth>innerWidth,
    labelledInputs:[...document.querySelectorAll('label[for]')].every(n=>!!document.getElementById(n.htmlFor)),
    imageCount:document.images.length,
    allImagesLoaded:[...document.images].every(n=>n.complete&&n.naturalWidth>0),
    placeholderCount:[...document.images].filter(n=>new URL(n.src).pathname.split(';')[0]==='/images/catalog-placeholder.svg').length,
    disabledPurchase:(()=>{const a=[...document.querySelectorAll('button')].filter(n=>/购物车|加购/.test(n.textContent));return a.length>0&&a.every(n=>n.matches(':disabled'));})(),
    csrfQueryFields:document.querySelectorAll('form[method=get] input[name=_csrf],form[method=GET] input[name=_csrf]').length,
    unicodeKeywordHelp:[...document.querySelectorAll('input[name=q]')].every(n=>!n.hasAttribute('maxlength')&&!!n.getAttribute('aria-describedby')&&n.getAttribute('aria-describedby').split(/\s+/).every(id=>document.getElementById(id)?.textContent.includes('120'))),
    forbiddenScripts:[...document.scripts].filter(n=>!n.src).length
   }));
   if(data.overflowing||!data.labelledInputs||!data.allImagesLoaded||data.csrfQueryFields||data.forbiddenScripts||!data.unicodeKeywordHelp)throw Error('DOM accessibility or rendering check failed for '+c.name);
   if(c.kind==='detail'&&(!data.disabledPurchase||!data.imageCount))throw Error('Detail placeholder check failed');
   if(c.placeholder&&data.placeholderCount<1)throw Error('Image fallback not visible');
   const filename=c.name+'-'+width+'.png';
   await page.screenshot({path:path.join(out,filename),fullPage:true});
   results.push({name:c.name,kind:c.kind,width,httpStatus:response.status(),...data,screenshot:filename,passed:true});
  }
  await context.close();
 }finally {await browser.close();fs.writeFileSync(path.join(out,'result.json'),JSON.stringify(results,null,2));}
 process.stdout.write(JSON.stringify({passed:true,checks:results.length}));
})().catch(e=>{process.stderr.write(e.message.replace(/;CSUCAMPUSCRAFT_(?:USER|ADMIN)_SESSION=[A-Za-z0-9.-]+/g,';SESSION=[REDACTED]'));process.exit(1)});

