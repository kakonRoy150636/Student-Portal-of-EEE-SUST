import React from 'react';
import { NavLink } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { useAuth } from '@/contexts/AuthContext';
import { DeptCrest } from '@/components/shared/DeptCrest';
import { filterNavSections, ROLE_LABEL } from '@/layouts/nav';

export const Sidebar = () => {
  const { role, user } = useAuth();
  const navSections = filterNavSections(role);

  return (
    <aside className="sticky top-0 z-20 hidden h-screen w-64 shrink-0 flex-col border-r border-[var(--border)] bg-[var(--bg-elevated)]/95 p-4 backdrop-blur md:flex">
      <div className="flex items-center gap-3 px-2 pb-5">
        <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-[var(--accent-edge)] bg-[var(--accent-soft)]">
          <DeptCrest className="h-8 w-8 opacity-95" variant="mono" />
        </div>
        <div>
          <p className="font-display text-sm font-bold tracking-tight text-[var(--text)]">SUST EEE</p>
          <p className="text-xs text-[var(--text-muted)]">Student Portal</p>
        </div>
      </div>

      <nav className="flex-1 space-y-6 overflow-y-auto pr-1" aria-label="Primary">
        {navSections.map((section) => (
          <div key={section.group} className="space-y-1">
            <p className="px-3 text-[11px] font-bold uppercase tracking-[0.16em] text-[var(--text-subtle)]">
              {section.group}
            </p>
            {section.items.map((item) => (
              <NavLink
                key={item.name}
                to={item.path}
                end={item.path === '/dashboard'}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-[var(--accent-soft)] text-[var(--text)] shadow-[inset_3px_0_0_var(--accent)]'
                      : 'text-[var(--text-muted)] hover:bg-[var(--surface-muted)] hover:text-[var(--text)]',
                  )
                }
              >
                <item.icon className="h-4 w-4 shrink-0" />
                <span>{item.name}</span>
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      <div className="mt-4 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3">
        <p className="text-xs font-semibold text-[var(--text)]">{user?.full_name || 'Signed in'}</p>
        <p className="mt-0.5 text-xs text-[var(--text-muted)]">
          {role ? ROLE_LABEL[role] ?? role : '—'}
        </p>
      </div>
    </aside>
  );
};
