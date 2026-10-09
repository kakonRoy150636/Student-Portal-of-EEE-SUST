import { test, expect, type Page, type BrowserContext } from '@playwright/test';

// Opt in only against the disposable, seeded stack described in
// docs/SEMESTER_WORKFLOW_VERIFICATION.md. Every mutation below uses the real API.
// No intercepted responses, forged sessions, or mocked notification/credit data.
type Session = { page: Page; headers: Record<string, string>; user: { id: string; full_name: string } };
type InboxItem = { id: number; data_payload: { type: string; url: string } };
const apiBase = '/api/v1';
const offeringsBase = `${apiBase}/course-offerings`;
const apiUrl = (path: string) => `${process.env.SEMESTER_E2E_API_ORIGIN ?? ''}${path}`;

async function login(page: Page, identifier: string, password: string): Promise<Session> {
  await page.goto('/auth/login');
  await page.getByLabel('Student ID / Employee Email').fill(identifier);
  await page.getByLabel('Password', { exact: true }).fill(password);
  const responsePromise = page.waitForResponse((response) =>
    new URL(response.url()).pathname === `${apiBase}/auth/login` && response.request().method() === 'POST');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  const response = await responsePromise;
  expect(response.status()).toBe(200);
  const { user, tokens } = await response.json();
  await expect(page).toHaveURL(/\/dashboard$/);
  // Tokens stay in memory; do not log them or save storage state.
  return { page, user, headers: { Authorization: `Bearer ${tokens.access_token}` } };
}

async function mutateFromUi(page: Page, path: string, method: string, action: () => Promise<void>) {
  const responsePromise = page.waitForResponse((response) =>
    new URL(response.url()).pathname === path && response.request().method() === method);
  await action();
  return responsePromise;
}

async function inbox(session: Session): Promise<InboxItem[]> {
  const response = await session.page.request.get(apiUrl(`${apiBase}/notifications`), { headers: session.headers });
  expect(response.status()).toBe(200);
  return response.json();
}

function notificationCount(items: InboxItem[], type: string) {
  const matches = items.filter((item) => item.data_payload.type === type);
  for (const item of matches) expect(item.data_payload.url).toBe('/notifications');
  return matches.length;
}

async function verifyCredits(session: Session, expected: number) {
  const response = await session.page.request.get(apiUrl(`${offeringsBase}/enrollments/me/credits`), { headers: session.headers });
  expect(response.status()).toBe(200);
  expect((await response.json()).active_credit_total).toBe(expected);
  const dashboard = await session.page.request.get(apiUrl(`${apiBase}/dashboard/summary`), { headers: session.headers });
  expect(dashboard.status()).toBe(200);
  expect((await dashboard.json()).student.credit_hours).toBe(expected);
  await expect(session.page.getByLabel(`Total active credits: ${expected}`, { exact: true })).toBeVisible();
}

