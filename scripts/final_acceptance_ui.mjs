/**
 * Browser UI evidence for three V2 studies: load, financial, risks, verdict,
 * refresh persistence, reopen persistence.
 */
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const OUT = "/opt/cursor/artifacts/final-acceptance";
const WEB = "https://saudi-business-web.vercel.app";
const creds = JSON.parse(
  fs.readFileSync("/opt/cursor/artifacts/workflow-validation/creds.json", "utf8")
);

fs.mkdirSync(OUT, { recursive: true });

const STUDIES = [
  {
    name: "uber",
    email: creds.uber.email,
    password: creds.uber.password,
    url: `${WEB}/projects/14/studies/${creds.uber.study_id}/workspace`,
  },
  {
    name: "residential",
    email: creds.validator.email,
    password: creds.validator.password,
    url: `${WEB}/projects/20/studies/${creds.validator.residential_study_id}/workspace`,
  },
  {
    name: "datacenter",
    email: creds.validator.email,
    password: creds.validator.password,
    url: `${WEB}/projects/21/studies/${creds.validator.datacenter_study_id}/workspace`,
  },
];

async function login(page, email, password) {
  await page.goto(`${WEB}/login`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(1000);
  const en = page.getByRole("button", { name: /English|EN/i });
  if (await en.count()) {
    try {
      await en.first().click({ timeout: 2000 });
    } catch {}
  }
  await page.locator('input[type="email"], input[name="email"]').first().fill(email);
  await page.locator('input[type="password"], input[name="password"]').first().fill(password);
  await page.locator('button[type="submit"]').first().click();
  await page.waitForTimeout(2500);
}

async function captureStudy(browser, study) {
  const result = {
    name: study.name,
    url: study.url,
    gates: {},
    texts: {},
    errors: [],
  };
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    locale: "en-US",
  });
  const page = await context.newPage();
  page.setDefaultTimeout(45000);

  try {
    await login(page, study.email, study.password);
    await page.screenshot({
      path: path.join(OUT, `${study.name}_01_after_login.png`),
      fullPage: true,
    });

    await page.goto(study.url, { waitUntil: "networkidle", timeout: 90000 });
    await page.waitForTimeout(4000);
    await page.screenshot({
      path: path.join(OUT, `${study.name}_02_workspace_load.png`),
      fullPage: true,
    });
    const body = await page.locator("body").innerText();
    result.gates.workspace_loads =
      !/not found|404|something went wrong/i.test(body) && body.length > 200;
    result.texts.body_excerpt = body.slice(0, 2500);

    result.gates.financial_visible =
      /npv|irr|capex|payback|revenue|تحليل مالي|صافي القيمة/i.test(body) ||
      (await page.locator("text=/NPV|IRR|CAPEX|Financial/i").count()) > 0;
    result.gates.risks_visible =
      /risk|مخاطر|regulatory|competition|absorption|interconnection/i.test(body) ||
      (await page.locator("text=/risk|Risk|مخاطر/i").count()) > 0;
    result.gates.verdict_visible =
      /NO_GO|NO-GO|DEFER|GO_WITH|GO\b|لا تمضي|تأجيل|verdict|القرار/i.test(body) ||
      (await page.locator("text=/NO_GO|DEFER|GO|Verdict|القرار/i").count()) > 0;

    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(1000);
    await page.screenshot({
      path: path.join(OUT, `${study.name}_03_workspace_bottom.png`),
      fullPage: true,
    });

    await page.reload({ waitUntil: "networkidle" });
    await page.waitForTimeout(3000);
    const afterRefresh = await page.locator("body").innerText();
    await page.screenshot({
      path: path.join(OUT, `${study.name}_04_after_refresh.png`),
      fullPage: true,
    });
    result.gates.refresh_persistence =
      /NO_GO|DEFER|GO|NPV|IRR|risk/i.test(afterRefresh) && afterRefresh.length > 200;

    await page.goto(`${WEB}/projects`, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1500);
    await page.goto(study.url, { waitUntil: "networkidle", timeout: 90000 });
    await page.waitForTimeout(3000);
    const afterReopen = await page.locator("body").innerText();
    await page.screenshot({
      path: path.join(OUT, `${study.name}_05_after_reopen.png`),
      fullPage: true,
    });
    result.gates.reopen_persistence =
      /NO_GO|DEFER|GO|NPV|IRR|risk/i.test(afterReopen) && afterReopen.length > 200;

    result.texts.after_refresh_excerpt = afterRefresh.slice(0, 1500);
    result.texts.after_reopen_excerpt = afterReopen.slice(0, 1500);
    result.pass = Object.values(result.gates).every(Boolean);
  } catch (e) {
    result.errors.push(String(e).slice(0, 500));
    result.pass = false;
    try {
      await page.screenshot({
        path: path.join(OUT, `${study.name}_ERROR.png`),
        fullPage: true,
      });
    } catch {}
  } finally {
    await context.close();
  }
  return result;
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const results = [];
  for (const study of STUDIES) {
    console.log("UI", study.name);
    results.push(await captureStudy(browser, study));
  }
  await browser.close();
  const report = {
    generated_at: new Date().toISOString(),
    results,
    overall_pass: results.every((r) => r.pass),
  };
  fs.writeFileSync(path.join(OUT, "ui_acceptance.json"), JSON.stringify(report, null, 2));
  console.log(
    JSON.stringify(
      results.map((r) => ({ name: r.name, pass: r.pass, gates: r.gates, errors: r.errors })),
      null,
      2
    )
  );
  console.log("UI_OVERALL", report.overall_pass);
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
