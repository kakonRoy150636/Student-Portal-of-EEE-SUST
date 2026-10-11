import React, { useState } from 'react';
import { Check, Copy } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { AnnouncementPermissions, CourseWorkspace } from '@/types/courseWorkspace';

const permissionKeys: Array<keyof AnnouncementPermissions> = ['can_manage', 'can_publish', 'can_edit', 'can_archive', 'can_pin'];

export function WorkspaceSettings({ workspace }: { workspace: CourseWorkspace }) {
  const [copied, setCopied] = useState(false);
  const copyId = async () => {
    try {
      await navigator.clipboard.writeText(workspace.offering_id);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };

  return (
    <section id="workspace-panel-settings" role="tabpanel" aria-labelledby="workspace-tab-settings" className="space-y-4">
      <div><p className="kicker">Workspace configuration</p><h2 className="mt-1 font-display text-lg font-semibold">Settings</h2><p className="mt-1 text-sm text-[var(--text-muted)]">Read-only course and permission details from the server.</p></div>
      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Offering details</CardTitle></CardHeader>
          <CardContent className="space-y-4 text-sm">
            <Detail label="Course code" value={workspace.course.course_code} />
            <Detail label="Semester" value={workspace.semester.title} />
            <Detail label="Target term" value={workspace.semester.target_term ?? 'Not configured'} />
            <Detail label="Status" value={<Badge variant={workspace.offering_status === 'published' ? 'success' : 'secondary'}>{workspace.offering_status}</Badge>} />
            <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[var(--border)] pt-3"><span className="text-[var(--text-muted)]">Offering ID</span><span className="flex items-center gap-2"><code className="max-w-[16rem] truncate rounded bg-[var(--surface-muted)] px-2 py-1 text-xs">{workspace.offering_id}</code><Button size="icon" variant="ghost" aria-label="Copy offering ID" onClick={() => void copyId}>{copied ? <Check className="h-4 w-4" aria-hidden="true" /> : <Copy className="h-4 w-4" aria-hidden="true" />}</Button></span></div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Announcement permissions</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {permissionKeys.map((key) => { const allowed = workspace.permissions[key]; return <div key={key} className="flex items-center justify-between gap-3 rounded-lg border border-[var(--border)] p-3"><span className="text-sm capitalize text-[var(--text-muted)]">{key.replace(/^can_/, '').replace(/_/g, ' ')}</span><Badge variant={allowed ? 'success' : 'secondary'}>{allowed ? 'Allowed' : 'Not available'}</Badge></div>; })}
            <p className="pt-2 text-sm text-[var(--text-muted)]">Editing permissions are supplied per announcement as well and can change with its lifecycle.</p>
          </CardContent>
        </Card>
      </div>
      <Card><CardHeader><CardTitle>Existing academic views</CardTitle></CardHeader><CardContent className="flex flex-wrap gap-3"><Link className="text-sm font-semibold text-[var(--accent-bright)] underline" to={`/resources`}>Resource hub</Link><Link className="text-sm font-semibold text-[var(--accent-bright)] underline" to={`/schedule?offeringId=${encodeURIComponent(workspace.offering_id)}`}>Schedule</Link><Link className="text-sm font-semibold text-[var(--accent-bright)] underline" to={`/attendance?offeringId=${encodeURIComponent(workspace.offering_id)}`}>Attendance</Link></CardContent></Card>
    </section>
  );
}

function Detail({ label, value }: { label: string; value: React.ReactNode }) {
  return <div className="flex items-center justify-between gap-3"><span className="text-[var(--text-muted)]">{label}</span><span className="text-right font-medium">{value}</span></div>;
}
