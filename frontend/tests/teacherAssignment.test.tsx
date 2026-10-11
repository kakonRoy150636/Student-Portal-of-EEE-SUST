import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type {
  CourseOffering,
  RosterEntry,
  Semester,
  TeacherAssignmentRequest,
} from '@/types/academic';

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  user: { id: 'teacher-1', role: 'teacher' },
}));

vi.mock('@/contexts/AuthContext', () => ({ useAuth: () => ({ user: mocks.user }) }));
vi.mock('@/lib/axios', () => ({ api: { get: mocks.get, post: mocks.post } }));

import TeacherAssignmentPage from '../src/features/teacher-assignment/pages/TeacherAssignmentPage';

const baseOffering: CourseOffering = {
  id: 'offering-1',
  course_id: 'course-1',
  semester_id: 1,
  semester_title: 'Fall 2026',
  semester_is_active: true,
  course_code: 'EEE 301',
  course_title: 'Power Systems',
  course_type: 'theory',
  credit_hours: 3,
  publication_status: 'published',
  assigned_teachers: [],
  created_by: null,
  published_by: 'admin-1',
  published_at: '2026-07-01T00:00:00Z',
  request_status: null,
};

const pendingRequest: TeacherAssignmentRequest = {
  id: 'request-1',
  course_offering_id: 'offering-2',
  teacher_id: mocks.user.id,
  teacher_name: 'Dr. Ada Rahman',
  course_code: 'EEE 302',
  course_title: 'Power Electronics',
  semester_id: 1,
  semester_title: 'Fall 2026',
  status: 'pending',
  decided_by: null,
  decided_at: null,
  rejection_reason: null,
  created_at: '2026-07-01T00:00:00Z',
  updated_at: '2026-07-01T00:00:00Z',
};

const rejectedRequest: TeacherAssignmentRequest = {
  ...pendingRequest,
  id: 'request-2',
  course_offering_id: 'offering-3',
  course_code: 'EEE 303',
  course_title: 'Control Systems',
  status: 'rejected',
  rejection_reason: 'Another teacher was selected.',
};

const activeSemester: Semester = {
  id: 1,
  title: 'Fall 2026',
  target_term: '3-1',
  is_active: true,
  start_date: '2026-07-01',
  end_date: '2026-12-31',
};

const approvedOffering: CourseOffering = {
  ...baseOffering,
  id: 'offering-4',
  course_code: 'EEE 304',
  course_title: 'Digital Signal Processing',
  assigned_teachers: [{ teacher_id: mocks.user.id, teacher_name: 'Dr. Ada Rahman', role: 'course_teacher' }],
};

const roster: RosterEntry[] = [{
  student_id: 'student-1',
  identifier: '2022331010',
  full_name: 'Samira Karim',
  email: 'samira@example.com',
  status: 'enrolled',
  credit_hours: 3,
}];

let offerings: CourseOffering[];
let requests: TeacherAssignmentRequest[];
let semesters: Semester[];

function response<T>(data: T) {
  return Promise.resolve({ data });
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(<QueryClientProvider client={client}><TeacherAssignmentPage /></QueryClientProvider>);
}

function setupApi() {
  mocks.get.mockImplementation((path: string) => {
    if (path.endsWith('/semesters/active')) return response(semesters);
    if (path.endsWith('/available')) return response(offerings);
    if (path.endsWith('/assignment-requests/mine')) return response(requests);
    if (path.endsWith('/roster')) return response(roster);
    throw new Error(`Unexpected GET ${path}`);
  });
  mocks.post.mockImplementation(async (path: string) => {
    if (path === '/course-offerings/provide') {
      const provided: CourseOffering = {
        ...baseOffering,
        id: 'provided-1',
        course_code: 'EEE 499',
        course_title: 'Advanced Embedded Systems',
        credit_hours: 3,
        target_term: '3-1',
        created_by: mocks.user.id,
        assigned_teachers: [{ teacher_id: mocks.user.id, teacher_name: 'Dr. Ada Rahman', role: 'course_teacher' }],
      };
      offerings = [...offerings, provided];
      return response(provided);
    }
    expect(path).toBe('/course-offerings/offering-1/assignment-requests');
    const created: TeacherAssignmentRequest = {
      ...pendingRequest,
      id: 'request-new',
      course_offering_id: 'offering-1',
      course_code: 'EEE 301',
      course_title: 'Power Systems',
    };
    requests = [...requests, created];
    offerings = offerings.map((offering) => offering.id === 'offering-1'
      ? { ...offering, request_status: 'pending' }
      : offering);
    return response(created);
  });
}

