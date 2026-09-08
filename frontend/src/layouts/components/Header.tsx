import React from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Bell, Search, LogOut, Terminal, Activity } from 'lucide-react';

export const Header = () => {
  const { user, logout } = useAuth();

  return (
    <header className="h-16 border-b border-slate-800/80 bg-[#070D18]/80 backdrop-blur-xl px-8 flex items-center justify-between sticky top-0 z-30 font-mono">
      {/* টার্মিনাল সার্চ বার */}
      <div className="flex items-center gap-3 flex-1 max-w-md">
        <div className="relative w-full">
          <Terminal className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-cyan-400" />
          <input
            type="text"
            placeholder="query database (Ctrl + K)..."
            className="w-full rounded-lg border border-slate-800 bg-slate-950/70 pl-9 pr-4 py-1.5 text-xs text-cyan-300 placeholder-slate-600 transition-all focus:border-[#FF1E56] focus:outline-none focus:ring-1 focus:ring-[#FF1E56]/30 font-mono"
          />
        </div>
      </div>

      {/* টেলিমেট্রি স্ট্যাটাস ও ইউজার কন্ট্রোলস */}
      <div className="flex items-center gap-5">
        <div className="hidden lg:flex items-center gap-2 text-[11px] text-slate-400 bg-slate-900/60 px-3 py-1 rounded border border-slate-800">
          <Activity className="h-3.5 w-3.5 text-[#00F0FF] animate-pulse" />
          <span>SYS.TELEMETRY: <strong className="text-[#00F0FF]">ACTIVE</strong></span>
        </div>

        {/* নোটিফিকেশন বেল */}
        <button className="relative flex h-9 w-9 items-center justify-center rounded-lg border border-slate-800 bg-slate-900/80 text-slate-300 hover:text-cyan-400 hover:border-cyan-500/40 transition-all">
          <Bell className="h-4 w-4" />
          <span className="absolute top-2 right-2 h-1.5 w-1.5 rounded-full bg-[#FF1E56] animate-ping" />
        </button>

        <div className="h-6 w-px bg-slate-800" />

        {/* ইউজার আইডেন্টিটি */}
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-[#00F0FF]/40 bg-[#00F0FF]/10 text-xs font-bold text-[#00F0FF]">
            {user?.full_name ? user.full_name.charAt(0) : 'K'}
          </div>
          <div className="hidden text-left sm:block">
            <p className="text-xs font-bold text-white uppercase">{user?.full_name || 'Kakon Chandro Roy'}</p>
            <p className="text-[10px] text-slate-500">ID: {user?.identifier || '2021338001'}</p>
          </div>
        </div>

        {/* সাইন আউট */}
        <button
          onClick={logout}
          title="Disconnect Session"
          className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-800 bg-slate-900/80 text-slate-400 hover:text-[#FF1E56] hover:border-[#FF1E56]/40 transition-all"
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    </header>
  );
};