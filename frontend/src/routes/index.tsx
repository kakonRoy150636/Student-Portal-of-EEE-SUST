import React, { lazy, Suspense } from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AppLayout } from '@/layouts/AppLayout';
import { AuthLayout } from '@/layouts/AuthLayout';
import { ProtectedRoute } from './ProtectedRoute';
import { ErrorBoundary } from './ErrorBoundary';
import { UserRole } from '@/types/auth';
import { RouteFallback } from '@/components/shared/PageSkeleton';

const LoginPage = lazy(() => import('@/features/auth/pages/LoginPage'));
const RegisterPage = lazy(() => import('@/features/auth/pages/RegisterPage'));
const ForgotPasswordPage = lazy(() => import('@/features/auth/pages/ForgotPasswordPage'));
const ResetPasswordPage = lazy(() => import('@/features/auth/pages/ResetPasswordPage'));
const AccountSecurityPage = lazy(() => import('@/features/account/pages/AccountSecurityPage'));
const DashboardPage = lazy(() => import('@/features/dashboard/pages/RoleDashboardPage'));
const SchedulePage = lazy(() => import('@/features/schedule/pages/SchedulePage'));
const RoomBookingPage = lazy(() => import('@/features/room-booking/pages/RoomBookingPage'));
const AttendancePage = lazy(() => import('@/features/attendance/pages/AttendancePage'));
const ResourcesPage = lazy(() => import('@/features/resources/pages/ResourcesPage'));
const LabManagementPage = lazy(() => import('@/features/lab-management/pages/LabManagementPage'));
const ProjectHubPage = lazy(() => import('@/features/project-hub/pages/ProjectHubPage'));
const CareerPortalPage = lazy(() => import('@/features/career/pages/CareerPortalPage'));
const AIAssistantPage = lazy(() => import('@/features/ai-assistant/pages/AIAssistantPage'));
const AdminPanelPage = lazy(() => import('@/features/admin/pages/AdminPanelPage'));
const NotificationsPage = lazy(() => import('@/features/notifications/pages/NotificationsPage'));
const AlumniLandingPage = lazy(() => import('@/features/alumni/pages/AlumniLandingPage'));
const AlumniDirectoryPage = lazy(() => import('@/features/alumni/pages/AlumniDirectoryPage'));
const AlumniEventsPage = lazy(() => import('@/features/alumni/pages/AlumniEventsPage'));

const Fallback = RouteFallback;

export const router = createBrowserRouter([
  {
    path: '/auth',
    element: <AuthLayout />,
    errorElement: <ErrorBoundary />,
    children: [
      { path: 'login', element: <Suspense fallback={<Fallback />}><LoginPage /></Suspense> },
      { path: 'register', element: <Suspense fallback={<Fallback />}><RegisterPage /></Suspense> },
      { path: 'forgot-password', element: <Suspense fallback={<Fallback />}><ForgotPasswordPage /></Suspense> },
      { path: 'reset-password', element: <Suspense fallback={<Fallback />}><ResetPasswordPage /></Suspense> },
      { index: true, element: <Navigate to="/auth/login" replace /> }
    ]
  },
  {
    path: '/',
    element: <ProtectedRoute><AppLayout /></ProtectedRoute>,
    errorElement: <ErrorBoundary />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'dashboard', element: <Suspense fallback={<Fallback />}><DashboardPage /></Suspense> },
      { path: 'schedule', element: <ProtectedRoute roles={[UserRole.STUDENT, UserRole.CR, UserRole.TEACHER]}><Suspense fallback={<Fallback />}><SchedulePage /></Suspense></ProtectedRoute> },
      { path: 'room-booking', element: <ProtectedRoute roles={[UserRole.STUDENT, UserRole.CR, UserRole.TEACHER, UserRole.SUPER_ADMIN]}><Suspense fallback={<Fallback />}><RoomBookingPage /></Suspense></ProtectedRoute> },
      { path: 'attendance', element: <ProtectedRoute roles={[UserRole.STUDENT, UserRole.CR, UserRole.TEACHER]}><Suspense fallback={<Fallback />}><AttendancePage /></Suspense></ProtectedRoute> },
      { path: 'resources', element: <Suspense fallback={<Fallback />}><ResourcesPage /></Suspense> },
      { path: 'labs', element: <ProtectedRoute roles={[UserRole.TEACHER, UserRole.LAB_ASSISTANT, UserRole.SUPER_ADMIN]}><Suspense fallback={<Fallback />}><LabManagementPage /></Suspense></ProtectedRoute> },
      { path: 'projects', element: <ProtectedRoute roles={[UserRole.STUDENT, UserRole.CR, UserRole.TEACHER]}><Suspense fallback={<Fallback />}><ProjectHubPage /></Suspense></ProtectedRoute> },
      { path: 'career', element: <ProtectedRoute roles={[UserRole.STUDENT, UserRole.CR]}><Suspense fallback={<Fallback />}><CareerPortalPage /></Suspense></ProtectedRoute> },
      { path: 'ai', element: <Suspense fallback={<Fallback />}><AIAssistantPage /></Suspense> },
      { path: 'admin', element: <ProtectedRoute roles={[UserRole.SUPER_ADMIN]}><Suspense fallback={<Fallback />}><AdminPanelPage /></Suspense></ProtectedRoute> },
      { path: 'notifications', element: <Suspense fallback={<Fallback />}><NotificationsPage /></Suspense> },
      { path: 'account/security', element: <Suspense fallback={<Fallback />}><AccountSecurityPage /></Suspense> },
      { path: 'alumni/directory', element: <ProtectedRoute roles={[UserRole.ALUMNI, UserRole.SUPER_ADMIN]}><Suspense fallback={<Fallback />}><AlumniDirectoryPage /></Suspense></ProtectedRoute> },
      { path: 'alumni/events', element: <ProtectedRoute roles={[UserRole.ALUMNI, UserRole.SUPER_ADMIN]}><Suspense fallback={<Fallback />}><AlumniEventsPage /></Suspense></ProtectedRoute> }
    ]
  },
  { path: '*', element: <Navigate to="/dashboard" replace /> }
]);
