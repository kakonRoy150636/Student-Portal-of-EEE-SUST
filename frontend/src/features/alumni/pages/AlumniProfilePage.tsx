import React from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Mail, Phone, MapPin } from 'lucide-react';
import { PageHeader } from '@/components/shared/PageHeader';
import { PageSkeleton } from '@/components/shared/PageSkeleton';
import { EmptyState } from '@/components/shared/EmptyState';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { alumniApi } from '../api/alumniApi';
import { CareerTimeline } from '../components/CareerTimeline';

export default function AlumniProfilePage() {
  const { id = '' } = useParams();
  const query = useQuery({ queryKey: ['alumni', 'profile', id], queryFn: async () => (await alumniApi.profile(id)).data, retry: false });
  if (query.isLoading) return <PageSkeleton cards={2} rows={4} />;
  if (query.isError || !query.data) return <EmptyState title="Profile unavailable" description="This profile may be hidden or no longer active." />;
  const profile = query.data;
  return <div className="space-y-6">
    <PageHeader kicker="Alumni profile" title={profile.full_name} description={`${profile.department} · Batch ${profile.batch_year}`} action={<Link to="/alumni"><Button variant="outline" size="sm"><ArrowLeft className="h-4 w-4" /> Back to alumni</Button></Link>} />
    <div className="grid gap-6 lg:grid-cols-[1.1fr_1.9fr]">
      <section className="surface space-y-4 p-5">
        <div className="flex flex-wrap gap-2"><Badge>{profile.is_verified ? 'Verified alumni' : 'Alumni'}</Badge><Badge variant="secondary">Batch {profile.batch_year}</Badge></div>
        <p className="text-sm leading-6 text-[var(--text-muted)]">{profile.bio || 'This alumnus has not added a biography yet.'}</p>
        <div className="space-y-2 text-sm text-[var(--text-muted)]">
          {(profile.current_city || profile.current_country) && <p className="flex items-center gap-2"><MapPin className="h-4 w-4 text-[var(--accent-bright)]" />{[profile.current_city, profile.current_country].filter(Boolean).join(', ')}</p>}
          {profile.email && <p className="flex items-center gap-2"><Mail className="h-4 w-4 text-[var(--accent-bright)]" />{profile.email}</p>}
          {profile.phone && <p className="flex items-center gap-2"><Phone className="h-4 w-4 text-[var(--accent-bright)]" />{profile.phone}</p>}
        </div>
      </section>
      <section className="surface p-5"><p className="kicker mb-4">Career timeline</p><CareerTimeline employments={profile.employments} /></section>
    </div>
  </div>;
}
