import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Calendar, Clock, CheckSquare, BookOpen, FolderGit2, Briefcase, Bot, FlaskConical } from 'lucide-react';
import { cn } from '@/lib/utils';

export const Sidebar = () => {
  const items = [
    { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
    { name: 'Schedule', path: '/schedule', icon: Calendar },
    { name: 'Room Booking', path: '/room-booking', icon: Clock },
    { name: 'Attendance', path: '/attendance', icon: CheckSquare },
    { name: 'Lab Management', path: '/labs', icon: FlaskConical },
    { name: 'Resources', path: '/resources', icon: BookOpen },
    { name: 'Project Hub', path: '/projects', icon: FolderGit2 },
    { name: 'Career Portal', path: '/career', icon: Briefcase },
    { name: 'AI Assistant', path: '/ai', icon: Bot }
  ];

  return (
    <aside className="w-64 border-r bg-white dark:bg-slate-900 p-4 space-y-4">
      <div className="font-bold text-lg text-emerald-600 px-2">SUST EEE Portal</div>
      <nav className="space-y-1">
        {items.map((i) => (
          <NavLink
            key={i.name}
            to={i.path}
            className={({ isActive }) =>
              cn("flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-lg",
                 isActive ? "bg-emerald-50 text-emerald-600" : "text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800")
            }
          >
            <i.icon className="h-4 w-4" />
            {i.name}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
};
