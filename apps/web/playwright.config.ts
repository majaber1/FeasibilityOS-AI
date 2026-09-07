import { defineConfig, devices } from "@playwright/test";
import path from "path";

const repoRoot = path.resolve(__dirname, "../..");
const frontendPort = Number(process.env.PLAYWRIGHT_FRONTEND_PORT || 3100);
const backendPort = Number(process.env.PLAYWRIGHT_BACKEND_PORT || 8100);
const frontendUrl = `http://127.0.0.1:${frontendPort}`;
const backendUrl = `http://127.0.0.1:${backendPort}`;

export default defineConfig({
  testDir: "./e2e",
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
  webServer: [
    {
      command: `python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port ${backendPort}`,
      url: `${backendUrl}/health`,
      cwd: repoRoot,
      timeout: 120000,
      reuseExistingServer: false,
      env: {
        ...process.env,
        DATABASE_URL: "sqlite:///./playwright_wave65.db",
        JWT_SECRET: "test-secret-at-least-32-characters-long",
        PYTHONPATH: "backend",
      },
    },
    {
      command: `npx next start --port ${frontendPort} --hostname 127.0.0.1`,
      url: frontendUrl,
      timeout: 120000,
      reuseExistingServer: false,
      env: {
        ...process.env,
        BACKEND_API_URL: backendUrl,
      },
    },
  ],
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
