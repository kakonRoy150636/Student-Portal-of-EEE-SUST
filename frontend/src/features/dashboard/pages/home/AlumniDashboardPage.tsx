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
  active: 'var(--accent-bright)',
  pending: '#FB7185',
  rejected: '#FB7185',
  expired: '#94A3B8',
};

export const AlumniDashboardPage = () => {
  const { user } = useAuth();
  const { data, isLoading } = useDashboardSummary();
  const a = data?.alumni;

  // Reuses the existing GET /alumni/me, which returns 200 + null when the
  // signed-in alumnus has not submitted a batch/department claim yet.
  const profile = useQuery({
    queryKey: ['alumni', 'me'],
    queryFn: async () => (await alumniApi.getMyProfile()).data,
    retry: false,
  });

  const p = profile.data;

  return (
    <div className="space-y-6 relative z-10">
      <DashboardHero
        consoleName="05 // ALUMNI CONSOLE"
        roleName="ALUMNI"
        unreadNotifications={a?.unread_notifications}
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Directory Members"
          value={isLoading ? undefined : a?.visible_alumni ?? 0}
          icon={<Users2 className="h-5 w-5" />}
          subtitle="Verified and opted into the directory"
          tag="MEASURED // DIRECTORY"
          loading={isLoading}
        />
        <StatCard
          title="Verified Alumni"
          value={isLoading ? undefined : a?.active_alumni ?? 0}
          icon={<UserCheck className="h-5 w-5" />}
          subtitle="Membership approved by an admin"
          tag="MEASURED // MEMBERS"
          loading={isLoading}
        />
        <StatCard
          title="Mentorship Links"
          value={isLoading ? undefined : a?.mentorship_pairs ?? 0}
          icon={<Handshake className="h-5 w-5" />}
          subtitle="Active or requested pairs"
          tag="MEASURED // MENTORSHIP"
          loading={isLoading}
        />
        <StatCard
          title="Career Openings"
          value={isLoading ? undefined : a?.career_opportunities ?? 0}
          icon={<Briefcase className="h-5 w-5" />}
          subtitle="Verified listings on the portal"
          tag="MEASURED // CAREER"
          loading={isLoading}
        />
      </div>

      <section className="hud-box corner-brackets rounded-xl p-5">
        <h2 className="font-mono text-sm font-bold text-slate-300 mb-4">Your membership</h2>

        {profile.isLoading ? (
          <div className="h-16 animate-pulse rounded bg-slate-900/60" aria-hidden="true" />
        ) : !p ? (
          <p className="text-xs font-mono text-slate-400">
            No alumni profile is linked to <span className="text-slate-200">{user?.identifier}</span> yet.
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
            <dl className="grid flex-1 grid-cols-2 sm:grid-cols-3 gap-3 text-xs font-mono">
              <div>
                <dt className="text-slate-500">Batch</dt>
                <dd className="font-bold text-slate-100">{p.batch_year}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Department</dt>
                <dd className="font-bold text-slate-100">{p.department}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Status</dt>
                <dd className="font-bold uppercase" style={{ color: STATUS_STYLE[p.membership_status] ?? '#94A3B8' }}>
                  {p.membership_status}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">Company</dt>
                <dd className="font-bold text-slate-100">{p.current_company || '—'}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Designation</dt>
                <dd className="font-bold text-slate-100">{p.designation || '—'}</dd>
              </div>
              <div>
                <dt className="text-slate-500">In directory</dt>
                <dd className="font-bold text-slate-100">{p.is_visible ? 'Visible' : 'Hidden'}</dd>
              </div>
            </dl>
          </div>
        )}
      </section>
    </div>
  );
};
