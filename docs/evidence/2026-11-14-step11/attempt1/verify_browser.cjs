const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {chromium}=require('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/playwright');
const out=process.env.STEP11_BROWSER_OUT,cookies=JSON.parse(process.env.STEP11_BROWSER_COOKIES),orders=JSON.parse(process.env.STEP11_BROWSER_ORDERS),fixed=JSON.parse(process.env.STEP11_BROWSER_FIXED);
fs.mkdirSync(out,{recursive:true});let requestNo=0;const checks=[],shots=[];let completed=false,error=null;
function check(name,ok){checks.push({name,passed:!!ok});if(!ok)throw Error(name);}
async function control(op,obj){const r=await fetch(process.env.STEP11_BROWSER_CONTROL+op,{method:'POST',headers:{Authorization:'Bearer '+process.env.STEP11_BROWSER_CONTROL_TOKEN,'Content-Type':'application/json'},body:JSON.stringify(obj)});if(!r.ok)throw Error('Audit rejected '+op);return r.json();}
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true,args:['--no-proxy-server']});
 try{
  for(const viewport of [{width:1366,height:768},{width:1920,height:1080}]){
   const ctx=await browser.newContext({viewport,locale:'zh-CN'});
   await ctx.addCookies([{name:'CSUCAMPUSCRAFT_USER_SESSION',value:cookies.alice,domain:'127.0.0.1',path:'/',httpOnly:true,sameSite:'Lax'},{name:'CSUCAMPUSCRAFT_ADMIN_SESSION',value:cookies.admin,domain:'127.0.0.1',path:'/',httpOnly:true,sameSite:'Lax'}]);
   const page=await ctx.newPage(),pending=new Set(),ids=new Map();let responseError=null;
   await page.route(/^http:\/\/127\.0\.0\.1:808[01]\//,async route=>{
    const req=route.request(),u=new URL(req.url());if(req.resourceType()!=='document'){await route.continue();return;}
    const id='browser-'+viewport.width+'-'+(++requestNo);ids.set(req,id);
    const fields=req.postData()?new URLSearchParams(req.postData()):null;
    await control('/before',{id,method:req.method(),port:Number(u.port),path:u.pathname+u.search,form_fields:fields?[...new Set([...fields.keys()])].sort():null});await route.continue();
   });
   page.on('response',r=>{
    const req=r.request(),id=ids.get(req);if(!id)return;
    const task=(async()=>{let bytes=Buffer.alloc(0),available=true;try{bytes=await r.body();}catch(e){available=false;if(![302,303].includes(r.status()))throw e;}
      await control('/after',{id,status:r.status(),content_type:r.headers()['content-type']||'',location:r.headers()['location']||null,body_base64:bytes.toString('base64'),body_available:available,response_path:new URL(r.url()).pathname+new URL(r.url()).search});
    })().catch(e=>{responseError=String(e.message);}).finally(()=>pending.delete(task));pending.add(task);
   });
   async function settled(){await page.waitForLoadState('domcontentloaded');while(pending.size)await Promise.all([...pending]);if(responseError)throw Error(responseError);}
   async function submit(selector,url){await Promise.all([page.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname===url),page.locator(selector).click()]);await page.waitForLoadState('networkidle');await settled();}
   async function go(url,status,port=8081){const r=await page.goto('http://127.0.0.1:'+port+url,{waitUntil:'domcontentloaded'});await settled();check(url+'-navigation-'+viewport.width,r.status()===status);return r;}
   async function shot(name,status,kind){
    await settled();await page.evaluate(async()=>{if(document.fonts)await document.fonts.ready;await Promise.all([...document.images].map(i=>i.decode().catch(()=>{})));});
    const dom=await page.evaluate(()=>{const root=document.querySelector('[data-page-id]'),b=document.querySelector('#cart-quantity'),ids=[...document.querySelectorAll('[id]')].map(x=>x.id);return {port:Number(location.port),pageId:root?.dataset.pageId,errorStatus:document.querySelector('[data-error-status]')?.dataset.errorStatus,orderNo:root?.dataset.orderNo,orderStatus:root?.dataset.orderStatus,orderTotal:root?.dataset.orderTotal,orderCount:root?.dataset.orderCount,page:root?.dataset.page,size:root?.dataset.size,badge:b?.dataset.cartQuantity,badgeText:b?.textContent.trim(),overflow:document.documentElement.scrollWidth>innerWidth+1,uniqueIds:ids.length===new Set(ids).size,labels:[...document.querySelectorAll('input:not([type=hidden]),textarea,select')].every(n=>n.id&&document.querySelector('label[for="'+n.id+'"]')),forms:[...document.forms].filter(f=>f.method.toLowerCase()==='post').map(f=>({action:f.getAttribute('action'),csrf:f.querySelectorAll('input[name=_csrf]').length})),images:[...document.images].every(i=>i.complete&&i.naturalWidth>0),sessionLinks:[...document.querySelectorAll('[href],[action]')].some(n=>/;CSUCAMPUSCRAFT_/.test(n.getAttribute('href')||n.getAttribute('action')||'')),receipt:document.querySelector('[data-payment-no]')?.textContent.trim(),shippedTime:document.querySelector('[data-shipped-time]')?.textContent.trim(),shippingNodes:document.querySelectorAll('[data-shipping-value]').length,shipForms:document.querySelectorAll('[data-ship-order-form]').length};});
    check(name+'-page-'+viewport.width,kind==='error'?dom.errorStatus===String(status):dom.pageId===kind);check(name+'-no-overflow-'+viewport.width,!dom.overflow);check(name+'-unique-ids-'+viewport.width,dom.uniqueIds);check(name+'-labels-'+viewport.width,dom.labels);check(name+'-all-CSRF-'+viewport.width,dom.forms.every(x=>x.csrf===1));check(name+'-images-'+viewport.width,dom.images);check(name+'-no-session-url-'+viewport.width,!dom.sessionLinks);
    if(dom.port===8080)check(name+'-current-cart1-'+viewport.width,dom.badge==='1'&&dom.badgeText==='1');
    if(kind==='A07')check(name+'-only-PAID-form-'+viewport.width,dom.shipForms===(dom.orderStatus==='PAID'?1:0));
    const filename=name+'-'+viewport.width+'.png';check(name+'-new-PNG-'+viewport.width,!fs.existsSync(path.join(out,filename)));await page.screenshot({path:path.join(out,filename),fullPage:true,mask:[page.locator('[data-shipping-value],[name=receiverName],[name=receiverPhone],[name=receiverAddress]')],maskColor:'#6f786f'});
    const raw=fs.readFileSync(path.join(out,filename));shots.push({path:filename,viewport,pngWidth:raw.readUInt32BE(16),pngHeight:raw.readUInt32BE(20),sha256:crypto.createHash('sha256').update(raw).digest('hex'),status,observation:dom,shippingFieldsMasked:true});
    return dom;
   }
   const no=orders[String(viewport.width)];
   await go('/orders',200);await shot('a06-allsite-orders',200,'A06');
   await go('/orders?'+new URLSearchParams({orderNo:no,status:'PAID',userId:'1',size:'1'}),200);check('combined-count1-'+viewport.width,await page.locator('[data-order-count="1"]').count()===1);await shot('a06-CUSTOMER-status-exact-order',200,'A06');
   await page.locator('tr[data-order-id] a').first().click();await settled();
   await page.locator('[data-ship-confirmation] summary').click();const prompt=await page.locator('[data-ship-confirmation]').textContent();check('confirmation-before-POST-'+viewport.width,prompt.includes(no)&&prompt.includes('库存')&&prompt.includes('收货'));await shot('a07-paid-confirm-before-ship',200,'A07');
   await page.locator('[data-ship-order-form] input[name=_csrf]').evaluate(n=>n.remove());await submit('[data-confirm-ship]','/orders/'+no+'/ship');await shot('a07-missing-CSRF-403',403,'error');
   await go('/orders/'+no,200);await page.locator('[data-ship-confirmation] summary').click();await submit('[data-confirm-ship]','/orders/'+no+'/ship');check('actual-first-shipment-'+viewport.width,await page.locator('[data-order-status=SHIPPED]').count()===1);
   const shipped=await shot('journey-admin-first-shipped',200,'A07');check('shipment-flash-'+viewport.width,(await page.locator('body').innerText()).includes('发货'));
   await go('/orders/'+no,200,8080);const user=await shot('journey-user-same-shipped-snapshot',200,'U08');check('same-receipt-both-ends-'+viewport.width,user.receipt===shipped.receipt&&!!user.receipt);check('user-same-first-shipped-time-'+viewport.width,(await page.locator('body').innerText()).includes(shipped.shippedTime));
   await go('/orders?'+new URLSearchParams({orderNo:no,status:'SHIPPED',userId:'1',size:'1'}),200);await shot('a06-after-ship-filter',200,'A06');
   await go('/orders?status=ALL&userId=1&page=2&size=2',200);await shot('a06-CUSTOMER-page2-preserves-filter',200,'A06');
   await go('/orders?'+new URLSearchParams({orderNo:no,userId:'2'}),200);check('cross-customer-AND-empty-'+viewport.width,await page.locator('[data-order-count="0"]').count()===1);await shot('a06-empty-intersection',200,'A06');
   await go('/orders?userId=1&page=999&size=2',200);await shot('a06-outofrange-recovery',200,'A06');
   await go('/orders/'+fixed.completed,200);check('completed-no-ship-form-'+viewport.width,await page.locator('[data-ship-order-form]').count()===0);await shot('a07-completed-keeps-first-shipped-time',200,'A07');
   await go('/orders?size=51',400);await shot('a06-invalid-query-400',400,'error');
   await go('/orders/UNKNOWN_STEP11_ORDER',404);await shot('a07-unknown-order-404',404,'error');
   await settled();await ctx.close();
  }
  check('exact26screenshots',shots.length===26);completed=true;
 }catch(e){error=String(e.message);throw e;}
 finally{await browser.close();fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({overall:completed?'PASS':'FAIL',completed,error,checks,screenshots:shots,browser:'Microsoft Edge via Playwright',transport:'Actual browser requests to 8080/8081 continued after seven-table before snapshot; redirect responses separately observed'},null,2));}
})().catch(e=>{process.stderr.write(String(e.message));process.exitCode=1;});
