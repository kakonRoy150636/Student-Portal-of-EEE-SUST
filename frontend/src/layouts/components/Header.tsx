import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/contexts/AuthContext';
import { Avatar } from '@/components/shared/Avatar';
import { Bell, LogOut } from 'lucide-react';
import { api } from '@/lib/axios';

interface NotificationRow {
  id: number;
  title: string;
  body: string;
  is_read: boolean;
}

export const Header = () => {
  const { user, logout } = useAuth();

  /**
   * Replaces the old decorative bell, which had no click handler and an
   * always-animating unread dot -- so it asserted unread mail that may not
   * exist. The count is now the real number of unread rows for this user,
   * and the dot only appears when that count is greater than zero.
   *
   * The decorative "query database (Ctrl + K)" input was removed rather than
   * left in place: it had no handler, so it looked like a working search and
   * silently did nothing.
   */
  const notifications = useQuery({
    queryKey: ['notifications'],
    queryFn: async () => (await api.get<NotificationRow[]>('/notifications')).data,
    retry: false,
  });

  const rows = notifications.data ?? [];
  const unread = rows.filter((n) => !n.is_read).length;

  return (
    <header className="h-16 border-b border-slate-800/80 bg-[#070D18]/80 backdrop-blur-xl px-8 flex items-center justify-between sticky top-0 z-30 font-mono">
      <div className="flex items-center gap-3 min-w-0">
        <span className="text-[11px] uppercase tracking-widest text-slate-500 truncate">
          {user?.role ? user.role.replace('_', ' ').toUpperCase() : ''} CONSOLE
        </span>
      </div>

      <div className="flex items-center gap-5">
        <Link
          to="/notifications"
          className="relative flex h-9 w-9 items-center justify-center rounded-lg border border-slate-800 bg-slate-900/80 text-slate-300 hover:border-[var(--accent-edge)] transition-colors"
          aria-label={unread > 0 ? `Notifications, ${unread} unread` : 'Notifications'}
        >
          <Bell className="h-4 w-4" />
          {unread > 0 && (
            <span
              className="absolute -top-1.5 -right-1.5 min-w-[18px] h-[18px] px-1 rounded-full text-[10px] font-black flex items-center justify-center"
              style={{ backgroundColor: 'var(--accent)', color: '#050B14' }}
            >
              {unread > 99 ? '99+' : unread}
            </span>
          )}
        </Link>

        <div className="h-6 w-px bg-slate-800" />

        <div className="flex items-center gap-3">
          <Avatar
            avatarKey={user?.avatar_key}
            fullName={user?.full_name}
            className="h-9 w-9"
            alt={user?.full_name ? `${user.full_name}'s profile photo` : null}
          />
          <div className="hidden text-left sm:block">
            <p className="text-xs font-bold text-white uppercase">{user?.full_name || 'Guest'}</p>
            <p className="text-[10px] text-slate-500">{user?.identifier || '—'}</p>
          </div>
        </div>

        <button
          onClick={logout}
          title="Disconnect Session"
          aria-label="Disconnect Session"
          className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-800 bg-slate-900/80 text-slate-400 hover:border-[#FB7185]/40 hover:text-[#FB7185] transition-all"
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    </header>
  );
};

/** Small shared panel used by the header popover and the notifications route. */
export const NotificationList = ({ rows }: { rows: NotificationRow[] }) => {
  if (!rows.length) {
    return (
      <p className="px-4 py-6 text-center text-xs font-mono text-slate-500">
        No notifications for your account.
      </p>
    );
  }
  return (
    <ul className="divide-y divide-slate-800/80">
      {rows.map((n) => (
        <li key={n.id} className="px-4 py-3">
          <div className="flex items-start gap-2">
            {!n.is_read && (
              <span
                className="mt-1.5 h-1.5 w-1.5 rounded-full shrink-0"
                style={{ backgroundColor: 'var(--accent)' }}
                aria-label="Unread"
              />
            )}
            <div className="min-w-0">
              <p className="text-xs font-bold text-slate-100">{n.title}</p>
              <p className="text-[11px] font-mono text-slate-400 break-words">{n.body}</p>
            </div>
          </div>
        </li>
      ))}
    </ul>
  );
};
