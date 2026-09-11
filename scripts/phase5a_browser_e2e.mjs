/**
 * Phase 5A mandatory browser E2E against local frontend :3000 (BFF → API :8000).
 */
import { createRequire } from "module";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(path.join(__dirname, "../apps/web/package.json"));
const { chromium } = require("playwright");

const BASE = process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:3000";
const ART = "/opt/cursor/artifacts";
const PASSWORD = "Phase5ATrust9!";

const LEAK_RE =
  /\borg_[a-zA-Z0-9]+\b|req_[a-zA-Z0-9]+|chatcmpl-|console\.groq\.com|platform\.openai\.com|\/billing|\b\d+\s*[KkMm]?\s*TPM\b|\bTPD\b|Traceback \(most recent call last\)|llama-3\.|gpt-oss-|Error code:\s*429|<tool_call>|\"tool_calls\"\s*:|Fill evidence now|Output JSON inside|Strict rules:/i;

const SCENARIOS = [
  {
    id: "saas",
    name: "SaaS Compliance Platform",
    industry: "technology",
    investment: 900000,
    archetype: "saas_digital",
    description:
      "B2B SaaS platform for AI compliance monitoring in Saudi enterprises. Subscription ARR, CAC, LTV, monthly churn. Cloud software product sold to companies.",
  },
  {
    id: "cyber",
    name: "Cybersecurity Services KSA",
    industry: "technology",
    investment: 750000,
    archetype: "services",
    description:
      "Cybersecurity consulting and managed SOC services for Saudi companies. Professional services retainers, billable consultants, project delivery — not a software product and not a data center.",
  },
  {
    id: "residential",
    name: "Residential Compound Riyadh",
    industry: "industrial",
    investment: 25000000,
    archetype: "real_estate",
    description:
      "Develop a residential compound in Riyadh with villas for sale and lease. Land acquisition, construction CAPEX, unit sales, absorption rate. Real estate development project.",
  },
  {
    id: "datacenter",
    name: "Data Center 20MW",
    industry: "technology",
    investment: 180000000,
    archetype: "data_center",
    description:
      "Build and operate a 20 MW colocation data center in Jeddah. Power capacity MW, PUE, rack leasing, IT load, hyperscale and enterprise tenants.",
  },
  {
    id: "uber",
    name: "Uber-like Ride Hailing",
    industry: "technology",
    investment: 1200000,
    archetype: "services",
    description:
      "Build an Uber-like ride-hailing marketplace in Riyadh with drivers, trips, take-rate commission, and driver CAC. Mobility marketplace platform connecting riders and drivers.",
  },
];

function leakHits(text) {
  if (!text) return [];
  const hits = [];
  const re = new RegExp(LEAK_RE.source, "gi");
  let m;
  while ((m = re.exec(text)) !== null) hits.push(m[0]);
  return [...new Set(hits)].slice(0, 20);
}

async function shot(page, name) {
  const file = path.join(ART, name);
  await page.screenshot({ path: file, fullPage: true });
  return file;
}

async function ensureEnglish(page) {
  const lang = page.getByLabel("Switch language");
  if (await lang.isVisible().catch(() => false)) {
    const label = await lang.innerText();
    if (/English/i.test(label)) {
      await lang.click();
      await page.waitForTimeout(500);
    }
  }
}

async function waitIdle(page, timeout = 300000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    const analyzing = await page.getByText(/Analyzing\.\.\.|جارٍ التحليل/i).count();
    if (analyzing === 0) {
      await page.waitForTimeout(350);
      return;
    }
    await page.waitForTimeout(700);
  }
  throw new Error("Timed out waiting for AI idle");
}

async function phaseText(page) {
  return ((await page.getByTestId("study-phase").textContent().catch(() => "")) || "").trim();
}

