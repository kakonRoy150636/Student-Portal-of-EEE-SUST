import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { PageHeader } from '@/components/shared/PageHeader';
import { EmptyState } from '@/components/shared/EmptyState';
import { PageSkeleton } from '@/components/shared/PageSkeleton';
import { careerApi } from '../api/careerApi';

export default function CareerPortalPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['career', 'opportunities'],
    queryFn: async () => (await careerApi.getOpportunities()).data,
    retry: false,
  });
  const rows = data ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Career"
        title="Career portal"
        description="Openings currently listed for students. Only published fields are shown."
      />
      {isLoading && <PageSkeleton cards={0} rows={3} />}
      {isError && (
        <p className="rounded-xl border border-[var(--danger)] bg-[var(--danger-soft)] px-4 py-3 text-sm text-[var(--danger)]" role="alert">
          Could not load openings.
        </p>
      )}
      {!isLoading && !isError && rows.length === 0 && (
        <EmptyState title="No openings listed" description="There are no published career circulars right now." />
      )}
      <div className="space-y-3">
        {rows.map((item) => (
          <article key={`${item.title}-${item.organization}`} className="surface flex flex-col gap-2 p-5 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h3 className="text-sm font-semibold text-[var(--text)]">{item.title}</h3>
              <p className="mt-1 text-sm text-[var(--text-muted)]">{item.organization}</p>
            </div>
            <p className="text-sm text-[var(--text-muted)]">Deadline {item.deadline}</p>
          </article>
        ))}
      </div>
    </div>
  );
}
