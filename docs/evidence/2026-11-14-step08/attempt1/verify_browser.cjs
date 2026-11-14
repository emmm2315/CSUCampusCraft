const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {chromium}=require('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/playwright');
const out=process.env.STEP08_BROWSER_OUT,cases=JSON.parse(process.env.STEP08_BROWSER_CASES||'[]'),cookies=JSON.parse(process.env.STEP08_BROWSER_COOKIES||'{}');
fs.mkdirSync(out,{recursive:true});
const prior=fs.existsSync(path.join(out,'result.json'))?JSON.parse(fs.readFileSync(path.join(out,'result.json'),'utf8')):{checks:[],screenshots:[]};
const checks=[...prior.checks],shots=[...prior.screenshots];let complete=false,error=null,seq=0;
function check(name,ok){checks.push({name,passed:!!ok});if(!ok)throw Error(name);}
async function control(op,obj){const r=await fetch(process.env.STEP08_BROWSER_CONTROL+op,{method:'POST',headers:{'Authorization':'Bearer '+process.env.STEP08_BROWSER_CONTROL_TOKEN,'Content-Type':'application/json'},body:JSON.stringify(obj)});if(!r.ok)throw Error('HTTP audit rejected '+op);}
async function observe(id,method,url,fn,fields){await control('/before',{id,method,path:url,form_fields:fields});const r=await fn();const u=new URL(r.url()),chain=[];for(let q=r.request().redirectedFrom();q;q=q.redirectedFrom()){const z=await q.response(),v=new URL(q.url());chain.unshift({path:v.pathname+v.search,status:z.status(),location:z.headers()['location']||null});}await control('/after',{id,response_path:u.pathname+u.search,redirect_chain:chain,status:r.status(),content_type:r.headers()['content-type']||'',location:r.headers()['location']||null,body_base64:(await r.body()).toString('base64')});return r;}
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true,args:['--no-proxy-server']});
 try{
  for(const viewport of [{width:1366,height:768},{width:1920,height:1080}]){
   for(const c of cases){
    const context=await browser.newContext({viewport,locale:'zh-CN'});
    if(cookies[c.account])await context.addCookies([{name:'CSUCAMPUSCRAFT_USER_SESSION',value:cookies[c.account],domain:'127.0.0.1',path:'/',httpOnly:true,secure:false,sameSite:'Lax'}]);
    const page=await context.newPage();const id=c.name+'-'+viewport.width;
    let r=await observe(id+'-get','GET',c.path,()=>page.goto('http://127.0.0.1:8080'+c.path,{waitUntil:'domcontentloaded'}));
    if(c.action){
      check(id+'-initial-U06',await page.locator('[data-checkout-form]').count()===1);
      if(c.action==='replaced'){
        const old=await page.locator('input[name=confirmationToken]').inputValue();
        await observe(id+'-replace','GET','/checkout',()=>page.goto('http://127.0.0.1:8080/checkout',{waitUntil:'domcontentloaded'}));
        await page.locator('input[name=confirmationToken]').evaluate((n,v)=>n.value=v,old);
      }
      const fields={receiverName:'测试收货人',receiverPhone:'1',receiverAddress:'仅用于验证的模拟地址'};
      if(c.action==='fields')fields.receiverName='';
      if(c.action==='script'){fields.receiverName='<script>alert(1)</script>';fields.receiverPhone='';fields.receiverAddress='<script>alert(2)</script>';}
      for(const [k,v] of Object.entries(fields))await page.locator('[name='+k+']').fill(v);
      await page.locator('[data-checkout-form]').evaluate(f=>f.noValidate=true);
      if(c.action==='csrf')await page.locator('[data-checkout-form] input[name=_csrf]').evaluate(n=>n.remove());
      const promise=()=>Promise.all([page.waitForResponse(x=>new URL(x.url()).pathname==='/orders'&&x.request().method()==='POST'),page.locator('[data-checkout-form] button[type=submit]').click()]).then(x=>x[0]);
      r=await observe(id+'-post','POST','/orders',promise,['confirmationToken','receiverName','receiverPhone','receiverAddress',...(c.action==='csrf'?[]:['_csrf'])]);
      await page.waitForLoadState('domcontentloaded');
      if(c.action==='script'){
        check(id+'-script-name-literal',(await page.locator('#receiverName').inputValue())===fields.receiverName);
        check(id+'-script-address-literal',(await page.locator('#receiverAddress').inputValue())===fields.receiverAddress);
        check(id+'-no-script-injection',await page.locator('script:not([src])').count()===0);
      }
    }
    check(id+'-status',r.status()===c.status);
    await page.evaluate(async()=>{if(document.fonts)await document.fonts.ready;await Promise.all(Array.from(document.images).map(i=>i.decode().catch(()=>{})));});
    const dom=await page.evaluate(()=>{
      const root=document.querySelector('[data-page-id]'),b=document.querySelector('#cart-quantity'),ids=[...document.querySelectorAll('[id]')].map(n=>n.id);
      return {pageId:root?.dataset.pageId,errorStatus:document.querySelector('[data-error-status]')?.dataset.errorStatus,errorCode:document.querySelector('[data-error-code]')?.dataset.errorCode,badge:b?.dataset.cartQuantity,badgeText:b?.textContent.trim(),overflow:document.documentElement.scrollWidth>innerWidth+1,uniqueIds:ids.length===new Set(ids).size,labelProblems:[...document.querySelectorAll('input:not([type=hidden]),textarea,select')].filter(n=>!n.id||!document.querySelector('label[for="'+n.id+'"]')).length,postForms:[...document.forms].filter(f=>f.method.toLowerCase()==='post').map(f=>({action:f.getAttribute('action'),csrfCount:f.querySelectorAll('input[name=_csrf]').length})),checkoutItemCount:root?.dataset.checkoutItemCount,checkoutQuantity:root?.dataset.checkoutQuantity,checkoutTotal:root?.dataset.checkoutTotal,checkoutRows:[...document.querySelectorAll('tr[data-checkout-item-id]')].map(n=>({id:n.dataset.checkoutItemId,productId:n.dataset.productId,quantity:n.dataset.quantity,itemVersion:n.dataset.itemVersion,unitPrice:n.dataset.unitPrice,subtotal:n.dataset.lineSubtotal})),cartCheckoutLink:!!document.querySelector('a[data-checkout-link]'),imagesLoaded:[...document.images].every(i=>i.complete&&i.naturalWidth>0),tokenInVisibleText:document.querySelector('input[name=confirmationToken]')?document.body.innerText.includes(document.querySelector('input[name=confirmationToken]').value):false,sessionInLinks:[...document.querySelectorAll('[href],[action]')].some(n=>/;CSUCAMPUSCRAFT_/.test(n.getAttribute('href')||n.getAttribute('action')||''))};
    });
    check(id+'-page',c.kind==='error'?dom.errorStatus===String(c.status):dom.pageId===c.kind);
    check(id+'-no-overflow',!dom.overflow);check(id+'-unique-ids',dom.uniqueIds);check(id+'-labels',dom.labelProblems===0);
    check(id+'-csrf-every-form',dom.postForms.every(f=>f.csrfCount===1));check(id+'-images',dom.imagesLoaded);
    check(id+'-badge',dom.badge===String(c.badge)&&dom.badgeText===String(c.badge));check(id+'-no-session-urls',!dom.sessionInLinks);check(id+'-token-not-visible',!dom.tokenInVisibleText);
    if(c.total){check(id+'-exact-total',dom.checkoutTotal===c.total);check(id+'-line-count',dom.checkoutRows.length===2);check(id+'-quantities',dom.checkoutRows.reduce((s,x)=>s+Number(x.quantity),0)===3);}
    if(c.code)check(id+'-code',dom.errorCode===c.code);
    if(c.cartLink)check(id+'-cart-checkout-link',dom.cartCheckoutLink);
    const filename=id+'.png';check(id+'-new-screenshot',!fs.existsSync(path.join(out,filename)));
    await page.screenshot({path:path.join(out,filename),fullPage:true,mask:[page.locator('[name=receiverName],[name=receiverPhone],[name=receiverAddress]')],maskColor:'#6f786f'});
    const b=fs.readFileSync(path.join(out,filename));shots.push({path:filename,viewport,pngWidth:b.readUInt32BE(16),pngHeight:b.readUInt32BE(20),sha256:crypto.createHash('sha256').update(b).digest('hex'),status:r.status(),account:c.account,observation:dom,shippingFieldsMasked:true});await context.close();
   }
  }
  complete=true;
 }catch(e){error='Browser assertion: '+String(e.message).replace(/;CSUCAMPUSCRAFT_[^=]*=[A-Za-z0-9.-]+/g,';SESSION=[REDACTED]');throw e;}
 finally{await browser.close();fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({overall:complete?'PASS':'FAIL',completed:complete,error,checks,screenshots:shots},null,2));}
 process.stdout.write(JSON.stringify({overall:'PASS',screenshots:shots.length,checks:checks.length,secretsRecorded:false}));
})().catch(()=>{process.stderr.write(error||'Browser tool failed');process.exit(1);});