async function openOfferingDialog(user: ReturnType<typeof userEvent.setup>) {
  const button = screen.getByRole('button', { name: 'Offer a course', exact: true });
  await waitFor(() => expect((button as HTMLButtonElement).disabled).toBe(false));
  await user.click(button);
  return within(screen.getByRole('dialog', { name: 'Offer a course' }));
}

async function fillOfferingForm(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText('Course code'), 'EEE 499');
  await user.type(screen.getByLabelText('Course name'), 'Advanced Embedded Systems');
  await user.type(screen.getByLabelText('Credits'), '3');
  await user.selectOptions(screen.getByLabelText('Course type (theory/lab)'), 'theory');
  await user.selectOptions(screen.getByLabelText('Semester'), String(activeSemester.id));
}

beforeEach(() => {
  offerings = [
    baseOffering,
    { ...baseOffering, id: 'offering-2', course_code: 'EEE 302', course_title: 'Power Electronics' },
    { ...baseOffering, id: 'offering-3', course_code: 'EEE 303', course_title: 'Control Systems' },
    approvedOffering,
  ];
  requests = [pendingRequest, rejectedRequest];
  semesters = [activeSemester];
  mocks.get.mockReset();
  mocks.post.mockReset();
  setupApi();
});

afterEach(() => cleanup());

