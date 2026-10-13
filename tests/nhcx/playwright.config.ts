import { defineConfig, devices } from "@playwright/test";
import dotenv from "dotenv";
import path from "path";

// The NHCX end-to-end GUI runner (tests/nhcx/*.nhcx.ts) against the live NHCX
// sandbox. It shares the backend runner's configuration file, so both runners
// use the same test data. Start it with `care/scripts/nhcx-e2e.sh run --mode gui`.
const E2E_DIR = path.resolve(
  __dirname,
  process.env.NHCX_TEST_E2E_DIR || "../../../care/care/nhcx/tests/e2e",
);
dotenv.config({ path: path.join(E2E_DIR, ".env") });

const waitSeconds = Number(process.env.NHCX_TEST_WAIT_SECONDS || 120);
const channel = process.env.NHCX_TEST_BROWSER_CHANNEL;

export default defineConfig({
  testDir: ".",
  testMatch: /.*\.nhcx\.ts/,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  // one test walks a claim through several payer round trips
  timeout: (waitSeconds * 6 + 300) * 1000,
  expect: { timeout: 15000 },
  outputDir: path.join(E2E_DIR, "artifacts/gui/playwright"),
  reporter: [["list"]],
  use: {
    baseURL: process.env.NHCX_TEST_APP_URL || "http://localhost:4000",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    actionTimeout: 30000,
    navigationTimeout: 60000,
    launchOptions: {
      slowMo: Number(process.env.NHCX_TEST_SLOWMO_MS || 0),
    },
  },
  projects: [
    {
      name: "nhcx",
      use: {
        ...devices["Desktop Chrome"],
        channel: channel && channel !== "chromium" ? channel : undefined,
      },
    },
  ],
});
