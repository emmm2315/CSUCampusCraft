const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {chromium}=require('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/playwright');
const out=process.env.STEP09_BROWSER_OUT,cases=JSON.parse(process.env.STEP09_BROWSER_CASES||'[]'),cookies=JSON.parse(process.env.STEP09_BROWSER_COOKIES||'{}');
fs.mkdirSync(out,{recursive:true});const checks=[],shots=[];let complete=false,error=null;
function check(name,ok){checks.push({name,passed:!!ok});if(!ok)throw Error(name);}
async function control(op,obj){const r=await fetch(process.env.STEP09_BROWSER_CONTROL+op,{method:'POST',headers:{'Authorization':'Bearer '+process.env.STEP09_BROWSER_CONTROL_TOKEN,'Content-Type':'application/json'},body:JSON.stringify(obj)});if(!r.ok)throw Error('HTTP audit rejected '+op);}
async function observe(id,method,url,fn,fields){await control('/before',{id,method,path:url,form_fields:fields});const r=await fn(),u=new URL(r.url()),chain=[];for(let q=r.request().redirectedFrom();q;q=q.redirectedFrom()){const z=await q.response(),v=new URL(q.url());chain.unshift({path:v.pathname+v.search,status:z.status(),location:z.headers()['location']||null});}await control('/after',{id,response_path:u.pathname+u.search,redirect_chain:chain,status:r.status(),content_type:r.headers()['content-type']||'',location:r.headers()['location']||null,body_base64:(await r.body()).toString('base64')});return r;}
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true,args:['--no-proxy-server']});
 try{
  for(const viewport of [{width:1366,height:768},{width:1920,height:1080}]){
   for(const c of cases){
    const context=await browser.newContext({viewport,locale:'zh-CN'});
    if(cookies[c.account])await context.addCookies([{name:'CSUCAMPUSCRAFT_USER_SESSION',value:cookies[c.account],domain:'127.0.0.1',path:'/',httpOnly:true,secure:false,sameSite:'Lax'}]);
    const page=await context.newPage(),id=c.name+'-'+viewport.width;
    let r=await observe(id+'-get','GET',c.path,()=>page.goto('http://127.0.0.1:8080'+c.path,{waitUntil:'domcontentloaded'}));
    if(c.action){
      check(id+'-initial-confirmation-form',await page.locator('[data-checkout-form]').count()===1);
      const fields={receiverName:'<script>alert(1)</script>',receiverPhone:'',receiverAddress:'<script>alert(2)</script>'};
      for(const [k,v] of Object.entries(fields))await page.locator('[name='+k+']').fill(v);
      await page.locator('[data-checkout-form]').evaluate(f=>f.noValidate=true);
      if(c.action==='csrf')await page.locator('[data-checkout-form] input[name=_csrf]').evaluate(n=>n.remove());
      const fn=()=>Promise.all([page.waitForResponse(x=>new URL(x.url()).pathname==='/orders'&&x.request().method()==='POST'),page.locator('[data-checkout-form] button[type=submit]').click()]).then(x=>x[0]);
      r=await observe(id+'-post','POST','/orders',fn,['confirmationToken','receiverName','receiverPhone','receiverAddress',...(c.action==='csrf'?[]:['_csrf'])]);
      await page.waitForLoadState('domcontentloaded');
      if(c.action==='script'){
        check(id+'-literal-script-input',await page.locator('#receiverName').inputValue()===fields.receiverName);
        check(id+'-literal-script-textarea',await page.locator('#receiverAddress').inputValue()===fields.receiverAddress);
        check(id+'-no-injected-inline-script',await page.locator('script:not([src])').count()===0);
      }
    }
    check(id+'-status',r.status()===c.status);
    await page.evaluate(async()=>{if(document.fonts)await document.fonts.ready;await Promise.all([...document.images].map(i=>i.decode().catch(()=>{})));});
    const dom=await page.evaluate(()=>{
      const root=document.querySelector('[data-page-id]'),b=document.querySelector('#cart-quantity'),ids=[...document.querySelectorAll('[id]')].map(n=>n.id);
      return {pageId:root?.dataset.pageId,errorStatus:document.querySelector('[data-error-status]')?.dataset.errorStatus,badge:b?.dataset.cartQuantity,badgeText:b?.textContent.trim(),overflow:document.documentElement.scrollWidth>innerWidth+1,uniqueIds:ids.length===new Set(ids).size,labelProblems:[...document.querySelectorAll('input:not([type=hidden]),textarea,select')].filter(n=>!n.id||!document.querySelector('label[for="'+n.id+'"]')).length,postForms:[...document.forms].filter(f=>f.method.toLowerCase()==='post').map(f=>({action:f.getAttribute('action'),csrfCount:f.querySelectorAll('input[name=_csrf]').length})),orderTotal:root?.dataset.orderTotal,orderNo:root?.dataset.orderNo,orderStatus:root?.dataset.orderStatus,orderCount:root?.dataset.orderCount,page:root?.dataset.page,size:root?.dataset.size,orders:[...document.querySelectorAll('tr[data-order-id]')].map(n=>Number(n.dataset.orderId)),items:[...document.querySelectorAll('tr[data-order-item-id]')].map(n=>({...n.dataset})),imagesLoaded:[...document.images].every(i=>i.complete&&i.naturalWidth>0),forbiddenActions:[...document.querySelectorAll('[href],[action]')].some(n=>/\/orders\/[^/]+\/(?:payment|cancel|ship)(?:$|[/?])/.test(n.getAttribute('href')||n.getAttribute('action')||'')),sessionInLinks:[...document.querySelectorAll('[href],[action]')].some(n=>/;CSUCAMPUSCRAFT_/.test(n.getAttribute('href')||n.getAttribute('action')||'')),shippingNodes:document.querySelectorAll('[data-shipping-value]').length};
    });
    check(id+'-page',c.kind==='error'?dom.errorStatus===String(c.status):dom.pageId===c.kind);
    check(id+'-no-page-overflow',!dom.overflow);check(id+'-unique-ids',dom.uniqueIds);check(id+'-accessible-labels',dom.labelProblems===0);
    check(id+'-csrf-forms',dom.postForms.every(f=>f.csrfCount===1));check(id+'-loaded-images',dom.imagesLoaded);check(id+'-no-future-actions',!dom.forbiddenActions);
    check(id+'-badge',dom.badge===String(c.badge)&&dom.badgeText===String(c.badge));check(id+'-no-session-urls',!dom.sessionInLinks);
    if(c.expectedList){const e=c.expectedList;check(id+'-SQL-count-and-page',Number(dom.orderCount)===e.total&&Number(dom.page)===e.page&&Number(dom.size)===e.size);check(id+'-SQL-row-order',JSON.stringify(dom.orders)===JSON.stringify(e.ids));}
    if(c.expectedOrder){
      const e=c.expectedOrder;check(id+'-SQL-order-header',dom.orderNo===e.orderNo&&dom.orderStatus===e.status&&dom.orderTotal===e.totalAmount);check(id+'-shipping-wrapper-count',dom.shippingNodes===3);
      check(id+'-all-snapshot-lines',dom.items.length===c.expectedItems.length);
      for(let i=0;i<c.expectedItems.length;i++){const x=c.expectedItems[i],n=dom.items[i];check(id+'-snapshot-'+x.id,Number(n.orderItemId)===x.id&&Number(n.orderProductId)===x.productId&&n.snapshotSku===x.skuSnapshot&&n.snapshotName===x.productNameSnapshot&&n.snapshotCover===x.coverImageSnapshot&&n.unitPrice===x.unitPrice&&Number(n.quantity)===x.quantity&&n.lineAmount===x.lineAmount);}
      for(const field of ['receiverName','receiverPhone','receiverAddress']){const value=await page.locator('[data-shipping-value='+field+']').textContent();check(id+'-shipping-hash-'+field,crypto.createHash('sha256').update(value).digest('hex')===e[field+'Sha256']);}
    }
    const filename=id+'.png';check(id+'-new-file',!fs.existsSync(path.join(out,filename)));
    await page.screenshot({path:path.join(out,filename),fullPage:true,mask:[page.locator('[data-shipping-value],[name=receiverName],[name=receiverPhone],[name=receiverAddress]')],maskColor:'#6f786f'});
    const bytes=fs.readFileSync(path.join(out,filename));shots.push({path:filename,viewport,pngWidth:bytes.readUInt32BE(16),pngHeight:bytes.readUInt32BE(20),sha256:crypto.createHash('sha256').update(bytes).digest('hex'),status:r.status(),account:c.account,observation:dom,shippingFieldsMasked:true});await context.close();
   }
  }
  complete=true;
 }catch(e){error='Browser assertion: '+String(e.message);throw e;}
 finally{await browser.close();fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({overall:complete?'PASS':'FAIL',completed:complete,error,checks,screenshots:shots,browser:'Microsoft Edge via Playwright'},null,2));}
})().catch(e=>{process.stderr.write('Browser verification failed: '+e.message+'\n');process.exitCode=1;});
