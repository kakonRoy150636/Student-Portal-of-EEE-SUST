import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/contexts/AuthContext';
import { ThemeSwitcher } from '@/components/shared/ThemeSwitcher';
import { filterNavSections, flattenNav, PRIMARY_MOBILE_PATHS } from '@/layouts/nav';

export const MobileDrawer = ({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) => {
  const { role } = useAuth();
  const sections = filterNavSections(role);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-40 md:hidden">
      <button
        type="button"
        className="absolute inset-0 bg-black/45"
        aria-label="Close navigation"
        onClick={onClose}
      />
      <aside className="absolute inset-y-0 left-0 flex w-[min(20rem,88vw)] flex-col bg-[var(--bg-elevated)] p-4 shadow-card">
        <div className="mb-4 flex items-center justify-between">
          <p className="font-display text-sm font-bold">SUST EEE</p>
          <button
            type="button"
            onClick={onClose}
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-[var(--border)] text-[var(--text-muted)]"
            aria-label="Close navigation"
            title="Close navigation"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <nav className="flex-1 space-y-5 overflow-y-auto" aria-label="Mobile">
          {sections.map((section) => (
            <div key={section.group} className="space-y-1">
              <p className="px-2 text-[11px] font-bold uppercase tracking-[0.16em] text-[var(--text-subtle)]">
                {section.group}
              </p>
              {section.items.map((item) => (
                <NavLink
                  key={item.name}
                  to={item.path}
                  end={item.path === '/dashboard'}
                  onClick={onClose}
                  className={({ isActive }) =>
                    cn(
                      'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium',
                      isActive
                        ? 'bg-[var(--accent-soft)] text-[var(--text)]'
                        : 'text-[var(--text-muted)] hover:bg-[var(--surface-muted)]',
                    )
                  }
                >
                  <item.icon className="h-4 w-4" />
                  {item.name}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
        <div className="pt-4">
          <ThemeSwitcher />
        </div>
      </aside>
    </div>
  );
};

export const MobileBottomNav = () => {
  const { role } = useAuth();
  const location = useLocation();
  const items = flattenNav(role)
    .filter((item) => (PRIMARY_MOBILE_PATHS as readonly string[]).includes(item.path))
    .filter((item, index, list) => list.findIndex((candidate) => candidate.path === item.path) === index)
    .slice(0, 4);

  if (items.length === 0) return null;

  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-4 border-t border-[var(--border)] bg-[var(--bg-elevated)]/95 px-2 py-1.5 backdrop-blur md:hidden"
      aria-label="Primary mobile"
    >
      {items.map((item) => {
        const active = location.pathname === item.path || (item.path !== '/dashboard' && location.pathname.startsWith(item.path));
        return (
          <NavLink
            key={item.path}
            to={item.path}
            className={cn(
              'flex flex-col items-center gap-1 rounded-lg px-2 py-1.5 text-[11px] font-medium',
              active ? 'text-[var(--accent-bright)]' : 'text-[var(--text-muted)]',
            )}
          >
            <item.icon className="h-4 w-4" />
            <span>{item.name}</span>
          </NavLink>
        );
      })}
    </nav>
  );
};

export const MobileNav = MobileDrawer;
