import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { DashboardHero } from './DashboardHero';
import { StatCard } from '@/components/shared/StatCard';
import { UserCheck, Users2, Handshake, Briefcase } from 'lucide-react';
import { useDashboardSummary } from '../../hooks/useDashboardSummary';
import { alumniApi } from '@/features/alumni/api/alumniApi';
import { Avatar } from '@/components/shared/Avatar';
import { useAuth } from '@/contexts/AuthContext';

const STATUS_STYLE: Record<string, string> = {
  active: 'var(--success)',
  pending: 'var(--warn)',
  rejected: 'var(--danger)',
  expired: 'var(--text-muted)',
};

export const AlumniDashboardPage = () => {
  const { user } = useAuth();
  const { data, isLoading } = useDashboardSummary();
  const a = data?.alumni;

  const profile = useQuery({
    queryKey: ['alumni', 'me'],
    queryFn: async () => (await alumniApi.getMyProfile()).data,
    retry: false,
  });

  const p = profile.data;

  return (
    <div className="space-y-6">
      <DashboardHero
        roleName="ALUMNI"
        unreadNotifications={a?.unread_notifications}
        greetingHint="Directory membership, mentorship, and career openings."
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          title="Directory members"
          value={isLoading ? undefined : a?.visible_alumni ?? 0}
          icon={<Users2 className="h-5 w-5" />}
          subtitle="Verified and opted into the directory"
          tag="Directory"
          loading={isLoading}
        />
        <StatCard
          title="Verified alumni"
          value={isLoading ? undefined : a?.active_alumni ?? 0}
          icon={<UserCheck className="h-5 w-5" />}
          subtitle="Membership approved by an admin"
          tag="Members"
          loading={isLoading}
        />
        <StatCard
          title="Mentorship links"
          value={isLoading ? undefined : a?.mentorship_pairs ?? 0}
          icon={<Handshake className="h-5 w-5" />}
          subtitle="Active or requested pairs"
          tag="Mentorship"
          loading={isLoading}
        />
        <StatCard
          title="Career openings"
          value={isLoading ? undefined : a?.career_opportunities ?? 0}
          icon={<Briefcase className="h-5 w-5" />}
          subtitle="Verified listings on the portal"
          tag="Career"
          loading={isLoading}
        />
      </div>

      <section className="surface p-5">
        <h2 className="mb-4 font-display text-base font-semibold text-[var(--text)]">Your membership</h2>
        {profile.isLoading ? (
          <div className="h-16 animate-pulse rounded-lg bg-[var(--surface-muted)]" aria-hidden="true" />
        ) : !p ? (
          <p className="text-sm text-[var(--text-muted)]">
            No alumni profile is linked to <span className="text-[var(--text)]">{user?.identifier}</span> yet.
            Submit a batch and department claim to be verified.
          </p>
        ) : (
          <div className="flex flex-wrap items-start gap-4">
            <Avatar
              avatarKey={user?.avatar_key}
              fullName={user?.full_name}
              className="h-12 w-12"
              alt={`${user?.full_name ?? 'Alumnus'}'s profile photo`}
            />
            <dl className="grid flex-1 grid-cols-2 gap-3 text-sm sm:grid-cols-3">
              <div>
                <dt className="text-xs text-[var(--text-subtle)]">Batch</dt>
                <dd className="font-semibold text-[var(--text)]">{p.batch_year}</dd>
              </div>
              <div>
                <dt className="text-xs text-[var(--text-subtle)]">Department</dt>
                <dd className="font-semibold text-[var(--text)]">{p.department}</dd>
              </div>
              <div>
                <dt className="text-xs text-[var(--text-subtle)]">Status</dt>
                <dd className="font-semibold uppercase" style={{ color: STATUS_STYLE[p.membership_status] ?? 'var(--text-muted)' }}>
                  {p.membership_status}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-[var(--text-subtle)]">Company</dt>
                <dd className="font-semibold text-[var(--text)]">{p.current_company || '—'}</dd>
              </div>
              <div>
                <dt className="text-xs text-[var(--text-subtle)]">Designation</dt>
                <dd className="font-semibold text-[var(--text)]">{p.designation || '—'}</dd>
              </div>
              <div>
                <dt className="text-xs text-[var(--text-subtle)]">In directory</dt>
                <dd className="font-semibold text-[var(--text)]">{p.is_visible ? 'Visible' : 'Hidden'}</dd>
              </div>
            </dl>
          </div>
        )}
      </section>
    </div>
  );
};
