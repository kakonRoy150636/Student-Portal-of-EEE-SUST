import React from 'react';
import { Link, useLocation } from 'react-router-dom';

const LABELS: Record<string, string> = {
  dashboard: 'Dashboard',
  schedule: 'Schedule',
  attendance: 'Attendance',
  resources: 'Resources',
  labs: 'Lab Management',
  'room-booking': 'Room Booking',
  projects: 'Project Hub',
  career: 'Career Portal',
  ai: 'AI Assistant',
  admin: 'Admin Panel',
  notifications: 'Notifications',
};

export const Breadcrumbs = () => {
  const location = useLocation();
  const slug = location.pathname.split('/').filter(Boolean)[0] ?? 'dashboard';
  const label = LABELS[slug] ?? slug.replace('-', ' ');

  return (
    <nav aria-label="Breadcrumb" className="mb-4 text-xs text-[var(--text-muted)]">
      <ol className="flex items-center gap-2">
        <li>
          <Link to="/dashboard" className="hover:text-[var(--text)]">
            SUST EEE
          </Link>
        </li>
        <li aria-hidden="true">/</li>
        <li className="font-medium text-[var(--text)]" aria-current="page">
          {label}
        </li>
      </ol>
    </nav>
  );
};
