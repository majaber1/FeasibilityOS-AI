import { chromium } from 'playwright-core';
import fs from 'fs';

const WEB = process.env.WEB;
const tok = process.env.VERCEL_OIDC_TOKEN;
if (!WEB || !tok) {
  console.error('Missing WEB or VERCEL_OIDC_TOKEN');
  process.exit(2);
}

const SCENARIOS = {
  A: { name: 'WhatsApp AI Platform', desc: 'WhatsApp AI Platform SaaS subscription for Saudi SMBs with churn and CAC focus' },
  B: { name: 'Riyadh Residential Complex', desc: 'Existing residential complex in Riyadh construction already started needs financing land units BOQ' },
  C: { name: 'Enterprise Data Center', desc: 'Enterprise data center Tier III MW rack capacity cooling power for existing company' },
  D: { name: 'Government Awarded Project', desc: 'Government award letter ترسية جهة حكومية contract BOQ financing need advance payment' },
};
const SID = process.env.SCENARIO || 'A';
const scenario = SCENARIOS[SID];
if (!scenario) throw new Error('Unknown scenario ' + SID);
const email = `ui_${SID.toLowerCase()}_${Date.now()}@example.com`;
const password = 'PreviewGold9!';
const art = '/opt/cursor/artifacts';

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  extraHTTPHeaders: {
    'x-vercel-trusted-oidc-idp-token': tok,
  },
  locale: 'en-US',
});
const page = await context.newPage();
page.setDefaultTimeout(45000);

async function shot(name) {
  const p = `${art}/preview-ui-${SID}-${name}.png`;
  await page.screenshot({ path: p, fullPage: true });
  console.log('SHOT', p);
}

