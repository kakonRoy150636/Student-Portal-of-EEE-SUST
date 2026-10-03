import React from 'react';
import { getErrorMessage } from '@/lib/errors';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { CalendarDays, MapPin, Users } from 'lucide-react';

import { alumniApi } from '@/features/alumni/api/alumniApi';
import { PageHeader } from '@/components/shared/PageHeader';
import { EmptyState } from '@/components/shared/EmptyState';
import { PageSkeleton } from '@/components/shared/PageSkeleton';
import { Button } from '@/components/ui/button';

const fmtDateTime = (iso: string) =>
  new Date(iso).toLocaleString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

/**
 * Alumni events with RSVP.
 *
 * Capacity is whatever the server reports: `capacity === null` means the
 * event is unlimited and the count is shown without a ceiling. A full event
 * comes back as a 409 from the service and is surfaced verbatim, never
 * optimistically faked in the list.
 */
export default function AlumniEventsPage() {
  const qc = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: ['alumni', 'events'],
    queryFn: async () => (await alumniApi.events()).data,
    retry: false,
  });

  const rsvp = useMutation({
    mutationFn: (eventId: string) => alumniApi.rsvp(eventId, 'attending'),
    onSuccess: async () => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: ['alumni', 'events'] }),
        qc.invalidateQueries({ queryKey: ['alumni', 'dashboard'] }),
      ]);
    },
  });

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Alumni"
        title="Alumni events"
        description="Reunions, webinars and meetups published by the department. RSVPs are counted by the server."
      />

      {isLoading && <PageSkeleton cards={0} rows={4} />}

      {isError && (
        <p
          className="rounded-xl border border-[var(--danger)] bg-[var(--danger-soft)] px-4 py-3 text-sm text-[var(--danger)]"
          role="alert"
        >
          Events could not be loaded. Try again in a moment.
        </p>
      )}

      {!isLoading && !isError && (data?.length ?? 0) === 0 && (
        <EmptyState
          title="No published events"
          description="When the department publishes an alumni event it will appear here."
        />
      )}

      <div className="space-y-4">
        {(data ?? []).map((event) => {
          const full = event.capacity !== null && event.attending_count >= event.capacity;
          return (
            <article key={event.id} className="surface p-5">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="min-w-0 space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-base font-semibold">{event.title}</h2>
                    <span className="rounded-md bg-[var(--accent-soft)] px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide text-[var(--accent-bright)]">
                      {event.event_type}
                    </span>
                    {event.members_only && (
                      <span className="rounded-md bg-[var(--surface-muted)] px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide text-[var(--text-subtle)]">
                        Members only
                      </span>
                    )}
                  </div>
                  <p className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-[var(--text-subtle)]">
                    <span className="inline-flex items-center gap-1">
                      <CalendarDays className="h-3.5 w-3.5" aria-hidden="true" />
                      {fmtDateTime(event.starts_at)}
                    </span>
                    <span className="inline-flex items-center gap-1">
                      <MapPin className="h-3.5 w-3.5" aria-hidden="true" />
                      {event.venue}
                    </span>
                    <span className="inline-flex items-center gap-1">
                      <Users className="h-3.5 w-3.5" aria-hidden="true" />
                      {event.capacity !== null
                        ? `${event.attending_count} / ${event.capacity} attending`
                        : `${event.attending_count} attending`}
                    </span>
                  </p>
                  <p className="max-w-3xl text-sm leading-6 text-[var(--text-muted)]">{event.description}</p>
                </div>
                <Button
                  size="sm"
                  disabled={rsvp.isPending || full}
                  onClick={() => rsvp.mutate(event.id)}
                >
                  {full ? 'At capacity' : rsvp.variables === event.id && rsvp.isPending ? 'Saving…' : 'RSVP'}
                </Button>
              </div>
              {rsvp.isError && rsvp.variables === event.id && (
                <p role="alert" className="mt-3 text-xs text-[var(--danger)]">
                  {getErrorMessage(rsvp.error, 'Your RSVP could not be saved.')}
                </p>
              )}
            </article>
          );
        })}
      </div>
    </div>
  );
}
