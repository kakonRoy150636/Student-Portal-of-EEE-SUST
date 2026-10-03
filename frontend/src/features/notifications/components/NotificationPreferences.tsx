import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/axios';
import { getErrorMessage } from '@/lib/errors';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

const labels = {
  class_reminder: 'Class reminders', lab_reminder: 'Lab reminders',
  exam_reminder: 'Academic reminders', announcement: 'Announcements',
};
type NotificationType = keyof typeof labels;
type Preferences = {
  per_type: Record<NotificationType, { push: boolean; in_app: boolean }>;
  quiet_start: string | null;
  quiet_end: string | null;
  timezone: 'Asia/Dhaka';
};

function PreferencesForm({ initial }: { initial: Preferences }) {
  const [value, setValue] = useState(initial);
  const queryClient = useQueryClient();
  const save = useMutation({
    mutationFn: async () => (await api.put<Preferences>('/notifications/preferences', {
      per_type: value.per_type, quiet_start: value.quiet_start, quiet_end: value.quiet_end,
    })).data,
    onSuccess: (data) => queryClient.setQueryData(['notification-preferences'], data),
  });
  const setChannel = (type: NotificationType, channel: 'push' | 'in_app', enabled: boolean) => {
    save.reset();
    setValue((old) => ({ ...old, per_type: { ...old.per_type, [type]: { ...old.per_type[type], [channel]: enabled } } }));
  };
  return (
    <form className="space-y-4" onSubmit={(event) => { event.preventDefault(); save.mutate(); }}>
      <h2 className="text-lg font-semibold">Notification preferences</h2>
      <p className="text-sm text-[var(--text-muted)]">Quiet hours pause push messages. Your in-app choices still apply.</p>
      <div className="space-y-3">
        {(Object.keys(labels) as NotificationType[]).map((type) => (
          <fieldset key={type} disabled={save.isPending} className="flex flex-wrap items-center gap-4">
            <legend className="mb-1 text-sm font-medium">{labels[type]}</legend>
            {(['push', 'in_app'] as const).map((channel) => (
              <label key={channel} className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={value.per_type[type][channel]}
                  onChange={(event) => setChannel(type, channel, event.target.checked)} />
                {channel === 'push' ? 'Push' : 'In-app'}
              </label>
            ))}
          </fieldset>
        ))}
      </div>
      <fieldset disabled={save.isPending} className="flex flex-wrap gap-4">
        <legend className="mb-2 text-sm font-medium">Quiet hours · Asia/Dhaka</legend>
        <label className="text-sm">From
          <Input type="time" value={value.quiet_start?.slice(0, 5) ?? ''}
            onChange={(event) => { save.reset(); setValue({ ...value, quiet_start: event.target.value || null }); }} />
        </label>
        <label className="text-sm">Until
          <Input type="time" value={value.quiet_end?.slice(0, 5) ?? ''}
            onChange={(event) => { save.reset(); setValue({ ...value, quiet_end: event.target.value || null }); }} />
        </label>
      </fieldset>
      <p className="text-xs text-[var(--text-muted)]">Set both times, or clear both. Matching times disable quiet hours.</p>
      <Button type="submit" disabled={save.isPending}>{save.isPending ? 'Saving…' : 'Save preferences'}</Button>
      {save.isSuccess && <p role="status" className="text-sm">Preferences saved.</p>}
      {save.isError && <p role="alert" className="text-sm text-[var(--danger)]">{getErrorMessage(save.error, 'Could not save preferences.')}</p>}
    </form>
  );
}

export function NotificationPreferences() {
  const query = useQuery({ queryKey: ['notification-preferences'],
    queryFn: async () => (await api.get<Preferences>('/notifications/preferences')).data });
  return <section className="surface max-w-3xl p-5">
    {query.isPending && <p role="status">Loading preferences…</p>}
    {query.isError && <p role="alert">Could not load notification preferences.</p>}
    {query.data && <PreferencesForm initial={query.data} />}
  </section>;
}
