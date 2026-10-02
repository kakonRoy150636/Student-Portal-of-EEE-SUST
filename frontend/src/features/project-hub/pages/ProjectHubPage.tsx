import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Github, Users } from 'lucide-react';
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
        description="Capstone and thesis projects registered for the department, newest first."
      />
      {isLoading && <PageSkeleton cards={0} rows={3} />}
      {isError && (
        <p className="rounded-xl border border-[var(--danger)] bg-[var(--danger-soft)] px-4 py-3 text-sm text-[var(--danger)]" role="alert">
          Could not load projects.
        </p>
      )}
      {!isLoading && !isError && rows.length === 0 && (
        <EmptyState
          title="No projects listed"
          description="No capstone or thesis projects have been registered yet."
        />
      )}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {rows.map((item) => (
          <article key={item.id} className="surface flex flex-col gap-3 p-5">
            <div className="flex items-start justify-between gap-3">
              <Badge variant="secondary" className="capitalize">{item.tier.replace(/_/g, ' ')}</Badge>
              {item.github_repo_url && (
                <a
                  href={item.github_repo_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-[var(--accent-bright)] underline-offset-2 hover:underline"
                >
                  <Github className="h-3.5 w-3.5" aria-hidden="true" /> Repository
                </a>
              )}
            </div>
            <h3 className="font-display text-base font-semibold text-[var(--text)]">{item.title}</h3>
            <p className="line-clamp-3 text-sm text-[var(--text-muted)]">{item.abstract}</p>
            <div className="mt-auto flex flex-wrap items-center gap-4 text-xs text-[var(--text-subtle)]">
              <span>{item.supervisor_name ?? 'Supervisor not assigned'}</span>
              <span className="inline-flex items-center gap-1">
                <Users className="h-3.5 w-3.5" aria-hidden="true" />
                {item.member_count} member{item.member_count === 1 ? '' : 's'}
              </span>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
