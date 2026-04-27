import { defineConfig } from "@playwright/test";

const apiBaseUrl = process.env.E2E_API_URL ?? "http://localhost:8000/api";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: {
    timeout: 15_000,
  },
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: "list",
  use: {
    baseURL: apiBaseUrl.endsWith("/") ? apiBaseUrl : `${apiBaseUrl}/`,
    extraHTTPHeaders: {
      Accept: "application/json",
    },
  },
});
