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

  const pending = useQuery({
    queryKey: ['auth', 'pending-approvals'],
    queryFn: async () => (await authApi.pendingApprovals()).data as PendingUser[],
    retry: false,
  });

  const approve = useMutation({
    mutationFn: (id: string) => authApi.approveUser(id),
    onSuccess: async () => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: ['auth', 'pending-approvals'] }),
        qc.invalidateQueries({ queryKey: ['dashboard', 'summary'] }),
      ]);
    },
  });

  return (
    <div className="space-y-6">
      <DashboardHero
        roleName="SUPER ADMIN"
        unreadNotifications={a?.unread_notifications}
        greetingHint="Approvals, catalogue counts, and account health."
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          title="Registered users"
          value={isLoading ? undefined : a?.users_total ?? 0}
          icon={<Users className="h-5 w-5" />}
          subtitle={`${a?.users_active ?? 0} active account(s)`}
          tag="Accounts"
          loading={isLoading}
        />
        <StatCard
          title="Awaiting approval"
          value={isLoading ? undefined : a?.pending_approvals ?? 0}
          icon={<ShieldAlert className="h-5 w-5" />}
          subtitle="Inactive until an admin approves them"
          tag="Queue"
          tone={(a?.pending_approvals ?? 0) > 0 ? 'warn' : 'muted'}
          loading={isLoading}
        />
        <StatCard
          title="Verified alumni"
          value={isLoading ? undefined : a?.active_alumni ?? 0}
          icon={<UserCheck className="h-5 w-5" />}
          subtitle={`${a?.pending_alumni_claims ?? 0} claim(s) pending`}
          tag="Alumni"
          loading={isLoading}
        />
        <StatCard
          title="Courses / projects"
          value={isLoading ? undefined : `${a?.courses ?? 0} / ${a?.projects ?? 0}`}
          icon={<BookOpen className="h-5 w-5" />}
          subtitle="Catalogue and project hub totals"
          tag="Catalogue"
          loading={isLoading}
        />
      </div>

      <section className="surface p-5">
        <div className="flex items-center justify-between gap-3 border-b border-[var(--border)] pb-3">
          <h2 className="flex items-center gap-2 font-display text-base font-semibold text-[var(--text)]">
            <Users2 className="h-4 w-4 text-[var(--accent-bright)]" />
            Accounts awaiting approval
          </h2>
          <span className="text-xs text-[var(--text-subtle)]">
            {pending.isLoading ? 'Loading' : `${pending.data?.length ?? 0} pending`}
          </span>
        </div>

        {pending.isLoading ? (
          <div className="mt-4 space-y-2" aria-hidden="true">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-12 animate-pulse rounded-lg bg-[var(--surface-muted)]" />
            ))}
          </div>
        ) : !pending.data?.length ? (
          <p className="mt-4 text-sm text-[var(--text-muted)]">No accounts are waiting for approval.</p>
        ) : (
          <ul className="mt-4 space-y-2">
            {pending.data.map((u) => (
              <li
                key={u.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] p-3"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium text-[var(--text)]">{u.full_name}</p>
                  <p className="truncate text-xs text-[var(--text-muted)]">
                    {ROLE_LABEL[u.role] ?? u.role} · {u.identifier} · {u.email}
                  </p>
                </div>
                <Button size="sm" disabled={approve.isPending} onClick={() => approve.mutate(u.id)}>
                  {approve.isPending && approve.variables === u.id ? 'Approving…' : 'Approve'}
                </Button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="surface p-5">
        <h2 className="mb-3 flex items-center gap-2 font-display text-base font-semibold text-[var(--text)]">
          <FolderGit2 className="h-4 w-4 text-[var(--accent-bright)]" />
          Accounts by role
        </h2>
        <ul className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-3">
          {Object.entries(a?.users_by_role ?? {}).map(([role, count]) => (
            <li
              key={role}
              className="flex items-center justify-between gap-3 rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] px-3 py-2"
            >
              <span className="capitalize text-[var(--text-muted)]">{role.replace('_', ' ')}</span>
              <span className="font-semibold tabular-nums text-[var(--text)]">{count}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
};
