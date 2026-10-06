import {
  LayoutDashboard,
  Calendar,
  CheckSquare,
  BookOpen,
  FolderGit2,
  Briefcase,
  Bot,
  FlaskConical,
  Clock,
  Shield,
  GraduationCap,
  Bell,
} from 'lucide-react';
import { UserRole } from '@/types/auth';
import type { LucideIcon } from 'lucide-react';

export type NavItem = {
  name: string;
  path: string;
  icon: LucideIcon;
  hint?: string;
  roles?: UserRole[];
};

export type NavSection = {
  group: string;
  items: NavItem[];
};

export const NAV_SECTIONS: NavSection[] = [
  {
    group: 'Academic',
    items: [
      { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard, hint: 'Overview and today’s work' },
      { name: 'Schedule', path: '/schedule', icon: Calendar, hint: 'Class routine', roles: [UserRole.STUDENT, UserRole.CR, UserRole.TEACHER] },
      { name: 'Attendance', path: '/attendance', icon: CheckSquare, hint: 'Attendance records', roles: [UserRole.STUDENT, UserRole.CR, UserRole.TEACHER] },
      { name: 'Resources', path: '/resources', icon: BookOpen, hint: 'Notes and course files' },
      { name: 'Project Hub', path: '/projects', icon: FolderGit2, hint: 'Capstone projects', roles: [UserRole.STUDENT, UserRole.CR, UserRole.TEACHER] },
    ],
  },
  {
    group: 'Campus',
    items: [
      { name: 'Lab Management', path: '/labs', icon: FlaskConical, hint: 'Equipment inventory', roles: [UserRole.TEACHER, UserRole.LAB_ASSISTANT, UserRole.SUPER_ADMIN] },
      { name: 'Room Booking', path: '/room-booking', icon: Clock, hint: 'Reserve a room', roles: [UserRole.STUDENT, UserRole.CR, UserRole.TEACHER, UserRole.SUPER_ADMIN] },
    ],
  },
  {
    group: 'Career',
    items: [
      { name: 'Career Portal', path: '/career', icon: Briefcase, hint: 'Openings and internships', roles: [UserRole.STUDENT, UserRole.CR] },
      { name: 'Alumni Network', path: '/alumni', icon: GraduationCap, hint: 'Batches and career journeys' },
      { name: 'Edit Alumni Profile', path: '/alumni/me/edit', icon: GraduationCap, hint: 'Update your alumni journey', roles: [UserRole.ALUMNI] },
      { name: 'Alumni Events', path: '/alumni/events', icon: Calendar, hint: 'Reunions and webinars', roles: [UserRole.ALUMNI, UserRole.SUPER_ADMIN] },
    ],
  },
  {
    group: 'Tools',
    items: [
      { name: 'AI Assistant', path: '/ai', icon: Bot, hint: 'Academic questions' },
      { name: 'Notifications', path: '/notifications', icon: Bell, hint: 'Your notices' },
    ],
  },
  {
    group: 'Administration',
    items: [
      { name: 'Admin Panel', path: '/admin', icon: Shield, hint: 'Approvals and catalogue', roles: [UserRole.SUPER_ADMIN] },
    ],
  },
];

export const filterNavSections = (role: UserRole | null): NavSection[] =>
  NAV_SECTIONS
    .map((section) => ({
      ...section,
      items: section.items.filter((item) => !item.roles || (role && item.roles.includes(role))),
    }))
    .filter((section) => section.items.length > 0);

export const flattenNav = (role: UserRole | null): NavItem[] =>
  filterNavSections(role).flatMap((section) => section.items);

export const PRIMARY_MOBILE_PATHS = ['/dashboard', '/schedule', '/attendance', '/notifications'] as const;

export const ROLE_LABEL: Record<string, string> = {
  super_admin: 'Administrator',
  teacher: 'Teacher',
  cr: 'Class Representative',
  student: 'Student',
  lab_assistant: 'Lab Assistant',
  alumni: 'Alumni',
};
