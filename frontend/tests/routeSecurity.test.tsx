import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { UserRole } from '@/types/auth';

const auth = vi.hoisted(() => ({
  value: {
    isAuthenticated: true,
    role: null as UserRole | null,
    loading: false,
  },
}));

vi.mock('@/contexts/AuthContext', () => ({ useAuth: () => auth.value }));

import { ProtectedRoute } from '../src/routes/ProtectedRoute';

afterEach(() => {
  cleanup();
  auth.value = { isAuthenticated: true, role: null, loading: false };
});

describe('ProtectedRoute role enforcement', () => {
  it('redirects when an authenticated response has no role', () => {
    render(
      <MemoryRouter initialEntries={['/teacher-assignment']}>
        <Routes>
          <Route
            path="/teacher-assignment"
            element={
              <ProtectedRoute roles={[UserRole.TEACHER]}>
                <p>Teacher-only roster</p>
              </ProtectedRoute>
            }
          />
          <Route path="/dashboard" element={<p>Dashboard</p>} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.queryByText('Teacher-only roster')).toBeNull();
    expect(screen.getByText('Dashboard')).toBeTruthy();
  });
});
