import { expect, test } from '@playwright/test';

test('teacher can open a course workspace and save a draft announcement', async ({ page }) => {
  const workspace = {
    offering_id: 'offering-1', offering_status: 'published',
    course: { id: 'course-1', course_code: 'EEE 401', title: 'Power Systems II', credit_hours: 3, type: 'theory', description: 'Course description' },
    semester: { id: 1, title: 'Fall 2026', target_term: '4-1', is_active: true, start_date: '2026-07-01', end_date: '2026-12-31' },
    authorized_teachers: [{ teacher_id: 'teacher-1', teacher_name: 'Dr. Ada Rahman', role: 'provider' }],
    active_enrollment_count: 18, unread_announcement_count: 0, recent_activity: [], upcoming_schedules: [], resources: [], events: [], questions: [],
    permissions: { can_manage: true, can_publish: true, can_edit: true, can_archive: true, can_pin: true },
    can_manage: true, can_publish: true, can_edit: true, can_archive: true, can_pin: true,
    links: { self: '/course-offerings/offering-1/workspace', announcements: '/course-offerings/offering-1/announcements', resources: '/course-offerings/offering-1/resources', attendance: '/attendance/courses/offering-1/summary' },
  };
  let feed: Array<Record<string, unknown>> = [];
  await page.route('**/api/v1/**', async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (path.endsWith('/auth/refresh')) return route.fulfill({ json: { tokens: { access_token: 'test' } } });
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 'teacher-1', role: 'teacher', full_name: 'Dr. Ada Rahman', identifier: 'teacher' } });
    if (path.endsWith('/notifications/stream')) return route.fulfill({ contentType: 'text/event-stream', body: ': heartbeat\n\n' });
    if (path.endsWith('/notifications/summary')) return route.fulfill({ json: { items: [], unread_count: 0 } });
    if (path.endsWith('/course-offerings/offering-1/workspace')) return route.fulfill({ json: workspace });
    if (path.endsWith('/course-offerings/offering-1/announcements') && request.method() === 'GET') return route.fulfill({ json: { items: feed, total: feed.length, limit: 10, offset: 0, has_more: false } });
    if (path.endsWith('/course-offerings/offering-1/announcements') && request.method() === 'POST') {
      const payload = request.postDataJSON();
      if (!isAnnouncementPayload(payload)) return route.fulfill({ status: 422, json: { detail: 'Invalid test payload' } });
      const created = { id: 'announcement-1', offering_id: 'offering-1', author_id: 'teacher-1', author_name: 'Dr. Ada Rahman', ...payload, is_pinned: false, created_at: '2026-10-12T09:00:00Z', updated_at: '2026-10-12T09:00:00Z', archived_at: null, is_read: true, can_manage: true, can_publish: true, can_edit: true, can_archive: true, can_pin: true };
      feed = [created];
      return route.fulfill({ status: 201, json: created });
    }
    if (path.endsWith('/resources')) return route.fulfill({ json: [] });
    return route.fulfill({ json: {} });
  });

  await page.goto('/teacher/courses/offering-1');
  await expect(page.getByRole('heading', { name: 'Power Systems II' })).toBeVisible();
  await expect(page.getByText('18', { exact: true }).first()).toBeVisible();
  await page.getByRole('tab', { name: 'Announcements' }).click();
  await page.getByRole('button', { name: 'Create announcement' }).first().click();
  const dialog = page.getByRole('dialog', { name: 'Create announcement' });
  await dialog.getByLabel('Title').fill('Draft from browser');
  await dialog.getByLabel('Body').fill('Plain-text browser draft');
  await dialog.getByRole('button', { name: 'Save draft' }).click();
  await expect(page.getByRole('dialog', { name: 'Draft from browser' })).toBeVisible();
  await expect(page.getByText('draft', { exact: true }).last()).toBeVisible();
});

function isAnnouncementPayload(value: unknown): value is { title: string; body: string; status: string; announcement_type: string; audience: string; publish_at: string | null } {
  if (typeof value !== 'object' || value === null) return false;
  const payload = Object.fromEntries(Object.entries(value));
  return typeof payload.title === 'string' && typeof payload.body === 'string' && typeof payload.status === 'string'
    && typeof payload.announcement_type === 'string' && typeof payload.audience === 'string'
    && (typeof payload.publish_at === 'string' || payload.publish_at === null);
}
