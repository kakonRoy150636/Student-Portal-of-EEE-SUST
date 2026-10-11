import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Archive, Edit3, Pin, PinOff, Plus, Search } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { ConfirmDialog } from '@/components/shared/ConfirmDialog';
import { EmptyState } from '@/components/shared/EmptyState';
import { PageSkeleton } from '@/components/shared/PageSkeleton';
import { getErrorMessage } from '@/lib/errors';
import { useDebounce } from '@/hooks/useDebounce';
import type {
  AnnouncementAudience,
  AnnouncementStatus,
  AnnouncementType,
  CourseAnnouncement,
} from '@/types/courseWorkspace';
import { announcementFilterValues } from '../api/courseWorkspaceApi';
import { useCourseAnnouncementMutations, useCourseAnnouncements, type CourseAnnouncementFilters } from '../hooks/useCourseWorkspace';
import { AnnouncementBody } from './AnnouncementBody';
import { AnnouncementDialog, type AnnouncementSubmission } from './AnnouncementDialog';

interface WorkspaceAnnouncementsProps {
  offeringId: string;
  manager: boolean;
  canManage?: boolean;
  initialAnnouncementId?: string | null;
  createRequest?: number;
}

const audienceValues: AnnouncementAudience[] = ['enrolled_students', 'cr_only', 'teachers_only'];

function isAnnouncementType(value: string): value is AnnouncementType {
  return announcementFilterValues.types.some((item) => item === value);
}

function isAnnouncementStatus(value: string): value is AnnouncementStatus {
  return announcementFilterValues.statuses.some((item) => item === value);
}

function isAnnouncementAudience(value: string): value is AnnouncementAudience {
  return audienceValues.some((item) => item === value);
}

function formatDate(value: string | null): string {
  if (!value) return 'Not scheduled';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Date unavailable' : date.toLocaleString();
}

function label(value: string): string {
  return value.replace(/_/g, ' ');
}

