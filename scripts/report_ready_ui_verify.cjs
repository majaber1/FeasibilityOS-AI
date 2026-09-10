/**
 * Browser evidence: REPORT_READY full report panel, decision, refresh/reopen.
 */
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const OUT = "/opt/cursor/artifacts/report-ready-verification";
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

function sectionVisible(body) {
  return {
    evidence: /Evidence|الأدلة/i.test(body),
    assumptions: /Assumptions|الافتراضات/i.test(body),
    calculations: /Calculations|NPV|IRR/i.test(body),
    risks: /Risks|مخاطر/i.test(body),
    decision: /Decision rationale|Verdict|NO_GO|INSUFFICIENT|القرار/i.test(body),
  };
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
    await page.goto(study.url, { waitUntil: "networkidle", timeout: 90000 });
    await page.waitForTimeout(5000);

    await page.screenshot({
      path: path.join(OUT, `${study.name}_01_workspace.png`),
      fullPage: true,
    });

    const body = await page.locator("body").innerText();
    result.texts.body_excerpt = body.slice(0, 3000);

    const reportPanel = page.locator('[data-testid="feasibility-report-panel"]');
    result.gates.report_panel_visible = (await reportPanel.count()) > 0;
    result.gates.phase_report_ready =
      /Report Ready|REPORT_READY|التقرير جاهز/i.test(body) ||
      (await page.locator('[data-testid="study-phase"]').innerText().catch(() => "")).includes("Report");

    result.gates.decision_visible =
      (await page.locator('[data-testid="study-verdict"]').count()) > 0 ||
      /NO_GO|INSUFFICIENT_EVIDENCE|GO_WITH_CONDITIONS|\bGO\b|DEFER/i.test(body);

    const sections = sectionVisible(body);
    result.gates.sections = sections;
    result.gates.sections_complete = Object.values(sections).every(Boolean);

    for (const key of [
      "evidence",
      "assumptions",
      "calculations",
      "risks",
      "decision_rationale",
    ]) {
      const el = page.locator(`[data-testid="report-section-${key}"]`);
      result.gates[`section_${key}`] = (await el.count()) > 0;
    }

    await page.reload({ waitUntil: "networkidle" });
    await page.waitForTimeout(3500);
    const afterRefresh = await page.locator("body").innerText();
    await page.screenshot({
      path: path.join(OUT, `${study.name}_02_after_refresh.png`),
      fullPage: true,
    });
    result.gates.refresh_report_persist =
      (await page.locator('[data-testid="feasibility-report-panel"]').count()) > 0 &&
      /NO_GO|INSUFFICIENT|NPV|Evidence/i.test(afterRefresh);

    await page.goto(`${WEB}/projects`, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1200);
    await page.goto(study.url, { waitUntil: "networkidle", timeout: 90000 });
    await page.waitForTimeout(3500);
    const afterReopen = await page.locator("body").innerText();
    await page.screenshot({
      path: path.join(OUT, `${study.name}_03_after_reopen.png`),
      fullPage: true,
    });
    result.gates.reopen_report_persist =
      (await page.locator('[data-testid="feasibility-report-panel"]').count()) > 0 &&
      /NO_GO|INSUFFICIENT|NPV|Evidence/i.test(afterReopen);

    const flatGates = { ...result.gates };
    delete flatGates.sections;
    result.pass =
      Object.entries(flatGates)
        .filter(([k]) => k !== "sections")
        .every(([, v]) => v === true) && result.gates.sections_complete;
  } catch (e) {
    result.errors.push(String(e).slice(0, 600));
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
  let browser;
  try {
    browser = await chromium.launch({ headless: true });
  } catch (e) {
    console.error("chromium launch failed", e);
    process.exit(1);
  }
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
  fs.writeFileSync(path.join(OUT, "ui_report_verify.json"), JSON.stringify(report, null, 2));
  console.log(
    JSON.stringify(
      results.map((r) => ({ name: r.name, pass: r.pass, gates: r.gates, errors: r.errors })),
      null,
      2
    )
  );
  console.log("UI_OVERALL", report.overall_pass);
  process.exit(report.overall_pass ? 0 : 2);
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