test('live semester workflow: creation, assignment, notifications, enrollment credits and access control', async ({ browser, baseURL }) => {
  test.skip(process.env.SEMESTER_E2E !== '1', 'Requires the disposable semester E2E stack; see the verification guide.');
  test.setTimeout(90_000);
  const courseCode = process.env.SEMESTER_E2E_COURSE_CODE || 'EEE 399';
  const contexts: BrowserContext[] = [];
  const session = async (identifier: string, password: string) => {
    const context = await browser.newContext({ baseURL, serviceWorkers: 'block' });
    contexts.push(context);
    return login(await context.newPage(), identifier, password);
  };
  try {
    const admin = await session('dev-admin', 'DevAdmin123!');
    const teacher = await session('dev-teacher-1', 'DevTeacher123!');
    const student = await session('dev-student-1', 'DevStudent123!');
    const classmate = await session('dev-student-2', 'DevStudent123!');
    const unrelatedTeacher = await session('dev-teacher-2', 'DevTeacher123!');
    const beforeStudentInbox = await inbox(student);
    const beforeClassmateInbox = await inbox(classmate);
    const beforeTeacherInbox = await inbox(teacher);
    let offeringId: string;
    let requestId: string;
    let enrollmentId: number;
    let baselineCredits: number;
    let courseCredits: number;

    const coursesResponse = await admin.page.request.get(apiUrl(`${apiBase}/courses`), { headers: admin.headers });
    expect(coursesResponse.status()).toBe(200);
    const course = (await coursesResponse.json()).find((item: { course_code: string }) => item.course_code === courseCode);
    expect(course).toBeTruthy();
    courseCredits = Number(course.credits);
    const semesterResponse = await admin.page.request.get(apiUrl(`${offeringsBase}/semesters/active`), { headers: admin.headers });
    expect(semesterResponse.status()).toBe(200);
    const semester = (await semesterResponse.json())[0];
    expect(semester?.is_active).toBe(true);

    await admin.page.goto('/admin/academic');
    await expect(admin.page.getByRole('heading', { name: 'Academic management' })).toBeVisible();
    await admin.page.getByRole('button', { name: 'New offering', exact: true }).first().click();
    await admin.page.getByLabel('Course', { exact: true }).selectOption(course.id);
    await admin.page.getByLabel('Semester', { exact: true }).selectOption(String(semester.id));
    const created = await mutateFromUi(
      admin.page,
      `${apiBase}/course-offerings`,
      'POST',
      () => admin.page.getByRole('button', { name: 'Create offering', exact: true }).click(),
    );
    expect(created.status()).toBe(201);
    offeringId = (await created.json()).id;

    const publishButton = admin.page.getByRole('button', { name: `Publish ${courseCode}`, exact: true });
    await expect(publishButton).toBeVisible();
    await publishButton.click();
    await expect(admin.page.getByRole('heading', { name: 'Publish course offering?' })).toBeVisible();
    const published = await mutateFromUi(
      admin.page,
      `${apiBase}/course-offerings/${offeringId}/publish`,
      'POST',
      () => admin.page.getByRole('button', { name: 'Confirm', exact: true }).click(),
    );
    expect(published.status()).toBe(200);
    expect((await published.json()).publication_status).toBe('published');

    await teacher.page.goto('/teacher-assignment');
    await expect(teacher.page.getByRole('heading', { name: 'Course assignment' })).toBeVisible();
    const requestButton = teacher.page.getByRole('button', { name: `Request assignment for ${courseCode}`, exact: true });
    await expect(requestButton).toBeVisible();
    const request = await mutateFromUi(
      teacher.page,
      `${apiBase}/course-offerings/${offeringId}/assignment-requests`,
      'POST',
      () => requestButton.click(),
    );
    expect(request.status()).toBe(201);
    requestId = (await request.json()).id;
    await expect(teacher.page.getByText('Assignment request submitted and marked pending review.')).toBeVisible();

    await admin.page.reload();
    await expect(admin.page.getByRole('heading', { name: 'Academic management' })).toBeVisible();
    const approveButton = admin.page.getByRole('button', { name: `Approve Dr. Samira Rahman for ${courseCode}`, exact: true });
    await expect(approveButton).toBeVisible();
    await approveButton.click();
    await expect(admin.page.getByRole('heading', { name: 'Approve teacher assignment?' })).toBeVisible();
    const approved = await mutateFromUi(
      admin.page,
      `${apiBase}/course-offerings/assignment-requests/${requestId}`,
      'PATCH',
      () => admin.page.getByRole('button', { name: 'Approve request', exact: true }).click(),
    );
    expect(approved.status()).toBe(200);
    expect((await approved.json()).status).toBe('approved');

    const studentAfterAssignment = await inbox(student);
    const classmateAfterAssignment = await inbox(classmate);
    expect(notificationCount(studentAfterAssignment, 'course_assignment')).toBe(
      notificationCount(beforeStudentInbox, 'course_assignment') + 1,
    );
    expect(notificationCount(classmateAfterAssignment, 'course_assignment')).toBe(
      notificationCount(beforeClassmateInbox, 'course_assignment') + 1,
    );

    await student.page.goto('/course-selection');
    await expect(student.page.getByRole('heading', { name: 'Course selection' })).toBeVisible();
    await expect(student.page.getByText(courseCode, { exact: true })).toBeVisible();
    await expect(student.page.getByRole('button', { name: `Select ${courseCode}`, exact: true })).toBeVisible();
    const beforeCreditsResponse = await student.page.request.get(apiUrl(`${offeringsBase}/enrollments/me/credits`), { headers: student.headers });
    expect(beforeCreditsResponse.status()).toBe(200);
    baselineCredits = Number((await beforeCreditsResponse.json()).active_credit_total);

    const enrolled = await mutateFromUi(
      student.page,
      `${apiBase}/course-offerings/${offeringId}/enroll`,
      'POST',
      () => student.page.getByRole('button', { name: `Select ${courseCode}`, exact: true }).click(),
    );
    expect(enrolled.status()).toBe(201);
    enrollmentId = (await enrolled.json()).id;
    await expect(student.page.getByText('Course selected.', { exact: true })).toBeVisible();
    await verifyCredits(student, baselineCredits + courseCredits);

    const studentAfterEnrollment = await inbox(student);
    const teacherAfterEnrollment = await inbox(teacher);
    expect(notificationCount(studentAfterEnrollment, 'course_enrollment')).toBe(
      notificationCount(beforeStudentInbox, 'course_enrollment') + 1,
    );
    expect(notificationCount(teacherAfterEnrollment, 'course_enrollment')).toBe(
      notificationCount(beforeTeacherInbox, 'course_enrollment') + 1,
    );

    const dropButton = student.page.getByRole('button', { name: `Drop ${courseCode}`, exact: true });
    await expect(dropButton).toBeVisible();
    await dropButton.click();
    await expect(student.page.getByRole('heading', { name: `Drop ${courseCode}?` })).toBeVisible();
    const dropped = await mutateFromUi(
      student.page,
      `${apiBase}/course-offerings/enrollments/${enrollmentId}/drop`,
      'POST',
      () => student.page.getByRole('button', { name: 'Confirm drop', exact: true }).click(),
    );
    expect(dropped.status()).toBe(200);
    expect((await dropped.json()).status).toBe('drop');
    await expect(student.page.getByText('Course dropped.', { exact: true })).toBeVisible();
    await verifyCredits(student, baselineCredits);

    const reselected = await mutateFromUi(
      student.page,
      `${apiBase}/course-offerings/enrollments/${enrollmentId}/reselect`,
      'POST',
      () => student.page.getByRole('button', { name: `Reselect ${courseCode}`, exact: true }).click(),
    );
    expect(reselected.status()).toBe(200);
    expect((await reselected.json()).status).toBe('enrolled');
    await expect(student.page.getByText('Course reselected.', { exact: true })).toBeVisible();
    await verifyCredits(student, baselineCredits + courseCredits);

    const studentAfterReselect = await inbox(student);
    const teacherAfterReselect = await inbox(teacher);
    expect(notificationCount(studentAfterReselect, 'course_enrollment')).toBe(
      notificationCount(studentAfterEnrollment, 'course_enrollment') + 1,
    );
    expect(notificationCount(teacherAfterReselect, 'course_enrollment')).toBe(
      notificationCount(teacherAfterEnrollment, 'course_enrollment') + 1,
    );

    const unauthenticated = await student.page.request.get(apiUrl(`${offeringsBase}/published`));
    expect(unauthenticated.status()).toBe(401);
    const studentCreate = await student.page.request.post(apiUrl(offeringsBase), {
      headers: student.headers,
      data: { course_id: course.id, semester_id: semester.id },
    });
    expect(studentCreate.status()).toBe(403);
    const studentAdminRequests = await student.page.request.get(apiUrl(`${offeringsBase}/assignment-requests`), { headers: student.headers });
    expect(studentAdminRequests.status()).toBe(403);
    const teacherDecision = await teacher.page.request.patch(apiUrl(`${offeringsBase}/assignment-requests/${requestId}`), {
      headers: teacher.headers,
      data: { decision: 'reject' },
    });
    expect(teacherDecision.status()).toBe(403);

    await unrelatedTeacher.page.goto('/admin/academic');
    await expect(unrelatedTeacher.page).toHaveURL(/\/dashboard$/);
    await student.page.goto('/teacher-assignment');
    await expect(student.page).toHaveURL(/\/dashboard$/);
    await teacher.page.goto('/course-selection');
    await expect(teacher.page).toHaveURL(/\/dashboard$/);
  } finally {
    await Promise.all(contexts.map((context) => context.close()));
  }
});