export function WorkspaceAnnouncements({ offeringId, manager, canManage: canManageProp = true, initialAnnouncementId, createRequest = 0 }: WorkspaceAnnouncementsProps) {
  const canManage = manager && canManageProp;
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState<AnnouncementStatus | 'all'>(manager ? 'all' : 'published');
  const [announcementType, setAnnouncementType] = useState<AnnouncementType | 'all'>('all');
  const [audience, setAudience] = useState<AnnouncementAudience | 'all'>('all');
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<CourseAnnouncement | null>(null);
  const [editing, setEditing] = useState<CourseAnnouncement | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [archiveTarget, setArchiveTarget] = useState<CourseAnnouncement | null>(null);
  const lastCreateRequest = useRef(0);
  const debouncedSearch = useDebounce(search, 300);
  const filters: CourseAnnouncementFilters = useMemo(() => ({
    search: debouncedSearch,
    status,
    announcement_type: announcementType,
    audience,
    limit: 10,
    offset,
  }), [announcementType, audience, debouncedSearch, offset, status]);
  const feedQuery = useCourseAnnouncements(offeringId, filters);
  const mutations = useCourseAnnouncementMutations(offeringId);
  const mutating = mutations.create.isPending || mutations.update.isPending;
  const mutationError = mutations.create.error ?? mutations.update.error ?? mutations.publish.error ?? mutations.archive.error ?? mutations.pin.error ?? mutations.markRead.error;

  useEffect(() => {
    setOffset(0);
  }, [announcementType, audience, debouncedSearch, status]);

  useEffect(() => {
    if (!initialAnnouncementId || selected || !feedQuery.data) return;
    const match = feedQuery.data.items.find((item) => item.id === initialAnnouncementId);
    if (match) openAnnouncement(match);
    // A notification can provide this query parameter once; the feed remains the source of truth.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [feedQuery.data, initialAnnouncementId]);

  useEffect(() => {
    if (!canManage || createRequest === 0 || createRequest === lastCreateRequest.current) return;
    lastCreateRequest.current = createRequest;
    openCreate();
    // openCreate only resets local mutation state and opens the dialog.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canManage, createRequest]);

  const visibleItems = useMemo(() => {
    const items = feedQuery.data?.items ?? [];
    if (audience === 'all') return items;
    return items.filter((item) => item.audience === audience);
  }, [audience, feedQuery.data?.items]);

  function openAnnouncement(item: CourseAnnouncement) {
    setSelected(item.is_read || manager ? item : { ...item, is_read: true });
    if (!manager && !item.is_read) mutations.markRead.mutate(item.id);
  }

  function openCreate() {
    mutations.create.reset();
    mutations.update.reset();
    setEditing(null);
    setDialogOpen(true);
  }

  function submitAnnouncement(submission: AnnouncementSubmission) {
    if (submission.mode === 'update' && editing) {
      mutations.update.mutate({ announcementId: editing.id, payload: submission.payload }, {
        onSuccess: (updated) => { setEditing(null); setDialogOpen(false); setSelected(updated); },
      });
    } else if (submission.mode === 'create') {
      mutations.create.mutate(submission.payload, {
        onSuccess: (created) => { setDialogOpen(false); setSelected(created); },
      });
    }
  }

  function refresh() {
    void feedQuery.refetch();
  }

  return (
    <section id="workspace-panel-announcements" role="tabpanel" aria-labelledby="workspace-tab-announcements" className="space-y-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div><p className="kicker">Course communication</p><h2 className="mt-1 font-display text-lg font-semibold">Announcements</h2><p className="mt-1 text-sm text-[var(--text-muted)]">{manager ? 'Manage drafts, publication, scheduling, and pinned updates.' : 'Published updates for this course, with unread notices highlighted.'}</p></div>
        {canManage && <Button onClick={openCreate}><Plus className="h-4 w-4" aria-hidden="true" />Create announcement</Button>}
      </div>
      <div className="grid gap-3 rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] p-3 sm:grid-cols-2 lg:grid-cols-4">
        <label className="relative sm:col-span-2 lg:col-span-1"><span className="sr-only">Search announcements</span><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-subtle)]" aria-hidden="true" /><Input className="pl-9" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search announcements" aria-label="Search announcements" /></label>
        <label><span className="mb-1 block text-xs font-semibold text-[var(--text-muted)]">Status</span><select className="h-10 w-full rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] px-3 text-sm" value={status} onChange={(event) => { const value = event.target.value; if (value === 'all' || isAnnouncementStatus(value)) setStatus(value); }} aria-label="Filter announcements by status"><option value="all">All statuses</option>{(manager ? announcementFilterValues.statuses : ['published']).map((value) => <option key={value} value={value}>{label(value)}</option>)}</select></label>
        <label><span className="mb-1 block text-xs font-semibold text-[var(--text-muted)]">Type</span><select className="h-10 w-full rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] px-3 text-sm" value={announcementType} onChange={(event) => { const value = event.target.value; if (value === 'all' || isAnnouncementType(value)) setAnnouncementType(value); }} aria-label="Filter announcements by type"><option value="all">All types</option>{announcementFilterValues.types.map((value) => <option key={value} value={value}>{label(value)}</option>)}</select></label>
        <label><span className="mb-1 block text-xs font-semibold text-[var(--text-muted)]">Audience</span><select className="h-10 w-full rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] px-3 text-sm" value={audience} onChange={(event) => { const value = event.target.value; if (value === 'all' || isAnnouncementAudience(value)) setAudience(value); }} aria-label="Filter announcements by audience"><option value="all">All audiences</option>{audienceValues.filter((value) => manager || value !== 'teachers_only').map((value) => <option key={value} value={value}>{label(value)}</option>)}</select></label>
      </div>
      {mutationError && <div className="space-y-1 rounded-xl border border-[var(--danger)] bg-[var(--danger-soft)] p-3 text-sm text-[var(--danger)]" role="alert"><p className="font-semibold">Could not update this announcement.</p><p>{getErrorMessage(mutationError, 'Please retry the action.')}</p></div>}
      {feedQuery.isPending && <PageSkeleton cards={0} rows={4} />}
      {feedQuery.isError && <div className="space-y-3 rounded-xl border border-[var(--danger)] bg-[var(--danger-soft)] p-4" role="alert"><p className="font-semibold text-[var(--danger)]">Could not load announcements.</p><p className="text-sm text-[var(--danger)]">{getErrorMessage(feedQuery.error, 'Please retry when connected.')}</p><Button variant="outline" onClick={refresh} disabled={feedQuery.isFetching}>Try again</Button></div>}
      {!feedQuery.isPending && !feedQuery.isError && visibleItems.length === 0 && <EmptyState title="No announcements found" description={manager ? 'Create a draft or adjust the filters to find course updates.' : 'Published course updates will appear here when available.'} action={canManage ? <Button size="sm" onClick={openCreate}>Create announcement</Button> : undefined} />}
      {!feedQuery.isPending && !feedQuery.isError && visibleItems.length > 0 && <div className="space-y-3">{visibleItems.map((item) => <AnnouncementCard key={item.id} item={item} manager={canManage} onOpen={() => openAnnouncement(item)} onEdit={() => { setEditing(item); setDialogOpen(true); }} onPublish={() => mutations.publish.mutate(item.id)} onArchive={() => setArchiveTarget(item)} onPin={() => mutations.pin.mutate({ announcementId: item.id, pinned: !item.is_pinned })} busy={mutating || mutations.publish.isPending || mutations.archive.isPending || mutations.pin.isPending} />)}</div>}
      {!feedQuery.isPending && !feedQuery.isError && feedQuery.data && feedQuery.data.total > 0 && <div className="flex flex-col gap-3 border-t border-[var(--border)] pt-4 sm:flex-row sm:items-center sm:justify-between"><p className="text-sm text-[var(--text-muted)]">{visibleItems.length > 0 ? `Showing ${feedQuery.data.offset + 1}–${Math.min(feedQuery.data.offset + visibleItems.length, feedQuery.data.total)} of ${feedQuery.data.total}` : 'No announcements match this audience filter.'}</p><div className="flex gap-2"><Button size="sm" variant="outline" onClick={() => setOffset((value) => Math.max(0, value - (feedQuery.data?.limit ?? 10)))} disabled={offset === 0 || feedQuery.isFetching}>Previous</Button><Button size="sm" variant="outline" onClick={() => setOffset((value) => value + (feedQuery.data?.limit ?? 10))} disabled={!feedQuery.data.has_more || feedQuery.isFetching}>Next</Button></div></div>}

      <AnnouncementDialog open={dialogOpen} announcement={editing} pending={mutating} error={mutations.create.error ?? mutations.update.error} onOpenChange={(open) => { if (!open && !mutating) { setDialogOpen(false); setEditing(null); } }} onSubmit={submitAnnouncement} />
      <Dialog open={Boolean(selected)} onOpenChange={(open) => { if (!open) setSelected(null); }}>
        <DialogContent className="max-h-[90vh] overflow-y-auto" aria-describedby="workspace-announcement-detail-description">
          {selected && <><DialogHeader><div className="flex flex-wrap items-center gap-2 pr-8"><DialogTitle>{selected.title}</DialogTitle>{!selected.is_read && !manager && <Badge variant="danger">Unread</Badge>}{selected.is_pinned && <Badge variant="secondary">Pinned</Badge>}</div></DialogHeader><div id="workspace-announcement-detail-description" className="space-y-4"><div className="flex flex-wrap gap-2"><AnnouncementBadge value={selected.announcement_type} /><Badge variant="outline">{label(selected.audience)}</Badge><Badge variant={selected.status === 'published' ? 'success' : 'secondary'}>{selected.status}</Badge></div><div className="text-xs text-[var(--text-muted)]">By {selected.author_name} · {selected.publish_at ? `Published ${formatDate(selected.publish_at)}` : `Created ${formatDate(selected.created_at)}`}</div><AnnouncementBody body={selected.body} />{canManage && <div className="flex flex-wrap gap-2 border-t border-[var(--border)] pt-4">{selected.can_edit && <Button size="sm" variant="outline" onClick={() => { setEditing(selected); setDialogOpen(true); setSelected(null); }}><Edit3 className="h-4 w-4" aria-hidden="true" />Edit</Button>}{selected.can_publish && <Button size="sm" onClick={() => { mutations.publish.mutate(selected.id); setSelected(null); }}>Publish now</Button>}{selected.can_pin && <Button size="sm" variant="outline" onClick={() => mutations.pin.mutate({ announcementId: selected.id, pinned: !selected.is_pinned })}>{selected.is_pinned ? <PinOff className="h-4 w-4" aria-hidden="true" /> : <Pin className="h-4 w-4" aria-hidden="true" />}{selected.is_pinned ? 'Unpin' : 'Pin'}</Button>}{selected.can_archive && <Button size="sm" variant="destructive" onClick={() => { setArchiveTarget(selected); setSelected(null); }}><Archive className="h-4 w-4" aria-hidden="true" />Archive</Button>}</div>}</div></>}
        </DialogContent>
      </Dialog>
      <ConfirmDialog open={Boolean(archiveTarget)} title="Archive announcement?" message="Archived announcements leave the live feed and cannot be edited or published again." onCancel={() => setArchiveTarget(null)} onConfirm={() => { if (archiveTarget) mutations.archive.mutate(archiveTarget.id, { onSuccess: () => setArchiveTarget(null) }); }} />
    </section>
  );
}

function AnnouncementCard({ item, manager, onOpen, onEdit, onPublish, onArchive, onPin, busy }: { item: CourseAnnouncement; manager: boolean; onOpen: () => void; onEdit: () => void; onPublish: () => void; onArchive: () => void; onPin: () => void; busy: boolean }) {
  return <article className={`surface p-4 ${!item.is_read && !manager ? 'border-[var(--accent-edge)] bg-[var(--accent-soft)]/20' : ''}`}><div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between"><div className="min-w-0"><div className="flex flex-wrap items-center gap-2">{!item.is_read && !manager && <Badge variant="danger">Unread</Badge>}{item.is_pinned && <Badge variant="secondary">Pinned</Badge>}<AnnouncementBadge value={item.announcement_type} /><Badge variant="outline">{label(item.audience)}</Badge><Badge variant={item.status === 'published' ? 'success' : 'secondary'}>{item.status}</Badge></div><button type="button" className="mt-3 text-left font-display text-lg font-semibold text-[var(--text)] underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]" onClick={onOpen} aria-label={`Open announcement ${item.title}`}>{item.title}</button><div className="mt-2 line-clamp-4"><AnnouncementBody body={item.body} /></div><p className="mt-3 text-xs text-[var(--text-subtle)]">By {item.author_name} · {item.publish_at ? `Publish ${formatDate(item.publish_at)}` : `Created ${formatDate(item.created_at)}`}</p></div><div className="flex shrink-0 flex-wrap gap-2 lg:max-w-[16rem] lg:justify-end"><Button size="sm" variant="outline" onClick={onOpen}>Open</Button>{manager && item.can_edit && <Button size="sm" variant="outline" onClick={onEdit} disabled={busy}><Edit3 className="h-4 w-4" aria-hidden="true" />Edit</Button>}{manager && item.can_publish && <Button size="sm" onClick={onPublish} disabled={busy}>Publish now</Button>}{manager && item.can_pin && <Button size="sm" variant="ghost" onClick={onPin} disabled={busy} aria-label={item.is_pinned ? `Unpin ${item.title}` : `Pin ${item.title}`}>{item.is_pinned ? <PinOff className="h-4 w-4" aria-hidden="true" /> : <Pin className="h-4 w-4" aria-hidden="true" />}</Button>}{manager && item.can_archive && <Button size="sm" variant="ghost" onClick={onArchive} disabled={busy} aria-label={`Archive ${item.title}`}><Archive className="h-4 w-4" aria-hidden="true" /></Button>}</div></div></article>;
}

function AnnouncementBadge({ value }: { value: AnnouncementType }) {
  return <Badge variant={value === 'urgent' ? 'danger' : value === 'exam' ? 'secondary' : 'outline'}>{label(value)}</Badge>;
}
