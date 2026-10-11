import React, { useState } from 'react';
import { Download, FileText } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { EmptyState } from '@/components/shared/EmptyState';
import { PageSkeleton } from '@/components/shared/PageSkeleton';
import { getErrorMessage } from '@/lib/errors';
import { safeExternalUrl } from '@/lib/externalUrl';
import { courseWorkspaceApi } from '../api/courseWorkspaceApi';
import { useCourseResources } from '../hooks/useCourseWorkspace';
import type { CourseWorkspaceResource } from '@/types/courseWorkspace';

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const categories = ['syllabus', 'lecture_note', 'slide', 'lab_manual', 'previous_question', 'reference', 'other'];

export function WorkspaceResources({ offeringId, courseCode, manager = false }: { offeringId: string; courseCode: string; manager?: boolean }) {
  const query = useCourseResources(offeringId);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState('other');

  const download = async (resource: CourseWorkspaceResource) => {
    setDownloadError(null);
    setDownloadingId(resource.id);
    try {
      const response = await courseWorkspaceApi.downloadResource(resource.id);
      const url = safeExternalUrl(response.data.download_url);
      if (!url) throw new Error('The server returned an invalid download link.');
      window.open(url, '_blank', 'noopener,noreferrer');
    } catch (error) {
      setDownloadError(getErrorMessage(error, 'Could not prepare this download.'));
    } finally {
      setDownloadingId(null);
    }
  };

  const upload = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const input = event.currentTarget.elements.namedItem('resource-file');
    const file = input instanceof HTMLInputElement ? input.files?.[0] : undefined;
    if (!file || !title.trim()) { setUploadError('Choose a file and provide a title.'); return; }
    setUploadError(null);
    setUploading(true);
    try {
      const presigned = await courseWorkspaceApi.createResourceUpload(offeringId, {
        file_name: file.name, file_size: file.size, mime_type: file.type,
      });
      const uploadUrl = safeExternalUrl(presigned.data.upload_url);
      if (!uploadUrl) throw new Error('The server returned an invalid upload URL.');
      const put = await fetch(uploadUrl, { method: 'PUT', headers: { 'Content-Type': presigned.data.content_type }, body: file });
      if (!put.ok) throw new Error('The file upload was rejected by storage.');
      await courseWorkspaceApi.finalizeResource(offeringId, {
        file_key: presigned.data.file_key, title: title.trim(), category, course_code: courseCode,
        file_name: file.name, file_size_bytes: file.size, mime_type: file.type,
      });
      setTitle('');
      event.currentTarget.reset();
      await query.refetch();
    } catch (error) {
      setUploadError(getErrorMessage(error, 'Could not upload this resource.'));
    } finally {
      setUploading(false);
    }
  };

  return (
    <section id="workspace-panel-resources" role="tabpanel" aria-labelledby="workspace-tab-resources" className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="kicker">Course files</p>
          <h2 className="mt-1 font-display text-lg font-semibold">Resources</h2>
          <p className="mt-1 text-sm text-[var(--text-muted)]">Files scoped to this course. Downloads are issued through the authenticated resource service.</p>
        </div>
        <Link className="text-sm font-semibold text-[var(--accent-bright)] underline underline-offset-2" to="/resources">Open resource hub</Link>
      </div>
      {manager && <Card><CardHeader><CardTitle>Upload course resource</CardTitle></CardHeader><CardContent><form className="grid gap-3 sm:grid-cols-2" onSubmit={upload}><label><span className="mb-1 block text-sm font-semibold">Title</span><input className="h-10 w-full rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] px-3 text-sm" value={title} onChange={(event) => setTitle(event.target.value)} required /></label><label><span className="mb-1 block text-sm font-semibold">Type</span><select className="h-10 w-full rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] px-3 text-sm" value={category} onChange={(event) => setCategory(event.target.value)}>{categories.map((item) => <option key={item} value={item}>{item.replace(/_/g, ' ')}</option>)}</select></label><label className="sm:col-span-2"><span className="mb-1 block text-sm font-semibold">File</span><input name="resource-file" type="file" className="block w-full text-sm" accept=".pdf,.ppt,.pptx,.doc,.docx,.zip,.png,.jpg,.jpeg" required /></label>{uploadError && <p className="sm:col-span-2 text-sm text-[var(--danger)]" role="alert">{uploadError}</p>}<div className="sm:col-span-2 flex justify-end"><Button type="submit" disabled={uploading}>{uploading ? 'Uploading…' : 'Upload resource'}</Button></div></form></CardContent></Card>}
      {query.isPending && <PageSkeleton cards={0} rows={4} />}
      {query.isError && (
        <div className="space-y-3 rounded-xl border border-[var(--danger)] bg-[var(--danger-soft)] p-4" role="alert">
          <p className="font-semibold text-[var(--danger)]">Could not load course resources.</p>
          <p className="text-sm text-[var(--danger)]">{getErrorMessage(query.error, 'Please retry when connected.')}</p>
          <Button variant="outline" onClick={() => void query.refetch()} disabled={query.isFetching}>Try again</Button>
        </div>
      )}
      {downloadError && <p className="rounded-xl border border-[var(--danger)] bg-[var(--danger-soft)] px-4 py-3 text-sm text-[var(--danger)]" role="alert">{downloadError}</p>}
      {!query.isPending && !query.isError && (query.data ?? []).length === 0 && (
        <EmptyState title="No course resources" description="No files have been published for this course yet." />
      )}
      {!query.isPending && !query.isError && (query.data ?? []).length > 0 && (
        <div className="space-y-3">
          {(query.data ?? []).map((item) => (
            <article key={item.id} className="surface flex flex-col gap-4 p-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex min-w-0 items-start gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[var(--accent-soft)] text-[var(--accent-bright)]"><FileText className="h-5 w-5" aria-hidden="true" /></div>
                <div className="min-w-0">
                  <h3 className="break-words text-sm font-semibold">{item.title}</h3>
                  <p className="mt-1 break-words text-xs text-[var(--text-muted)]">{item.file_name} · {formatBytes(item.file_size_bytes)} · {item.download_count} download{item.download_count === 1 ? '' : 's'}</p>
                  {item.description && <p className="mt-2 whitespace-pre-wrap break-words text-sm text-[var(--text-muted)]">{item.description}</p>}
                </div>
              </div>
              <div className="flex shrink-0 flex-wrap items-center gap-2">
                <Badge variant="secondary">{item.category}</Badge>
                {item.is_faculty_verified && <Badge variant="success">Faculty verified</Badge>}
                <Button size="sm" variant="outline" onClick={() => void download(item)} disabled={downloadingId === item.id}>
                  <Download className="h-4 w-4" aria-hidden="true" />
                  {downloadingId === item.id ? 'Preparing…' : 'Download'}
                </Button>
                {manager && item.can_manage && !item.archived_at && <Button size="sm" variant="ghost" onClick={() => void courseWorkspaceApi.updateResource(offeringId, item.id, { is_published: !item.is_published }).then(() => query.refetch())}>
                  {item.is_published ? 'Unpublish' : 'Publish'}
                </Button>}
                {manager && item.can_manage && !item.archived_at && <Button size="sm" variant="ghost" onClick={() => void courseWorkspaceApi.updateResource(offeringId, item.id, { archived: true }).then(() => query.refetch())}>Archive</Button>}
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
