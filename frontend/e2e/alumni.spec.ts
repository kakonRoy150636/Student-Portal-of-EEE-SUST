import { test, expect } from '@playwright/test';

test('standalone alumni section loads dynamic batches, summary and privacy-safe cards', async ({ page }) => {
  await page.route('**/api/v1/**', async (route) => {
    const path = new URL(route.request().url()).pathname;
    let data: unknown = {};
    if (path.endsWith('/auth/refresh')) data = { tokens: { access_token: 'test' } };
    if (path.endsWith('/auth/me')) data = { id: 'student', role: 'student', full_name: 'Student' };
    if (path.endsWith('/notifications/summary')) data = { items: [], unread_count: 0 };
    if (path.endsWith('/notifications/stream')) { await route.fulfill({ contentType: 'text/event-stream', body: ': heartbeat\n\n' }); return; }
    if (path.endsWith('/alumni/batches')) data = [{ year: 2010, alumni_count: 0 }, { year: 2026, alumni_count: 1 }];
    if (path.endsWith('/alumni/batches/2026/summary')) data = { year: 2026, total: 1, employed: 1, higher_study: 0, abroad: 0, top_companies: [{ name: 'Power Grid Company', count: 1 }], top_countries: [{ name: 'Bangladesh', count: 1 }] };
    if (path.endsWith('/alumni/')) data = { items: [{ id: 'alum-1', full_name: 'First Engineer', batch_year: 2026, department: 'EEE', current_city: 'Sylhet', current_country: 'Bangladesh', linkedin_url: null, email: null, phone: null, current_employment: { id: 'job-1', alumni_id: 'alum-1', organization: 'Power Grid Company', position: 'Engineer', sector: 'industry', city: 'Sylhet', country: 'Bangladesh', start_date: null, end_date: null, is_current: true } }], page: 1, page_size: 12, total: 1, pages: 1 };
    await route.fulfill({ json: data });
  });
  await page.goto('/alumni');
  await expect(page.getByRole('heading', { name: 'SUST EEE alumni' })).toBeVisible();
  await expect(page.getByText('Power Grid Company', { exact: false })).toBeVisible();
  await expect(page.getByText('first@example.com', { exact: true })).toHaveCount(0);
  await expect(page.getByRole('combobox', { name: 'Alumni batch' })).toBeVisible();
  await page.getByRole('link', { name: 'View profile' }).click();
  await expect(page).toHaveURL(/\/alumni\/profile\/alum-1$/);
});
