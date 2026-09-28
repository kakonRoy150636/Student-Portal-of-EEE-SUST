import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowRight,
  Award,
  CalendarDays,
  GraduationCap,
  Images,
  Newspaper,
  Users,
} from 'lucide-react';

import { alumniApi } from '@/features/alumni/api/alumniApi';
import { StatCard } from '@/components/shared/StatCard';
import { EmptyState } from '@/components/shared/EmptyState';

const fmtDate = (iso: string) =>
  new Date(iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });

const NAV_LINK =
  'inline-flex h-9 items-center rounded-md border border-[var(--border)] px-3 text-sm font-medium text-[var(--text)] transition-colors hover:bg-[var(--surface-muted)]';

/**
 * Public alumni landing page.
 *
 * Reachable without a session. Every number on it comes from
 * GET /api/v1/alumni/landing, which counts rows in the database -- so a fresh
 * install honestly reads 0 rather than showing invented figures, and a failed
 * request shows an error state instead of a stale total.
 */
export default function AlumniLandingPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['alumni', 'landing'],
    queryFn: async () => (await alumniApi.landing()).data,
    retry: false,
  });

  const stats = data?.stats;

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text)]">
      <header className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-5 py-5">
        <Link to="/alumni" className="flex items-center gap-2">
          <GraduationCap className="h-5 w-5 text-[var(--accent-bright)]" aria-hidden="true" />
          <span className="text-sm font-semibold">SUST EEE Alumni</span>
        </Link>
        <nav className="flex items-center gap-2" aria-label="Alumni">
          <Link to="/auth/login" className={NAV_LINK}>
            Sign in
          </Link>
          <Link
            to="/auth/register"
            className="inline-flex h-9 items-center rounded-md bg-[var(--primary)] px-3 text-sm font-semibold text-[var(--primary-fg)] transition-opacity hover:opacity-90"
          >
            Join the portal
          </Link>
        </nav>
      </header>

      <main className="mx-auto max-w-6xl space-y-10 px-5 pb-16">
        <section className="space-y-4 pt-6">
          <p className="kicker">Alumni Association</p>
          <h1 className="font-display max-w-3xl text-3xl font-bold leading-tight sm:text-4xl">
            One department, every graduating batch
          </h1>
          <p className="max-w-2xl text-sm leading-6 text-[var(--text-muted)] sm:text-base">
            The alumni area of the SUST EEE Student Portal: a verified directory, department events,
            scholarships and mentorship -- built on the same accounts students and faculty already use.
          </p>
          <div className="flex flex-wrap gap-3 pt-1">
            <Link
              to="/auth/login"
              className="inline-flex h-10 items-center gap-1.5 rounded-lg bg-[var(--primary)] px-4 text-sm font-semibold text-[var(--primary-fg)] transition-opacity hover:opacity-90"
            >
              Open the portal <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
            <Link
              to="/auth/register"
              className="inline-flex h-10 items-center rounded-lg border border-[var(--border)] px-4 text-sm font-semibold text-[var(--text)] transition-colors hover:bg-[var(--surface-muted)]"
            >
              Register as alumni
            </Link>
          </div>
        </section>

        <section aria-labelledby="alumni-stats" className="space-y-4">
          <h2 id="alumni-stats" className="kicker">
            Measured from the directory
          </h2>
          {isError && (
            <p
              className="rounded-xl border border-[var(--danger)] bg-[var(--danger-soft)] px-4 py-3 text-sm text-[var(--danger)]"
              role="alert"
            >
              Live alumni figures are unavailable right now. Nothing is shown rather than a stale number.
            </p>
          )}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5">
            <StatCard
              title="Verified alumni"
              tag="Members"
              value={isLoading || isError ? undefined : stats?.active_alumni ?? 0}
              loading={isLoading}
              icon={<Users className="h-5 w-5" />}
              subtitle="Approved by an administrator"
            />
            <StatCard
              title="Batches represented"
              tag="Batches"
              value={isLoading || isError ? undefined : stats?.batches ?? 0}
              loading={isLoading}
              icon={<GraduationCap className="h-5 w-5" />}
              subtitle="Distinct graduating years"
            />
            <StatCard
              title="Published events"
              tag="Events"
              value={isLoading || isError ? undefined : stats?.published_events ?? 0}
              loading={isLoading}
              icon={<CalendarDays className="h-5 w-5" />}
              subtitle="Reunions, webinars and meetups"
            />
            <StatCard
              title="Open scholarships"
              tag="Funding"
              value={isLoading || isError ? undefined : stats?.open_scholarships ?? 0}
              loading={isLoading}
              icon={<Award className="h-5 w-5" />}
              subtitle="Deadline still ahead"
            />
            <StatCard
              title="News posts"
              tag="News"
              value={isLoading || isError ? undefined : stats?.published_news ?? 0}
              loading={isLoading}
              icon={<Newspaper className="h-5 w-5" />}
              subtitle="Published department updates"
            />
          </div>
        </section>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <section aria-labelledby="alumni-news" className="space-y-3">
            <h2 id="alumni-news" className="font-display text-lg font-semibold">
              Latest news
            </h2>
            {isLoading && (
              <div className="h-32 animate-pulse rounded-xl bg-[var(--surface-muted)]" aria-hidden="true" />
            )}
            {!isLoading && (data?.news.length ?? 0) === 0 && (
              <EmptyState title="No news yet" description="Published alumni news will appear here." />
            )}
            <div className="space-y-3">
              {(data?.news ?? []).map((post) => (
                <article key={post.id} className="surface p-4">
                  <h3 className="text-sm font-semibold">{post.title}</h3>
                  {post.published_at && (
                    <p className="mt-1 text-xs text-[var(--text-subtle)]">{fmtDate(post.published_at)}</p>
                  )}
                  <p className="mt-2 line-clamp-3 text-sm leading-6 text-[var(--text-muted)]">{post.body}</p>
                </article>
              ))}
            </div>
          </section>

          <section aria-labelledby="alumni-events" className="space-y-3">
            <h2 id="alumni-events" className="font-display text-lg font-semibold">
              Upcoming events
            </h2>
            {isLoading && (
              <div className="h-32 animate-pulse rounded-xl bg-[var(--surface-muted)]" aria-hidden="true" />
            )}
            {!isLoading && (data?.events.length ?? 0) === 0 && (
              <EmptyState title="No published events" description="Event announcements will appear here." />
            )}
            <div className="space-y-3">
              {(data?.events ?? []).map((event) => (
                <article key={event.id} className="surface p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h3 className="text-sm font-semibold">{event.title}</h3>
                    <span className="rounded-md bg-[var(--accent-soft)] px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide text-[var(--accent-bright)]">
                      {event.event_type}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-[var(--text-subtle)]">
                    {fmtDate(event.starts_at)} · {event.venue}
                    {event.capacity !== null ? ` · ${event.attending_count}/${event.capacity} attending` : ` · ${event.attending_count} attending`}
                  </p>
                  <p className="mt-2 line-clamp-3 text-sm leading-6 text-[var(--text-muted)]">{event.description}</p>
                </article>
              ))}
            </div>
          </section>
        </div>

        <section aria-labelledby="alumni-scholarships" className="space-y-3">
          <h2 id="alumni-scholarships" className="font-display text-lg font-semibold">
            Open scholarships
          </h2>
          {isLoading && (
            <div className="h-28 animate-pulse rounded-xl bg-[var(--surface-muted)]" aria-hidden="true" />
          )}
          {!isLoading && (data?.scholarships.length ?? 0) === 0 && (
            <EmptyState
              title="No open scholarships"
              description="Funded opportunities still accepting applications will appear here."
            />
          )}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {(data?.scholarships ?? []).map((item) => (
              <article key={item.id} className="surface p-4">
                <div className="flex items-start justify-between gap-3">
                  <h3 className="text-sm font-semibold">{item.title}</h3>
                  {item.amount_bdt !== null && (
                    <span className="shrink-0 text-sm font-semibold tabular-nums text-[var(--accent-bright)]">
                      ৳{item.amount_bdt.toLocaleString()}
                    </span>
                  )}
                </div>
                <p className="mt-1 text-xs text-[var(--text-subtle)]">
                  Deadline {fmtDate(item.deadline)} · {item.application_target}
                </p>
                <p className="mt-2 line-clamp-3 text-sm leading-6 text-[var(--text-muted)]">{item.eligibility}</p>
              </article>
            ))}
          </div>
        </section>

        <section aria-labelledby="alumni-gallery" className="space-y-3">
          <h2 id="alumni-gallery" className="flex items-center gap-2 font-display text-lg font-semibold">
            <Images className="h-4 w-4 text-[var(--accent-bright)]" aria-hidden="true" /> Gallery
          </h2>
          {isLoading && (
            <div className="h-28 animate-pulse rounded-xl bg-[var(--surface-muted)]" aria-hidden="true" />
          )}
          {!isLoading && (data?.gallery.length ?? 0) === 0 && (
            <EmptyState title="No albums yet" description="Photos from alumni events will be published here." />
          )}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {(data?.gallery ?? []).map((album) => (
              <article key={album.id} className="surface p-4">
                <h3 className="text-sm font-semibold">{album.title}</h3>
                <p className="mt-1 text-xs text-[var(--text-subtle)]">{album.photos.length} photo(s)</p>
                {album.description && (
                  <p className="mt-2 line-clamp-2 text-sm leading-6 text-[var(--text-muted)]">{album.description}</p>
                )}
              </article>
            ))}
          </div>
        </section>
      </main>

      <footer className="border-t border-[var(--border)] px-5 py-6">
        <p className="mx-auto max-w-6xl text-xs text-[var(--text-subtle)]">
          Shahjalal University of Science &amp; Technology · Department of Electrical &amp; Electronic
          Engineering
        </p>
      </footer>
    </div>
  );
}
