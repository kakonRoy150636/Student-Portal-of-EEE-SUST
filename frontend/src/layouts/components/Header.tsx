import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Bell, LogOut, Menu, Search } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { Avatar } from '@/components/shared/Avatar';
import { ThemeSwitcher } from '@/components/shared/ThemeSwitcher';
import { useNotifications, type NotificationRow } from '@/features/notifications/NotificationContext';
import { pushUrl } from '@/lib/pushUrl';
import { CommandSearch } from './CommandSearch';
import { ROLE_LABEL } from '@/layouts/nav';

export type { NotificationRow };

export const Header = ({ onOpenMobileNav }: { onOpenMobileNav?: () => void }) => {
  const { user, logout } = useAuth();
  const [searchOpen, setSearchOpen] = useState(false);

  const { unread_count: unread } = useNotifications();

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setSearchOpen(true);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-3 border-b border-[var(--border)] bg-[var(--bg)]/85 px-4 backdrop-blur-xl sm:px-6">
      <div className="flex min-w-0 items-center gap-2">
        <button
          type="button"
          className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[var(--text-muted)] md:hidden"
          onClick={onOpenMobileNav}
          aria-label="Open navigation"
          title="Open navigation"
        >
          <Menu className="h-4 w-4" />
        </button>
        <div className="hidden min-w-0 sm:block">
          <p className="truncate text-sm font-semibold text-[var(--text)]">
            {user?.role ? ROLE_LABEL[user.role] ?? user.role : 'Portal'}
          </p>
          <p className="truncate text-xs text-[var(--text-muted)]">{user?.identifier || 'SUST EEE'}</p>
        </div>
      </div>

      <div className="flex items-center gap-2 sm:gap-3">
        <button
          type="button"
          onClick={() => setSearchOpen(true)}
          className="hidden h-10 items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 text-sm text-[var(--text-muted)] hover:text-[var(--text)] md:inline-flex"
          aria-label="Search pages"
          title="Search pages (Ctrl+K)"
        >
          <Search className="h-4 w-4" />
          <span>Search</span>
          <kbd className="rounded border border-[var(--border)] px-1.5 py-0.5 text-[10px] text-[var(--text-subtle)]">
            Ctrl K
          </kbd>
        </button>
        <button
          type="button"
          onClick={() => setSearchOpen(true)}
          className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[var(--text-muted)] md:hidden"
          aria-label="Search pages"
          title="Search pages"
        >
          <Search className="h-4 w-4" />
        </button>

        <ThemeSwitcher className="hidden lg:inline-flex" />

        <Link
          to="/notifications"
          className="relative inline-flex h-10 w-10 items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[var(--text-muted)] hover:text-[var(--text)]"
          aria-label={unread > 0 ? `Notifications, ${unread} unread` : 'Notifications'}
          title="Notifications"
        >
          <Bell className="h-4 w-4" />
          {unread > 0 && (
            <span aria-live="polite" className="absolute -right-1.5 -top-1.5 inline-flex min-w-[18px] items-center justify-center rounded-full bg-[var(--accent)] px-1 text-[10px] font-bold text-[var(--primary-fg)]">
              {unread > 99 ? '99+' : unread}
            </span>
          )}
        </Link>

        <div className="hidden items-center gap-2 sm:flex">
          <Avatar
            avatarKey={user?.avatar_key}
            fullName={user?.full_name}
            className="h-9 w-9"
            alt={user?.full_name ? `${user.full_name}'s profile photo` : null}
          />
          <div className="hidden text-left lg:block">
            <p className="text-sm font-semibold text-[var(--text)]">{user?.full_name || 'Guest'}</p>
            <p className="text-xs text-[var(--text-muted)]">{user?.identifier || '—'}</p>
          </div>
        </div>

        <button
          type="button"
          onClick={logout}
          title="Sign out"
          aria-label="Sign out"
          className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[var(--text-muted)] hover:border-[var(--danger)] hover:text-[var(--danger)]"
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>

      <CommandSearch open={searchOpen} onOpenChange={setSearchOpen} />
    </header>
  );
};

/** Shared list used by the notifications route. */
export const NotificationList = ({ rows }: { rows: NotificationRow[] }) => {
  const { markRead, marking, markError } = useNotifications();
  if (!rows.length) {
    return <p className="px-4 py-8 text-center text-sm text-[var(--text-muted)]">No notifications for your account.</p>;
  }
  return (
    <div>
    {markError && <p role="alert" className="p-3 text-[var(--danger)]">Could not mark notifications as read. Try again.</p>}
    <ul className="divide-y divide-[var(--border)]">
      {rows.map((n) => (
        <li key={n.id} className="px-4 py-3">
          <div className="flex items-start gap-2">
            {!n.is_read && (
              <span
                className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--accent)]"
                aria-label="Unread"
              />
            )}
            <div className="min-w-0">
              <p className="text-sm font-semibold text-[var(--text)]">{n.title}</p>
              <p className="break-words text-sm text-[var(--text-muted)]">{n.body}</p>
              <div className="mt-2 flex gap-3 text-sm">
                <Link className="underline" to={pushUrl(n.data_payload?.url, window.location.origin)} onClick={() => markRead(n.id)}>Open</Link>
                {!n.is_read && <button className="underline" disabled={marking} onClick={() => markRead(n.id)}>Mark as read</button>}
              </div>
            </div>
          </div>
        </li>
      ))}
    </ul>
    </div>
  );
};
