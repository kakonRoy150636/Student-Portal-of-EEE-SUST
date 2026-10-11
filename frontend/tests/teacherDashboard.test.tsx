import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { UserRole } from '@/types/auth';
import { ThemeProvider } from '@/contexts/ThemeContext';

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  role: 'teacher' as UserRole | null,
}));

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 'user-1', role: mocks.role, full_name: 'Ada Rahman' },
    role: mocks.role,
    isAuthenticated: true,
    loading: false,
  }),
}));
vi.mock('@/lib/axios', () => ({ api: { get: mocks.get, post: mocks.post } }));

import RoleDashboardPage from '../src/features/dashboard/pages/RoleDashboardPage';
import TeacherAssignmentPage from '../src/features/teacher-assignment/pages/TeacherAssignmentPage';
import { Sidebar } from '../src/layouts/components/Sidebar';
import { MobileDrawer } from '../src/layouts/components/MobileNav';
import { flattenNav } from '../src/layouts/nav';
import { ProtectedRoute } from '../src/routes/ProtectedRoute';

function renderDashboard(initialPath = '/dashboard') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <ThemeProvider>
        <MemoryRouter initialEntries={[initialPath]}>
          <Sidebar />
          <MobileDrawer open onClose={() => {}} />
          <Routes>
            <Route path="/dashboard" element={<RoleDashboardPage />} />
            <Route
              path="/teacher-assignment"
              element={<ProtectedRoute roles={[UserRole.TEACHER]}><TeacherAssignmentPage /></ProtectedRoute>}
            />
          </Routes>
        </MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>,
  );
  return client;
}

beforeEach(() => {
  mocks.role = UserRole.TEACHER;
  mocks.get.mockReset();
  mocks.post.mockReset();
  mocks.get.mockImplementation((path: string) => {
    if (path === '/dashboard/summary') return Promise.resolve({ data: {} });
    if (path === '/auth/admin/pending-approvals') return Promise.resolve({ data: [] });
    if (path === '/alumni/me') return Promise.resolve({ data: null });
    if (path === '/course-offerings/semesters/active') {
      return Promise.resolve({ data: [{ id: 1, title: 'Fall 2026', target_term: '3-1', is_active: true }] });
    }
    if (path === '/course-offerings/available' || path === '/course-offerings/assignment-requests/mine') {
      return Promise.resolve({ data: [] });
    }
    throw new Error(`Unexpected GET ${path}`);
  });
});

afterEach(() => cleanup());

describe('Teacher course offering entry', () => {
  it('takes a teacher from the dashboard header to the existing offering form even while counters are loading', async () => {
    mocks.get.mockImplementationOnce(() => new Promise(() => {}));
    const user = userEvent.setup();
    renderDashboard();

    const shortcut = screen.getByRole('button', { name: 'Offer a course', exact: true });
    expect((shortcut as HTMLButtonElement).disabled).toBe(false);
    expect(screen.getByRole('heading', { name: /Ada Rahman/ }).closest('section')?.contains(shortcut)).toBe(true);
    expect(mocks.get).toHaveBeenCalledTimes(1);
    expect(mocks.get).toHaveBeenCalledWith('/dashboard/summary');
    for (const label of ['Primary', 'Mobile']) {
      const nav = within(screen.getByRole('navigation', { name: label, exact: true }));
      expect(nav.getByRole('link', { name: 'Course Assignment' }).getAttribute('href')).toBe('/teacher-assignment');
    }
    expect(flattenNav(UserRole.TEACHER).find((item) => item.path === '/teacher-assignment')?.hint).toContain('Offer a course');

    await user.click(shortcut);
    expect(await screen.findByRole('heading', { name: 'Course assignment', exact: true })).toBeTruthy();
    const offerButton = screen.getByRole('button', { name: 'Offer a course', exact: true });
    await waitFor(() => expect((offerButton as HTMLButtonElement).disabled).toBe(false));
    await user.click(offerButton);
    const dialog = within(screen.getByRole('dialog', { name: 'Offer a course' }));
    expect(dialog.getByLabelText('Course code')).toBeTruthy();
    expect(dialog.getByLabelText('Semester')).toBeTruthy();
    expect(mocks.post).not.toHaveBeenCalled();
  });

  it('keeps the shortcut available when dashboard counters fail', async () => {
    mocks.get.mockRejectedValueOnce(new Error('Counters unavailable'));
    const client = renderDashboard();

    await waitFor(() => expect(client.getQueryState(['dashboard', 'summary'])?.status).toBe('error'));
    expect((screen.getByRole('button', { name: 'Offer a course', exact: true }) as HTMLButtonElement).disabled).toBe(false);
  });

  it.each([UserRole.STUDENT, UserRole.CR, UserRole.SUPER_ADMIN, UserRole.LAB_ASSISTANT, UserRole.ALUMNI, null])(
    'hides the offering shortcut and navigation and prevents teacher queries for role %s',
    async (role) => {
      mocks.role = role;
      const client = renderDashboard('/teacher-assignment');

      // The protected page redirects to that role's real dashboard without mounting teacher hooks.
      await waitFor(() => expect(client.getQueryState(['dashboard', 'summary'])?.status).toBe('success'));
      expect(screen.getByRole('heading', { name: /Ada Rahman/ })).toBeTruthy();
      expect(screen.queryByRole('button', { name: 'Offer a course', exact: true })).toBeNull();
      expect(screen.queryByRole('link', { name: 'Course Assignment' })).toBeNull();
      expect(screen.queryByRole('heading', { name: 'Course assignment', exact: true })).toBeNull();
      expect(flattenNav(role).some((item) => item.path === '/teacher-assignment' || item.hint?.includes('Offer a course'))).toBe(false);
      expect(mocks.get.mock.calls.some(([path]) => path.startsWith('/course-offerings'))).toBe(false);
      expect(mocks.post).not.toHaveBeenCalled();
    },
  );
});
