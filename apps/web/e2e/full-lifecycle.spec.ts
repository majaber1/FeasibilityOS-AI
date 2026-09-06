import { expect, test, type Page } from "@playwright/test";

const PASSWORD = "LifecycleTest9!";

async function addAssumption(page: Page, key: string, labelEn: string, labelAr: string, value: string) {
  await page.getByTestId("add-assumption-btn").click();
  await page.getByTestId("assumption-key-input").fill(key);
  await page.getByTestId("assumption-label-en").fill(labelEn);
  await page.getByTestId("assumption-label-ar").fill(labelAr);
  await page.getByTestId("assumption-value-input").fill(value);
  await page.getByTestId("assumption-origin-select").selectOption("USER");
  await page.getByTestId("save-assumption-btn").click();
  await expect(page.getByTestId(`assumption-card-${key}`)).toBeVisible();
}

test("full founder lifecycle persists after refresh and relogin", async ({ page }, testInfo) => {
  const consoleErrors: string[] = [];
  const pageErrors: string[] = [];
  const unexpectedNetwork: string[] = [];

  page.on("console", (msg) => {
    if (msg.type() !== "error") return;
    const text = msg.text();
    if (text.includes("404 (Not Found)") && /favicon\.ico/i.test(text)) return;
    if (text === "Failed to load resource: the server responded with a status of 404 (Not Found)") return;
    consoleErrors.push(text);
  });
  page.on("pageerror", (err) => pageErrors.push(`${page.url()} :: ${String(err)}`));
  page.on("response", (response) => {
    const status = response.status();
    const url = response.url();
    if (/\/favicon\.ico(\?|$)/i.test(url) && status === 404) return;
    if (status >= 500) unexpectedNetwork.push(`${status} ${url}`);
    if (status === 401 || status === 403) unexpectedNetwork.push(`${status} ${url}`);
    if (status === 404) unexpectedNetwork.push(`${status} ${url}`);
  });

  const email = `wave65_${Date.now()}@example.com`;

  await page.goto("/register");
  await page.getByLabel("Switch language").click();
  await page.getByTestId("register-name").fill("Wave 65 Founder");
  await page.getByTestId("register-email").fill(email);
  await page.getByTestId("register-password").fill(PASSWORD);
  await page.getByTestId("register-submit").click();
  await expect(page.getByTestId("projects-workspace")).toBeVisible({ timeout: 30000 });

  await page.getByTestId("add-project-btn").click();
  await page.getByTestId("project-name-input").fill("REFERENCE_TEST_DATA — Scrap AI Marketplace");
  await page.getByTestId("project-industry-select").selectOption("technology");
  await page.getByTestId("project-investment-input").fill("850000");
  await page.getByTestId("save-project-btn").click();
  await expect(page.getByTestId("project-workspace")).toBeVisible({ timeout: 30000 });
  await expect(page.getByTestId("project-workspace-title")).toContainText("REFERENCE_TEST_DATA — Scrap AI Marketplace");

  await page.getByTestId("edit-project-profile").click();
  await page.getByTestId("project-profile-name").fill("REFERENCE_TEST_DATA — Scrap AI Marketplace");
  await page.getByTestId("project-profile-investment").fill("860000");
  await page.getByTestId("save-project-profile").click();
  await expect(page.getByTestId("edit-project-profile")).toBeVisible();

  await page.getByTestId("start-study-btn").click();
  await expect(page.getByTestId("study-workspace")).toBeVisible({ timeout: 30000 });

  await page.getByTestId("study-section-profile").click();
  await page.getByTestId("profile-activity-input").fill("AI marketplace + recycling brokerage");
  await page.getByTestId("save-business-profile").click();
  await expect(page.getByText(/Saved|تم الحفظ/)).toBeVisible();

  await page.getByTestId("study-section-assumptions").click();
  await addAssumption(page, "capex", "CAPEX", "النفقات الرأسمالية", "860000");
  await addAssumption(page, "revenue_year1", "Year 1 revenue", "إيراد السنة الأولى", "320000");

  await page.getByTestId("study-section-financial").click();
  await expect(page.getByTestId("financial-analysis-workspace")).toBeVisible();
  await page.getByTestId("compute-saved-assumptions").click();
  await expect(page.getByTestId("financial-analysis-result")).toBeVisible({ timeout: 30000 });
  await page.getByTestId("open-assumptions-from-financial").click();
  await expect(page.getByTestId("assumption-card-capex")).toBeVisible();
  await page.getByTestId("study-section-financial").click();
  await expect(page.getByTestId("financial-analysis-result")).toBeVisible();

  await page.getByTestId("study-section-validation").click();
  await expect(page.getByTestId("validation-os-workspace")).toBeVisible({ timeout: 30000 });
  const hypoCards = page.locator('[data-testid^="hypo-card-"]');
  await expect(hypoCards.first()).toBeVisible();
  const hypoIds: string[] = [];
  const count = await hypoCards.count();
  expect(count).toBeGreaterThan(0);
  for (let i = 0; i < count; i += 1) {
    const testId = await hypoCards.nth(i).getAttribute("data-testid");
    if (testId) hypoIds.push(testId.replace("hypo-card-", ""));
  }

  for (const hypoId of hypoIds) {
    await page.getByTestId("subtab-evidence").click();
    await page.getByTestId("add-evidence-btn").click();
    await page.getByTestId("evidence-title-input").fill(`Founder interview ${hypoId}`);
    await page.getByTestId("evidence-interview-role").fill("Prospective buyer");
    await page.getByTestId("evidence-interview-quote").fill("User-recorded note; not a market census.");
    await page.getByTestId("evidence-hypo-select").selectOption(hypoId);
    await page.getByTestId("evidence-direction-select").selectOption("SUPPORTING");
    await page.getByTestId("evidence-strength-select").selectOption("STRONG");
    await page.getByTestId("confirm-record-evidence-btn").click();
    await expect(page.getByTestId("add-evidence-btn")).toBeVisible({ timeout: 20000 });
  }

  await page.getByTestId("subtab-decision").click();
  await page.getByTestId("decision-btn-GO").click();
  await page.getByTestId("decision-reason-input").fill("Critical hypotheses have founder-recorded interviews. Market size remains UNKNOWN.");
  await page.getByTestId("submit-decision-btn").click();
  await expect(page.getByTestId("latest-decision-banner")).toBeVisible({ timeout: 20000 });

  await page.getByTestId("study-section-launch").click();
  await expect(page.getByTestId("launch-os-workspace")).toBeVisible({ timeout: 30000 });
  await page.getByTestId("launch-tasks-tab").click();
  await page.getByTestId("launch-task-title").fill("Open CR and municipal file");
  await page.getByTestId("launch-add-task").click();
  await expect(page.getByText("Open CR and municipal file")).toBeVisible({ timeout: 20000 });

  await page.getByTestId("study-section-growth").click();
  await expect(page.getByTestId("growth-os-workspace")).toBeVisible({ timeout: 30000 });
  await expect(page.getByTestId("growth-health-state")).toContainText("INSUFFICIENT_DATA");

  await page.reload();
  await expect(page.getByTestId("study-workspace")).toBeVisible({ timeout: 30000 });
  await page.getByTestId("study-section-financial").click();
  await expect(page.getByTestId("financial-analysis-result")).toBeVisible();
  await page.getByTestId("study-section-validation").click();
  await expect(page.getByTestId("latest-decision-banner")).toBeVisible();
  await page.getByTestId("study-section-launch").click();
  await page.getByTestId("launch-tasks-tab").click();
  await expect(page.getByText("Open CR and municipal file")).toBeVisible();
  await page.getByTestId("study-section-growth").click();
  await expect(page.getByTestId("growth-health-state")).toContainText("INSUFFICIENT_DATA");

  await page.screenshot({ path: testInfo.outputPath("01-lifecycle-before-relogin.png"), fullPage: true });
  await page.getByRole("button", { name: /Log out|خروج/ }).click();
  await page.goto("/login");
  await page.getByTestId("login-email").fill(email);
  await page.getByTestId("login-password").fill(PASSWORD);
  await page.getByTestId("login-submit").click();
  await expect(page).toHaveURL(/\/dashboard/);
  await page.goto("/projects");
  await expect(page.getByText("REFERENCE_TEST_DATA — Scrap AI Marketplace")).toBeVisible();
  await page.getByRole("link", { name: "REFERENCE_TEST_DATA — Scrap AI Marketplace", exact: true }).click();
  await expect(page.getByTestId("project-workspace-title")).toContainText("REFERENCE_TEST_DATA — Scrap AI Marketplace");
  await page.getByRole("link", { name: /View decision|عرض القرار/ }).click();
  await expect(page.getByTestId("study-workspace")).toBeVisible({ timeout: 30000 });
  await page.getByTestId("study-section-assumptions").click();
  await expect(page.getByTestId("assumption-card-capex")).toBeVisible();
  await page.getByTestId("study-section-validation").click();
  await expect(page.getByTestId("latest-decision-banner")).toBeVisible();
  await page.getByTestId("study-section-launch").click();
  await page.getByTestId("launch-tasks-tab").click();
  await expect(page.getByText("Open CR and municipal file")).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("02-lifecycle-after-relogin.png"), fullPage: true });

  expect(pageErrors, pageErrors.join("\n")).toEqual([]);
  expect(consoleErrors, consoleErrors.join("\n")).toEqual([]);
  expect(unexpectedNetwork, unexpectedNetwork.join("\n")).toEqual([]);
});
