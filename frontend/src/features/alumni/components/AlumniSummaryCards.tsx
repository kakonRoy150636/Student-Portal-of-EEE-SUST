import React from 'react';
import { Globe2, GraduationCap, Users, BriefcaseBusiness } from 'lucide-react';
import { StatCard } from '@/components/shared/StatCard';
import type { AlumniBatchSummary } from '../api/alumniApi';

export function AlumniSummaryCards({ summary, loading }: { summary?: AlumniBatchSummary; loading?: boolean }) {
  const year = summary?.year ? `Batch ${summary.year}` : 'Selected batch';
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <StatCard title="Alumni" value={summary?.total} loading={loading} icon={<Users className="h-5 w-5" />} subtitle={year} />
      <StatCard title="Employed" value={summary?.employed} loading={loading} icon={<BriefcaseBusiness className="h-5 w-5" />} subtitle="Current employment records" />
      <StatCard title="Higher study" value={summary?.higher_study} loading={loading} icon={<GraduationCap className="h-5 w-5" />} subtitle="Current higher-study records" tone="muted" />
      <StatCard title="Abroad" value={summary?.abroad} loading={loading} icon={<Globe2 className="h-5 w-5" />} subtitle="Current records outside Bangladesh" tone="warn" />
    </div>
  );
}
