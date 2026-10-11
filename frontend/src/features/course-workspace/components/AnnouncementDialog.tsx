import React, { useEffect, useId, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { getErrorMessage } from '@/lib/errors';
import type {
  AnnouncementAudience,
  AnnouncementType,
  CourseAnnouncement,
  CourseAnnouncementCreatePayload,
  CourseAnnouncementUpdatePayload,
} from '@/types/courseWorkspace';

interface AnnouncementDialogProps {
  open: boolean;
  announcement?: CourseAnnouncement | null;
  pending: boolean;
  error: unknown;
  onOpenChange: (open: boolean) => void;
  onSubmit: (submission: AnnouncementSubmission) => void;
}

export type AnnouncementSubmission =
  | { mode: 'create'; payload: CourseAnnouncementCreatePayload }
  | { mode: 'update'; payload: CourseAnnouncementUpdatePayload };

interface AnnouncementForm {
  title: string;
  body: string;
  announcement_type: AnnouncementType;
  audience: AnnouncementAudience;
  status: 'draft' | 'scheduled' | 'published';
  publish_at: string;
}

const emptyForm: AnnouncementForm = {
  title: '',
  body: '',
  announcement_type: 'general',
  audience: 'enrolled_students',
  status: 'draft',
  publish_at: '',
};

const announcementTypes: AnnouncementType[] = ['general', 'class_update', 'class_cancelled', 'exam', 'assignment', 'urgent', 'resource', 'administrative'];
const audiences: AnnouncementAudience[] = ['enrolled_students', 'cr_only', 'teachers_only'];

function isAnnouncementType(value: string): value is AnnouncementType {
  return announcementTypes.some((item) => item === value);
}

function isAnnouncementAudience(value: string): value is AnnouncementAudience {
  return audiences.some((item) => item === value);
}

function isEditableStatus(value: string): value is 'draft' | 'scheduled' | 'published' {
  return value === 'draft' || value === 'scheduled' || value === 'published';
}

function dateTimeInput(value: string | null): string {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const pad = (part: number) => String(part).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function toIso(value: string): string | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

function displayValue(value: string): string {
  return value.replace(/_/g, ' ');
}

export function AnnouncementDialog({ open, announcement, pending, error, onOpenChange, onSubmit }: AnnouncementDialogProps) {
  const [form, setForm] = useState<AnnouncementForm>(emptyForm);
  const [validationError, setValidationError] = useState('');
  const descriptionId = useId();
  const isEditing = Boolean(announcement);

  useEffect(() => {
    if (!open) return;
    setValidationError('');
    setForm(announcement ? {
      title: announcement.title,
      body: announcement.body,
      announcement_type: announcement.announcement_type,
      audience: announcement.audience,
      status: announcement.status === 'archived' ? 'draft' : announcement.status,
      publish_at: dateTimeInput(announcement.publish_at),
    } : emptyForm);
  }, [announcement, open]);

  const update = <K extends keyof AnnouncementForm>(key: K, value: AnnouncementForm[K]) => {
    setForm((current) => ({ ...current, [key]: value }));
    setValidationError('');
  };

  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!form.title.trim()) { setValidationError('Title is required.'); return; }
    if (!form.body.trim()) { setValidationError('Body is required.'); return; }
    if (form.status === 'scheduled') {
      const publishAt = toIso(form.publish_at);
      if (!publishAt) { setValidationError('Choose a future publish time for a scheduled announcement.'); return; }
      if (new Date(publishAt).getTime() <= Date.now()) { setValidationError('Scheduled publish time must be in the future.'); return; }
    }
    const publishAt = form.status === 'scheduled' ? toIso(form.publish_at) : null;
    if (isEditing) {
      const payload: CourseAnnouncementUpdatePayload = {
        title: form.title.trim(),
        body: form.body.trim(),
        announcement_type: form.announcement_type,
        audience: form.audience,
        status: form.status,
        publish_at: publishAt,
      };
      onSubmit({ mode: 'update', payload });
    } else {
      const payload: CourseAnnouncementCreatePayload = {
        title: form.title.trim(),
        body: form.body.trim(),
        announcement_type: form.announcement_type,
        audience: form.audience,
        status: form.status,
        publish_at: publishAt,
      };
      onSubmit({ mode: 'create', payload });
    }
  };

  const errorMessage = error ? getErrorMessage(error, 'Could not save this announcement.') : '';
  return (
    <Dialog open={open} onOpenChange={(nextOpen) => { if (!pending) onOpenChange(nextOpen); }}>
      <DialogContent className="max-h-[90vh] overflow-y-auto" aria-describedby={descriptionId}>
        <DialogHeader><DialogTitle>{isEditing ? 'Edit announcement' : 'Create announcement'}</DialogTitle></DialogHeader>
        <p id={descriptionId} className="mb-4 text-sm text-[var(--text-muted)]">Announcements are stored as plain text. Links are displayed only when they use a safe HTTP(S) URL.</p>
        {(validationError || errorMessage) && <div className="mb-4 space-y-1 rounded-xl border border-[var(--danger)] bg-[var(--danger-soft)] p-3 text-sm text-[var(--danger)]" role="alert"><p className="font-semibold">{validationError || 'Could not save announcement.'}</p>{errorMessage && <p>{errorMessage}</p>}<p>Your entries are still here; correct the issue and try again.</p></div>}
        <form className="space-y-4" onSubmit={submit} noValidate>
          <div><label className="mb-1 block text-sm font-semibold" htmlFor="workspace-announcement-title">Title</label><input id="workspace-announcement-title" className="flex h-10 w-full rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] px-3 py-2 text-sm text-[var(--text)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]" value={form.title} onChange={(event) => update('title', event.target.value)} maxLength={200} disabled={pending} required /></div>
          <div><label className="mb-1 block text-sm font-semibold" htmlFor="workspace-announcement-body">Body</label><textarea id="workspace-announcement-body" className="min-h-36 w-full resize-y rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] px-3 py-2 text-sm leading-6 text-[var(--text)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]" value={form.body} onChange={(event) => update('body', event.target.value)} maxLength={20000} disabled={pending} required /></div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div><label className="mb-1 block text-sm font-semibold" htmlFor="workspace-announcement-type">Type</label><select id="workspace-announcement-type" className="h-10 w-full rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] px-3 text-sm text-[var(--text)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]" value={form.announcement_type} onChange={(event) => { const value = event.target.value; if (isAnnouncementType(value)) update('announcement_type', value); }} disabled={pending}>{announcementTypes.map((type) => <option key={type} value={type}>{displayValue(type)}</option>)}</select></div>
            <div><label className="mb-1 block text-sm font-semibold" htmlFor="workspace-announcement-audience">Audience</label><select id="workspace-announcement-audience" className="h-10 w-full rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] px-3 text-sm text-[var(--text)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]" value={form.audience} onChange={(event) => { const value = event.target.value; if (isAnnouncementAudience(value)) update('audience', value); }} disabled={pending}>{audiences.map((audience) => <option key={audience} value={audience}>{displayValue(audience)}</option>)}</select></div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div><label className="mb-1 block text-sm font-semibold" htmlFor="workspace-announcement-status">Status</label><select id="workspace-announcement-status" className="h-10 w-full rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] px-3 text-sm text-[var(--text)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]" value={form.status} onChange={(event) => { const value = event.target.value; if (isEditableStatus(value)) update('status', value); }} disabled={pending || announcement?.status === 'published'}><option value="draft">Draft</option><option value="scheduled">Schedule</option><option value="published">Publish now</option></select></div>
            {form.status === 'scheduled' ? <div><label className="mb-1 block text-sm font-semibold" htmlFor="workspace-announcement-publish-at">Publish at</label><input id="workspace-announcement-publish-at" type="datetime-local" className="h-10 w-full rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] px-3 text-sm text-[var(--text)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]" value={form.publish_at} onChange={(event) => update('publish_at', event.target.value)} disabled={pending} required /><p className="mt-1 text-xs text-[var(--text-muted)]">Your local time is sent with its timezone.</p></div> : <div className="flex items-end"><p className="text-xs text-[var(--text-muted)]">{form.status === 'published' ? 'Publishing now sends the announcement to its selected audience.' : 'Drafts remain visible to course staff until published.'}</p></div>}
          </div>
          <div className="flex justify-end gap-2 pt-2"><Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={pending}>Cancel</Button><Button type="submit" disabled={pending}>{pending ? 'Saving…' : isEditing ? 'Save changes' : form.status === 'scheduled' ? 'Schedule announcement' : form.status === 'published' ? 'Publish announcement' : 'Save draft'}</Button></div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
