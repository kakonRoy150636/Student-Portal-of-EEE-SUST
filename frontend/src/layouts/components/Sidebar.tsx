import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Calendar, Clock, CheckSquare,
  BookOpen, FolderGit2, Briefcase, Bot, FlaskConical, Crosshair
} from 'lucide-react';
import { cn } from '@/lib/utils';

export const Sidebar = () => {
  const navSections = [
    {
      group: '01 // TELEMETRY',
      items: [
        { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
        { name: 'Schedule', path: '/schedule', icon: Calendar },
        { name: 'Attendance', path: '/attendance', icon: CheckSquare },
      ]
    },
    {
      group: '02 // ACADEMICS',
      items: [
        { name: 'Lab Management', path: '/labs', icon: FlaskConical },
        { name: 'Room Booking', path: '/room-booking', icon: Clock },
        { name: 'Resources', path: '/resources', icon: BookOpen },
        { name: 'Project Hub', path: '/projects', icon: FolderGit2 },
      ]
    },
    {
      group: '03 // INTELLIGENCE',
      items: [
        { name: 'Career Portal', path: '/career', icon: Briefcase },
        { name: 'AI Assistant', path: '/ai', icon: Bot, isAi: true },
      ]
    }
  ];

  return (
    <aside className="w-64 border-r border-slate-800/80 bg-[#070D18]/90 backdrop-blur-xl p-4 flex flex-col justify-between hidden md:flex min-h-screen sticky top-0 z-20 font-mono">
      <div className="space-y-6">
        <div className="flex items-center gap-3 px-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-[#FF1E56]/50 bg-[#FF1E56]/10 text-[#FF1E56] shadow-[0_0_15px_rgba(255,30,86,0.2)]">
            <Crosshair className="h-5 w-5 animate-[spin_20s_linear_infinite]" />
          </div>
          <div>
            <span className="font-mono font-black text-sm tracking-wider text-white">
              SUST // EEE
            </span>
            <p className="text-[10px] font-mono text-cyan-400">COMMAND INTERFACE</p>
          </div>
        </div>

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
                        ? 'border-l-2 border-[#FF1E56] bg-gradient-to-r from-[#FF1E56]/15 to-transparent text-white font-bold'
                        : 'text-slate-400 hover:text-cyan-300 hover:bg-slate-900/60'
                    )
                  }
                >
                  <div className="flex items-center gap-3">
                    <i.icon className="h-4 w-4 transition-transform group-hover:scale-110 text-slate-400 group-hover:text-cyan-400" />
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

      <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3 font-mono text-[10px] space-y-1">
        <div className="flex items-center justify-between text-slate-400">
          <span>STATION:</span>
          <span className="text-[#00F0FF] font-bold">SUST IICT</span>
        </div>
        <div className="flex items-center justify-between text-slate-400">
          <span>UPLINK:</span>
          <span className="text-[#FF1E56] font-bold">ONLINE (99.4%)</span>
        </div>
      </div>
    </aside>
  );
};
