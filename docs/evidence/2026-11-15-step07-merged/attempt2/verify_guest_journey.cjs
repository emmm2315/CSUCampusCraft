const fs=require('fs'),path=require('path'),crypto=require('crypto'),http=require('http');
const {chromium}=require('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/playwright');
const out=process.env.STEP07_JOURNEY_OUT,productId=process.env.STEP07_JOURNEY_PRODUCT,origin='http://127.0.0.1:8080';
const controlPort=Number(process.env.STEP07_JOURNEY_CONTROL),controlToken=process.env.STEP07_JOURNEY_CONTROL_TOKEN;
fs.mkdirSync(out,{recursive:true});
const checks=[],shots=[],posts=[];let completed=false,failure=null;
function check(name,ok){checks.push({name,passed:!!ok});if(!ok)throw Error(name);}
function safeError(e){let s=String(e.message||e);const p=process.env.STEP07_JOURNEY_PASSWORD;if(p)s=s.split(p).join('[REDACTED]');return s.replace(/[0-9a-f]{64}/g,'[REDACTED-TOKEN]');}
async function control(endpoint,obj){
 const bytes=Buffer.from(JSON.stringify(obj));
 const result=await new Promise((resolve,reject)=>{
  const r=http.request({hostname:'127.0.0.1',port:controlPort,path:endpoint,method:'POST',headers:{'Content-Type':'application/json','Content-Length':bytes.length,'X-Audit-Token':controlToken}},resp=>{const chunks=[];resp.on('data',b=>chunks.push(b));resp.on('end',()=>resolve({status:resp.statusCode,body:Buffer.concat(chunks).toString('utf8')}));});
  r.on('error',reject);r.setTimeout(20000,()=>r.destroy(Error('Local audit observer timeout')));r.end(bytes);
 });
 if(result.status!==200)throw Error('Local observer rejected '+endpoint);
 return JSON.parse(result.body);
}
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true,args:['--no-proxy-server']});
 try{
  const viewport={width:1366,height:768};const context=await browser.newContext({viewport,locale:'zh-CN'});const page=await context.newPage();
  const requestIds=new WeakMap();let nextPost=0;let responses=Promise.resolve();
  await page.route(origin+'/**',async route=>{
   const req=route.request();
   if(req.method()==='POST'){
    const id=String(++nextPost);requestIds.set(req,id);
    const values=new URLSearchParams(req.postData()||'');
    await control('/before',{id,path:new URL(req.url()).pathname,form_fields:[...new Set(values.keys())].sort()});
   }
   await route.continue();
  });
  page.on('response',response=>{
   const req=response.request();if(!req.isNavigationRequest()||!req.url().startsWith(origin))return;
   responses=responses.then(async()=>{
    let body=Buffer.alloc(0),available=true;
    try{body=await response.body();}catch(e){available=false;}
    const headers=response.headers(),u=new URL(req.url());
    const data={id:requestIds.get(req)||null,method:req.method(),path:u.pathname+u.search,status:response.status(),content_type:headers['content-type']||null,location:headers.location||null,set_cookie_present:!!headers['set-cookie'],cookie_names:[...new Set((await context.cookies(origin)).map(x=>x.name))],body_base64:body.toString('base64'),body_available:available};
    if(!available)check('redirect-body-empty-'+req.method()+'-'+u.pathname,[302,303].includes(response.status())&&(!headers['content-length']||headers['content-length']==='0'));
    await control('/response',data);
    if(req.method()==='POST')posts.push({id:data.id,path:data.path,status:data.status,location:data.location});
   });
  });
  async function settle(){await page.waitForLoadState('domcontentloaded');await responses;}
  async function shot(name){
   await page.evaluate(async()=>{if(document.fonts)await document.fonts.ready;for(let y=0;y<document.documentElement.scrollHeight;y+=innerHeight){scrollTo(0,y);await new Promise(r=>setTimeout(r,40));}scrollTo(0,0);await Promise.all(Array.from(document.images).map(i=>i.decode().catch(()=>{})));});
   await page.waitForFunction(()=>Array.from(document.images).every(i=>i.complete&&i.naturalWidth>0));
   const observation=await page.evaluate(()=>({pageId:document.querySelector('[data-page-id]')?.dataset.pageId||'U04',badge:document.getElementById('cart-quantity')?.textContent.trim(),overflow:document.documentElement.scrollWidth>innerWidth+1,guestLink:document.querySelector('[data-login-to-add]')?.getAttribute('href')||null,addForms:document.querySelectorAll('form[data-add-cart]').length,postForms:Array.from(document.forms).filter(f=>f.method==='post').length,authenticated:document.body.dataset.authenticated,labels:Array.from(document.querySelectorAll('input:not([type=hidden])')).every(i=>i.id&&document.querySelector('label[for="'+i.id+'"]'))}));
   check(name+'-no-overflow',!observation.overflow);check(name+'-labels',observation.labels);
   const filename=name+'-1366.png';await page.screenshot({path:path.join(out,filename),fullPage:true});
   const b=fs.readFileSync(path.join(out,filename));shots.push({path:filename,viewport,pngWidth:b.readUInt32BE(16),pngHeight:b.readUInt32BE(20),sha256:crypto.createHash('sha256').update(b).digest('hex'),observation});
  }
  const first=await page.goto(origin+'/products/'+productId,{waitUntil:'domcontentloaded'});await settle();check('guest-detail-200',first.status()===200);
  check('guest-detail-no-post-form',await page.locator('form[method=post]').count()===0);
  check('guest-detail-no-add-form',await page.locator('form[data-add-cart]').count()===0);
  const link=page.locator('a[data-login-to-add]');check('guest-login-link-one',await link.count()===1);
  const href=new URL(await link.getAttribute('href'),origin);check('guest-login-target',href.origin===origin&&href.pathname==='/login'&&href.searchParams.get('returnUrl')==='/products/'+productId);
  check('guest-badge-zero',(await page.locator('#cart-quantity').textContent()).trim()==='0');
  await shot('journey-guest-login-link');
  await Promise.all([page.waitForURL(u=>u.pathname==='/login'),link.click()]);await settle();
  check('login-return-hidden',await page.locator('input[name=returnUrl]').inputValue()==='/products/'+productId);
  await shot('journey-login-page');
  await page.locator('input[name=username]').fill('alice');await page.locator('input[name=password]').fill(process.env.STEP07_JOURNEY_PASSWORD);
  await Promise.all([page.waitForURL(u=>u.pathname==='/products/'+productId),page.locator('form[action="/login"] button[type=submit]').click()]);await settle();
  check('login-post-303',posts.length===1&&posts[0].path==='/login'&&posts[0].status===303);
  check('returned-detail-authenticated',await page.locator('body').getAttribute('data-authenticated')==='true');
  check('returned-detail-real-add-form',await page.locator('form[data-add-cart]').count()===1);
  check('returned-detail-no-auto-replay',(await page.locator('#cart-quantity').textContent()).trim()==='0');
  await shot('journey-returned-detail-manual-add');
  const form=page.locator('form[data-add-cart]');check('manual-form-product',await form.locator('input[name=productId]').inputValue()===productId);check('manual-form-one-csrf',await form.locator('input[name=_csrf]').count()===1);
  await form.locator('input[name=quantity]').fill('1');
  await Promise.all([page.waitForURL(u=>u.pathname==='/cart'),form.locator('button[type=submit]').click()]);await settle();
  check('manual-add-post-303',posts.length===2&&posts[1].path==='/cart/items'&&posts[1].status===303&&posts[1].location==='/cart');
  check('cart-after-manual-one-row',await page.locator('tr[data-cart-item-id]').count()===1);
  check('cart-after-manual-badge-one',(await page.locator('#cart-quantity').textContent()).trim()==='1');
  check('cart-after-manual-product',await page.locator('tr[data-cart-item-id]').getAttribute('data-product-id')===productId);
  await shot('journey-cart-after-manual-add');
  await responses;await control('/complete',{posts:posts.length,screenshots:shots.length});
  await context.close();completed=true;
 }catch(e){failure=safeError(e);throw e;}
 finally{
  await browser.close();fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({overall:completed&&checks.every(x=>x.passed)?'PASS':'FAIL',completed,error:failure,checks,screenshots:shots,posts,secretsRecorded:false},null,2));
 }
 process.stdout.write(JSON.stringify({overall:'PASS',completed,checks:checks.length,screenshots:shots.length,posts:posts.length,secretsRecorded:false}));
})().catch(e=>{process.stderr.write(failure||'Guest journey failed');process.exit(1);});