const steps = {};
try {
  await page.goto(WEB + '/', { waitUntil: 'domcontentloaded' });
  await shot('01-home');
  steps.home = 'PASS';

  // Register via UI if available, else API then login UI
  await page.goto(WEB + '/register', { waitUntil: 'domcontentloaded' });
  await shot('02-register');
  const emailInput = page.locator('input[type="email"], input[name="email"]').first();
  const passInput = page.locator('input[type="password"], input[name="password"]').first();
  const nameInput = page.locator('input[name="full_name"], input[name="name"], input[name="fullName"]').first();
  if (await nameInput.count()) await nameInput.fill(`Preview UI ${SID}`);
  await emailInput.fill(email);
  await passInput.fill(password);
  await page.locator('button[type="submit"]').first().click();
  await page.waitForTimeout(2500);
  // If still on register, use API register + login page
  if (page.url().includes('register')) {
    const reg = await context.request.post(WEB + '/api/backend/auth/register', {
      headers: { 'x-vercel-trusted-oidc-idp-token': tok, 'content-type': 'application/json' },
      data: { email, password, full_name: `Preview UI ${SID}` },
    });
    console.log('api register', reg.status());
    await page.goto(WEB + '/login', { waitUntil: 'domcontentloaded' });
    await page.locator('input[type="email"], input[name="email"]').first().fill(email);
    await page.locator('input[type="password"], input[name="password"]').first().fill(password);
    await page.locator('button[type="submit"]').first().click();
  }
  await page.waitForTimeout(3000);
  await shot('03-after-auth');
  if (page.url().includes('login') || page.url().includes('register')) {
    throw new Error('Auth failed, still on ' + page.url());
  }
  steps.auth = 'PASS';

  // Create project
  await page.goto(WEB + '/projects', { waitUntil: 'domcontentloaded' });
  await shot('04-projects');
  const addBtn = page.getByTestId('add-project-btn').or(page.getByRole('button', { name: /add|إضافة/i })).first();
  await addBtn.click();
  await page.getByTestId('project-name-input').or(page.locator('input[name="name"]')).first().fill(scenario.name);
  const save = page.getByTestId('save-project-btn').or(page.getByRole('button', { name: /save|حفظ/i })).first();
  await save.click();
  await page.waitForTimeout(2500);
  await shot('05-project-created');
  steps.project = 'PASS';

  // Open AI study workspace
  const aiLink = page.getByTestId(/ai-study|start-study/).first().or(page.locator('a[href*="workspace"]').first());
  if (await aiLink.count()) {
    await aiLink.click();
  } else {
    // navigate from current project URL
    const m = page.url().match(/\/projects\/(\d+)/);
    const pid = m ? m[1] : null;
    if (!pid) throw new Error('No project id');
    await page.goto(`${WEB}/projects/${pid}/studies/new/workspace`, { waitUntil: 'domcontentloaded' });
  }
  await page.waitForTimeout(2000);
  await shot('06-workspace');

  const workspace = page.getByTestId('v2-study-workspace').or(page.getByTestId('study-workspace')).first();
  await workspace.waitFor({ state: 'visible', timeout: 30000 });
  steps.workspace = 'PASS';

  // Describe project
  const input = page.locator('textarea, input[type="text"]').last();
  await input.fill(scenario.desc);
  await page.getByRole('button', { name: /send|إرسال/i }).or(page.locator('button[type="submit"]')).first().click();
  await page.waitForTimeout(8000);
  await shot('07-after-discovery');

  const discovery = page.getByTestId('discovery-questions-panel').or(page.locator('[data-testid*="discovery"]')).first();
  await discovery.waitFor({ state: 'visible', timeout: 60000 });
  const bodyText = await page.locator('body').innerText();
  if (bodyText.includes('###') || bodyText.includes('```json')) {
    throw new Error('Markdown/JSON dump visible in discovery UX');
  }
  steps.discovery = 'PASS';
  await shot('08-discovery-questions');

  // Answer ALL structured question cards deterministically
  const cards = discovery.locator('[data-testid^="discovery-question-"], [data-question-type]');
  const cardCount = await cards.count();
  console.log('question cards', cardCount);
  for (let i = 0; i < cardCount; i++) {
    const card = cards.nth(i);
    const qType = await card.getAttribute('data-question-type');
    const buttons = card.locator('button');
    const bCount = await buttons.count();
    if (qType === 'MULTI_SELECT' && bCount > 0) {
      await buttons.first().click();
    } else if ((qType === 'SINGLE_SELECT' || qType === 'YES_NO' || !qType) && bCount > 0) {
      // Prefer a middle/stable option when present
      await buttons.nth(Math.min(1, bCount - 1)).click();
    }
    const inputs = card.locator('input:not([type="hidden"]), textarea');
    const iCount = await inputs.count();
    for (let j = 0; j < iCount; j++) {
      const inp = inputs.nth(j);
      const type = (await inp.getAttribute('type')) || 'text';
      if (type === 'number' || type === 'text' || type === 'date') {
        await inp.fill(type === 'date' ? '2026-01-01' : (qType === 'PERCENTAGE' ? '5' : '250'));
      }
    }
  }
  // Fallback: ensure every visible option group has a selection by clicking unlabeled buttons still white
  const allChoice = discovery.locator('button').filter({ hasNotText: /save|حفظ|submit|إرسال/i });
  // Click revenue-model-ish labels if present
  for (const label of ['اشتراك', 'Subscription', 'فكرة', 'Idea', 'نعم', 'Yes', 'لا', 'No']) {
    const btn = discovery.getByRole('button', { name: label }).first();
    if (await btn.count()) {
      try { await btn.click({ timeout: 1000 }); } catch {}
    }
  }
  await page.getByTestId('discovery-questions-submit').or(discovery.getByRole('button', { name: /save|حفظ/i })).first().click();
  // Wait until required remaining drops or gate appears
  for (let attempt = 0; attempt < 8; attempt++) {
    await page.waitForTimeout(1500);
    const body = await page.locator('body').innerText();
    if (await page.getByTestId('information-gate-buttons').count()) break;
    if (await page.getByTestId('gate-research').count()) break;
    if (!/\d+\s*(required|سؤال مطلوب)/i.test(body) || /0\s*(required|سؤال مطلوب)/i.test(body)) break;
    // re-click save after filling any empty inputs
    const empties = discovery.locator('input').evaluateAll
      ? null
      : null;
    const emptyInputs = discovery.locator('input');
    const eCount = await emptyInputs.count();
    for (let j = 0; j < eCount; j++) {
      const val = await emptyInputs.nth(j).inputValue();
      if (!val) await emptyInputs.nth(j).fill('250');
    }
    // ensure single-select groups: click first unselected-looking button in each card
    for (let i = 0; i < cardCount; i++) {
      const card = cards.nth(i);
      const selected = card.locator('button.bg-brand-600, button[class*="bg-brand"], button[class*="bg-emerald"]');
      if ((await selected.count()) === 0) {
        const b = card.locator('button').first();
        if (await b.count()) await b.click();
      }
    }
    await page.getByTestId('discovery-questions-submit').or(discovery.getByRole('button', { name: /save|حفظ/i })).first().click();
  }
  await shot('09-answers-saved');
  steps.answers = 'PASS';

  // Information gate
  const gate = page.getByTestId('information-gate-buttons').or(page.getByTestId('gate-research')).first();
  await gate.waitFor({ state: 'visible', timeout: 30000 });
  await shot('10-information-gate');
  steps.gate = 'PASS';
  await page.getByTestId('gate-provisional').click();
  await page.waitForTimeout(8000);
  await shot('11-after-provisional');

  const assumptions = page.getByTestId('assumptions-panel').or(page.getByText(/assumptions|الافتراضات/i)).first();
  await assumptions.waitFor({ state: 'visible', timeout: 60000 });
  steps.assumptions = 'PASS';

  const approve = page.getByTestId('approve-assumptions').or(page.getByRole('button', { name: /approve assumptions|الموافقة على الافتراضات/i })).first();
  await approve.click();
  await page.waitForTimeout(10000);
  await shot('12-after-assumptions-approve');
  steps.approveAssumptions = 'PASS';

  // Status strip / decision
  const strip = page.getByTestId('study-status-strip').or(page.getByTestId('study-phase')).first();
  await strip.waitFor({ state: 'visible', timeout: 30000 });
  await shot('13-status-strip');
  steps.status = 'PASS';

  // Locale toggle
  const lang = page.getByLabel(/language|Switch language|اللغة/i).first();
  if (await lang.count()) {
    await lang.click();
    await page.waitForTimeout(1500);
    if (page.url().includes('login')) throw new Error('Locale toggle logged out');
    await shot('14-locale-toggle');
    steps.locale = 'PASS';
  } else {
    steps.locale = 'SKIP';
  }

  // Refresh persistence
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3000);
  await workspace.waitFor({ state: 'visible', timeout: 30000 });
  await shot('15-after-refresh');
  steps.refresh = 'PASS';

  console.log('STEPS', JSON.stringify(steps, null, 2));
  fs.writeFileSync(`${art}/preview-ui-golden-${SID}-steps.json`, JSON.stringify(steps, null, 2));
  const failed = Object.entries(steps).filter(([, v]) => v !== 'PASS' && v !== 'SKIP');
  if (failed.length) process.exit(1);
  console.log(`GOLDEN ${SID} PREVIEW BROWSER: PASS`);
} catch (e) {
  console.error('FAIL', e);
  await shot('99-failure');
  fs.writeFileSync(`${art}/preview-ui-golden-${SID}-steps.json`, JSON.stringify({ error: String(e), steps }, null, 2));
  process.exit(1);
} finally {
  await browser.close();
}