async function waitPhase(page, preds, timeout = 300000) {
  const list = Array.isArray(preds) ? preds : [preds];
  const start = Date.now();
  while (Date.now() - start < timeout) {
    const label = await phaseText(page);
    for (const p of list) {
      if (typeof p === "string") {
        if (label.toLowerCase().includes(p.toLowerCase())) return label;
      } else if (p.test(label)) {
        return label;
      }
    }
    await page.waitForTimeout(1000);
  }
  throw new Error(`Timeout waiting for phase ${list}; got "${await phaseText(page)}"`);
}

async function sendChat(page, text) {
  const input = page.locator("form input[type=text]").last();
  await input.fill(text);
  await page.locator("form button[type=submit]").last().click();
}

async function clickSafe(locator) {
  await locator.scrollIntoViewIfNeeded().catch(() => {});
  try {
    await locator.click({ timeout: 12000 });
  } catch {
    await locator.click({ force: true, timeout: 12000 });
  }
}

async function assertNoLeaks(page, result, stage) {
  const body = await page.locator("body").innerText();
  const hits = leakHits(body);
  result.leakChecks.push({ stage, hits });
  if (hits.length) result.errors.push(`LEAK@${stage}: ${hits.join(", ")}`);
}

async function registerAndCreateProject(page, scenario) {
  const email = `phase5a_${scenario.id}_${Date.now()}@example.com`;
  await page.goto(`${BASE}/register`, { waitUntil: "domcontentloaded" });
  await ensureEnglish(page);
  await page.getByTestId("register-name").fill(`Phase5A ${scenario.name}`);
  await page.getByTestId("register-email").fill(email);
  await page.getByTestId("register-password").fill(PASSWORD);
  await clickSafe(page.getByTestId("register-submit"));
  await page.getByTestId("projects-workspace").waitFor({ timeout: 60000 });
  await ensureEnglish(page);

  await clickSafe(page.getByTestId("add-project-btn"));
  await page.getByTestId("project-name-input").fill(scenario.name);
  await page.getByTestId("project-industry-select").selectOption(scenario.industry);
  await page.getByTestId("project-investment-input").fill(String(scenario.investment));
  await clickSafe(page.getByTestId("save-project-btn"));
  await page.getByTestId("project-workspace").waitFor({ timeout: 60000 });
  return email;
}

async function openAiWorkspace(page) {
  await clickSafe(page.getByTestId("open-ai-study-workspace"));
  await page.getByTestId("v2-study-workspace").waitFor({ timeout: 60000 });
  await ensureEnglish(page);
}

async function maybeApproveEvidence(page, result) {
  const btn = page.getByRole("button", { name: /Approve Evidence|الموافقة على الأدلة/i });
  if (await btn.isVisible().catch(() => false)) {
    await clickSafe(btn);
    await waitIdle(page, 360000);
    result.phases.push("evidence_approved");
  }
}

