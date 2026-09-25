import React from 'react';
import { DashboardHero } from './DashboardHero';
import { StatCard } from '@/components/shared/StatCard';
import { Users, UserCheck, ShieldAlert, BookOpen, FolderGit2, Users2 } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { authApi } from '@/features/auth/api/authApi';
import { useDashboardSummary } from '../../hooks/useDashboardSummary';
import { Button } from '@/components/ui/button';

interface PendingUser {
  id: string;
  full_name: string;
  email: string;
  identifier: string;
  role: string;
}

const ROLE_LABEL: Record<string, string> = {
  teacher: 'Teacher',
  cr: 'Class Representative',
  lab_assistant: 'Lab Assistant / ER',
  alumni: 'Alumni',
};

export const AdminDashboardPage = () => {
  const { data, isLoading } = useDashboardSummary();
  const qc = useQueryClient();
  const a = data?.admin;

  // The approval queue is fetched from the endpoint that already backs the
  // Admin Panel, so approving here and approving there are the same action.
  const pending = useQuery({
    queryKey: ['auth', 'pending-approvals'],
    queryFn: async () => (await authApi.pendingApprovals()).data as PendingUser[],
    retry: false,
  });

  const approve = useMutation({
    mutationFn: (id: string) => authApi.approveUser(id),
    onSuccess: async () => {
      // The user is now active, so both the queue and the counts are stale.
      await Promise.all([
        qc.invalidateQueries({ queryKey: ['auth', 'pending-approvals'] }),
        qc.invalidateQueries({ queryKey: ['dashboard', 'summary'] }),
      ]);
    },
  });

  return (
    <div className="space-y-6 relative z-10">
      <DashboardHero consoleName="00 // ADMIN CONSOLE" roleName="SUPER ADMIN" unreadNotifications={0} />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Registered Users"
          value={isLoading ? undefined : a?.users_total ?? 0}
          icon={<Users className="h-5 w-5" />}
          subtitle={`${a?.users_active ?? 0} active account(s)`}
          tag="MEASURED // ACCOUNTS"
          loading={isLoading}
        />
        <StatCard
          title="Awaiting Approval"
          value={isLoading ? undefined : a?.pending_approvals ?? 0}
          icon={<ShieldAlert className="h-5 w-5" />}
          subtitle="Inactive until an admin approves them"
          tag="MEASURED // QUEUE"
          tone={(a?.pending_approvals ?? 0) > 0 ? 'warn' : 'muted'}
          loading={isLoading}
        />
        <StatCard
          title="Verified Alumni"
          value={isLoading ? undefined : a?.active_alumni ?? 0}
          icon={<UserCheck className="h-5 w-5" />}
          subtitle={`${a?.pending_alumni_claims ?? 0} claim(s) pending`}
          tag="MEASURED // ALUMNI"
          loading={isLoading}
        />
        <StatCard
          title="Courses / Projects"
          value={isLoading ? undefined : `${a?.courses ?? 0} / ${a?.projects ?? 0}`}
          icon={<BookOpen className="h-5 w-5" />}
          subtitle="Catalogue and project hub totals"
          tag="MEASURED // CATALOGUE"
          loading={isLoading}
        />
      </div>

      <section className="hud-box corner-brackets rounded-xl p-5">
        <div className="flex items-center justify-between gap-3 pb-3 border-b border-slate-800/80">
          <h2 className="font-mono text-sm font-bold text-slate-300 flex items-center gap-2">
            <Users2 className="h-4 w-4" style={{ color: 'var(--accent-bright)' }} />
            Accounts awaiting approval
          </h2>
          <span className="text-[10px] font-mono text-slate-500">
            {pending.isLoading ? 'loading' : `${pending.data?.length ?? 0} pending`}
          </span>
        </div>

        {pending.isLoading ? (
          <div className="mt-4 space-y-2" aria-hidden="true">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-12 animate-pulse rounded bg-slate-900/60" />
            ))}
          </div>
        ) : !pending.data?.length ? (
          <p className="mt-4 text-xs font-mono text-slate-500">No accounts are waiting for approval.</p>
        ) : (
          <ul className="mt-4 space-y-2">
            {pending.data.map((u) => (
              <li
                key={u.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-800/80 bg-slate-900/40 p-3"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium text-slate-100">{u.full_name}</p>
                  <p className="text-[11px] font-mono text-slate-500 truncate">
                    {ROLE_LABEL[u.role] ?? u.role} · {u.identifier} · {u.email}
                  </p>
                </div>
                <Button
                  size="sm"
                  disabled={approve.isPending}
                  onClick={() => approve.mutate(u.id)}
                >
                  {approve.isPending && approve.variables === u.id ? 'Approving…' : 'Approve'}
                </Button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="hud-box corner-brackets rounded-xl p-5">
        <h2 className="font-mono text-sm font-bold text-slate-300 mb-3 flex items-center gap-2">
          <FolderGit2 className="h-4 w-4" style={{ color: 'var(--accent-bright)' }} />
          Accounts by role
        </h2>
        <ul className="text-xs font-mono text-slate-400 grid grid-cols-2 sm:grid-cols-3 gap-2">
          {Object.entries(a?.users_by_role ?? {}).map(([role, count]) => (
            <li
              key={role}
              className="flex items-center justify-between gap-3 rounded bg-slate-900/80 border border-slate-800 px-3 py-2"
            >
              <span className="capitalize">{role.replace('_', ' ')}</span>
              <span className="font-bold text-slate-200 tabular-nums">{count}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
};
