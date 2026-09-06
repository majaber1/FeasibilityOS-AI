import { defineConfig, devices } from "@playwright/test";
import path from "path";

const repoRoot = path.resolve(__dirname, "../..");

export default defineConfig({
  testDir: "./e2e",
  timeout: 240000,
  expect: { timeout: 20000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "on-first-retry",
    video: "off",
  },
  webServer: [
    {
      command: "python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000",
      url: "http://127.0.0.1:8000/health",
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
      command: "npx next start --port 3000 --hostname 127.0.0.1",
      url: "http://127.0.0.1:3000",
      timeout: 120000,
      reuseExistingServer: false,
      env: {
        ...process.env,
        BACKEND_API_URL: "http://127.0.0.1:8000",
      },
    },
  ],
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
