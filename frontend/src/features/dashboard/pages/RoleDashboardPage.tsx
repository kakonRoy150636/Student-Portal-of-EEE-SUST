import React from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { UserRole } from '@/types/auth';
import { StudentDashboardPage } from './home/StudentDashboardPage';
import { CrDashboardPage } from './home/CrDashboardPage';
import { TeacherDashboardPage } from './home/TeacherDashboardPage';
import { ErDashboardPage } from './home/ErDashboardPage';
import { AdminDashboardPage } from './home/AdminDashboardPage';

export default function RoleDashboardPage() {
  const { role } = useAuth();

  switch (role) {
    case UserRole.CR:
      return <CrDashboardPage />;
    case UserRole.TEACHER:
      return <TeacherDashboardPage />;
    case UserRole.LAB_ASSISTANT:
      return <ErDashboardPage />;
    case UserRole.SUPER_ADMIN:
      return <AdminDashboardPage />;
    case UserRole.STUDENT:
    default:
      return <StudentDashboardPage />;
  }
}