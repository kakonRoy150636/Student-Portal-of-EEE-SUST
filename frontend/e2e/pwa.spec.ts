import { test, expect } from '@playwright/test';

test('manifest, installed worker and routine support offline navigation and logout cleanup', async ({ page, context }) => {
  const user = { id: 'pwa-student', role: 'student', full_name: 'Test Student', identifier: 'test' };
  await page.route('**/api/v1/**', async (route) => {
    const path = new URL(route.request().url()).pathname;
    const data = path.endsWith('/auth/refresh') ? { tokens: { access_token: 'test' } }
      : path.endsWith('/auth/me') ? user
      : path.endsWith('/schedules/my-routine') ? [{ id: 'class-1', course_code: 'EEE101', course_title: 'Circuits', day_of_week: 'Monday', start_time: '10:00', end_time: '11:00', room_number: '201', instructor_name: 'Teacher', is_lab: false }]
      : path.endsWith('/notifications/summary') ? { items: [], unread_count: 0 } : {};
    if (path.endsWith('/notifications/stream')) await route.fulfill({ contentType: 'text/event-stream', body: ': heartbeat\n\n' });
    else await route.fulfill({ json: data });
  });
  await page.addInitScript(() => {
    Object.defineProperty(window, 'permissionCalls', { value: 0, writable: true });
    Notification.requestPermission = async () => { (window as unknown as { permissionCalls: number }).permissionCalls += 1; return 'denied'; };
  });
  await page.goto('/schedule');
  await expect(page.getByText('EEE101', { exact: true })).toBeVisible();
  await page.evaluate(() => navigator.serviceWorker.ready);
  await expect.poll(() => page.evaluate(() => Boolean(navigator.serviceWorker.controller))).toBe(true);
  await expect.poll(() => page.evaluate(() => new Promise<boolean>((resolve) => {
    const open = indexedDB.open('portal-offline', 1);
    open.onsuccess = () => { const db = open.result; const request = db.transaction('routine').objectStore('routine').get('last');
      request.onsuccess = () => { resolve(Boolean(request.result?.classes?.length)); db.close(); }; };
  }))).toBe(true);
  expect(await page.evaluate(() => (window as unknown as { permissionCalls: number }).permissionCalls)).toBe(0);
  const manifest = await (await page.request.get('/manifest.webmanifest')).json();
  expect(manifest.display).toBe('standalone');
  expect(manifest.icons.some((icon: { purpose: string }) => icon.purpose === 'maskable')).toBe(true);
  await context.setOffline(true);
  await page.goto('/schedule');
  await expect(page.getByRole('heading', { name: 'Offline class routine' })).toBeVisible();
  await expect(page.getByText('EEE101 · Circuits')).toBeVisible();
  await expect(page.getByText('Monday 10:00–11:00 · 201')).toBeVisible();
  expect(await page.evaluate(async () => {
    const keys = await caches.keys();
    const urls = await Promise.all(keys.map(async (key) => (await (await caches.open(key)).keys()).map((r) => r.url)));
    return urls.flat().some((url) => url.includes('/api/'));
  })).toBe(false);
  await context.setOffline(false);
  await page.goto('/schedule');
  await expect(page.getByText('EEE101', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await expect(page).toHaveURL(/\/auth\/login/);
  await expect.poll(() => page.evaluate(() => new Promise<boolean>((resolve) => {
    const open = indexedDB.open('portal-offline', 1);
    open.onsuccess = () => {
      const db = open.result;
      const request = db.transaction('routine').objectStore('routine').get('last');
      request.onsuccess = () => { resolve(request.result === undefined); db.close(); };
      request.onerror = () => { resolve(false); db.close(); };
    };
    open.onerror = () => resolve(false);
  }))).toBe(true);
  await page.goto('/offline.html');
  await expect(page.getByText('No routine saved yet. Open Class routine while online first.')).toBeVisible();
});

test('iPhone users see Home Screen instructions before push controls', async ({ page }) => {
  await page.addInitScript(() => Object.defineProperty(navigator, 'userAgent', { value: 'iPhone', configurable: true }));
  await page.route('**/api/v1/**', async (route) => {
    const path = new URL(route.request().url()).pathname;
    const data = path.endsWith('/auth/refresh') ? { tokens: { access_token: 'test' } }
      : path.endsWith('/auth/me') ? { id: 'student', role: 'student', full_name: 'Student' }
      : path.endsWith('/notifications/summary') ? { items: [], unread_count: 0 }
      : { per_type: Object.fromEntries(['class_reminder', 'lab_reminder', 'exam_reminder', 'announcement'].map((type) => [type, { push: true, in_app: true }])), quiet_start: null, quiet_end: null, timezone: 'Asia/Dhaka' };
    if (path.endsWith('/notifications/stream')) await route.fulfill({ contentType: 'text/event-stream', body: ': heartbeat\n\n' });
    else await route.fulfill({ json: data });
  });
  await page.goto('/notifications');
  await expect(page.getByRole('heading', { name: 'Install on iPhone or iPad' })).toBeVisible();
  await expect(page.getByText('Tap Share, then Add to Home Screen.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Enable push on this device' })).toHaveCount(0);
});

test('notification center applies live SSE updates, unread badge and mark-as-read', async ({ page }) => {
  let read = false;
  const item = () => ({ id: 7, title: 'Class reminder', body: 'Open portal for details.', is_read: read, created_at: '2030-01-01T00:00:00Z', data_payload: { url: '/schedule' } });
  await page.route('**/api/v1/**', async (route) => {
    const path = new URL(route.request().url()).pathname;
    let data: unknown = {};
    if (path.endsWith('/auth/refresh')) data = { tokens: { access_token: 'test' } };
    if (path.endsWith('/auth/me')) data = { id: 'student', role: 'student', full_name: 'Student' };
    if (path.endsWith('/notifications/7/read')) { read = true; data = item(); }
    if (path.endsWith('/notifications/summary')) data = { items: read ? [item()] : [], unread_count: 0 };
    if (path.endsWith('/notifications/preferences')) data = {
      per_type: Object.fromEntries(['class_reminder', 'lab_reminder', 'exam_reminder', 'announcement'].map((type) => [type, { push: true, in_app: true }])),
      quiet_start: null, quiet_end: null, timezone: 'Asia/Dhaka',
    };
    if (path.endsWith('/notifications/stream')) {
      await route.fulfill({ contentType: 'text/event-stream', body: `event: notifications\ndata: ${JSON.stringify({ items: [item()], unread_count: read ? 0 : 1 })}\n\n` });
    } else await route.fulfill({ json: data });
  });
  await page.goto('/notifications');
  await expect(page.getByText('Class reminder', { exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Notifications, 1 unread', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Mark as read', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Mark as read', exact: true })).toHaveCount(0);
  await expect(page.locator('header').getByRole('link', { name: 'Notifications', exact: true })).toBeVisible();
});

test('academic assistant renders cited API answers and quota errors', async ({ page }) => {
  let calls = 0;
  await page.route('**/api/v1/**', async (route) => {
    const path = new URL(route.request().url()).pathname;
    let data: unknown = {};
    if (path.endsWith('/auth/refresh')) data = { tokens: { access_token: 'test' } };
    if (path.endsWith('/auth/me')) data = { id: 'student', role: 'student', full_name: 'Student' };
    if (path.endsWith('/notifications/summary')) data = { items: [], unread_count: 0 };
    if (path.endsWith('/notifications/stream')) { await route.fulfill({ contentType: 'text/event-stream', body: ': heartbeat\n\n' }); return; }
    if (path.endsWith('/ai/query')) {
      expect(route.request().postDataJSON()).toEqual({ prompt: 'What is Ohm law?', course_code: 'EEE 311' });
      calls += 1;
      if (calls === 2) { await route.fulfill({ status: 429, json: { detail: 'Daily AI query quota exhausted' } }); return; }
      data = { answer: 'Voltage equals current times resistance [S1]', grounded: true, quota_remaining: 1,
        citations: [{ source_id: 'S1', chunk_id: 'test', document_name: 'Test Syllabus', page_number: 7, section: 'Circuit laws' }] };
    }
    await route.fulfill({ json: data });
  });
  await page.goto('/ai');
  await page.getByRole('textbox', { name: 'Ask a syllabus question' }).fill('What is Ohm law?');
  await page.getByRole('button', { name: 'Send', exact: true }).click();
  await expect(page.getByText('Voltage equals current times resistance [S1]')).toBeVisible();
  await expect(page.getByRole('list', { name: 'Sources' })).toContainText('Test Syllabus · page 7 · Circuit laws');
  await page.getByRole('textbox', { name: 'Ask a syllabus question' }).fill('What is Ohm law?');
  await page.getByRole('button', { name: 'Send', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Daily AI query quota exhausted');
});
