# SUST EEE Portal – Role Based Architecture

## Overview

The portal serves four primary personas with distinct homepages, navigation, and permissions:

- **Student**
- **Class Representative (CR)**
- **Teacher**
- **ER / Lab Assistant (ER)**
- **Super Admin**

All accounts are created with a real `full_name` which is displayed in the header, hero banner, and breadcrumbs.

## Roles

| Role | Backend Enum | Registration Flow | Approval Required |
|------|--------------|-------------------|-------------------|
| STUDENT | `student` | Self-service | No |
| CR | `cr` | Via student registration form | Yes - Admin |
| TEACHER | `teacher` | Dedicated `/auth/register/teacher` | Yes - Admin |
| ER / LAB_ASSISTANT | `lab_assistant` | Via registration form with role `er` | Yes - Admin |
| SUPER_ADMIN | `super_admin` | Seeded | No |

> Mapping note: Frontend "ER" choice is mapped to backend `UserRole.LAB_ASSISTANT`.

## Homepage Differentiation

Each role sees a different console label and dashboard content:

- **Student**: COMMAND CONSOLE → TodayRoutine + AttendanceGauge + QuickStats
- **CR**: CR CONSOLE → Student tools + Class Representative Tasks
- **Teacher**: FACULTY CONSOLE → Faculty Tasks
- **ER / Lab Assistant**: ER CONSOLE → Lab management tasks
- **Super Admin**: ADMIN CONSOLE → Administration overview

Name is pulled from `user.full_name` from `/auth/me` and rendered in the dashboard hero.

### Frontend Component Boundary

`/dashboard` is a protected role resolver. It does not contain persona-specific UI itself:

| Role | Homepage component | Primary responsibility |
|------|--------------------|------------------------|
| Student | `features/dashboard/pages/home/StudentDashboardPage.tsx` | Routine, attendance, academic stats |
| CR | `features/dashboard/pages/home/CrDashboardPage.tsx` | Student view plus batch coordination |
| Teacher | `features/dashboard/pages/home/TeacherDashboardPage.tsx` | Faculty and course operations |
| ER | `features/dashboard/pages/home/ErDashboardPage.tsx` | Lab operations and equipment workflow |
| Super Admin | `features/dashboard/pages/home/AdminDashboardPage.tsx` | Approval, user and system oversight |

Shared identity and telemetry UI belongs to `DashboardHero.tsx`. New role-specific cards should be
added to the matching homepage component, not to a shared conditional dashboard.

## Navigation

`Sidebar` is role-aware. Items are filtered by `roles` property:

- Schedule, Attendance → Student, CR, Teacher
- Lab Management → Teacher, LAB_ASSISTANT, SUPER_ADMIN
- Room Booking → Student, CR, Teacher, SUPER_ADMIN
- Project Hub → Student, CR, Teacher
- Career Portal → Student, CR
- Admin Panel → SUPER_ADMIN only

Route guard `ProtectedRoute` also enforces role constraints.

## Account Creation

Registration form collects:
- `full_name` → displayed everywhere
- `identifier` / email / password
- Role selection: Student, CR, Teacher, ER

On successful registration:
- Students can login immediately
- CR / Teacher / ER accounts stay `is_active = false` until admin approves via `/auth/admin/approve/{user_id}`

## Data Flow

1. Login → `POST /auth/login` returns access token + user
2. Token stored in `localStorage` and Axios interceptor
3. `AuthProvider` loads user on mount via `GET /auth/me`
4. UI renders based on `user.role`

### Access Control Layers

1. `ProtectedRoute` blocks unauthenticated users and protects role-restricted frontend routes.
2. `Sidebar` filters navigation items by `UserRole`.
3. Backend `RequireRole` remains authoritative for API access; frontend visibility is only a UX layer.
4. CR and ER accounts are stored as inactive until admin approval, so they cannot authenticate before approval.

## Backend Changes

- `auth.schemas.StudentRegisterRequest.role` extended: `Literal["student","cr","er"]`
- `auth_service.register_student` maps `er` → `UserRole.LAB_ASSISTANT`
- Approval required for `CR` and `LAB_ASSISTANT`
- Authentication message updated for ER pending approval

## Future Enhancements

- Dedicated ER registration endpoint with lab-specific profile
- Audit log for role changes and approvals
- Fine grained permissions per endpoint
