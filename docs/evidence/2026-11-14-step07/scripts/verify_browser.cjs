const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { chromium } = require('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/playwright');

const base = process.env.STEP07_BROWSER_BASE || 'http://127.0.0.1:18080';
const out = process.env.STEP07_BROWSER_OUT || 'D:/severlt/tmp/step07-validation/browser';
const username = process.env.STEP07_BROWSER_USER || 'alice';
const repo = process.env.STEP07_REPO || 'D:/severlt/实验1/CSUCampusCraft';
const teachingPassword = fs.readFileSync(path.join(repo, 'README.md'), 'utf8').match(/教学密码为\s*`([^`]+)`/);
const password = process.env.STEP07_BROWSER_PASSWORD || teachingPassword?.[1];
if (!password) throw new Error('Teaching password is unavailable; provide the private browser environment value');
const viewports = [{ width: 1366, height: 768 }, { width: 1920, height: 1080 }, { width: 390, height: 844 }];
const checks = [], screenshots = [], requests = [], errors = [];
const documentStatuses = new WeakMap();
let completed = false;
fs.mkdirSync(out, { recursive: true });

function check(name, passed, observation) {
    checks.push({ name, passed: Boolean(passed), ...(observation === undefined ? {} : { observation }) });
}
function publicError(error) {
    return String(error.message || error).split(password).join('[TEACHING_PASSWORD_REDACTED]')
        .replace(/;CSUCAMPUSCRAFT_(?:USER|ADMIN)_SESSION=[A-Za-z0-9.-]+/g, ';SESSION=[REDACTED]');
}
function must(name, passed) {
    check(name, passed);
    if (!passed) throw new Error(name);
}
async function settleImages(page) {
    await page.evaluate(async () => {
        if (document.fonts) await document.fonts.ready;
        for (let y = 0; y < document.documentElement.scrollHeight; y += innerHeight) {
            scrollTo(0, y);
            await new Promise(resolve => setTimeout(resolve, 30));
        }
        scrollTo(0, 0);
    });
    await page.waitForFunction(() => Array.from(document.images).every(image => image.complete && image.naturalWidth > 0), null, { timeout: 10000 });
}
async function snapshot(page, name, expectedPage, expectedStatus = 200) {
    for (const viewport of viewports) {
        await page.setViewportSize(viewport);
        await settleImages(page);
        const observation = await page.evaluate(() => {
            const ids = Array.from(document.querySelectorAll('[id]')).map(node => node.id);
            const root = document.querySelector('[data-page-id]');
            return {
                pageId: root?.dataset.pageId,
                documentOverflow: document.documentElement.scrollWidth > innerWidth + 1,
                documentWidth: document.documentElement.scrollWidth,
                viewportWidth: innerWidth,
                duplicateIds: ids.filter((id, index) => ids.indexOf(id) !== index),
                labelProblems: Array.from(document.querySelectorAll('input:not([type=hidden]),select,textarea')).filter(node => !node.id || !document.querySelector('label[for="' + CSS.escape(node.id) + '"]')).length,
                brokenDescriptions: Array.from(document.querySelectorAll('[aria-describedby]')).flatMap(node => node.getAttribute('aria-describedby').split(/\s+/).filter(id => !document.getElementById(id))),
                brokenErrorAnchors: Array.from(document.querySelectorAll('.error-summary a[href^="#"]')).filter(node => !document.getElementById(node.getAttribute('href').slice(1))).length,
                postFormsWithOneCsrf: Array.from(document.forms).filter(form => form.method.toLowerCase() === 'post').every(form => form.querySelectorAll('input[name=_csrf]').length === 1),
                cartFormVersionsMatchRows: Array.from(document.querySelectorAll('[data-cart-quantity-form],[data-cart-remove-form]')).every(form => form.querySelectorAll('input[name=version]').length === 1 && form.querySelector('input[name=version]').value === form.closest('[data-cart-item-id]').dataset.version),
                sessionInLinks: Array.from(document.querySelectorAll('[href],[action]')).some(node => /;CSUCAMPUSCRAFT_(?:USER|ADMIN)_SESSION=/.test((node.getAttribute('href') || '') + (node.getAttribute('action') || ''))),
                cartQuantity: document.querySelector('#cart-quantity')?.dataset.cartQuantity ?? null,
                checkoutAllowed: root?.dataset.checkoutAllowed ?? null,
                rows: Array.from(document.querySelectorAll('[data-cart-item-id]')).map(node => ({ itemId: node.dataset.cartItemId, productId: node.dataset.productId, quantity: node.dataset.quantity, version: node.dataset.version, valid: node.dataset.valid })),
                invalidReasons: Array.from(document.querySelectorAll('.cart-invalid-reason')).map(node => node.textContent.trim()),
                imagesLoaded: Array.from(document.images).every(image => image.complete && image.naturalWidth > 0),
                fallbackCount: document.querySelectorAll('img[data-image-fallback-used=true]').length,
                tableScrollsLocally: Array.from(document.querySelectorAll('.table-container')).every(node => node.scrollWidth <= node.clientWidth || getComputedStyle(node).overflowX === 'auto'),
                purchaseDisabled: document.querySelector('[data-add-to-cart] button')?.matches(':disabled') ?? null,
                checkoutDisabled: document.querySelector('.cart-summary-actions button')?.matches(':disabled') ?? null,
                checkoutHrefPresent: Boolean(document.querySelector('a[href="/checkout"]')),
                globalError: document.querySelector('.global-alerts .alert-danger p')?.textContent.trim() ?? null
            };
        });
        const label = name + '-' + viewport.width;
        const status = documentStatuses.get(page) ?? null;
        check(label + '-document-status-' + expectedStatus, status === expectedStatus, status);
        check(label + '-page-id', observation.pageId === expectedPage);
        check(label + '-no-document-overflow', !observation.documentOverflow, observation.documentWidth);
        check(label + '-unique-ids', observation.duplicateIds.length === 0, observation.duplicateIds);
        check(label + '-labels', observation.labelProblems === 0);
        check(label + '-descriptions', observation.brokenDescriptions.length === 0, observation.brokenDescriptions);
        check(label + '-error-anchors', observation.brokenErrorAnchors === 0);
        check(label + '-csrf', observation.postFormsWithOneCsrf);
        check(label + '-cookie-only', !observation.sessionInLinks);
        check(label + '-images', observation.imagesLoaded);
        if (process.env.STEP07_EXPECT_MISSING_COVER === '1' && ['detail-guest', 'detail-authenticated'].includes(name)) {
            check(label + '-missing-cover-fell-back', observation.fallbackCount > 0);
        }
        check(label + '-table-scroll-contained', observation.tableScrollsLocally);
        if (expectedPage === 'U05') {
            check(label + '-no-unimplemented-checkout-link', !observation.checkoutHrefPresent);
            check(label + '-checkout-phase-labeled', observation.checkoutDisabled === true);
            check(label + '-badge-includes-every-row', Number(observation.cartQuantity) === observation.rows.reduce((sum, row) => sum + Number(row.quantity), 0));
            check(label + '-row-form-versions', observation.cartFormVersionsMatchRows);
            check(label + '-whole-cart-readiness', (observation.checkoutAllowed === 'true') === (observation.rows.length > 0 && observation.rows.every(row => row.valid === 'true')));
        }
        const filename = label + '.png';
        await page.screenshot({ path: path.join(out, filename), fullPage: true });
        const buffer = fs.readFileSync(path.join(out, filename));
        screenshots.push({ path: filename, viewport, status, sha256: crypto.createHash('sha256').update(buffer).digest('hex'), pngWidth: buffer.readUInt32BE(16), pngHeight: buffer.readUInt32BE(20), observation });
    }
}
async function go(page, pathname, expectedStatus = 200) {
    const response = await page.goto(base + pathname, { waitUntil: 'domcontentloaded' });
    must('GET-' + pathname + '-status-' + expectedStatus, response.status() === expectedStatus);
    return response;
}
async function submit(page, selector, expectedStatus) {
    const form = page.locator(selector);
    const pathname = await form.getAttribute('action');
    const [response] = await Promise.all([
        page.waitForResponse(value => value.request().method() === 'POST' && new URL(value.url()).pathname === pathname),
        form.locator('button[type=submit]').click()
    ]);
    await page.waitForLoadState('domcontentloaded');
    must('POST-' + pathname + '-status-' + expectedStatus, response.status() === expectedStatus);
}
async function firstRow(page, predicate = {}) {
    const rows = await page.locator('[data-cart-item-id]').evaluateAll(nodes => nodes.map(node => ({ id: node.dataset.cartItemId, productId: node.dataset.productId, quantity: Number(node.dataset.quantity), version: node.dataset.version, valid: node.dataset.valid === 'true' })));
    return rows.find(row => Object.entries(predicate).every(([key, value]) => row[key] === value));
}

(async () => {
    const browser = await chromium.launch({ executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless: true, args: ['--no-proxy-server'] });
    const context = await browser.newContext({ viewport: viewports[0], locale: 'zh-CN' });
    const page = await context.newPage();
    page.on('response', response => {
        const url = new URL(response.url());
        if (url.origin === base) requests.push({ method: response.request().method(), path: url.pathname, status: response.status(), resourceType: response.request().resourceType() });
        if (response.request().resourceType() === 'document' && response.request().frame() === page.mainFrame()) documentStatuses.set(page, response.status());
    });
    page.on('pageerror', error => errors.push(publicError(error)));
    try {
        await go(page, '/products/1');
        must('guest-badge-zero', await page.locator('#cart-quantity').getAttribute('data-cart-quantity') === '0');
        const loginLink = new URL(await page.locator('.catalog-guest-purchase a').getAttribute('href'), base);
        must('guest-explicit-login-link', loginLink.pathname === '/login' && loginLink.searchParams.get('returnUrl') === '/products/1');
        await snapshot(page, 'detail-guest', 'U03');
        await page.locator('.catalog-guest-purchase a').click();
        await page.locator('#username').fill(username);
        await page.locator('#password').fill(password);
        await submit(page, 'form[action="/login"]', 303);
        must('login-returned-to-detail', new URL(page.url()).pathname === '/products/1');
        must('login-return-did-not-replay-add', await page.locator('[data-add-to-cart]').count() === 1);
        await snapshot(page, 'detail-authenticated', 'U03');

        await go(page, '/cart');
        const initialRows = await page.locator('[data-cart-item-id]').count();
        const hasInvalid = await page.locator('[data-cart-item-id][data-valid=false]').count() > 0;
        check('initial-invalid-fixture-present', hasInvalid);
        if (hasInvalid) await snapshot(page, 'cart-invalid', 'U05');
        let row = await firstRow(page, { valid: true });
        must('initial-valid-row-present', Boolean(row));
        const quantitySelector = 'tr[data-cart-item-id="' + row.id + '"] form[data-cart-quantity-form]';
        await page.locator(quantitySelector).evaluate(form => { form.noValidate = true; form.querySelector('input[name=quantity]').value = '0'; });
        await submit(page, quantitySelector, 400);
        const fieldId = '#cart-' + row.id + '-quantity';
        must('cart-400-value-retained', await page.locator(fieldId).inputValue() === '0');
        must('cart-400-field-associated', await page.locator(fieldId).getAttribute('aria-invalid') === 'true');
        await snapshot(page, 'cart-quantity-400', 'U05', 400);

        await go(page, '/cart');
        row = await firstRow(page, { valid: true });
        const competing = await context.newPage();
        await go(competing, '/cart');
        const competingForm = competing.locator('tr[data-cart-item-id="' + row.id + '"] form[data-cart-quantity-form]');
        await competingForm.locator('input[name=quantity]').fill(row.quantity === 1 ? '2' : '1');
        await submit(competing, 'tr[data-cart-item-id="' + row.id + '"] form[data-cart-quantity-form]', 303);
        await competing.close();
        await submit(page, 'tr[data-cart-item-id="' + row.id + '"] form[data-cart-quantity-form]', 409);
        must('cart-409-quantity-disabled', await page.locator('tr[data-cart-item-id="' + row.id + '"] form[data-cart-quantity-form] button').isDisabled());
        must('cart-409-remove-disabled', await page.locator('tr[data-cart-item-id="' + row.id + '"] form[data-cart-remove-form] button').isDisabled());
        await snapshot(page, 'cart-stale-version-409', 'U05', 409);

        await go(page, '/products/1');
        await page.locator('[data-add-to-cart]').evaluate(form => { form.noValidate = true; form.querySelector('input[name=quantity]').value = '0'; });
        await submit(page, '[data-add-to-cart]', 400);
        must('detail-400-value-retained', await page.locator('#purchase-quantity').inputValue() === '0');
        must('detail-400-field-associated', await page.locator('#purchase-quantity').getAttribute('aria-invalid') === 'true');
        await snapshot(page, 'detail-quantity-400', 'U03', 400);

        await go(page, '/products/1');
        await page.locator('[data-add-to-cart]').evaluate(form => { form.noValidate = true; form.querySelector('input[name=quantity]').value = '99'; });
        await submit(page, '[data-add-to-cart]', 409);
        must('detail-409-submit-disabled', await page.locator('[data-add-to-cart] button').isDisabled());
        await snapshot(page, 'detail-stock-409', 'U03', 409);
        await go(page, '/products/11');
        must('sold-out-submit-disabled', await page.locator('[data-add-to-cart] button').isDisabled());
        await snapshot(page, 'detail-sold-out', 'U03');

        await go(page, '/cart');
        let removed = 0;
        while (await page.locator('[data-cart-item-id]').count() > 0) {
            await submit(page, 'tr[data-cart-item-id]:first-child form[data-cart-remove-form]', 303);
            removed++;
            if (removed > 30) throw new Error('Unexpected number of cart rows');
        }
        check('all-initial-cart-rows-removed', removed === initialRows);
        must('empty-cart-badge-zero', await page.locator('#cart-quantity').getAttribute('data-cart-quantity') === '0');
        must('empty-cart-state-visible', await page.locator('[data-cart-empty]').isVisible());
        await snapshot(page, 'cart-empty', 'U05');

        await go(page, '/products/1');
        await page.locator('#purchase-quantity').fill('1');
        await submit(page, '[data-add-to-cart]', 303);
        must('add-success-return-cart', new URL(page.url()).pathname === '/cart');
        must('healthy-cart-allows-future-checkout', await page.locator('[data-page-id=U05]').getAttribute('data-checkout-allowed') === 'true');
        must('add-success-badge-one', await page.locator('#cart-quantity').getAttribute('data-cart-quantity') === '1');
        const healthy = await firstRow(page, { productId: '1' });
        await submit(page, 'tr[data-cart-item-id="' + healthy.id + '"] form[data-cart-quantity-form]', 303);
        must('same-quantity-keeps-version', (await firstRow(page, { productId: '1' })).version === healthy.version);
        await page.locator('tr[data-cart-item-id="' + healthy.id + '"] input[name=quantity]').fill('2');
        await submit(page, 'tr[data-cart-item-id="' + healthy.id + '"] form[data-cart-quantity-form]', 303);
        must('quantity-success-badge-two', await page.locator('#cart-quantity').getAttribute('data-cart-quantity') === '2');
        await snapshot(page, 'cart-healthy', 'U05');
        for (const pathname of ['/', '/products', '/products/1']) {
            await go(page, pathname);
            must('shared-badge-' + pathname, await page.locator('#cart-quantity').getAttribute('data-cart-quantity') === '2');
        }
        await go(page, '/cart');
        await submit(page, 'form[data-cart-remove-form]', 303);
        must('browser-final-cart-empty', await page.locator('[data-cart-empty]').isVisible());
        check('no-client-page-errors', errors.length === 0, errors);
        completed = true;
    } catch (error) {
        errors.push(publicError(error));
        await page.screenshot({ path: path.join(out, 'failure.png'), fullPage: true }).catch(() => {});
    } finally {
        await browser.close();
        const result = { overall: completed && checks.every(value => value.passed) ? 'PASS' : 'FAIL', completed, secretsRecorded: false, checks, screenshots, requests, errors };
        fs.writeFileSync(path.join(out, 'result.json'), JSON.stringify(result, null, 2));
        process.stdout.write(JSON.stringify({ overall: result.overall, completed, checks: checks.length, failedChecks: checks.filter(value => !value.passed).map(value => value.name), screenshots: screenshots.length, errors }));
        if (result.overall !== 'PASS') process.exitCode = 1;
    }
})().catch(error => { process.stderr.write(publicError(error)); process.exitCode = 1; });
