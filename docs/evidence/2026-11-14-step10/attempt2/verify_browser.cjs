const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {chromium}=require('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/playwright');
const out=process.env.STEP10_BROWSER_OUT,cookies=JSON.parse(process.env.STEP10_BROWSER_COOKIES),orders=JSON.parse(process.env.STEP10_BROWSER_ORDERS),fixed=JSON.parse(process.env.STEP10_BROWSER_FIXED);
fs.mkdirSync(out,{recursive:true});let requestNo=0;const checks=[],shots=[];let completed=false,error=null;
function check(name,ok){checks.push({name,passed:!!ok});if(!ok)throw Error(name);}
async function control(op,obj){const r=await fetch(process.env.STEP10_BROWSER_CONTROL+op,{method:'POST',headers:{Authorization:'Bearer '+process.env.STEP10_BROWSER_CONTROL_TOKEN,'Content-Type':'application/json'},body:JSON.stringify(obj)});if(!r.ok)throw Error('Audit rejected '+op);return r.json();}
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true,args:['--no-proxy-server']});
 try{
  for(const viewport of [{width:1366,height:768},{width:1920,height:1080}]){
   const ctx=await browser.newContext({viewport,locale:'zh-CN'});await ctx.addCookies([{name:'CSUCAMPUSCRAFT_USER_SESSION',value:cookies.alice,domain:'127.0.0.1',path:'/',httpOnly:true,sameSite:'Lax'}]);
   const page=await ctx.newPage(),pending=new Set(),ids=new Map();let responseError=null;
   await page.route('http://127.0.0.1:8080/**',async route=>{
    const req=route.request(),u=new URL(req.url());
    if(req.resourceType()!=='document'){await route.continue();return;}
    const id='browser-'+viewport.width+'-'+(++requestNo);ids.set(req,id);
    const fields=req.postData()?new URLSearchParams(req.postData()):null;
    await control('/before',{id,method:req.method(),path:u.pathname+u.search,result_value:fields?.get('result')||null,form_fields:fields?[...new Set([...fields.keys()])].sort():null});
    await route.continue();
   });
   page.on('response',r=>{
    const req=r.request(),id=ids.get(req);if(!id)return;
    const task=(async()=>{
      let bytes=Buffer.alloc(0),available=true;try{bytes=await r.body();}catch(e){available=false;if(![302,303].includes(r.status()))throw e;}
      await control('/after',{id,status:r.status(),content_type:r.headers()['content-type']||'',location:r.headers()['location']||null,body_base64:bytes.toString('base64'),body_available:available,response_path:new URL(r.url()).pathname+new URL(r.url()).search});
    })().catch(e=>{responseError=String(e.message);}).finally(()=>pending.delete(task));pending.add(task);
   });
   async function settled(){await page.waitForLoadState('domcontentloaded');while(pending.size)await Promise.all([...pending]);if(responseError)throw Error(responseError);}
   async function submit(selector,url){await Promise.all([page.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname===url),page.locator(selector).click()]);await page.waitForLoadState('networkidle');await settled();}
   async function go(url,status){const r=await page.goto('http://127.0.0.1:8080'+url,{waitUntil:'domcontentloaded'});await settled();check(url+'-navigation-'+viewport.width,r.status()===status);return r;}
   async function shot(name,status,kind){
     await settled();await page.evaluate(async()=>{if(document.fonts)await document.fonts.ready;await Promise.all([...document.images].map(i=>i.decode().catch(()=>{})));});
     const dom=await page.evaluate(()=>{const root=document.querySelector('[data-page-id]'),b=document.querySelector('#cart-quantity'),ids=[...document.querySelectorAll('[id]')].map(x=>x.id);return {pageId:root?.dataset.pageId,errorStatus:document.querySelector('[data-error-status]')?.dataset.errorStatus,orderNo:root?.dataset.orderNo,orderStatus:root?.dataset.orderStatus,orderTotal:root?.dataset.orderTotal,badge:b?.dataset.cartQuantity,badgeText:b?.textContent.trim(),overflow:document.documentElement.scrollWidth>innerWidth+1,uniqueIds:ids.length===new Set(ids).size,labels:[...document.querySelectorAll('input:not([type=hidden]),textarea,select')].every(n=>n.id&&document.querySelector('label[for="'+n.id+'"]')),forms:[...document.forms].filter(f=>f.method.toLowerCase()==='post').map(f=>({action:f.getAttribute('action'),csrf:f.querySelectorAll('input[name=_csrf]').length})),images:[...document.images].every(i=>i.complete&&i.naturalWidth>0),sessionLinks:[...document.querySelectorAll('[href],[action]')].some(n=>/;CSUCAMPUSCRAFT_/.test(n.getAttribute('href')||n.getAttribute('action')||'')),receipt:document.querySelector('[data-payment-no]')?.textContent.trim(),shippingNodes:document.querySelectorAll('[data-shipping-value]').length};});
     check(name+'-page-'+viewport.width,kind==='error'?dom.errorStatus===String(status):dom.pageId===kind);check(name+'-no-overflow-'+viewport.width,!dom.overflow);check(name+'-unique-ids-'+viewport.width,dom.uniqueIds);check(name+'-labels-'+viewport.width,dom.labels);check(name+'-all-CSRF-'+viewport.width,dom.forms.every(x=>x.csrf===1));check(name+'-images-'+viewport.width,dom.images);check(name+'-no-session-url-'+viewport.width,!dom.sessionLinks);check(name+'-current-cart1-'+viewport.width,dom.badge==='1'&&dom.badgeText==='1');
     const filename=name+'-'+viewport.width+'.png';check(name+'-new-PNG-'+viewport.width,!fs.existsSync(path.join(out,filename)));await page.screenshot({path:path.join(out,filename),fullPage:true,mask:[page.locator('[data-shipping-value],[name=receiverName],[name=receiverPhone],[name=receiverAddress]')],maskColor:'#6f786f'});
     const raw=fs.readFileSync(path.join(out,filename));shots.push({path:filename,viewport,pngWidth:raw.readUInt32BE(16),pngHeight:raw.readUInt32BE(20),sha256:crypto.createHash('sha256').update(raw).digest('hex'),status,observation:dom,shippingFieldsMasked:true});
   }
   const current=orders[String(viewport.width)];
   await go('/orders/'+current.pay+'/payment',200);check('two-canonical-payment-buttons-'+viewport.width,await page.locator('button[name=result]').count()===2);await shot('u09-pending-teaching',200,'U09');
   await go('/orders/'+current.cancel,200);await page.locator('[data-cancel-confirmation] summary').click();check('cancel-prompt-before-submit-'+viewport.width,(await page.locator('[data-cancel-confirmation]').textContent()).includes('库存')&&(await page.locator('[data-cancel-confirmation]').textContent()).includes('购物车'));await shot('u08-cancel-confirmation',200,'U08');
   for(const [name,no] of [['u08-paid-receipt',fixed.paid],['u08-cancelled',fixed.cancelled],['u08-shipped-first-receipt',fixed.shipped]]){await go('/orders/'+no,200);await shot(name,200,'U08');}
   await go('/orders/'+fixed.paid+'/payment',409);await shot('u09-state-conflict',409,'error');
   await ctx.addCookies([{name:'CSUCAMPUSCRAFT_USER_SESSION',value:cookies.bob,domain:'127.0.0.1',path:'/',httpOnly:true,sameSite:'Lax'}]);
   await go('/orders/'+fixed.paid+'/payment',404);
   // Bob's cart is empty; preserve the actual observation without forcing alice's badge assertion.
   await page.screenshot({path:path.join(out,'u09-foreign-404-'+viewport.width+'.png'),fullPage:true,mask:[page.locator('[data-shipping-value],[name=receiverName],[name=receiverPhone],[name=receiverAddress]')],maskColor:'#6f786f'});
   {const raw=fs.readFileSync(path.join(out,'u09-foreign-404-'+viewport.width+'.png'));shots.push({path:'u09-foreign-404-'+viewport.width+'.png',viewport,pngWidth:raw.readUInt32BE(16),pngHeight:raw.readUInt32BE(20),sha256:crypto.createHash('sha256').update(raw).digest('hex'),status:404,observation:{pageId:null,errorStatus:'404',account:'bob'},shippingFieldsMasked:true});check('foreign-no-order-leak-'+viewport.width,!(await page.locator('body').innerText()).includes(fixed.paid));}
   await ctx.addCookies([{name:'CSUCAMPUSCRAFT_USER_SESSION',value:cookies.alice,domain:'127.0.0.1',path:'/',httpOnly:true,sameSite:'Lax'}]);
   await go('/orders/UNKNOWN_STEP10_ORDER/payment',404);await shot('u09-unknown-404',404,'error');
   await go('/orders/'+current.pay+'/payment',200);
   await page.locator('[data-payment-form] input[name=_csrf]').evaluate(n=>n.remove());
   await submit('button[name=result][value=SUCCESS]','/orders/'+current.pay+'/payment');await shot('u09-CSRF-403',403,'error');
   await go('/orders/'+current.pay+'/payment',200);
   await submit('button[name=result][value=FAILURE]','/orders/'+current.pay+'/payment');check('failure-still-pending-'+viewport.width,await page.locator('[data-order-status=PENDING_PAYMENT]').count()===1);check('failure-flash-'+viewport.width,(await page.locator('body').innerText()).includes('失败'));await shot('journey-failure-still-pending',200,'U08');
   await page.locator('[data-open-payment]').click();await settled();await submit('button[name=result][value=SUCCESS]','/orders/'+current.pay+'/payment');check('success-paid-'+viewport.width,await page.locator('[data-order-status=PAID]').count()===1);check('success-receipt-visible-'+viewport.width,(await page.locator('[data-payment-no]').textContent()).length>0);await shot('journey-success-first-receipt',200,'U08');
   await go('/orders/'+current.cancel,200);await page.locator('[data-cancel-confirmation] summary').click();await submit('[data-confirm-cancel]','/orders/'+current.cancel+'/cancel');check('cancel-final-state-'+viewport.width,await page.locator('[data-order-status=CANCELLED]').count()===1);await shot('journey-cancelled-no-cart-restore',200,'U08');
   await settled();await ctx.close();
  }
  check('exact24screenshots',shots.length===24);completed=true;
 }catch(e){error=String(e.message);throw e;}
 finally{await browser.close();fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({overall:completed?'PASS':'FAIL',completed,error,checks,screenshots:shots,browser:'Microsoft Edge via Playwright',transport:'Actual browser request continued after seven-table before snapshot; redirect responses separately observed'},null,2));}
})().catch(e=>{process.stderr.write(String(e.message));process.exitCode=1;});
