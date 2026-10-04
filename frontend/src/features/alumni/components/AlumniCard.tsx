import React from 'react';
import { Link } from 'react-router-dom';
import { MapPin, BriefcaseBusiness, ExternalLink } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import type { AlumniDirectoryItem } from '../api/alumniApi';

export function AlumniCard({ alumni }: { alumni: AlumniDirectoryItem }) {
  const job = alumni.current_employment;
  const location = [job?.city ?? alumni.current_city, job?.country ?? alumni.current_country].filter(Boolean).join(', ');
  return (
    <article className="surface flex h-full flex-col justify-between gap-4 p-5">
      <div>
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="font-display text-lg font-semibold text-[var(--text)]">{alumni.full_name}</p>
            <p className="mt-1 text-xs text-[var(--text-muted)]">EEE · Batch {alumni.batch_year}</p>
          </div>
          <Badge variant="outline">{alumni.department}</Badge>
        </div>
        <div className="mt-4 space-y-2 text-sm text-[var(--text-muted)]">
          <p className="flex items-center gap-2"><BriefcaseBusiness className="h-4 w-4 text-[var(--accent-bright)]" />
            {job ? `${job.position} · ${job.organization}` : 'Career details not published'}
          </p>
          <p className="flex items-center gap-2"><MapPin className="h-4 w-4 text-[var(--accent-bright)]" />{location || 'Location not published'}</p>
        </div>
      </div>
      <div className="flex items-center justify-between gap-2">
        <Link to={`/alumni/profile/${alumni.id}`} className="text-sm font-semibold text-[var(--accent-bright)] hover:underline">View profile</Link>
        {alumni.linkedin_url && <a href={alumni.linkedin_url} target="_blank" rel="noopener noreferrer" aria-label={`${alumni.full_name} on LinkedIn`} className="text-[var(--text-muted)] hover:text-[var(--text)]"><ExternalLink className="h-4 w-4" /></a>}
      </div>
    </article>
  );
}
