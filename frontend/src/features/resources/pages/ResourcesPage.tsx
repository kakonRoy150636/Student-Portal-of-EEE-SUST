import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { FileText } from 'lucide-react';
import { PageHeader } from '@/components/shared/PageHeader';
import { EmptyState } from '@/components/shared/EmptyState';
import { PageSkeleton } from '@/components/shared/PageSkeleton';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { resourceApi } from '../api/resourceApi';
import { useDebounce } from '@/hooks/useDebounce';

const formatBytes = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

export default function ResourcesPage() {
  const [query, setQuery] = useState('');
  const debounced = useDebounce(query, 300);
  const { data, isLoading, isError } = useQuery({
    queryKey: ['resources', 'search', debounced],
    queryFn: async () => (await resourceApi.search(debounced || undefined)).data,
    retry: false,
  });

  const rows = data ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Academic"
        title="Resource hub"
        description="Course files stored for the department. Search matches titles only."
      />
      <Input
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Search by title"
        aria-label="Search resources by title"
      />
      {isLoading && <PageSkeleton cards={0} rows={4} />}
      {isError && (
        <p className="rounded-xl border border-[var(--danger)] bg-[var(--danger-soft)] px-4 py-3 text-sm text-[var(--danger)]" role="alert">
          Could not load resources.
        </p>
      )}
      {!isLoading && !isError && rows.length === 0 && (
        <EmptyState title="No resources found" description="No files match that title, or none have been published yet." />
      )}
      <div className="space-y-3">
        {rows.map((item) => (
          <article key={item.id} className="surface flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex min-w-0 items-start gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[var(--accent-soft)] text-[var(--accent-bright)]">
                <FileText className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-[var(--text)]">{item.title}</p>
                <p className="mt-1 text-xs text-[var(--text-muted)]">
                  {item.file_name} · {formatBytes(item.file_size_bytes)} · {item.download_count} download{item.download_count === 1 ? '' : 's'}
                </p>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="secondary">{item.category}</Badge>
              {item.is_faculty_verified && <Badge variant="success">Faculty verified</Badge>}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
