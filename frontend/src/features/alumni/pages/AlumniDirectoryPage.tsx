import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ExternalLink, Search } from 'lucide-react';

import { alumniApi, type DirectoryQuery } from '@/features/alumni/api/alumniApi';
import { PageHeader } from '@/components/shared/PageHeader';
import { EmptyState } from '@/components/shared/EmptyState';
import { PageSkeleton } from '@/components/shared/PageSkeleton';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

/**
 * Verified-alumni directory.
 *
 * The backend only returns rows with `is_visible = true` and
 * `membership_status = 'active'`, so an unverified or opted-out claim can
 * never appear here even if the id is known.
 */
export default function AlumniDirectoryPage() {
  const [query, setQuery] = useState<DirectoryQuery>({});
  const [q, setQ] = useState('');
  const [batch, setBatch] = useState('');
  const [industry, setIndustry] = useState('');

  const { data, isLoading, isError, isFetching } = useQuery({
    queryKey: ['alumni', 'directory', query],
    queryFn: async () => (await alumniApi.directory(query)).data,
    retry: false,
  });

  const apply = (event: React.FormEvent) => {
    event.preventDefault();
    const batchYear = batch.trim() === '' ? undefined : Number(batch.trim());
    setQuery({
      q: q.trim() === '' ? undefined : q.trim(),
      batch_year: batchYear !== undefined && Number.isFinite(batchYear) ? batchYear : undefined,
      industry: industry.trim() === '' ? undefined : industry.trim(),
    });
  };

  const reset = () => {
    setQ('');
    setBatch('');
    setIndustry('');
    setQuery({});
  };

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Alumni"
        title="Alumni directory"
        description="Verified alumni who opted into the directory. Pending or hidden claims are never listed."
      />

      <form onSubmit={apply} className="surface flex flex-wrap items-end gap-3 p-4">
        <div className="min-w-[12rem] flex-1">
          <label htmlFor="dir-q" className="mb-1 block text-xs text-[var(--text-subtle)]">
            Search
          </label>
          <Input
            id="dir-q"
            value={q}
            onChange={(event) => setQ(event.target.value)}
            placeholder="Name, company, or industry"
          />
        </div>
        <div className="w-32">
          <label htmlFor="dir-batch" className="mb-1 block text-xs text-[var(--text-subtle)]">
            Batch
          </label>
          <Input
            id="dir-batch"
            inputMode="numeric"
            value={batch}
            onChange={(event) => setBatch(event.target.value)}
            placeholder="2016"
          />
        </div>
        <div className="min-w-[10rem] flex-1">
          <label htmlFor="dir-industry" className="mb-1 block text-xs text-[var(--text-subtle)]">
            Industry
          </label>
          <Input
            id="dir-industry"
            value={industry}
            onChange={(event) => setIndustry(event.target.value)}
            placeholder="Telecom"
          />
        </div>
        <div className="flex gap-2">
          <Button type="submit" size="sm" disabled={isFetching}>
            <Search className="h-4 w-4" aria-hidden="true" /> Search
          </Button>
          <Button type="button" size="sm" variant="outline" onClick={reset}>
            Clear
          </Button>
        </div>
      </form>

      {isLoading && <PageSkeleton cards={0} rows={5} />}

      {isError && (
        <p
          className="rounded-xl border border-[var(--danger)] bg-[var(--danger-soft)] px-4 py-3 text-sm text-[var(--danger)]"
          role="alert"
        >
          The directory could not be loaded. Try again in a moment.
        </p>
      )}

      {!isLoading && !isError && (data?.length ?? 0) === 0 && (
        <EmptyState
          title="No matching alumni"
          description="No verified, visible profile matches these filters yet. Try a wider search."
        />
      )}

      {!isLoading && !isError && (data?.length ?? 0) > 0 && (
        <div className="surface overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Batch</TableHead>
                <TableHead>Department</TableHead>
                <TableHead>Company</TableHead>
                <TableHead>Industry</TableHead>
                <TableHead>Profile</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(data ?? []).map((profile) => (
                <TableRow key={profile.id}>
                  <TableCell className="font-medium">
                    {profile.user?.full_name ?? '—'}
                    {profile.designation && (
                      <span className="block text-xs text-[var(--text-subtle)]">{profile.designation}</span>
                    )}
                  </TableCell>
                  <TableCell className="tabular-nums">{profile.batch_year}</TableCell>
                  <TableCell>{profile.department}</TableCell>
                  <TableCell>{profile.current_company || '—'}</TableCell>
                  <TableCell>{profile.industry || '—'}</TableCell>
                  <TableCell>
                    {profile.linkedin_url ? (
                      <a
                        href={profile.linkedin_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-xs font-medium text-[var(--accent-bright)] hover:underline"
                      >
                        LinkedIn <ExternalLink className="h-3 w-3" aria-hidden="true" />
                      </a>
                    ) : (
                      <span className="text-xs text-[var(--text-subtle)]">—</span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
