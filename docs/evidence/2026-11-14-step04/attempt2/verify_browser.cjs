const {chromium}=require('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path');
const out=process.env.STEP04_BROWSER_OUT,password=process.env.STEP04_VALID_PASSWORD,wrong=process.env.STEP04_INVALID_PASSWORD;
if(!out||!password||!wrong)throw Error('Explicit output and secret environment variables required');
fs.mkdirSync(out,{recursive:true});
const checks=[],shots=[];
function check(name,okay){checks.push({name,passed:!!okay});if(!okay)throw Error('Browser assertion: '+name);}
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 try {
  for(const width of [1366,1920]){
   const context=await browser.newContext({viewport:{width,height:width===1366?768:1080}});
   const page=await context.newPage();
   let inlineExecuted=false;
   page.on('dialog',async d=>{inlineExecuted=true;await d.dismiss();});
   async function screenshot(name,status){
    await page.evaluate(()=>{document.querySelectorAll('img').forEach(n=>n.loading='eager');window.scrollTo(0,0);});
    await page.waitForFunction(()=>[...document.images].every(n=>n.complete&&n.naturalWidth>0),null,{timeout:8000});
    const data=await page.evaluate(()=>({
      pageId:document.querySelector('[data-page-id]')?.getAttribute('data-page-id')||null,
      overflowing:document.documentElement.scrollWidth>innerWidth,
      labelsLinked:[...document.querySelectorAll('label[for]')].every(n=>!!document.getElementById(n.htmlFor)),
      passwordEmpty:[...document.querySelectorAll('input[name=password]')].every(n=>n.value===''&&!n.getAttribute('value')),
      passwordType:[...document.querySelectorAll('input[name=password]')].every(n=>n.type==='password'),
      hasLogout:!!document.querySelector('form[action="/logout"]'),
      forms:[...document.querySelectorAll('form')].map(n=>({method:n.method,hasCsrf:n.method==='get'||!!n.querySelector('input[name=_csrf]')})),
      sessionUrlRewrite:[...document.querySelectorAll('[href],[action],[src]')].some(n=>['href','action','src'].some(a=>(n.getAttribute(a)||'').includes(';CSUCAMPUSCRAFT_'))),
      inlineScripts:[...document.scripts].filter(n=>!n.src).length,
      fieldErrors:document.querySelectorAll('.field-error').length,
      authError:!!document.querySelector('[data-auth-error]'),
      allImagesLoaded:[...document.images].every(n=>n.complete&&n.naturalWidth>0)
    }));
    check(name+'-no-overflow',!data.overflowing);
    check(name+'-labels',data.labelsLinked);
    check(name+'-password-not-retained',data.passwordEmpty&&data.passwordType);
    check(name+'-csrf-forms',data.forms.every(x=>x.hasCsrf));
    check(name+'-no-url-session',!data.sessionUrlRewrite);
    check(name+'-escaped-script',!inlineExecuted&&!data.inlineScripts);
    const file=name+'-'+width+'.png';
    await page.screenshot({path:path.join(out,file),fullPage:true});
    shots.push({name,width,viewportHeight:width===1366?768:1080,status,screenshot:file,...data,passed:true});
   }
   async function goto(port,p,expected,name){
    const r=await page.goto('http://127.0.0.1:'+port+p,{waitUntil:'networkidle',timeout:20000});
    check(name+'-status',r.status()===expected);
    await screenshot(name,r.status());
    return r;
   }
   async function submit(port,username,pwd,expected,name,{noValidate=false}={}){
    await page.locator('input[name=username]').fill(username);
    await page.locator('input[name=password]').fill(pwd);
    if(noValidate)await page.locator('form[action="/login"]').evaluate(n=>n.noValidate=true);
    const navigation=page.waitForNavigation({waitUntil:'networkidle',timeout:20000});
    const pending=page.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname==='/login',{timeout:20000});
    await page.locator('form[action="/login"] button[type=submit]').click();
    const response=await pending;
    check(name+'-post-status',response.status()===expected);
    await navigation;
    await screenshot(name,response.status());
    return response;
   }
   // Real forms on one browser context; cookie storage is shared across both ports.
   await goto(8080,'/login',200,'user-login');
   await submit(8080,'alice',wrong,200,'user-wrong-password');
   check('user-wrong-password-message',await page.locator('[data-auth-error]').count()===1);
   await goto(8080,'/login',200,'user-before-invalid-fields');
   await submit(8080,'',password,400,'user-fields-400',{noValidate:true});
   await goto(8080,'/login',200,'user-before-script-name');
   await submit(8080,'<script>authFixture()</script>',wrong,200,'user-escaped-username');
   check('user-script-not-executed',!inlineExecuted);
   await goto(8080,'/login',200,'user-before-correct');
   const oldUser=(await context.cookies()).find(c=>c.name==='CSUCAMPUSCRAFT_USER_SESSION')?.value;
   const userResponse=await submit(8080,'alice',password,303,'user-logged-in');
   const newUser=(await context.cookies()).find(c=>c.name==='CSUCAMPUSCRAFT_USER_SESSION')?.value;
   check('user-session-id-rotated',!!oldUser&&!!newUser&&oldUser!==newUser);
   check('user-login-returns-home',new URL(page.url()).pathname==='/');
   check('user-logout-control-present',await page.locator('form[action="/logout"]').count()===1);
   await goto(8081,'/login',200,'admin-login');
   await submit(8081,'admin',wrong,200,'admin-wrong-password');
   await goto(8081,'/login',200,'admin-before-invalid-fields');
   await submit(8081,'admin','',400,'admin-fields-400',{noValidate:true});
   await goto(8081,'/login',200,'admin-before-correct');
   const oldAdmin=(await context.cookies()).find(c=>c.name==='CSUCAMPUSCRAFT_ADMIN_SESSION')?.value;
   await submit(8081,'admin',password,303,'admin-logged-in');
   const cookieNames=(await context.cookies()).map(c=>c.name);
   const newAdmin=(await context.cookies()).find(c=>c.name==='CSUCAMPUSCRAFT_ADMIN_SESSION')?.value;
   check('admin-session-id-rotated',!!oldAdmin&&!!newAdmin&&oldAdmin!==newAdmin);
   check('two-cookie-names-in-same-browser',cookieNames.includes('CSUCAMPUSCRAFT_USER_SESSION')&&cookieNames.includes('CSUCAMPUSCRAFT_ADMIN_SESSION'));
   check('admin-logout-control-present',await page.locator('form[action="/logout"]').count()===1);
   await goto(8081,'/categories',404,'admin-unimplemented-404');
   await goto(8080,'/cart',404,'user-unimplemented-404');
   await goto(8080,'/',200,'user-before-logout');
   let navigation=page.waitForNavigation({waitUntil:'networkidle',timeout:20000});
   let wait=page.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname==='/logout');
   await page.locator('form[action="/logout"] button').click();
   check('user-real-logout-303',(await wait).status()===303);await navigation;
   await screenshot('user-logged-out',303);
   check('user-no-logout-after-exit',await page.locator('form[action="/logout"]').count()===0);
   await goto(8081,'/',200,'admin-survives-user-logout');
   check('admin-still-logged-in',await page.locator('form[action="/logout"]').count()===1);
   // Reverse isolation check.
   await goto(8080,'/login',200,'user-login-again');
   await submit(8080,'alice',password,303,'user-logged-in-again');
   await goto(8081,'/',200,'admin-before-logout');
   navigation=page.waitForNavigation({waitUntil:'networkidle',timeout:20000});
   wait=page.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname==='/logout');
   await page.locator('form[action="/logout"] button').click();
   check('admin-real-logout-303',(await wait).status()===303);await navigation;
   await screenshot('admin-logged-out',303);
   check('admin-logout-returns-login',new URL(page.url()).pathname==='/login');
   await goto(8080,'/',200,'user-survives-admin-logout');
   check('user-still-logged-in',await page.locator('form[action="/logout"]').count()===1);
   // Submit a real form with deliberately wrong token; captured 403 page contains no values.
   await goto(8080,'/login',200,'user-before-csrf-rejection');
   await page.locator('input[name=_csrf]').evaluate(n=>n.value='0'.repeat(64));
   await submit(8080,'alice',password,403,'user-login-csrf-403');
   await goto(8081,'/login',200,'admin-before-csrf-rejection');
   await page.locator('input[name=_csrf]').evaluate(n=>n.value='0'.repeat(64));
   await submit(8081,'admin',password,403,'admin-login-csrf-403');
   await context.close();
  }
 } finally {await browser.close();fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({overall:checks.every(x=>x.passed)?'PASS':'FAIL',checks,screenshots:shots},null,2));}
 process.stdout.write(JSON.stringify({overall:'PASS',checks:checks.length,screenshots:shots.length,secretsRecorded:false}));
})().catch(e=>{process.stderr.write(e.message.replace(/;CSUCAMPUSCRAFT_(?:USER|ADMIN)_SESSION=[A-Za-z0-9.-]+/g,';SESSION=[REDACTED]'));process.exit(1);});

