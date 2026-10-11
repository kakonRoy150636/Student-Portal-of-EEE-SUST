import React, { useState } from 'react';
import { CalendarPlus, Archive, MapPin } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { EmptyState } from '@/components/shared/EmptyState';
import { PageSkeleton } from '@/components/shared/PageSkeleton';
import { getErrorMessage } from '@/lib/errors';
import type { CourseEventType } from '@/types/courseWorkspace';
import { useCourseEvents, useCourseAnnouncementMutations } from '../hooks/useCourseWorkspace';

const eventTypes: CourseEventType[] = ['class', 'quiz', 'midterm', 'final', 'viva', 'assignment_deadline', 'lab_exam', 'presentation', 'holiday', 'other'];
const controlClassName = 'h-10 w-full rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] px-3 py-2 text-sm text-[var(--text)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]';

export function WorkspaceEvents({ offeringId, manager }: { offeringId: string; manager: boolean }) {
  const query = useCourseEvents(offeringId);
  const mutations = useCourseAnnouncementMutations(offeringId);
  const [formOpen, setFormOpen] = useState(false);
  const [title, setTitle] = useState('');
  const [eventType, setEventType] = useState<CourseEventType>('other');
  const [startsAt, setStartsAt] = useState('');
  const [location, setLocation] = useState('');
  const [error, setError] = useState('');

  const create = (event: React.FormEvent) => {
    event.preventDefault();
    if (!title.trim() || !startsAt) { setError('Title and start time are required.'); return; }
    setError('');
    mutations.createEvent.mutate({
      title: title.trim(), event_type: eventType, starts_at: new Date(startsAt).toISOString(),
      location: location.trim() || null, is_published: true,
    }, { onSuccess: () => { setTitle(''); setStartsAt(''); setLocation(''); setFormOpen(false); } });
  };

  return (
    <section id="workspace-panel-events" role="tabpanel" aria-labelledby="workspace-tab-events" className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div><p className="kicker">Course calendar</p><h2 className="mt-1 font-display text-lg font-semibold">Events and deadlines</h2><p className="mt-1 text-sm text-[var(--text-muted)]">Published classes, assessments, presentations, and deadlines for this offering.</p></div>
        {manager && <Button onClick={() => setFormOpen((value) => !value)}><CalendarPlus className="h-4 w-4" aria-hidden="true" />{formOpen ? 'Close form' : 'Add event'}</Button>}
      </div>
      {formOpen && <Card><CardHeader><CardTitle>New course event</CardTitle></CardHeader><CardContent><form className="grid gap-4 sm:grid-cols-2" onSubmit={create}>
        <label className="sm:col-span-2"><span className="mb-1 block text-sm font-semibold">Title</span><input className={controlClassName} value={title} onChange={(event) => setTitle(event.target.value)} required /></label>
        <label><span className="mb-1 block text-sm font-semibold">Type</span><select className={controlClassName} value={eventType} onChange={(event) => setEventType(event.target.value as CourseEventType)}>{eventTypes.map((type) => <option key={type} value={type}>{type.replace(/_/g, ' ')}</option>)}</select></label>
        <label><span className="mb-1 block text-sm font-semibold">Starts at</span><input className={controlClassName} type="datetime-local" value={startsAt} onChange={(event) => setStartsAt(event.target.value)} required /></label>
        <label className="sm:col-span-2"><span className="mb-1 block text-sm font-semibold">Location optional</span><input className={controlClassName} value={location} onChange={(event) => setLocation(event.target.value)} /></label>
        {error && <p className="sm:col-span-2 text-sm text-[var(--danger)]" role="alert">{error}</p>}
        {mutations.createEvent.isError && <p className="sm:col-span-2 text-sm text-[var(--danger)]" role="alert">{getErrorMessage(mutations.createEvent.error, 'Could not create event.')}</p>}
        <div className="sm:col-span-2 flex justify-end"><Button type="submit" disabled={mutations.createEvent.isPending}>{mutations.createEvent.isPending ? 'Saving…' : 'Save event'}</Button></div>
      </form></CardContent></Card>}
      {query.isPending && <PageSkeleton cards={0} rows={4} />}
      {query.isError && <div className="space-y-3 rounded-xl border border-[var(--danger)] bg-[var(--danger-soft)] p-4" role="alert"><p className="font-semibold text-[var(--danger)]">Could not load events.</p><p className="text-sm text-[var(--danger)]">{getErrorMessage(query.error, 'Please retry when connected.')}</p><Button variant="outline" onClick={() => void query.refetch()}>Try again</Button></div>}
      {!query.isPending && !query.isError && (query.data ?? []).length === 0 && <EmptyState title="No course events" description={manager ? 'Add the first class, assessment, or deadline for this offering.' : 'Published course events will appear here when available.'} />}
      {!query.isPending && !query.isError && (query.data ?? []).length > 0 && <div className="space-y-3">{(query.data ?? []).map((item) => <Card key={item.id}><CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-start sm:justify-between"><div><div className="flex flex-wrap items-center gap-2"><h3 className="font-semibold">{item.title}</h3><Badge variant="secondary">{item.event_type.replace(/_/g, ' ')}</Badge>{!item.is_published && <Badge variant="outline">Draft</Badge>}</div><p className="mt-2 text-sm text-[var(--text-muted)]">{new Date(item.starts_at).toLocaleString()}{item.ends_at ? ` – ${new Date(item.ends_at).toLocaleString()}` : ''}</p>{item.location && <p className="mt-1 flex items-center gap-1 text-sm text-[var(--text-muted)]"><MapPin className="h-3.5 w-3.5" aria-hidden="true" />{item.location}</p>}{item.description && <p className="mt-2 whitespace-pre-wrap text-sm text-[var(--text-muted)]">{item.description}</p>}</div>{manager && <Button size="sm" variant="ghost" onClick={() => mutations.archiveEvent.mutate(item.id)} disabled={mutations.archiveEvent.isPending} aria-label={`Archive ${item.title}`}><Archive className="h-4 w-4" aria-hidden="true" /></Button>}</CardContent></Card>)}</div>}
    </section>
  );
}
