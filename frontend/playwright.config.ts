import { defineConfig, devices } from "@playwright/test";

const isLiveMode = process.env.E2E_API_MODE === "live";
const port = isLiveMode ? 5173 : 4173;
const baseURL = `http://127.0.0.1:${port}`;

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  reporter: "list",
  use: {
    baseURL,
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: isLiveMode
    ? {
        // Live-backend mode requires Vite dev server so `/api` proxy routes to FastAPI (`vite preview` does not proxy `/api`).
        command: "npm run dev -- --host 127.0.0.1 --port 5173 --strictPort",
        url: "http://127.0.0.1:5173",
        reuseExistingServer: false,
        timeout: 120_000,
      }
    : {
        // Default mocked CI/local E2E builds a fresh production bundle and serves it strictly on port 4173.
        command: "npm run build && npm run preview -- --host 127.0.0.1 --port 4173 --strictPort",
        url: "http://127.0.0.1:4173",
        reuseExistingServer: false,
        timeout: 120_000,
      },
});
