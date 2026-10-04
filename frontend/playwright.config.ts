import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './e2e', workers: 1,
  use: { baseURL: 'http://127.0.0.1:4173',
    launchOptions: { executablePath: process.env.CHROME_PATH || (process.env.CI ? undefined : '/usr/bin/google-chrome'), args: ['--no-sandbox'] } },
  webServer: { command: 'npm run preview -- --host 127.0.0.1 --port 4173',
    url: 'http://127.0.0.1:4173', reuseExistingServer: !process.env.CI },
});
