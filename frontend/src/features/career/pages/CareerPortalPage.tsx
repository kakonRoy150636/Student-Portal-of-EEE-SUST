import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { CalendarClock, MapPin } from 'lucide-react';
import { PageHeader } from '@/components/shared/PageHeader';
import { EmptyState } from '@/components/shared/EmptyState';
import { PageSkeleton } from '@/components/shared/PageSkeleton';
import { Badge } from '@/components/ui/badge';
import { careerApi } from '../api/careerApi';

const formatDeadline = (value: string) => {
  const parsed = new Date(`${value}T23:59:59`);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString(undefined, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
};

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
        description="Verified openings with an open deadline, most urgent first."
      />
      {isLoading && <PageSkeleton cards={0} rows={3} />}
      {isError && (
        <p className="rounded-xl border border-[var(--danger)] bg-[var(--danger-soft)] px-4 py-3 text-sm text-[var(--danger)]" role="alert">
          Could not load openings.
        </p>
      )}
      {!isLoading && !isError && rows.length === 0 && (
        <EmptyState
          title="No openings listed"
          description="There are no verified, unexpired career circulars right now."
        />
      )}
      <div className="space-y-3">
        {rows.map((item) => (
          <article key={item.id} className="surface space-y-3 p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-[var(--text)]">{item.title}</h3>
                <p className="mt-1 text-sm text-[var(--text-muted)]">{item.organization_name}</p>
              </div>
              <Badge variant="secondary" className="capitalize">{item.type.replace(/_/g, ' ')}</Badge>
            </div>
            {item.description && (
              <p className="text-sm text-[var(--text-muted)]">{item.description}</p>
            )}
            <div className="flex flex-wrap items-center gap-4 text-xs text-[var(--text-subtle)]">
              <span className="inline-flex items-center gap-1">
                <CalendarClock className="h-3.5 w-3.5" aria-hidden="true" />
                Deadline {formatDeadline(item.application_deadline)}
              </span>
              {item.location && (
                <span className="inline-flex items-center gap-1">
                  <MapPin className="h-3.5 w-3.5" aria-hidden="true" />
                  {item.location}
                </span>
              )}
            </div>
            {item.tags.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {item.tags.map((tag) => (
                  <Badge key={tag} variant="outline">{tag}</Badge>
                ))}
              </div>
            )}
          </article>
        ))}
      </div>
    </div>
  );
}
