import { expect, test } from "@playwright/test";

const PASSWORD = "IndependentTool9!";

test("independent tools can start without a forced workflow chain", async ({ page }) => {
  const email = `tools_${Date.now()}@example.com`;

  await page.goto("/register");
  await page.getByLabel("Switch language").click();
  await page.getByTestId("register-name").fill("Independent Tools Founder");
  await page.getByTestId("register-email").fill(email);
  await page.getByTestId("register-password").fill(PASSWORD);
  await page.getByTestId("register-submit").click();
  await expect(page.getByTestId("projects-workspace")).toBeVisible({ timeout: 30000 });

  await page.goto("/tools/feasibility/new");
  await page.getByTestId("feasibility-title").fill("Standalone Cafe");
  await page.getByTestId("feasibility-investment").fill("450000");
  await page.getByTestId("start-feasibility").click();
  await expect(page).toHaveURL(/\/projects\/\d+\/studies\/\d+/, { timeout: 30000 });

  await page.goto("/tools/financial");
  await page.getByTestId("financial-investment").fill("450000");
  await page.getByTestId("financial-cashflows").fill("90000, 110000, 140000, 170000, 200000");
  await page.getByTestId("run-financial-analysis").click();
  await expect(page.getByText(/Feasible|Not Feasible|Borderline|مجد|غير مجد|حدّي/)).toBeVisible({ timeout: 20000 });

  await page.goto("/tools/proposal");
  await page.getByTestId("new-proposal-cta").click();
  await expect(page.getByText(/Choose proposal type|اختر نوع العرض/)).toBeVisible();

  await page.goto("/tools/funding");
  await expect(page.getByText(/Funding Matcher|مطابقة التمويل/)).toBeVisible();

  await page.goto("/tools/qualification");
  await expect(page.getByText(/Business Qualification|تأهيل الأعمال/)).toBeVisible();

  await page.goto("/tools/auctions");
  await expect(page.getByText(/not part of the current product|ليست جزءاً من المنتج الحالي/)).toBeVisible();
});
