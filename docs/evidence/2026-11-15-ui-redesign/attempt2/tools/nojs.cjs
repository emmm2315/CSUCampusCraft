/* Fresh optional browser supplement. All credentials arrive only via process env. */
'use strict';
const fs=require('fs'),path=require('path');
const {chromium}=require(process.env.UI_PLAYWRIGHT);
const base=process.env.CSU_UI_USER_BASE;
const username=process.env.CSU_UI_USERNAME;
const password=process.env.CSU_UI_PASSWORD;
const out=process.env.UI_NOJS_OUT;
const privateValues=new Set([username,password].filter(Boolean));
const log={javaScriptEnabled:false,checks:[],requests:[],externalRequests:[],overall:'RUNNING'};
const record=(name,condition,detail={})=>{log.checks.push({name,passed:!!condition,...detail});if(!condition)throw Error('Check failed: '+name);};
const sanitize=value=>{let s=String(value);for(const value of privateValues)if(value)s=s.split(value).join('[REDACTED]');return s;};
async function run(){
 if(!base||!username||!password||!out)throw Error('Missing private env configuration');
 if(fs.existsSync(out))throw Error('Use fresh no-JS output directory');
 fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 try{
  const context=await browser.newContext({javaScriptEnabled:false,viewport:{width:390,height:844},locale:'zh-CN',reducedMotion:'reduce'});
  await context.route('**/*',async route=>{const u=new URL(route.request().url());if(u.origin!==new URL(base).origin){log.externalRequests.push({origin:u.origin});return route.abort();}return route.continue();});
  const page=await context.newPage();
  page.on('response',response=>{
   const r=response.request();if(r.method()!=='POST')return;
   const params=new URLSearchParams(r.postData()||'');
   for(const key of ['_csrf','confirmationToken','password'])for(const value of params.getAll(key))privateValues.add(value);
   log.requests.push({method:r.method(),path:new URL(r.url()).pathname,status:response.status(),location:response.headers().location||null,fieldNames:[...params.keys()].sort()});
  });
  const start=await page.goto(base+'/login?returnUrl=%2Fcart',{waitUntil:'networkidle'});
  record('native-login-page',start.status()===200);
  const csrf=await page.locator('input[name="_csrf"]').inputValue();privateValues.add(csrf);
  record('server-rendered-csrf-without-js',csrf.length>0);
  await page.locator('input[name="username"]').fill(username);
  await page.locator('input[name="password"]').fill(password);
  const loginResponse=page.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname==='/login');
  await page.locator('form[method="post"] button[type="submit"]').click();
  const login=await loginResponse;await page.waitForURL(base+'/cart');await page.waitForLoadState('networkidle');
  record('native-login-post-303',login.status()===303,{status:login.status(),location:login.headers().location});
  const form=page.locator('form[data-cart-action="quantity"]').first();
  record('same-quantity-fixture-present',(await form.count())===1);
  const field=form.locator('input[name="quantity"]');const quantity=await field.inputValue();
  const version=await form.locator('input[name="version"]').inputValue();
  record('native-quantity-fields',/^\d+$/.test(quantity)&&/^\d+$/.test(version));
  const action=await form.getAttribute('action');
  const updated=page.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname===action);
  await field.fill(quantity);await form.locator('button[type="submit"]').click();
  const result=await updated;await page.waitForLoadState('networkidle');
  record('native-cart-noop-post-303',result.status()===303,{status:result.status(),location:result.headers().location});
  const current=page.locator('form[data-cart-action="quantity"]').first();
  record('same-quantity-and-version-preserved',(await current.locator('input[name="quantity"]').inputValue())===quantity&&(await current.locator('input[name="version"]').inputValue())===version);
  const viewport=await page.evaluate(()=>({viewport:innerWidth,document:document.documentElement.scrollWidth}));
  record('no-js-mobile-no-document-overflow',viewport.document<=viewport.viewport+1,viewport);
  record('theme-button-hidden-without-js',await page.locator('.ef-theme-toggle:visible').count()===0);
  record('no-external-resource-request',log.externalRequests.length===0);
  record('submitted-fields-preserved',log.requests.length===2&&log.requests[0].fieldNames.includes('_csrf')&&log.requests[0].fieldNames.includes('password')&&log.requests[1].fieldNames.includes('quantity')&&log.requests[1].fieldNames.includes('version'));
  log.overall='PASS';await context.close();
 }catch(error){log.overall='FAIL';log.error=sanitize(error.stack||error.message);throw error;}
 finally{await browser.close();fs.writeFileSync(path.join(out,'result.json'),JSON.stringify(log,null,2)+'\n');}
}
run().then(()=>console.log(JSON.stringify({overall:log.overall,checks:log.checks.length,posts:log.requests.length}))).catch(error=>{console.error(sanitize(error.message));process.exitCode=1;});
