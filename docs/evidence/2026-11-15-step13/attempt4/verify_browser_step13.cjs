'use strict';
// New STEP13-only reader: never imports or executes a historical evidence generator.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const deps = 'C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies';
const { chromium } = require(path.join(deps, 'node/node_modules/playwright'));
const sha = b => crypto.createHash('sha256').update(b).digest('hex');
const maskSelector = '[data-shipping-value], [data-customer-contact], input[type="password"], input[name="receiverName"], input[name="receiverPhone"], input[name="receiverAddress"], textarea[name="receiverAddress"]';
const checks = [];
function check(name, value) { checks.push({name, passed: !!value}); if (!value) throw new Error('CHECK_FAILED:' + name); }
function positive(value, name) { check(name, Number.isSafeInteger(value) && value > 0); return value; }
const startedAt = new Date().toISOString();
const screenshots = [];
const observations = [];
const imageFallbackObservations = [];
let out;
let browser;
let fixture;
let blockedWriteRequests=0;
async function main() {
  check('explicit-current-fixture-path', !!process.env.STEP13_UI_FIXTURE);
  fixture = JSON.parse(fs.readFileSync(process.env.STEP13_UI_FIXTURE, 'utf8').replace(/^\uFEFF/, ''));
  check('full-source-sha', /^[a-f0-9]{40}$/.test(fixture.sourceSha));
  positive(fixture.graduationCategoryId, 'graduation-id');
  positive(fixture.giftProductId, 'gift-id');
  positive(fixture.customerId, 'customer-id');
  positive(fixture.adminAlbumProductId, 'admin-album-product-id');
  positive(fixture.missingProductId, 'missing-image-product-id');
  positive(fixture.noGalleryProductId, 'no-gallery-product-id');
  check('safe-order-number', /^[A-Za-z0-9_-]{1,40}$/.test(fixture.orderNo));
  for (const key of ['userBase','adminBase']) {
    const u = new URL(fixture[key]);
    check('loopback-' + key, u.protocol === 'http:' && ['127.0.0.1','localhost'].includes(u.hostname) && !u.username && !u.password && u.pathname === '/');
  }
  check('ephemeral-user-cookie-present', !!process.env.STEP13_UI_USER_COOKIE);
  check('ephemeral-admin-cookie-present', !!process.env.STEP13_UI_ADMIN_COOKIE);
  check('new-output-directory-required', !!process.env.STEP13_UI_OUT);
  out = path.resolve(process.env.STEP13_UI_OUT);
  check('output-not-existing', !fs.existsSync(out));
  fs.mkdirSync(out, {recursive:true});
  const executable = process.env.STEP13_UI_BROWSER || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
  check('browser-executable-present', fs.existsSync(executable));
  browser = await chromium.launch({executablePath: executable, headless:true});
  const cases = [
    {name:'u01-home', side:'user', url:'/', pageId:'U01'},
    {name:'u02-graduation', side:'user', url:`/products?categoryId=${fixture.graduationCategoryId}&type=ALL`, pageId:'U02'},
    {name:'a08-customer-list', side:'admin', url:'/customers', pageId:'A08'},
    {name:'u05-persistent-cart', side:'user', url:'/cart', pageId:'U05'},
    {name:'u06-85-confirmation', side:'user', url:'/checkout', pageId:'U06'},
    {name:'u08-shipped-snapshot', side:'user', url:`/orders/${fixture.orderNo}`, pageId:'U08', shipped:true},
    {name:'a02-real-dashboard', side:'admin', url:'/', pageId:'A02'},
    {name:'a07-same-shipped-order', side:'admin', url:`/orders/${fixture.orderNo}`, pageId:'A07', shipped:true},
    {name:'a09-disable-warning', side:'admin', url:`/customers/${fixture.customerId}`, pageId:'A09', expand:true},
    {name:'a10-product-album', side:'admin', url:`/products/${fixture.adminAlbumProductId}/images`, pageId:'A10'},
  ];
  for (const viewport of [{width:1366,height:768},{width:1920,height:1080}]) {
    const contexts = {};
    try {
      for (const side of ['user','admin']) {
        const base = fixture[side+'Base'];
        const context = await browser.newContext({viewport,locale:'zh-CN',timezoneId:'Asia/Shanghai'});
        const value = process.env['STEP13_UI_'+side.toUpperCase()+'_COOKIE'];
        await context.addCookies([{name:side==='user'?'CSUCAMPUSCRAFT_USER_SESSION':'CSUCAMPUSCRAFT_ADMIN_SESSION',value,url:base,httpOnly:true,sameSite:'Lax'}]);
        // A screenshot fixture is read-only: reject any accidental non-GET request.
        await context.route('**/*', async route => {
          if (route.request().method() !== 'GET') { blockedWriteRequests++; return route.abort(); }
          await route.continue();
        });
        contexts[side] = context;
      }
      for (const spec of cases) {
        const page = await contexts[spec.side].newPage();
        const t0 = new Date().toISOString();
        try {
          const response = await page.goto(new URL(spec.url,fixture[spec.side+'Base']).href,{waitUntil:'networkidle'});
          check(spec.name+'-response-'+viewport.width, !!response);
          const status = response.status();
          check(spec.name+'-status-'+viewport.width,status === (spec.status || 200));
          if (spec.expand) {
            const disclosure = page.locator('details[data-disable-confirmation]');
            check(spec.name+'-enabled-warning-present-'+viewport.width, await disclosure.count() === 1);
            await disclosure.locator('summary').click();
            check(spec.name+'-warning-open-'+viewport.width, await disclosure.getAttribute('open') !== null);
          }
          const dom = await page.evaluate(() => {
            const root = document.querySelector('[data-page-id]');
            const attr = name => root ? root.getAttribute(name) : null;
            const all = s => Array.from(document.querySelectorAll(s));
            return {
              pageId:attr('data-page-id'), errorStatus:document.querySelector('[data-error-status]')?.getAttribute('data-error-status')||null,
              orderStatus:attr('data-order-status'), orderTotal:attr('data-order-total'), cartQuantity:attr('data-cart-quantity'),
              confirmationTotal:attr('data-checkout-total') || document.querySelector('[data-checkout-total]')?.textContent.trim() || null,
              dashboardCounts:all('[data-dashboard-card]').map(e=>({key:e.getAttribute('data-dashboard-card'),count:e.querySelector('[data-dashboard-count]')?.textContent.trim()||null})),
              contactMaskTargets:all('[data-customer-contact]').length,shippingMaskTargets:all('[data-shipping-value]').length,
              maskedInputTargets:all('input[type="password"], input[name="receiverName"], input[name="receiverPhone"], input[name="receiverAddress"], textarea[name="receiverAddress"]').length,
              overflow:document.documentElement.scrollWidth > window.innerWidth,
              formCsrfCounts:all('form[method="post"], form[method="POST"]').map(e=>e.querySelectorAll('input[name="_csrf"]').length),
              imageFailures:all('img').filter(e=>!e.complete||e.naturalWidth===0).length,
              sessionUrlRewrite:all('a[href]').some(e=>/;CSUCAMPUSCRAFT_[A-Z_]*SESSION=/i.test(e.getAttribute('href'))),
              // No text, input value, arbitrary dataset, hidden token, or contact value leaves the page.
            };
          });
          if (spec.pageId) check(spec.name+'-page-id-'+viewport.width,dom.pageId===spec.pageId);
          if (spec.shipped) check(spec.name+'-shipped-'+viewport.width,dom.orderStatus==='SHIPPED');
          if (spec.name==='u05-persistent-cart') check('fresh-cart-quantity-three-'+viewport.width,dom.cartQuantity==='3');
          if (spec.name==='u06-85-confirmation') check('server-confirmation-eighty-five-'+viewport.width,Number(dom.confirmationTotal)===85);
          check(spec.name+'-no-page-overflow-'+viewport.width,!dom.overflow);
          check(spec.name+'-post-forms-have-one-CSRF-'+viewport.width,dom.formCsrfCounts.every(n=>n===1));
          check(spec.name+'-images-loaded-'+viewport.width,dom.imageFailures===0);
          check(spec.name+'-cookie-only-links-'+viewport.width,!dom.sessionUrlRewrite);
          check(spec.name+'-only-GET-browser-requests-'+viewport.width,blockedWriteRequests===0);
          if (spec.name==='a02-real-dashboard') check('five-live-dashboard-counts-'+viewport.width,dom.dashboardCounts.length===5 && dom.dashboardCounts.every(c=>/^\d+$/.test(c.count)));
          const file = spec.name+'-'+viewport.width+'.png';
          await page.screenshot({path:path.join(out,file),fullPage:true,animations:'disabled',mask:[page.locator(maskSelector)],maskColor:'#9CA3AF'});
          const raw=fs.readFileSync(path.join(out,file));
          const record={name:spec.name,path:file,viewport,pngWidth:raw.readUInt32BE(16),pngHeight:raw.readUInt32BE(20),sha256:sha(raw),status,side:spec.side,observation:dom,contactAndShippingFieldsMasked:true};
          screenshots.push(record);
          observations.push({sequence:observations.length+1,method:'GET',side:spec.side,path:spec.url,status,startedAt:t0,completedAt:new Date().toISOString(),databaseObservation:'after-only/browser layer; batch before/after belongs to external orchestrator',artifact:file});
          fs.writeFileSync(path.join(out,'http.jsonl'),observations.map(x=>JSON.stringify(x)).join('\n')+'\n');
        } finally { await page.close(); }
      }
      // TST-04 actual browser load/error fallback; no extra screenshot or business POST.
      for (const sample of [{name:'missing-image-actual-fallback',id:fixture.missingProductId,missing:true},{name:'no-gallery-cover',id:fixture.noGalleryProductId,missing:false}]) {
        const page=await contexts.user.newPage();
        const t0=new Date().toISOString();
        try {
          const requestPath='/products/'+sample.id;
          const response=await page.goto(new URL(requestPath,fixture.userBase).href,{waitUntil:'networkidle'});
          check(sample.name+'-200-'+viewport.width,response && response.status()===200);
          await page.locator('[data-cover-image] img').scrollIntoViewIfNeeded();
          await page.waitForFunction(()=>{const i=document.querySelector('[data-cover-image] img');return i && i.complete && i.naturalWidth>0;});
          const dom=await page.evaluate(()=>{
            const root=document.querySelector('[data-page-id]');const image=document.querySelector('[data-cover-image] img');
            return {pageId:root?.getAttribute('data-page-id'),galleryCount:root?.getAttribute('data-gallery-count'),galleryEmpty:!!document.querySelector('[data-gallery-empty]'),coverLoaded:!!image&&image.complete&&image.naturalWidth>0,coverPath:image?new URL(image.currentSrc,location.href).pathname:null,fallbackUsed:image?.getAttribute('data-image-fallback-used')==='true'};
          });
          check(sample.name+'-detail-'+viewport.width,dom.pageId==='U03');
          check(sample.name+'-loaded-'+viewport.width,dom.coverLoaded);
          if(sample.missing)check(sample.name+'-placeholder-really-loaded-'+viewport.width,dom.fallbackUsed && dom.coverPath==='/images/catalog-placeholder.svg');
          else check(sample.name+'-no-album-cover-visible-'+viewport.width,dom.galleryEmpty && dom.galleryCount==='0');
          imageFallbackObservations.push({name:sample.name,viewport,productId:sample.id,...dom});
          observations.push({sequence:observations.length+1,method:'GET',side:'user',path:requestPath,status:response.status(),startedAt:t0,completedAt:new Date().toISOString(),databaseObservation:'after-only/browser DOM layer; no paired per-GET database assertion',artifact:null});
          fs.writeFileSync(path.join(out,'http.jsonl'),observations.map(x=>JSON.stringify(x)).join('\n')+'\n');
        } finally {await page.close();}
      }
    } finally { for(const c of Object.values(contexts)) await c.close(); }
  }
  check('twenty-fresh-screenshots',screenshots.length===20);
}
(async()=>{
  let failureClass=null;
  try {await main();} catch(e) {failureClass=e.name==='Error'?String(e.message).split(':')[0]:e.name;}
  finally {if(browser)await browser.close();}
  const result={overall:failureClass?'FAIL':'PASS',startedAt,completedAt:new Date().toISOString(),tested_source_sha:fixture?.sourceSha||null,checks,screenshots,imageFallbackObservations,failureClass,
    methods:'New STEP13-only Playwright reader, authenticated via ephemeral in-memory cookies; only real GET navigation; no business writes or old generators.',
    privacy:'Cookie/CSRF/confirmation values and raw bodies are never archived; shipping/contact/input fields are opaque-masked in PNG.',
    databaseBoundary:'Individual GETs are after-only at this layer. External orchestrator owns actual batch before/after snapshots; screenshot alone does not prove zero writes.'};
  if(out)fs.writeFileSync(path.join(out,'result.json'),JSON.stringify(result,null,2)+'\n');
  process.stdout.write(JSON.stringify({overall:result.overall,screenshotCount:screenshots.length,checks:checks.length,failureClass})+'\n');
  process.exitCode=failureClass?1:0;
})();
