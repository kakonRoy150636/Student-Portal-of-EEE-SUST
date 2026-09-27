import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { PageHeader } from '@/components/shared/PageHeader';
import { EmptyState } from '@/components/shared/EmptyState';
import { PageSkeleton } from '@/components/shared/PageSkeleton';
import { Badge } from '@/components/ui/badge';
import { projectApi } from '../api/projectApi';

export default function ProjectHubPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['projects'],
    queryFn: async () => (await projectApi.getProjects()).data,
    retry: false,
  });
  const rows = data ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Academic"
        title="Project hub"
        description="Capstone and thesis projects currently listed for the department."
      />
      {isLoading && <PageSkeleton cards={0} rows={3} />}
      {isError && (
        <p className="rounded-xl border border-[var(--danger)] bg-[var(--danger-soft)] px-4 py-3 text-sm text-[var(--danger)]" role="alert">
          Could not load projects.
        </p>
      )}
      {!isLoading && !isError && rows.length === 0 && (
        <EmptyState title="No projects listed" description="No capstone or thesis projects are published yet." />
      )}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {rows.map((item) => (
          <article key={`${item.title}-${item.tier}`} className="surface p-5">
            <Badge variant="secondary" className="capitalize">{item.tier.replace(/_/g, ' ')}</Badge>
            <h3 className="mt-3 font-display text-base font-semibold text-[var(--text)]">{item.title}</h3>
          </article>
        ))}
      </div>
    </div>
  );
}
