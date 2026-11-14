const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {chromium}=require('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/playwright');
const out=process.env.STEP12_BROWSER_OUT,phase=process.env.STEP12_BROWSER_PHASE,cookies=JSON.parse(process.env.STEP12_BROWSER_COOKIES),fixed=JSON.parse(process.env.STEP12_BROWSER_FIXED);
const changedMessage='顾客状态已更新。真实切换后的既有会话需重新登录，购物车与历史订单保留。';
fs.mkdirSync(out,{recursive:true});let requestNo=0;const checks=[],shots=[];let completed=false,error=null;
function check(name,ok){checks.push({name,passed:!!ok});if(!ok)throw Error(name);}
async function control(op,obj){const r=await fetch(process.env.STEP12_BROWSER_CONTROL+op,{method:'POST',headers:{Authorization:'Bearer '+process.env.STEP12_BROWSER_CONTROL_TOKEN,'Content-Type':'application/json'},body:JSON.stringify(obj)});if(!r.ok)throw Error('Audit rejected '+op);return r.json();}
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true,args:['--no-proxy-server']});
 try{
  for(const viewport of [{width:1366,height:768},{width:1920,height:1080}]){
   const ctx=await browser.newContext({viewport,locale:'zh-CN'});await ctx.addCookies([{name:'CSUCAMPUSCRAFT_ADMIN_SESSION',value:cookies.admin,domain:'127.0.0.1',path:'/',httpOnly:true,sameSite:'Lax'}]);
   const page=await ctx.newPage(),pending=new Set(),ids=new Map();let responseError=null;
   await page.route(/^http:\/\/127\.0\.0\.1:808[01]\//,async route=>{
    const req=route.request(),u=new URL(req.url());if(req.resourceType()!=='document'){await route.continue();return;}
    const id='browser-'+phase+'-'+viewport.width+'-'+(++requestNo);ids.set(req,id);const fields=req.postData()?new URLSearchParams(req.postData()):null;
    await control('/before',{id,method:req.method(),port:Number(u.port),path:u.pathname+u.search,target_status:fields?.get('targetStatus')||null,form_fields:fields?[...new Set([...fields.keys()])].sort():null});await route.continue();
   });
   page.on('response',r=>{
    const req=r.request();if(req.resourceType()!=='document')return;const u=new URL(r.url());if(u.hostname!=='127.0.0.1'||!['8080','8081'].includes(u.port))return;
    let id=ids.get(req);const afterOnly=!id;if(afterOnly){id='browser-'+phase+'-'+viewport.width+'-redirect-'+(++requestNo);ids.set(req,id);}
    const task=(async()=>{
     let bytes=Buffer.alloc(0),available=true;try{bytes=await r.body();}catch(e){available=false;if(![302,303].includes(r.status()))throw e;}
     const from=req.redirectedFrom(),fu=from?new URL(from.url()):null;
     await control(afterOnly?'/after-only':'/after',{id,method:req.method(),port:Number(u.port),path:u.pathname+u.search,redirected_from:fu?{method:from.method(),port:Number(fu.port),path:fu.pathname+fu.search}:null,status:r.status(),content_type:r.headers()['content-type']||'',location:r.headers()['location']||null,body_base64:bytes.toString('base64'),body_available:available});
    })().catch(e=>{responseError=String(e.message);}).finally(()=>pending.delete(task));pending.add(task);
   });
   async function settled(){await page.waitForLoadState('domcontentloaded');while(pending.size)await Promise.all([...pending]);if(responseError)throw Error(responseError);}
   async function submit(selector,url,port=8081){await Promise.all([page.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname===url&&new URL(r.url()).port===String(port)),page.locator(selector).click()]);await page.waitForLoadState('networkidle');await settled();await control('/register-private',{values:(await ctx.cookies()).map(c=>c.value)});}
   async function go(url,status,port=8081){const r=await page.goto('http://127.0.0.1:'+port+url,{waitUntil:'domcontentloaded'});await settled();check(url+'-navigation-'+viewport.width,r.status()===status);return r;}
   async function exactFlash(){check('exact-global-status-'+phase+'-'+viewport.width,(await page.locator('[role=status]').allTextContents()).some(s=>s.trim()===changedMessage));}
   async function shot(name,status,kind){
    await settled();await page.evaluate(async()=>{if(document.fonts)await document.fonts.ready;await Promise.all([...document.images].map(i=>i.decode().catch(()=>{})));});
    const dom=await page.evaluate(()=>{const root=document.querySelector('[data-page-id]'),ids=[...document.querySelectorAll('[id]')].map(x=>x.id);return {port:Number(location.port),pageId:root?.dataset.pageId,errorStatus:document.querySelector('[data-error-status]')?.dataset.errorStatus,customerId:root?.dataset.customerId,customerStatus:root?.dataset.customerStatus,customerCount:root?.dataset.customerCount,page:root?.dataset.page,size:root?.dataset.size,dashboardCounts:[...document.querySelectorAll('[data-dashboard-card]')].map(c=>({key:c.dataset.dashboardCard,count:c.querySelector('[data-dashboard-count]')?.textContent.trim()})),globalStatuses:[...document.querySelectorAll('[role=status]')].map(n=>n.textContent.trim()),contactNodes:document.querySelectorAll('[data-customer-contact]').length,overflow:document.documentElement.scrollWidth>innerWidth+1,uniqueIds:ids.length===new Set(ids).size,labels:[...document.querySelectorAll('input:not([type=hidden]),textarea,select')].every(n=>n.id&&document.querySelector('label[for="'+n.id+'"]')),forms:[...document.forms].filter(f=>f.method.toLowerCase()==='post').map(f=>({action:f.getAttribute('action'),csrf:f.querySelectorAll('input[name=_csrf]').length})),images:[...document.images].every(i=>i.complete&&i.naturalWidth>0),sessionLinks:[...document.querySelectorAll('[href],[action]')].some(n=>/;CSUCAMPUSCRAFT_/.test(n.getAttribute('href')||n.getAttribute('action')||''))};});
    check(name+'-page-'+viewport.width,kind==='error'?dom.errorStatus===String(status):dom.pageId===kind);check(name+'-no-overflow-'+viewport.width,!dom.overflow);check(name+'-unique-ids-'+viewport.width,dom.uniqueIds);check(name+'-labels-'+viewport.width,dom.labels);check(name+'-all-CSRF-'+viewport.width,dom.forms.every(x=>x.csrf===1));check(name+'-images-'+viewport.width,dom.images);check(name+'-no-session-url-'+viewport.width,!dom.sessionLinks);
    const filename=name+'-'+viewport.width+'.png';check(name+'-new-PNG-'+viewport.width,!fs.existsSync(path.join(out,filename)));await page.screenshot({path:path.join(out,filename),fullPage:true,mask:[page.locator('[data-customer-contact],[data-shipping-value],[name=receiverName],[name=receiverPhone],[name=receiverAddress],[name=password]')],maskColor:'#6f786f'});
    const raw=fs.readFileSync(path.join(out,filename));shots.push({path:filename,viewport,pngWidth:raw.readUInt32BE(16),pngHeight:raw.readUInt32BE(20),sha256:crypto.createHash('sha256').update(raw).digest('hex'),status,observation:dom,contactAndShippingFieldsMasked:true});return dom;
   }
   if(phase==='main'){
    await go('/',200);await shot('a02-live-five-metrics',200,'A02');
    await go('/customers',200);await shot('a08-CUSTOMER-only-list',200,'A08');
    await go('/customers?q=%25&status=ALL&page=1&size=10',200);check('percent-matches-one-literal-'+viewport.width,await page.locator('[data-customer-count="1"]').count()===1);await shot('a08-percent-literal-filter',200,'A08');
    await go('/login?returnUrl=%2Fcart',200,8080);await page.locator('[name=username]').fill('alice');await page.locator('[name=password]').fill(process.env.STEP12_BROWSER_PASSWORD);await submit('form button[type=submit]','/login',8080);check('fresh-user-cart-before-disable-'+viewport.width,await page.locator('[data-page-id=U05]').count()===1);
    await go('/customers/1',200);await page.locator('[data-disable-confirmation] summary').click();const prompt=await page.locator('[data-disable-confirmation]').textContent();check('disable-warning-before-submit-'+viewport.width,prompt.includes('alice')&&prompt.includes('重新登录')&&prompt.includes('购物车')&&prompt.includes('订单'));await shot('a09-disable-confirmation',200,'A09');
    await submit('[data-confirm-disable]','/customers/1/status');await exactFlash();check('disabled-current-state-'+viewport.width,await page.locator('[data-customer-status=DISABLED]').count()===1);await shot('journey-disabled-keeps-data',200,'A09');
    await go('/cart',200,8080);check('old-user-redirected-to-login-'+viewport.width,new URL(page.url()).pathname==='/login');await shot('journey-old-session-login-required',200,'U04');
    await go('/customers/1',200);await submit('[data-confirm-enable]','/customers/1/status');await exactFlash();check('enabled-current-state-'+viewport.width,await page.locator('[data-customer-status=ENABLED]').count()===1);await shot('journey-enabled-new-login-required',200,'A09');
    await page.locator('[data-customer-orders-link]').click();await settled();check('orders-link-keeps-CUSTOMER-'+viewport.width,new URL(page.url()).searchParams.get('userId')==='1');await shot('a06-from-customer-orders',200,'A06');
    await go('/customers?q=no-such-customer',200);check('empty-customer-results-'+viewport.width,await page.locator('[data-customer-count="0"]').count()===1);await shot('a08-empty-match',200,'A08');
    await go('/customers/999999',404);await shot('a09-unknown-404',404,'error');
   }else if(phase==='empty'){
    await go('/',200);check('zero-business-five-cards-'+viewport.width,await page.locator('[data-dashboard-count]').count()===5&&(await page.locator('[data-dashboard-count]').allTextContents()).every(s=>s.trim()==='0'));await shot('a02-empty-business-ADMIN-kept',200,'A02');
   }else if(phase==='error'){
    await go('/',500);check('error-not-zero-fallback-'+viewport.width,await page.locator('[data-dashboard-count]').count()===0);check('error-retry-available-'+viewport.width,await page.locator('[data-dashboard-retry][href="/"]').count()===1);await shot('a02-natural-permission-error-retry',500,'A02');
   }else throw Error('Unknown browser phase');
   await settled();await ctx.close();
  }
  check('phase-screenshot-count',shots.length===(phase==='main'?20:2));completed=true;
 }catch(e){error=String(e.message);throw e;}
 finally{await browser.close();fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({overall:completed?'PASS':'FAIL',completed,error,phase,checks,screenshots:shots,browser:'Microsoft Edge via Playwright',transport:'Actual browser responses; routed requests before/after, redirect GET fallback explicitly after-only'},null,2));}
})().catch(e=>{process.stderr.write(String(e.message));process.exitCode=1;});
