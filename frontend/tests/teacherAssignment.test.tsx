import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
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

function response<T>(data: T) {
  return Promise.resolve({ data });
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(<QueryClientProvider client={client}><TeacherAssignmentPage /></QueryClientProvider>);
}

function setupApi() {
  mocks.get.mockImplementation((path: string) => {
    if (path.endsWith('/semesters/active')) return response([activeSemester]);
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

beforeEach(() => {
  offerings = [
    baseOffering,
    { ...baseOffering, id: 'offering-2', course_code: 'EEE 302', course_title: 'Power Electronics' },
    { ...baseOffering, id: 'offering-3', course_code: 'EEE 303', course_title: 'Control Systems' },
    approvedOffering,
  ];
  requests = [pendingRequest, rejectedRequest];
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

  it('offers a published course for a matching semester term', async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole('button', { name: 'Offer a course', exact: true }));
    await user.type(screen.getByLabelText('Course code'), 'EEE 499');
    await user.type(screen.getByLabelText('Course name'), 'Advanced Embedded Systems');
    await user.type(screen.getByLabelText('Credits'), '3');
    await user.selectOptions(screen.getByLabelText('Course type (theory/lab)'), 'theory');
    await user.selectOptions(screen.getByLabelText('Semester'), String(activeSemester.id));
    await user.type(screen.getByLabelText('Description optional'), 'Teacher-provided course');

    const offerButtons = screen.getAllByRole('button', { name: 'Offer a course', exact: true });
    await user.click(offerButtons[offerButtons.length - 1]);

    await waitFor(() => expect(mocks.post).toHaveBeenCalledWith('/course-offerings/provide', {
      course_code: 'EEE 499',
      title: 'Advanced Embedded Systems',
      credit_hours: 3,
      course_type: 'theory',
      semester_id: activeSemester.id,
      description: 'Teacher-provided course',
    }));
    expect(await screen.findByText('Course offered successfully. It is published now, and matching-term students can choose to enroll.')).toBeTruthy();
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
