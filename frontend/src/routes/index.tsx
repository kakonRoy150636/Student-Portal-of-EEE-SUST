import React, { lazy, Suspense } from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AppLayout } from '@/layouts/AppLayout';
import { AuthLayout } from '@/layouts/AuthLayout';
import { ProtectedRoute } from './ProtectedRoute';
import { ErrorBoundary } from './ErrorBoundary';

const LoginPage = lazy(() => import('@/features/auth/pages/LoginPage'));
const RegisterPage = lazy(() => import('@/features/auth/pages/RegisterPage'));
const DashboardPage = lazy(() => import('@/features/dashboard/pages/DashboardPage'));
const SchedulePage = lazy(() => import('@/features/schedule/pages/SchedulePage'));
const RoomBookingPage = lazy(() => import('@/features/room-booking/pages/RoomBookingPage'));
const AttendancePage = lazy(() => import('@/features/attendance/pages/AttendancePage'));
const ResourcesPage = lazy(() => import('@/features/resources/pages/ResourcesPage'));
const LabManagementPage = lazy(() => import('@/features/lab-management/pages/LabManagementPage'));
const ProjectHubPage = lazy(() => import('@/features/project-hub/pages/ProjectHubPage'));
const CareerPortalPage = lazy(() => import('@/features/career/pages/CareerPortalPage'));
const AIAssistantPage = lazy(() => import('@/features/ai-assistant/pages/AIAssistantPage'));
const AdminPanelPage = lazy(() => import('@/features/admin/pages/AdminPanelPage'));

const Fallback = () => <div className="p-8 text-center text-xs text-slate-400">Loading module...</div>;

export const router = createBrowserRouter([
  {
    path: '/auth',
    element: <AuthLayout />,
    errorElement: <ErrorBoundary />,
    children: [
      { path: 'login', element: <Suspense fallback={<Fallback />}><LoginPage /></Suspense> },
      { path: 'register', element: <Suspense fallback={<Fallback />}><RegisterPage /></Suspense> },
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
      { path: 'schedule', element: <Suspense fallback={<Fallback />}><SchedulePage /></Suspense> },
      { path: 'room-booking', element: <Suspense fallback={<Fallback />}><RoomBookingPage /></Suspense> },
      { path: 'attendance', element: <Suspense fallback={<Fallback />}><AttendancePage /></Suspense> },
      { path: 'resources', element: <Suspense fallback={<Fallback />}><ResourcesPage /></Suspense> },
      { path: 'labs', element: <Suspense fallback={<Fallback />}><LabManagementPage /></Suspense> },
      { path: 'projects', element: <Suspense fallback={<Fallback />}><ProjectHubPage /></Suspense> },
      { path: 'career', element: <Suspense fallback={<Fallback />}><CareerPortalPage /></Suspense> },
      { path: 'ai', element: <Suspense fallback={<Fallback />}><AIAssistantPage /></Suspense> },
      { path: 'admin', element: <Suspense fallback={<Fallback />}><AdminPanelPage /></Suspense> }
    ]
  },
  { path: '*', element: <Navigate to="/dashboard" replace /> }
]);
