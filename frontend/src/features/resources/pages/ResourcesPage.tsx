import React, { useMemo, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Download, FileText, Trash2, Upload } from 'lucide-react';
import { PageHeader } from '@/components/shared/PageHeader';
import { EmptyState } from '@/components/shared/EmptyState';
import { PageSkeleton } from '@/components/shared/PageSkeleton';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useDebounce } from '@/hooks/useDebounce';
import { useAuth } from '@/contexts/AuthContext';
import { resourceApi } from '../api/resourceApi';

const MAX_UPLOAD_BYTES = 25 * 1024 * 1024;
const ALLOWED_EXTENSIONS = [
  '.pdf', '.txt', '.md', '.csv', '.zip', '.png', '.jpg', '.jpeg', '.gif', '.webp',
  '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
];
const CATEGORIES = ['lecture-note', 'book', 'question-bank', 'lab-manual', 'past-paper', 'other'];

const formatBytes = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

export default function ResourcesPage() {
  const qc = useQueryClient();
  const { user } = useAuth();
  const [query, setQuery] = useState('');
  const debounced = useDebounce(query, 300);

  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState(CATEGORIES[0]);
  const [courseCode, setCourseCode] = useState('');
  const [formError, setFormError] = useState('');
  const fileInput = useRef<HTMLInputElement>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['resources', 'search', debounced],
    queryFn: async () => (await resourceApi.search(debounced || undefined)).data,
    retry: false,
  });

  const upload = useMutation({
    mutationFn: () =>
      resourceApi.upload({
        // The mutation only runs from a submit handler that already checked
        // these, but the null-check keeps the type honest.
        file: file as File,
        title: title.trim(),
        category,
        course_code: courseCode.trim() || undefined,
      }),
    onSuccess: async () => {
      setFile(null);
      setTitle('');
      setCourseCode('');
      setFormError('');
      if (fileInput.current) fileInput.current.value = '';
      await qc.invalidateQueries({ queryKey: ['resources', 'search'] });
    },
    onError: (error: unknown) => {
      const detail =
        (error as { response?: { data?: { error?: string } } })?.response?.data?.error ??
        'The upload could not be completed.';
      setFormError(detail);
    },
  });

  const download = useMutation({
    mutationFn: (id: string) => resourceApi.download(id),
    onSuccess: ({ data: payload }) => {
      // A presigned URL carries its own authorisation; opening it directly
      // avoids buffering the file through the SPA.
      window.open(payload.download_url, '_blank', 'noopener,noreferrer');
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) => resourceApi.remove(id),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['resources', 'search'] });
    },
  });

  const rows = useMemo(() => data ?? [], [data]);

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    setFormError('');
    if (!file) {
      setFormError('Choose a file to upload.');
      return;
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      setFormError(`Files must be ${formatBytes(MAX_UPLOAD_BYTES)} or smaller.`);
      return;
    }
    const extension = `.${file.name.split('.').pop()?.toLowerCase() ?? ''}`;
    if (!ALLOWED_EXTENSIONS.includes(extension)) {
      setFormError(`Unsupported file type. Allowed: ${ALLOWED_EXTENSIONS.join(', ')}.`);
      return;
    }
    if (title.trim().length < 2) {
      setFormError('Give the resource a title of at least 2 characters.');
      return;
    }
    upload.mutate();
  };

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Academic"
        title="Resource hub"
        description="Verified course files. Uploads are checked server-side before they appear here."
      />

      <form onSubmit={submit} className="surface space-y-3 p-4" aria-label="Upload a resource">
        <p className="flex items-center gap-2 text-sm font-semibold">
          <Upload className="h-4 w-4" aria-hidden="true" /> Upload a resource
        </p>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label htmlFor="resource-file" className="mb-1 block text-xs text-[var(--text-muted)]">
              File ({ALLOWED_EXTENSIONS.join(', ')}, max {formatBytes(MAX_UPLOAD_BYTES)})
            </label>
            <input
              ref={fileInput}
              id="resource-file"
              type="file"
              accept={ALLOWED_EXTENSIONS.join(',')}
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              className="block w-full text-sm text-[var(--text-muted)]"
            />
          </div>
          <div>
            <label htmlFor="resource-title" className="mb-1 block text-xs text-[var(--text-muted)]">
              Title
            </label>
            <Input
              id="resource-title"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="EEE 311 — Machines II notes"
              maxLength={255}
            />
          </div>
          <div>
            <label htmlFor="resource-category" className="mb-1 block text-xs text-[var(--text-muted)]">
              Category
            </label>
            <select
              id="resource-category"
              value={category}
              onChange={(event) => setCategory(event.target.value)}
              className="h-10 w-full rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 text-sm"
            >
              {CATEGORIES.map((option) => (
                <option key={option} value={option}>{option}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="resource-course" className="mb-1 block text-xs text-[var(--text-muted)]">
              Course code (optional)
            </label>
            <Input
              id="resource-course"
              value={courseCode}
              onChange={(event) => setCourseCode(event.target.value)}
              placeholder="EEE 311"
              maxLength={12}
            />
          </div>
        </div>
        {formError && (
          <p role="alert" className="rounded-lg border border-[var(--danger)] bg-[var(--danger-soft)] px-3 py-2 text-sm text-[var(--danger)]">
            {formError}
          </p>
        )}
        <Button type="submit" size="sm" disabled={upload.isPending}>
          {upload.isPending ? 'Uploading…' : 'Upload'}
        </Button>
      </form>

      <Input
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Search by title or description"
        aria-label="Search resources"
      />

      {isLoading && <PageSkeleton cards={0} rows={4} />}
      {isError && (
        <p className="rounded-xl border border-[var(--danger)] bg-[var(--danger-soft)] px-4 py-3 text-sm text-[var(--danger)]" role="alert">
          Could not load resources.
        </p>
      )}
      {!isLoading && !isError && rows.length === 0 && (
        <EmptyState
          title="No resources found"
          description="Nothing matches that search yet, or no files have been uploaded."
        />
      )}

      <div className="space-y-3">
        {rows.map((item) => (
          <article key={item.id} className="surface flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex min-w-0 items-start gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[var(--accent-soft)] text-[var(--accent-bright)]">
                <FileText className="h-5 w-5" aria-hidden="true" />
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-[var(--text)]">{item.title}</p>
                <p className="mt-1 text-xs text-[var(--text-muted)]">
                  {item.file_name} · {formatBytes(item.file_size_bytes)} · {item.download_count} download
                  {item.download_count === 1 ? '' : 's'}
                </p>
                {item.description && (
                  <p className="mt-1 line-clamp-2 text-xs text-[var(--text-subtle)]">{item.description}</p>
                )}
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="secondary">{item.category}</Badge>
              {item.course_code && <Badge variant="outline">{item.course_code}</Badge>}
              {item.is_faculty_verified && <Badge variant="success">Faculty verified</Badge>}
              <Button
                size="sm"
                variant="outline"
                onClick={() => download.mutate(item.id)}
                disabled={download.isPending}
              >
                <Download className="mr-1 h-3.5 w-3.5" aria-hidden="true" /> Download
              </Button>
              {user?.role === 'super_admin' && (
                <Button
                  size="sm"
                  variant="ghost"
                  aria-label={`Delete ${item.title}`}
                  onClick={() => remove.mutate(item.id)}
                  disabled={remove.isPending}
                >
                  <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                </Button>
              )}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
