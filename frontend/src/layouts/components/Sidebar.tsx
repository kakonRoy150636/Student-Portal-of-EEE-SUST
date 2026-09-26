import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Calendar,
  Clock,
  CheckSquare,
  BookOpen,
  FolderGit2,
  Briefcase,
  Bot,
  FlaskConical,
  Shield,
  GraduationCap
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/contexts/AuthContext';
import { UserRole } from '@/types/auth';
import { DeptCrest } from '@/components/shared/DeptCrest';

type NavItem = { name: string; path: string; icon: React.ElementType; isAi?: boolean; roles?: UserRole[] };

export const Sidebar = () => {
  const { role } = useAuth();

  const allSections: { group: string; items: NavItem[] }[] = [
    {
      group: 'MAIN MENU',
      items: [
        { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
        { name: 'Schedule', path: '/schedule', icon: Calendar, roles: [UserRole.STUDENT, UserRole.CR, UserRole.TEACHER] },
        { name: 'Attendance', path: '/attendance', icon: CheckSquare, roles: [UserRole.STUDENT, UserRole.CR, UserRole.TEACHER] },
      ]
    },
    {
      group: 'ACADEMICS',
      items: [
        { name: 'Lab Management', path: '/labs', icon: FlaskConical, roles: [UserRole.TEACHER, UserRole.LAB_ASSISTANT, UserRole.SUPER_ADMIN] },
        { name: 'Room Booking', path: '/room-booking', icon: Clock, roles: [UserRole.STUDENT, UserRole.CR, UserRole.TEACHER, UserRole.SUPER_ADMIN] },
        { name: 'Resources', path: '/resources', icon: BookOpen },
        { name: 'Project Hub', path: '/projects', icon: FolderGit2, roles: [UserRole.STUDENT, UserRole.CR, UserRole.TEACHER] },
      ]
    },
    {
      group: 'TOOLS',
      items: [
        { name: 'Career Portal', path: '/career', icon: Briefcase, roles: [UserRole.STUDENT, UserRole.CR] },
        { name: 'AI Assistant', path: '/ai', icon: Bot, isAi: true },
      ]
    },
    {
      group: 'ALUMNI',
      items: [
        { name: 'Alumni Directory', path: '/dashboard', icon: GraduationCap, roles: [UserRole.ALUMNI] }
      ]
    },
    {
      group: 'ADMINISTRATION',
      items: [
        { name: 'Admin Panel', path: '/admin', icon: Shield, roles: [UserRole.SUPER_ADMIN] },
      ]
    }
  ];

  const navSections = allSections
    .map((sec) => ({
      ...sec,
      items: sec.items.filter((i) => !i.roles || (role && i.roles.includes(role)))
    }))
    .filter((sec) => sec.items.length > 0);

  return (
    <aside className="w-64 border-r border-slate-800/80 bg-[#0f2557]/95 p-4 flex flex-col justify-between hidden md:flex min-h-screen sticky top-0 z-20">
      <div className="space-y-6">
        {/* ব্র্যান্ডিং ও ডিপার্টমেন্ট ক্রেস্ট */}
        <div className="flex items-center gap-3 px-2">
          <div className="flex h-11 w-11 items-center justify-center rounded-lg border border-[var(--accent-edge)] bg-[var(--accent-soft)]">
            <DeptCrest className="h-8 w-8 opacity-95" variant="mono" />
          </div>
          <div>
            <span className="font-mono font-black text-sm tracking-wider text-white">
              SUST // EEE
            </span>
              <p className="text-[10px] font-medium tracking-wide text-amber-200/80">EEE STUDENT PORTAL</p>
          </div>
        </div>

        {/* সেকশন ভিত্তিক নেভিগেশন */}
        <nav className="space-y-5 font-mono">
          {navSections.map((sec) => (
            <div key={sec.group} className="space-y-1.5">
              <p className="px-3 text-[9px] font-bold tracking-widest text-slate-500 uppercase">
                {sec.group}
              </p>
              {sec.items.map((i) => (
                <NavLink
                  key={i.name}
                  to={i.path}
                  className={({ isActive }) =>
                    cn(
                      'group flex items-center justify-between px-3 py-2 text-xs font-semibold rounded-lg transition-all',
                      isActive
                        ? 'border-l-2 border-amber-300 bg-white/10 text-white font-semibold'
                        : 'text-slate-300 hover:text-white hover:bg-white/10'
                    )
                  }
                >
                  <div className="flex items-center gap-3">
                    <i.icon className="h-4 w-4 transition-transform group-hover:scale-105 text-slate-300 group-hover:text-amber-200" />
                    <span>{i.name}</span>
                  </div>
                  {i.isAi && (
                    <span className="px-1.5 py-0.2 rounded text-[9px] font-mono font-bold bg-cyan-500/20 text-cyan-400 border border-cyan-500/40">
                      RAG
                    </span>
                  )}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
      </div>

      {/* Signed-in identity, not invented telemetry. The previous footer
          claimed "UPLINK: ONLINE (99.4%)" and "STATION: SUST IICT" as
          literals -- figures no code measured. */}
      <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3 font-mono text-[10px] space-y-1">
        <div className="flex items-center justify-between text-slate-400 gap-2">
          <span>SESSION:</span>
          <span className="font-bold" style={{ color: 'var(--accent-bright)' }}>
            {role ? role.replace('_', ' ').toUpperCase() : '—'}
          </span>
        </div>
        <div className="flex items-center justify-between text-slate-400 gap-2">
          <span>PORTAL:</span>
          <span className="text-slate-300 font-bold">SUST IICT</span>
        </div>
      </div>
    </aside>
  );
};