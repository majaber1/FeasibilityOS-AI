import { defineConfig, devices } from "@playwright/test";

const frontendUrl = process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:3000";
const backendUrl = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";

export default defineConfig({
  testDir: "./e2e",
  testMatch: "**/v2-semantic-recovery.spec.ts",
  timeout: 240000,
  expect: { timeout: 20000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: frontendUrl,
    screenshot: "only-on-failure",
    trace: "on-first-retry",
    video: "off",
  },
  // Reuse already-running local/preview servers.
  webServer: undefined,
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
