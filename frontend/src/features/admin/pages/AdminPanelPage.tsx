import React from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { PageHeader } from '@/components/shared/PageHeader';
import { EmptyState } from '@/components/shared/EmptyState';
import { PageSkeleton } from '@/components/shared/PageSkeleton';
import { Button } from '@/components/ui/button';
import { authApi } from '@/features/auth/api/authApi';

interface PendingUser {
  id: string;
  full_name: string;
  email: string;
  identifier: string;
  role: string;
}

export default function AdminPanelPage() {
  const qc = useQueryClient();
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
      <PageHeader
        kicker="Administration"
        title="System administration"
        description="Approve pending teacher, CR, ER and alumni accounts, or manage course offerings and teacher assignments."
        action={<Link to="/admin/academic" className="inline-flex h-10 items-center rounded-lg border border-[var(--border)] px-4 py-2 text-sm font-semibold text-[var(--text)] hover:bg-[var(--surface-muted)]">Academic management</Link>}
      />
      {pending.isLoading && <PageSkeleton cards={0} rows={4} />}
      {pending.isError && (
        <p className="rounded-xl border border-[var(--danger)] bg-[var(--danger-soft)] px-4 py-3 text-sm text-[var(--danger)]" role="alert">
          Could not load the approval queue.
        </p>
      )}
      {!pending.isLoading && !pending.isError && (pending.data ?? []).length === 0 && (
        <EmptyState title="No pending approvals" description="Teacher and CR accounts remain inactive until approved." />
      )}
      <div className="space-y-3">
        {(pending.data ?? []).map((user) => (
          <article key={user.id} className="surface flex flex-wrap items-center justify-between gap-3 p-4">
            <div>
              <p className="text-sm font-semibold">{user.full_name}</p>
              <p className="text-xs text-[var(--text-muted)]">{user.identifier} · {user.email} · {user.role}</p>
            </div>
            <Button size="sm" disabled={approve.isPending} onClick={() => approve.mutate(user.id)}>
              {approve.isPending && approve.variables === user.id ? 'Approving…' : 'Approve'}
            </Button>
          </article>
        ))}
      </div>
    </div>
  );
}