async function runScenario(browser, scenario, { doPersistence = false } = {}) {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1200 },
    locale: "en-US",
  });
  const page = await context.newPage();
  page.setDefaultTimeout(90000);

  const result = {
    id: scenario.id,
    ok: false,
    email: null,
    expectedArchetype: scenario.archetype,
    observedArchetype: null,
    phases: [],
    screenshots: [],
    leakChecks: [],
    errors: [],
    finalPhase: null,
    studyUrl: null,
    persistence: null,
  };

  try {
    result.email = await registerAndCreateProject(page, scenario);
    await openAiWorkspace(page);

    await sendChat(page, scenario.description);
    await waitIdle(page, 360000);
    await waitPhase(page, [/Archetype Classification/i], 360000);
    result.phases.push("ARCHETYPE_CLASSIFICATION");
    result.screenshots.push(await shot(page, `phase5a-${scenario.id}-classification.png`));
    await assertNoLeaks(page, result, "classification");

    const profile = (await page.getByTestId("study-profile-panel").textContent().catch(() => "")) || "";
    const suggestion = (await page.getByTestId("archetype-suggestion").textContent().catch(() => "")) || "";
    const found = `${profile}\n${suggestion}`.match(
      /\b(saas_digital|services|real_estate|data_center|industrial|retail|other)\b/,
    );
    result.observedArchetype = found ? found[1] : null;

    if (["uber", "cyber"].includes(scenario.id) && result.observedArchetype === "data_center") {
      result.errors.push("WRONG_CLASSIFICATION: services/mobility suggested as data_center");
    }
    if (result.observedArchetype && result.observedArchetype !== scenario.archetype) {
      result.errors.push(
        `CLASSIFICATION_MISMATCH suggested=${result.observedArchetype} expected=${scenario.archetype}`,
      );
    }

    await clickSafe(page.getByTestId(`archetype-option-${scenario.archetype}`));
    await clickSafe(page.getByTestId("confirm-archetype-btn"));
    await waitIdle(page, 360000);
    result.phases.push("archetype_confirmed");

    const confirmProfile = page.getByTestId("confirm-profile-btn");
    if (await confirmProfile.isVisible({ timeout: 25000 }).catch(() => false)) {
      await clickSafe(confirmProfile);
      await waitIdle(page, 420000);
      result.phases.push("profile_confirmed");
    }

    if (await page.getByTestId("discovery-questions-panel").isVisible().catch(() => false)) {
      const blocks = page.locator('[data-testid^="discovery-question-"]');
      const n = await blocks.count();
      for (let i = 0; i < n; i++) {
        const block = blocks.nth(i);
        const select = block.locator("select");
        const input = block.locator("input, textarea");
        if ((await select.count()) > 0) {
          const opts = await select.locator("option").count();
          if (opts > 1) await select.selectOption({ index: 1 });
        } else if ((await input.count()) > 0) {
          const type = await input.first().getAttribute("type");
          await input.first().fill(type === "number" ? "100" : "100000");
        }
      }
      await clickSafe(page.getByTestId("discovery-questions-submit"));
      await waitIdle(page, 360000);
      result.phases.push("discovery_submitted");
      if (await confirmProfile.isVisible().catch(() => false)) {
        await clickSafe(confirmProfile);
        await waitIdle(page, 420000);
        result.phases.push("profile_confirmed");
      }
    }

    await maybeApproveEvidence(page, result);

    await waitPhase(page, [/Assumptions Review/i], 420000).catch((e) =>
      result.errors.push(String(e.message || e)),
    );
    result.screenshots.push(await shot(page, `phase5a-${scenario.id}-assumptions.png`));
    await assertNoLeaks(page, result, "assumptions");

    const approveAll = page.getByTestId("approve-all-eligible-assumptions-btn");
    if (await approveAll.isVisible().catch(() => false)) {
      if (await approveAll.isEnabled()) {
        await clickSafe(approveAll);
      } else {
        const rows = page.locator('[data-testid^="assumption-approve-"]');
        const rc = await rows.count();
        for (let i = 0; i < rc; i++) {
          const btn = rows.nth(i);
          if (await btn.isEnabled().catch(() => false)) await clickSafe(btn);
          await page.waitForTimeout(250);
        }
        if (await approveAll.isEnabled().catch(() => false)) await clickSafe(approveAll);
      }
      await waitIdle(page, 420000);
      result.phases.push("assumptions_approved");
    }

    for (const msg of [
      "Please complete financial analysis for this project.",
      "Assess the key risks.",
      "Provide the final investment decision and report.",
    ]) {
      const ph = await phaseText(page);
      if (/Report Ready/i.test(ph)) break;
      await sendChat(page, msg);
      await waitIdle(page, 420000);
      await assertNoLeaks(page, result, `chat:${msg.slice(0, 24)}`);
      await maybeApproveEvidence(page, result);
    }

    await waitPhase(page, [/Report Ready/i, /Decision Ready/i, /Funding Ready/i], 240000).catch((e) =>
      result.errors.push(String(e.message || e)),
    );
    result.finalPhase = await phaseText(page);
    result.screenshots.push(await shot(page, `phase5a-${scenario.id}-report.png`));
    await assertNoLeaks(page, result, "report");
    result.studyUrl = page.url();

    if (!/Report Ready|Decision Ready|Funding Ready/i.test(result.finalPhase || "")) {
      result.errors.push(`DID_NOT_REACH_REPORT phase=${result.finalPhase}`);
    }

    if (doPersistence) {
      await page.reload({ waitUntil: "domcontentloaded" });
      await page.getByTestId("v2-study-workspace").waitFor({ timeout: 60000 });
      const afterRefresh = await phaseText(page);
      result.screenshots.push(await shot(page, "phase5a-persistence-refresh.png"));
      await assertNoLeaks(page, result, "refresh");

      await page.evaluate(() => {
        try {
          localStorage.removeItem("sb_token");
        } catch {}
      });
      await page.goto(`${BASE}/api/session/logout`, { waitUntil: "domcontentloaded" }).catch(() => {});
      await page.goto(`${BASE}/login`, { waitUntil: "domcontentloaded" });
      await ensureEnglish(page);
      await page.getByTestId("login-email").fill(result.email);
      await page.getByTestId("login-password").fill(PASSWORD);
      await clickSafe(page.getByTestId("login-submit"));
      await page.waitForTimeout(2500);
      await page.goto(result.studyUrl, { waitUntil: "domcontentloaded" });
      await page.getByTestId("v2-study-workspace").waitFor({ timeout: 90000 });
      const afterLogin = await phaseText(page);
      result.screenshots.push(await shot(page, "phase5a-persistence-relogin.png"));
      await assertNoLeaks(page, result, "relogin");
      result.persistence = { refreshPhase: afterRefresh, reloginPhase: afterLogin };
      if (!afterRefresh || !afterLogin) result.errors.push("PERSISTENCE_FAILED");
    }

    const hardLeak = result.leakChecks.some((c) => c.hits.length > 0);
    const wrongDc = result.errors.some((e) => e.includes("WRONG_CLASSIFICATION"));
    const noReport = result.errors.some((e) => e.includes("DID_NOT_REACH_REPORT"));
    const persistFail = result.errors.some((e) => e.includes("PERSISTENCE_FAILED"));
    result.ok = !hardLeak && !wrongDc && !noReport && !persistFail;
  } catch (err) {
    result.errors.push(String(err && err.stack ? err.stack : err));
    try {
      result.screenshots.push(await shot(page, `phase5a-${scenario.id}-error.png`));
    } catch {}
    result.ok = false;
  } finally {
    await context.close();
  }
  return result;
}