describe('TeacherAssignmentPage', () => {
  it('shows offering details, request states, and prevents duplicate requests', async () => {
    renderPage();

    expect((await screen.findAllByText('EEE 301')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('Power Systems').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Fall 2026').length).toBeGreaterThan(0);
    expect(screen.getAllByText('pending').length).toBeGreaterThan(0);
    expect(screen.getAllByText('rejected').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Another teacher was selected.').length).toBeGreaterThan(0);
    expect(screen.getAllByRole('button', { name: /Request assignment for EEE 301/i }).length).toBeGreaterThan(0);
    expect(screen.queryByRole('button', { name: /Request assignment for EEE 302/i })).toBeNull();
    expect(screen.getAllByRole('button', { name: /View roster/i }).length).toBeGreaterThan(0);
  });

  it('submits an assignment request and refreshes its state', async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click((await screen.findAllByRole('button', { name: /Request assignment for EEE 301/i }))[0]);
    await waitFor(() => expect(mocks.post).toHaveBeenCalledWith('/course-offerings/offering-1/assignment-requests'));
    expect(await screen.findByText('Assignment request submitted and marked pending review.')).toBeTruthy();
    expect((await screen.findAllByText('pending')).length).toBeGreaterThan(2);
  });

  it('offers a published course for same-term students and CRs and seniors without automatic enrollment', async () => {
    const user = userEvent.setup();
    renderPage();

    expect(screen.getByText(/Students and CRs in the target term or a later valid current term \(seniors\).*Juniors are excluded; enrollment is never automatic\./)).toBeTruthy();
    const dialog = await openOfferingDialog(user);
    expect(dialog.getByText(/Enrollment is voluntary; no student or CR is enrolled automatically\./)).toBeTruthy();
    await fillOfferingForm(user);
    expect(dialog.getByText('Students and CRs in target term 3-1 or a later valid current term (seniors) can view this course, receive notices, and choose to enroll. Juniors in earlier terms are excluded.')).toBeTruthy();
    await user.type(screen.getByLabelText('Description optional'), 'Teacher-provided course');

    await user.click(dialog.getByRole('button', { name: 'Offer a course', exact: true }));

    await waitFor(() => expect(mocks.post).toHaveBeenCalledWith('/course-offerings/provide', {
      course_code: 'EEE 499',
      title: 'Advanced Embedded Systems',
      credit_hours: 3,
      course_type: 'theory',
      semester_id: activeSemester.id,
      description: 'Teacher-provided course',
    }));
    expect(await screen.findByText('Course offered successfully. It is published now for same-term students and CRs and eligible seniors. Enrollment is voluntary; no one was enrolled automatically.')).toBeTruthy();
    expect(screen.queryByRole('dialog', { name: 'Offer a course' })).toBeNull();
    expect(await screen.findByRole('heading', { name: 'Your provided courses' })).toBeTruthy();
    expect(screen.getAllByText('EEE 499').length).toBeGreaterThan(0);
    expect(screen.getByText(/published for same-term students and CRs and seniors in later valid current terms; juniors are excluded/)).toBeTruthy();
    expect(mocks.post).toHaveBeenCalledTimes(1);
  });

  it('requires every core field, validates credits, and keeps description optional in the POST contract', async () => {
    const user = userEvent.setup();
    renderPage();
    const dialog = await openOfferingDialog(user);
    const submit = dialog.getByRole('button', { name: 'Offer a course', exact: true });

    for (const label of ['Course code', 'Course name', 'Credits', 'Course type (theory/lab)', 'Semester']) {
      expect((dialog.getByLabelText(label) as HTMLInputElement | HTMLSelectElement).required).toBe(true);
    }
    expect((dialog.getByLabelText('Description optional') as HTMLTextAreaElement).required).toBe(false);
    await user.click(submit);
    expect(dialog.getByRole('alert').textContent).toContain('Course code is required.');
    await user.type(dialog.getByLabelText('Course code'), ' EEE 499 ');
    await user.click(submit);
    expect(dialog.getByRole('alert').textContent).toContain('Course name is required.');
    await user.type(dialog.getByLabelText('Course name'), ' Advanced Embedded Systems ');
    await user.click(submit);
    expect(dialog.getByRole('alert').textContent).toContain('Credits is required.');
    for (const invalidCredits of ['0', '100', '3.14']) {
      await user.clear(dialog.getByLabelText('Credits'));
      await user.type(dialog.getByLabelText('Credits'), invalidCredits);
      await user.click(submit);
      expect(dialog.getByRole('alert').textContent).toContain('Credits must be between 0.5 and 99.5 in 0.5 increments.');
    }
    await user.clear(dialog.getByLabelText('Credits'));
    await user.type(dialog.getByLabelText('Credits'), '1.5');
    await user.click(submit);
    expect(dialog.getByRole('alert').textContent).toContain('Course type (theory/lab) is required.');
    await user.selectOptions(dialog.getByLabelText('Course type (theory/lab)'), 'lab');
    await user.click(submit);
    expect(dialog.getByRole('alert').textContent).toContain('Select a semester with a target term.');
    expect(mocks.post).not.toHaveBeenCalled();

    await user.selectOptions(dialog.getByLabelText('Semester'), String(activeSemester.id));
    await user.click(submit);
    await waitFor(() => expect(mocks.post).toHaveBeenCalledWith('/course-offerings/provide', {
      course_code: 'EEE 499',
      title: 'Advanced Embedded Systems',
      credit_hours: 1.5,
      course_type: 'lab',
      semester_id: activeSemester.id,
    }));
    expect(await screen.findByText(/Course offered successfully\./)).toBeTruthy();
  });

  it('uses the selected active semester for eligibility guidance without offering inactive or unscoped semesters', async () => {
    semesters = [
      activeSemester,
      { ...activeSemester, id: 2, title: 'Senior semester', target_term: '4-1' },
      { ...activeSemester, id: 3, title: 'Inactive semester', is_active: false },
      { ...activeSemester, id: 4, title: 'Unscoped semester', target_term: null },
    ];
    const user = userEvent.setup();
    renderPage();
    const dialog = await openOfferingDialog(user);
    const semesterSelect = dialog.getByLabelText('Semester');
    expect(within(semesterSelect).getAllByRole('option').map((option) => option.textContent)).toEqual([
      'Select a semester', 'Fall 2026 — 3-1', 'Inactive semester — 3-1', 'Senior semester — 4-1',
    ]);
    await user.selectOptions(semesterSelect, '1');
    expect(dialog.getByText(/Students and CRs in target term 3-1 or a later valid current term \(seniors\)/)).toBeTruthy();
    await user.selectOptions(semesterSelect, '2');
    expect(dialog.getByText(/Students and CRs in target term 4-1 or a later valid current term \(seniors\)/)).toBeTruthy();
    expect(dialog.queryByText(/Students and CRs in target term 3-1/)).toBeNull();
    expect(mocks.post).not.toHaveBeenCalled();
  });

  it('explains when no configured semester is available and prevents submission', async () => {
    semesters = [];
    const user = userEvent.setup();
    renderPage();
    expect(await screen.findByText('No course-provision semesters')).toBeTruthy();
    const dialog = await openOfferingDialog(user);
    expect(dialog.getByText(/Ask an administrator to configure one, then refresh\./)).toBeTruthy();
    expect((dialog.getByLabelText('Semester') as HTMLSelectElement).disabled).toBe(true);
    expect((dialog.getByRole('button', { name: 'Offer a course', exact: true }) as HTMLButtonElement).disabled).toBe(true);
    expect(mocks.post).not.toHaveBeenCalled();
  });

  it('shows active-semester load errors instead of offering a course without a semester', async () => {
    mocks.get.mockRejectedValueOnce(new Error('Semester service unavailable'));
    const user = userEvent.setup();
    renderPage();
    expect(await screen.findByText('Could not load course-provision semesters.')).toBeTruthy();
    const dialog = await openOfferingDialog(user);
    expect(dialog.getByRole('alert').textContent).toContain('Could not load semesters.');
    expect(dialog.getByRole('alert').textContent).toContain('Semester service unavailable');
    expect((dialog.getByRole('button', { name: 'Offer a course', exact: true }) as HTMLButtonElement).disabled).toBe(true);
    expect(mocks.post).not.toHaveBeenCalled();
  });

  it.each([
    { status: 409, detail: 'An offering already exists for this semester.', title: 'This course is already offered for that semester.' },
    { status: 403, detail: 'Only teachers can provide courses.', title: 'Could not offer this course.' },
  ])('keeps entries and shows the server error for a $status response without a success state', async ({ status, detail, title }) => {
    mocks.post.mockRejectedValueOnce({ isAxiosError: true, response: { status, data: { detail } } });
    const user = userEvent.setup();
    renderPage();
    const dialog = await openOfferingDialog(user);
    await fillOfferingForm(user);
    await user.type(dialog.getByLabelText('Description optional'), 'Keep my course description');
    await user.click(dialog.getByRole('button', { name: 'Offer a course', exact: true }));

    const error = await dialog.findByRole('alert');
    expect(error.textContent).toContain(title);
    expect(error.textContent).toContain(detail);
    expect((dialog.getByLabelText('Course code') as HTMLInputElement).value).toBe('EEE 499');
    expect((dialog.getByLabelText('Description optional') as HTMLTextAreaElement).value).toBe('Keep my course description');
    expect((dialog.getByLabelText('Semester') as HTMLSelectElement).value).toBe('1');
    expect(screen.queryByText(/Course offered successfully\./)).toBeNull();
    expect(mocks.post).toHaveBeenCalledTimes(1);
  });

  it('prevents duplicate pending submissions and lets the teacher retry a failed provision with the same entries', async () => {
    let rejectProvision!: (error: Error) => void;
    mocks.post.mockImplementationOnce(() => new Promise((_resolve, reject) => { rejectProvision = reject; }));
    const user = userEvent.setup();
    renderPage();
    const dialog = await openOfferingDialog(user);
    await fillOfferingForm(user);
    await user.click(dialog.getByRole('button', { name: 'Offer a course', exact: true }));

    const pendingButton = await dialog.findByRole('button', { name: 'Offering course…' });
    expect((pendingButton as HTMLButtonElement).disabled).toBe(true);
    expect((dialog.getByLabelText('Course code') as HTMLInputElement).disabled).toBe(true);
    expect((dialog.getByRole('button', { name: 'Cancel' }) as HTMLButtonElement).disabled).toBe(true);
    await user.click(pendingButton);
    await user.keyboard('{Escape}');
    expect(screen.getByRole('dialog', { name: 'Offer a course' })).toBeTruthy();
    expect(mocks.post).toHaveBeenCalledTimes(1);

    await act(async () => rejectProvision(new Error('Connection interrupted')));
    expect((await dialog.findByRole('alert')).textContent).toContain('Connection interrupted');
    expect(dialog.getByText(/Your entries are still here\./)).toBeTruthy();
    expect((dialog.getByLabelText('Course name') as HTMLInputElement).value).toBe('Advanced Embedded Systems');
    await user.click(dialog.getByRole('button', { name: 'Offer a course', exact: true }));
    expect(await screen.findByText(/Course offered successfully\./)).toBeTruthy();
    expect(mocks.post).toHaveBeenCalledTimes(2);
    expect(mocks.post.mock.calls[1]).toEqual(mocks.post.mock.calls[0]);
  });

  it('opens the approved course roster', async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click((await screen.findAllByRole('button', { name: /View roster/i }))[0]);
    expect(await screen.findByText('EEE 304 roster')).toBeTruthy();
    expect((await screen.findAllByText('Samira Karim')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('2022331010').length).toBeGreaterThan(0);
    expect(mocks.get).toHaveBeenCalledWith('/course-offerings/offering-4/roster', expect.anything());
  });

  it('shows the empty state when the backend has no offerings', async () => {
    offerings = [];
    requests = [];
    renderPage();

    expect(await screen.findByText('No course offerings available')).toBeTruthy();
  });
});