async function main() {
  fs.mkdirSync(ART, { recursive: true });
  const only = (process.env.PHASE5A_ONLY || "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  const scenarios = only.length ? SCENARIOS.filter((s) => only.includes(s.id)) : SCENARIOS;

  const browser = await chromium.launch({ headless: true });
  const results = [];

  for (const scenario of scenarios) {
    console.log(`\n=== START ${scenario.id} ===`);
    const r = await runScenario(browser, scenario, { doPersistence: scenario.id === "saas" });
    results.push(r);
    console.log(
      JSON.stringify(
        {
          id: r.id,
          ok: r.ok,
          phase: r.finalPhase,
          arch: r.observedArchetype,
          errors: r.errors,
          phases: r.phases,
        },
        null,
        2,
      ),
    );
    fs.writeFileSync(path.join(ART, "phase5a_browser_e2e_partial.json"), JSON.stringify(results, null, 2));
  }

  await browser.close();
  const summary = {
    generatedAt: new Date().toISOString(),
    allOk: results.every((r) => r.ok),
    results,
  };
  fs.writeFileSync(path.join(ART, "phase5a_browser_e2e_results.json"), JSON.stringify(summary, null, 2));
  console.log("\n=== SUMMARY ===");
  console.log(
    JSON.stringify({ allOk: summary.allOk, rows: results.map((r) => [r.id, r.ok, r.finalPhase]) }, null, 2),
  );
  process.exit(summary.allOk ? 0 : 1);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
